import os
import json
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

app = FastAPI(
    title="Smart Agriculture Weather Service API",
    description="Hyperlocal weather forecasting + Gemini AI agricultural advisory",
    version="2.0",
)

# Allow the frontend (served from GitHub Pages) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://uditjain7125.github.io"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

weather_api_key = os.getenv("OPENWEATHER_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

# ── Gemini LLM ────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=gemini_api_key,
    temperature=0,
    max_output_tokens=400,
)


def _content_to_text(content) -> str:
    """Normalise Gemini response content (string or list of parts)."""
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


# ── Simple in-memory TTL cache ────────────────────────────────────────────────
CACHE_TTL_SECONDS = 30 * 60  # 30 minutes cache per city
_cache: dict[str, dict] = {}


def _cache_get(key: str) -> Optional[dict]:
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return entry["data"]


def _cache_set(key: str, data: dict) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "KrishiSanchar Weather Service API Running"}


@app.get("/weather/{city}")
def weather(city: str):
    clean_city = city.strip()
    cache_key = clean_city.lower()

    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    params = {
        "q": clean_city,
        "appid": weather_api_key,
        "units": "metric",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
    except Exception as exc:
        raise HTTPException(
            status_code=504,
            detail={"error": "Could not reach weather data provider", "details": str(exc)},
        )

    if response.status_code != 200:
        detail = response.json()
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()

    # Collect 5-day forecast
    forecasts = []
    for item in data.get("list", []):
        forecasts.append({
            "date": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "weather": item["weather"][0]["description"],
            "wind_speed": item["wind"]["speed"],
            "rain": item.get("rain", {}).get("3h", 0),
        })

    prompt = f"""You are an expert agriculture advisor.

5 Day Weather Forecast for {clean_city}:
{json.dumps(forecasts, indent=2)}

Analyze the weather and give farming advice.
Respond with ONLY valid JSON, no markdown, no code fences:

{{
  "irrigation": "practical advice for irrigation based on rain and humidity",
  "fertilizer": "advice for fertilizer application considering rain and wind",
  "pesticide": "advice for pesticide spray considering weather conditions",
  "crop_care": "general crop care advice for these weather conditions"
}}
"""

    try:
        result = llm.invoke(prompt)
        ai_text = _content_to_text(result.content)
        ai_text = re.sub(r"```json|```", "", ai_text).strip()

        try:
            ai_advice = json.loads(ai_text)
        except Exception:
            ai_advice = {
                "irrigation": ai_text,
                "fertilizer": "",
                "pesticide": "",
                "crop_care": "",
            }

        payload = {
            "city": clean_city,
            "forecast": forecasts,
            "ai_advice": ai_advice,
        }

        _cache_set(cache_key, payload)
        return {**payload, "cached": False}

    except Exception as e:
        return {
            "city": clean_city,
            "forecast": forecasts,
            "ai_advice": {
                "irrigation": "Keep monitoring soil moisture.",
                "fertilizer": "Avoid application during heavy winds or rains.",
                "pesticide": "Do not spray if rain is anticipated within 6 hours.",
                "crop_care": "Maintain regular field drainage.",
            },
            "error": str(e),
            "cached": False,
        }