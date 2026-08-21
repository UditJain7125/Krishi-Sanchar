import os
import json
import re
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

app = FastAPI()

# Allow the frontend (served from a different origin/port, e.g. a static
# file server on 127.0.0.1:5500 or opened via file://) to call this API.
# Tighten allow_origins to your actual frontend origin(s) in production.
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


@app.get("/weather/{city}")
def weather(city: str):

    params = {
        "q": city,
        "appid": weather_api_key,
        "units": "metric"
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        # Surface the real status code (e.g. 404 for an unknown city) instead
        # of always returning 200 with an "error" body, so the frontend's
        # res.ok check works correctly.
        detail = response.json()
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()

    # Collect 5-day forecast
    forecasts = []

    for item in data["list"]:
        forecasts.append({
            "date": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "weather": item["weather"][0]["description"],
            "wind_speed": item["wind"]["speed"],
            "rain": item.get("rain", {}).get("3h", 0)
        })


    prompt = f"""
You are an expert agriculture advisor.

5 Day Weather Forecast for {city}:

{json.dumps(forecasts, indent=2)}

Analyze the weather and give farming advice.

Return JSON only:

{{
  "irrigation":"",
  "fertilizer":"",
  "pesticide":"",
  "crop_care":""
}}
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            google_api_key=gemini_api_key,
            temperature=0
        )

        result = llm.invoke(prompt)

        ai_text = _content_to_text(result.content)
        ai_text = re.sub(r"```json|```", "", ai_text).strip()

        try:
            ai_advice = json.loads(ai_text)
        except Exception:
            # Keep the shape consistent for the frontend even if the model
            # didn't return valid JSON — fall back to a single-field object
            # instead of a bare string.
            ai_advice = {
                "irrigation": ai_text,
                "fertilizer": "",
                "pesticide": "",
                "crop_care": ""
            }

        return {
            "city": city,
            "forecast": forecasts,
            "ai_advice": ai_advice
        }


    except Exception as e:
        return {
            "error": str(e)
        }