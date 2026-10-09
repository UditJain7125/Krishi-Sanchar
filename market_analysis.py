"""
market_analysis.py  —  KrishiSanchar Market Analysis Service
-------------------------------------------------------------
Reads mandi commodity price records from the PostgreSQL (Neon) database
(populated daily by the GitHub Actions workflow fetch_market_data.yml)
instead of hitting data.gov.in at request-time.

This eliminates two failure modes that plagued the original design:
  1. data.gov.in blocking Render's AWS IP range (Connection Refused)
  2. data.gov.in downtime / intermittent unavailability

Gemini still provides the AI analysis (price range, best/worst market,
farmer advice) — only the raw price data source has changed.

Environment variables (set in Render → Environment):
    DATABASE_URL    — Neon PostgreSQL connection string
    GEMINI_API_KEY  — Google Gemini API key
"""

import json
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart Agriculture Market Analysis API",
    description="PostgreSQL-backed mandi prices + Gemini AI analysis",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://uditjain7125.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DATABASE_URL   = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Normalise URL scheme for SQLAlchemy / psycopg2
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]

# ── Database engine ───────────────────────────────────────────────────────────

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 15},
)

# ── Gemini LLM ────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.2,
    max_output_tokens=400,
    google_api_key=GEMINI_API_KEY
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

CACHE_TTL_SECONDS = 20 * 60   # 20 minutes
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


# ── DB query ──────────────────────────────────────────────────────────────────

def _fetch_from_db(crop_name_lower: str) -> list[dict]:
    """Return up to 30 market_prices rows for the given commodity."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT state, district, market, min_price, max_price, modal_price
                FROM   market_prices
                WHERE  LOWER(commodity) = :crop
                ORDER  BY fetched_at DESC
                LIMIT  30
            """), {"crop": crop_name_lower}).fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database unavailable",
                "details": str(exc),
            },
        )

    return [
        {
            "state":       r.state,
            "district":    r.district,
            "market":      r.market,
            "min_price":   r.min_price,
            "max_price":   r.max_price,
            "modal_price": r.modal_price,
        }
        for r in rows
    ]


def _db_last_updated() -> Optional[str]:
    """Return the ISO timestamp of the most recent fetch, or None."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT MAX(fetched_at) FROM market_prices")
            ).fetchone()
            if row and row[0]:
                return row[0].strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        pass
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    last = _db_last_updated()
    return {
        "message": "Smart Agriculture Market Analysis API v2 Running",
        "data_source": "PostgreSQL (updated daily via GitHub Actions)",
        "last_updated": last or "No data fetched yet",
    }


@app.get("/market-analysis/{crop}")
def market_analysis(crop: str):

    crop_name      = crop.strip().title()
    cache_key      = crop_name.lower()

    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    print("Querying DB for crop:", crop_name)

    records = _fetch_from_db(cache_key)

    if not records:
        raise HTTPException(
            status_code=404,
            detail={
                "crop": crop_name,
                "message": (
                    f'No market data found for "{crop_name}". '
                    "Price data is refreshed daily — the crop name may be "
                    "slightly different in the AGMARKNET dataset (e.g. "
                    '"Rice" vs "Paddy", "Groundnut" vs "Ground Nuts"). '
                    "Try an alternate spelling or check back tomorrow."
                ),
            },
        )

    # ── Gemini analysis ───────────────────────────────────────────────────────

    prompt = f"""You are an agriculture market expert. Analyze the mandi
price data below for {crop_name}.

Market Data (JSON):
{records}

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

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        # Remove trailing commas before } or ]
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)

        ai_analysis = json.loads(raw)

    except json.JSONDecodeError:
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

    last_updated = _db_last_updated()

    payload = {
        "crop":         crop_name,
        "market_prices": records,
        "analysis":     ai_analysis,
        "last_updated": last_updated,
    }

    _cache_set(cache_key, payload)
    return {**payload, "cached": False}