from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import pandas as pd
import re
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

with open(BASE_DIR / "model.pkl", "rb") as f:
    crop_model = pickle.load(f)

with open(BASE_DIR / "min_max_scaler.pkl", "rb") as f:
    min_max_scaler = pickle.load(f)

llm_primary = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.2,
    max_output_tokens=500,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

llm_fallback = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2,
    max_output_tokens=500,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

prompt = ChatPromptTemplate.from_template("""
You are an agriculture expert.

Based on the given crop and environmental conditions, return ONLY valid JSON.

Crop: {crop}
Nitrogen: {N}
Phosphorus: {P}
Potassium: {K}
Temperature: {temperature}°C
Humidity: {humidity}%
pH: {ph}
Rainfall: {rainfall} mm

Return exactly in this format:

{{
  "reason": "...",
  "fertilizer": "...",
  "irrigation": "...",
  "diseases": "...",
  "yield": "...",
  "season": "...",
  "additional_tips": [
    "...",
    "...",
    "..."
  ]
}}

Rules:
- Return ONLY valid JSON.
- Do not use markdown.
- Do not wrap the JSON inside ```json.
- Do not add any explanation before or after the JSON.
- Keep responses practical and concise.
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
    N: int
    P: int
    K: int
    temperature: float
    humidity: float
    ph: float
    rainfall: float

crop_dict = {
    1: "Rice",
    2: "Maize",
    3: "Chickpea",
    4: "Kidneybeans",
    5: "Pigeonpeas",
    6: "Mothbeans",
    7: "Mungbean",
    8: "Blackgram",
    9: "Lentil",
    10: "Pomegranate",
    11: "Banana",
    12: "Mango",
    13: "Grapes",
    14: "Watermelon",
    15: "Muskmelon",
    16: "Apple",
    17: "Orange",
    18: "Papaya",
    19: "Coconut",
    20: "Cotton",
    21: "Jute",
    22: "Coffee"
}

@app.get("/")
def home():
    return {
        "message": "Crop Recommendation API Running"
    }

@app.post("/crop_recommendation")
def crop_recommendation(data: ModelInput):
    df = pd.DataFrame(
        [[
            data.N,
            data.P,
            data.K,
            data.temperature,
            data.humidity,
            data.ph,
            data.rainfall
        ]],
        columns=[
            "N",
            "P",
            "K",
            "temperature",
            "humidity",
            "ph",
            "rainfall"
        ]
    )

    scaled = min_max_scaler.transform(df)
    prediction = crop_model.predict(scaled)
    crop = crop_dict[int(prediction[0])]

    advice = None
    for active_chain in (chain_primary, chain_fallback):
        try:
            result = active_chain.invoke({
                "crop": crop,
                **data.model_dump()
            })
            content = _content_to_text(result.content).strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:].strip()
            content = re.sub(r",(\s*[}\]])", r"\1", content)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and parsed.get("reason"):
                advice = parsed
                break
        except Exception:
            continue

    # Bulletproof fallback if Gemini is experiencing high demand (503)
    if not advice:
        advice = {
            "reason": f"Optimal crop choice for your soil parameters (N:{data.N}, P:{data.P}, K:{data.K}, pH:{data.ph}) and local weather conditions.",
            "fertilizer": "Apply balanced N-P-K fertilizer as per local soil test recommendations during basal dressing.",
            "irrigation": "Maintain adequate soil moisture during vegetative and flowering stages, avoiding excessive waterlogging.",
            "diseases": f"Monitor regularly for common foliar diseases and pests suitable to {crop.title()}.",
            "yield": f"High yield potential under recommended cultural practices.",
            "season": "Suited for current seasonal and climatic parameters.",
            "additional_tips": [
                "Ensure proper field leveling and drainage to prevent water stagnation.",
                "Use certified disease-free seeds from trusted agricultural centers.",
                "Practice timely weed management within the first 30 days of sowing."
            ]
        }

    return {
        "crop": crop,
        "advice": advice
    }