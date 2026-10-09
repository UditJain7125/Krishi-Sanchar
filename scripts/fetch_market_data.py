"""
fetch_market_data.py
--------------------
Fetches mandi commodity price records from the AGMARKNET open dataset
(data.gov.in) and upserts them into the market_prices table in the
KrishiSanchar PostgreSQL (Neon) database.

Run daily via GitHub Actions (.github/workflows/fetch_market_data.yml).
GitHub's runner IPs (Azure) are not blocked by data.gov.in — unlike
Render's AWS IPs which get Connection Refused.

Environment variables required (set as GitHub Secrets):
    DATABASE_URL          — Neon PostgreSQL connection string
    MARKETPRICE_API_KEY   — data.gov.in API key
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

DATABASE_URL     = os.getenv("DATABASE_URL", "")
MARKET_API_KEY   = os.getenv("MARKETPRICE_API_KEY", "")
AGMARKNET_URL    = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)

# How many records to pull per run (each page = 200 records)
PAGE_SIZE  = 200
MAX_PAGES  = 15   # 15 × 200 = up to 3 000 records per daily run

# ── DB setup ──────────────────────────────────────────────────────────────────

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.", file=sys.stderr)
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]

engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"connect_timeout": 15})
Session = sessionmaker(bind=engine)

# Ensure table exists (mirrors Database.py without importing the whole auth module)
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS market_prices (
            id          SERIAL PRIMARY KEY,
            commodity   VARCHAR(100) NOT NULL,
            state       VARCHAR(100),
            district    VARCHAR(100),
            market      VARCHAR(100),
            min_price   VARCHAR(30),
            max_price   VARCHAR(30),
            modal_price VARCHAR(30),
            fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_market_prices_commodity
            ON market_prices (commodity);
        CREATE INDEX IF NOT EXISTS ix_market_prices_fetched_at
            ON market_prices (fetched_at);
    """))
    conn.commit()

# ── Fetch from AGMARKNET ──────────────────────────────────────────────────────

session_http = requests.Session()
session_http.headers.update({"User-Agent": "curl/8.4.0"})

all_records: list[dict] = []
print(f"Fetching up to {MAX_PAGES} pages from AGMARKNET …")

for page in range(MAX_PAGES):
    params = {
        "api-key": MARKET_API_KEY,
        "format":  "json",
        "limit":   PAGE_SIZE,
        "offset":  page * PAGE_SIZE,
    }
    try:
        resp = session_http.get(AGMARKNET_URL, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        print(f"  Page {page}: fetch failed — {exc}")
        break

    batch = resp.json().get("records", [])
    if not batch:
        print(f"  Page {page}: no more records, stopping.")
        break

    all_records.extend(batch)
    print(f"  Page {page}: +{len(batch)} records (total {len(all_records)})")
    time.sleep(0.5)   # be polite to the government API

print(f"Fetched {len(all_records)} records total.")

if not all_records:
    print("Nothing to store — exiting.")
    sys.exit(0)

# ── Store in PostgreSQL ───────────────────────────────────────────────────────
# Replace today's data: delete rows older than 2 days, then insert fresh ones.

now = datetime.now(timezone.utc)

db = Session()
try:
    # Remove stale data (keep last 2 days as a safety buffer)
    db.execute(text(
        "DELETE FROM market_prices WHERE fetched_at < NOW() - INTERVAL '2 days'"
    ))

    rows_inserted = 0
    for r in all_records:
        commodity = (r.get("commodity") or "").strip()
        if not commodity:
            continue
        db.execute(text("""
            INSERT INTO market_prices
                (commodity, state, district, market,
                 min_price, max_price, modal_price, fetched_at)
            VALUES
                (:commodity, :state, :district, :market,
                 :min_price, :max_price, :modal_price, :fetched_at)
        """), {
            "commodity":   commodity,
            "state":       (r.get("state")       or "").strip() or None,
            "district":    (r.get("district")    or "").strip() or None,
            "market":      (r.get("market")      or "").strip() or None,
            "min_price":   (r.get("min_price")   or "").strip() or None,
            "max_price":   (r.get("max_price")   or "").strip() or None,
            "modal_price": (r.get("modal_price") or "").strip() or None,
            "fetched_at":  now,
        })
        rows_inserted += 1

    db.commit()
    print(f"✅  Stored {rows_inserted} rows in market_prices.")
except Exception as exc:
    db.rollback()
    print(f"ERROR storing data: {exc}", file=sys.stderr)
    sys.exit(1)
finally:
    db.close()
