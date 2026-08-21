import json
import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


app = FastAPI(
    title="Smart Agriculture Market Analysis API",
    description="AGMARKNET + Gemini powered market analysis",
    version="1.1"
)

# Allow the KrishiSanchar frontend (served from a different origin/port)
# to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://uditjain7125.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Keys
MARKET_API_KEY = os.getenv("MARKETPRICE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# AGMARKNET API
BASE_URL = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)


# -----------------------------
# Requests retry configuration
# -----------------------------

session = requests.Session()

retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504
    ]
)

adapter = HTTPAdapter(
    max_retries=retry
)

session.mount(
    "https://",
    adapter
)

# AGMARKNET silently blocks/throttles requests carrying the default
# "python-requests/x.x" User-Agent. Spoofing a curl-like UA fixes it.
session.headers.update({
    "User-Agent": "curl/8.4.0"
})


# -----------------------------
# Gemini Model
# -----------------------------

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.2,
    max_output_tokens=400,
    google_api_key=GEMINI_API_KEY
)


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


# -----------------------------
# Simple in-memory TTL cache
# -----------------------------
# Prices don't change every second, so we cache per-crop responses
# for a short window to cut latency and avoid hammering AGMARKNET/Gemini.

CACHE_TTL_SECONDS = 20 * 60  # 20 minutes
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


# -----------------------------
# AGMARKNET fetch with pagination
# -----------------------------
# We deliberately do NOT rely on AGMARKNET's server-side
# filters[commodity] — it has proven unreliable (sometimes ignored,
# sometimes causes 400s/timeouts). Instead we page through batches
# and filter client-side, stopping early once we have enough matches
# or we run out of pages to try.

PAGE_SIZE = 200
MAX_PAGES = 5  # cap total AGMARKNET calls per request


def _fetch_records_for_crop(crop_name_lower: str) -> list[dict]:
    matches: list[dict] = []

    for page in range(MAX_PAGES):
        params = {
            "api-key": MARKET_API_KEY,
            "format": "json",
            "limit": PAGE_SIZE,
            "offset": page * PAGE_SIZE,
        }

        response = session.get(BASE_URL, params=params, timeout=20)

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Market API failed",
                    "status_code": response.status_code,
                    "details": response.text,
                },
            )

        batch = response.json().get("records", [])

        if not batch:
            # No more records to page through
            break

        matches.extend(
            r for r in batch
            if r.get("commodity", "").strip().lower() == crop_name_lower
        )

        if len(matches) >= 20:
            # Enough data to give a meaningful analysis; stop paging
            break

    return matches


# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "Smart Agriculture Market Analysis API Running"
    }


@app.get("/market-analysis/{crop}")
def market_analysis(crop: str):

    crop_name = crop.strip().title()
    cache_key = crop_name.lower()

    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    print("Searching crop:", crop_name)

    try:
        records = _fetch_records_for_crop(cache_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Market API connection failed",
                "details": str(e),
            },
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail={
                "crop": crop_name,
                "message": (
                    "No market data found for this crop in the current "
                    "batches searched. AGMARKNET only returns a slice of "
                    "all mandi records per request; try again later or "
                    "check the spelling of the crop name."
                ),
            },
        )

    # Trim each record down to only the fields that matter for pricing.
    # Used both as the LLM input and as the market_prices returned to
    # the client, so we drop commodity/variety/grade/arrival_date.
    trimmed = [
        {
            "state": r.get("state"),
            "district": r.get("district"),
            "market": r.get("market"),
            "min_price": r.get("min_price"),
            "max_price": r.get("max_price"),
            "modal_price": r.get("modal_price"),
        }
        for r in records
    ]

    prompt = f"""You are an agriculture market expert. Analyze the mandi
price data below for {crop_name}.

Market Data (JSON):
{trimmed}

Respond with ONLY a valid JSON object, no markdown, no code fences, no
preamble, no explanation outside the JSON. Use exactly these keys:

{{
  "price_range": "<lowest> - <highest> per quintal, e.g. '₹1000 - ₹2400'",
  "best_market": "<market name, state> - <price>",
  "worst_market": "<market name, state> - <price>",
  "advice": "<1-2 short, practical sentences for a farmer deciding where to sell, under 40 words>"
}}

Do not include any text before or after the JSON object.
"""

    try:
        result = llm.invoke(prompt)
        raw = _content_to_text(result.content).strip()

        # Gemini sometimes wraps JSON in ```json fences despite instructions;
        # strip those defensively before parsing.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        # Gemini occasionally emits a trailing comma before a closing
        # } or ] despite instructions not to — that's invalid JSON and
        # makes json.loads() below raise, so strip it defensively.
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)

        ai_analysis = json.loads(raw)

    except json.JSONDecodeError:
        # Fall back to raw text so the client still gets something usable
        ai_analysis = {
            "price_range": None,
            "best_market": None,
            "worst_market": None,
            "advice": raw,
        }
    except Exception as e:
        ai_analysis = {
            "price_range": None,
            "best_market": None,
            "worst_market": None,
            "advice": "Gemini analysis failed: " + str(e),
        }

    payload = {
        "crop": crop_name,
        "market_prices": trimmed,
        "analysis": ai_analysis,
    }

    _cache_set(cache_key, payload)

    return {**payload, "cached": False}