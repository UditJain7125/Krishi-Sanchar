from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import pickle
import pandas as pd
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

app = FastAPI()

# Allow the KrishiSanchar frontend (served from a different origin/port)
# to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://uditjain7125.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "fertilizer_model.pkl", "rb") as f:
    fertilizer_model = pickle.load(f)

with open(BASE_DIR / "label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)

with open(BASE_DIR / "feature_columns.pkl", "rb") as f:
    feature_columns = pickle.load(f)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2,
    max_output_tokens=500,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

prompt = ChatPromptTemplate.from_template("""
You are an agriculture expert.

Crop: {crop_type}
Soil Type: {soil_type}
Recommended Fertilizer: {fertilizer_name}

Respond ONLY with a valid JSON object, no markdown, no code fences, no extra text before or after. Use this exact structure:

{{
  "reason": "short plain sentence explaining why this fertilizer suits this crop and soil",
  "application_method": "short plain sentence on how to apply it",
  "precautions": "short plain sentence on precautions to take",
  "best_time": "short plain sentence on the best time to apply it"
}}

Keep each value simple, conversational, and free of bullet points, numbering, or markdown symbols like asterisks.
""")

chain = prompt | llm


class ModelInput(BaseModel):
    temperature: float
    humidity: float
    moisture: float
    Soil_type: str
    Crop_type: str
    nitrogen: float
    phosphorus: float
    potassium: float


class FertilizerResponse(BaseModel):
    recommended_fertilizer: str
    explanation: Any


@app.get("/")
def home():
    return {"message": "Fertilizer Recommendation API Running"}


@app.post("/Fertilizer_recommendation", response_model=FertilizerResponse)
def fertilizer_recommendation(data: ModelInput):
    raw = pd.DataFrame([{
        "Temperature": data.temperature,
        "Humidity": data.humidity,
        "Moisture": data.moisture,
        "Nitrogen": data.nitrogen,
        "Phosphorus": data.phosphorus,
        "Potassium": data.potassium,
        "Soil Type": data.Soil_type,
        "Crop Type": data.Crop_type,
    }])

    encoded = pd.get_dummies(raw, columns=["Soil Type", "Crop Type"])
    encoded = encoded.reindex(columns=feature_columns, fill_value=0)

    pred = fertilizer_model.predict(encoded)[0]
    fertilizer_name = label_encoder.inverse_transform([pred])[0]

    response = chain.invoke({
        "crop_type": data.Crop_type,
        "soil_type": data.Soil_type,
        "fertilizer_name": fertilizer_name,
    })

    raw_text = response.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        explanation = json.loads(raw_text)
    except json.JSONDecodeError:
        explanation = {"raw_response": raw_text}

    return {
        "recommended_fertilizer": fertilizer_name,
        "explanation": explanation,
    }