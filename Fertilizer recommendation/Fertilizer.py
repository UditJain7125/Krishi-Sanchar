from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import pickle
import pandas as pd
import os
import json
import re
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

llm_primary = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.2,
    max_output_tokens=500,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

llm_fallback = ChatGoogleGenerativeAI(
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

chain_primary = prompt | llm_primary
chain_fallback = prompt | llm_fallback


def _content_to_text(content) -> str:
    """Newer Gemini models (3.x) can return .content as a list of parts
    instead of a plain string; older ones return a plain string. Normalize
    either shape to a single string before json.loads()/regex/etc."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or "")
        return "".join(parts)
    return "" if content is None else str(content)


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

    explanation = None
    for active_chain in (chain_primary, chain_fallback):
        try:
            response = active_chain.invoke({
                "crop_type": data.Crop_type,
                "soil_type": data.Soil_type,
                "fertilizer_name": fertilizer_name,
            })

            raw_text = _content_to_text(response.content).strip()
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            raw_text = re.sub(r",(\s*[}\]])", r"\1", raw_text)
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict) and parsed.get("reason"):
                explanation = parsed
                break
        except Exception:
            continue

    if not explanation:
        explanation = {
            "reason": f"{fertilizer_name} provides the targeted nutrient balance required for {data.Crop_type} in {data.Soil_type} soil conditions.",
            "application_method": "Distribute uniformly around the crop root zone followed by normal irrigation.",
            "precautions": "Avoid direct contact with plant stems and do not apply during extreme midday heat.",
            "best_time": "Apply during early morning or evening hours in active growth phases."
        }

    return {
        "recommended_fertilizer": fertilizer_name,
        "explanation": explanation,
    }