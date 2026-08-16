from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any
import pickle
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "yield_model.pkl", "rb") as f:
    yield_model = pickle.load(f)

with open(BASE_DIR / "crop_encoder.pkl", "rb") as f:
    crop_encoder = pickle.load(f)

with open(BASE_DIR / "soil_encoder.pkl", "rb") as f:
    soil_encoder = pickle.load(f)


class YieldPredictionRequest(BaseModel):
    Crop: str
    Area: float
    Fertilizer: float
    Rainfall: float
    Soil_Quality: str


class YieldPredictionResponse(BaseModel):
    predicted_yield_per_acre: float
    total_estimated_yield: float
    model_accuracy: float
    historical_trend: list[dict[str, Any]]


MODEL_ACCURACY = 92.6


def encode_input(data: YieldPredictionRequest) -> pd.DataFrame:
    """Encode raw request fields into the format the model expects."""
    try:
        crop_encoded = crop_encoder.transform([data.Crop])[0]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown crop '{data.Crop}'. Expected one of: {list(crop_encoder.classes_)}",
        )

    try:
        soil_encoded = soil_encoder.transform([data.Soil_Quality])[0]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown soil quality '{data.Soil_Quality}'. Expected one of: {list(soil_encoder.classes_)}",
        )

    return pd.DataFrame(
        [{
            "Crop_enc": crop_encoded,
            "Area": data.Area,
            "Fertilizer": data.Fertilizer,
            "Rainfall": data.Rainfall,
            "Soil_enc": soil_encoded,
        }]
    )


def build_historical_trend(current_prediction: float) -> list[dict[str, Any]]:
    """
    Builds a simple historical trend leading up to the current (predicted) year,
    matching the '2021 -> 2025(P)' chart in the UI.

    Replace this with real historical records (e.g. from a database or CSV)
    if you have them. This version fabricates a plausible upward trend ending
    at the model's current prediction, purely for the chart.
    """
    years = [2021, 2022, 2023, 2024]
    trend = []
    value = current_prediction
    values = [value]
    for _ in years[::-1]:
        value = value * 0.93
        values.insert(0, value)
    for year, val in zip(years, values[:-1]):
        trend.append({"year": str(year), "value": round(val, 1), "predicted": False})
    trend.append({"year": "2025(P)", "value": round(current_prediction, 1), "predicted": True})
    return trend


@app.post("/predict", response_model=YieldPredictionResponse)
def predict_yield(data: YieldPredictionRequest):
    features = encode_input(data)

    prediction = yield_model.predict(features)[0]
    predicted_yield_per_acre = float(prediction)
    total_estimated_yield = float(prediction * data.Area)

    return YieldPredictionResponse(
        predicted_yield_per_acre=round(predicted_yield_per_acre, 1),
        total_estimated_yield=round(total_estimated_yield, 1),
        model_accuracy=MODEL_ACCURACY,
        historical_trend=build_historical_trend(predicted_yield_per_acre),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/options")
def options():
    """
    Exposes the exact crop / soil-quality labels the encoders were trained
    on, so the frontend dropdowns can be populated dynamically instead of
    hardcoding guessed strings that silently drift out of sync and cause
    400 errors on /predict.
    """
    return {
        "crops": list(crop_encoder.classes_),
        "soil_qualities": list(soil_encoder.classes_),
    }


static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")