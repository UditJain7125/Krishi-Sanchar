"""
Shared PostgreSQL setup for KrishiSanchar's auth service: the SQLAlchemy
engine/session, and the two tables (farmer_profiles, history_entries).

auth_service.py imports everything it needs from here instead of defining
the database layer inline. Keeping this in its own file means any future
service (or a script/notebook) can reuse the exact same models without
duplicating table definitions.

Environment variables (set in Render -> Environment, never in git):
    DATABASE_URL     PostgreSQL connection string (e.g. from Neon)
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()

log = logging.getLogger("database")


# -----------------------------
# Config
# -----------------------------

def _clean(value: str) -> str:
    """Trim whitespace and any quote marks accidentally pasted around a
    value (this has bitten the GEMINI_API_KEY env var before)."""
    return value.strip().strip('"').strip("'").strip()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not _clean(value):
        raise RuntimeError(
            f"{name} is missing. Set it in the Render dashboard "
            "(Environment tab) or in a local .env file."
        )
    return _clean(value)


DATABASE_URL = _require_env("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    # Some providers (Neon included) hand out the short "postgres://"
    # scheme; SQLAlchemy only accepts "postgresql://".
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if DATABASE_URL.startswith("postgresql://"):
    # SQLAlchemy 2.1 changed the default driver for "postgresql://" from
    # psycopg2 to psycopg 3. Name the driver explicitly so it always
    # matches what requirements.txt installs (psycopg2-binary).
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]


# -----------------------------
# Engine / session
# -----------------------------

_engine_kwargs = {
    "pool_pre_ping": True,  # drop dead connections (Neon suspends idle compute)
    "pool_recycle": 300,
}
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs["connect_args"] = {"connect_timeout": 15}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# -----------------------------
# Models
# -----------------------------

class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    # "Email or Phone Number" from the signup form (normalised, unique)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(100))

    is_registered: Mapped[bool] = mapped_column(Boolean, default=True)
    aadhaar_link: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    land_area_acres: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    primary_crop: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    irrigation_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HistoryEntry(Base):
    """One row per action a farmer takes on the platform. Matches the
    "History" page's table columns directly: Date, Activity Type, Input
    Parameters, Result/Action.

    input_summary and result_summary are stored as ready-to-display text
    rather than structured JSON, because each activity type's inputs/
    results look completely different (an uploaded image name vs. N-P-K
    numbers vs. a fertilizer's kg breakdown) — the calling service builds
    the human-readable string once, at the moment of a successful
    prediction, and this table just stores it.
    """
    __tablename__ = "history_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("farmer_profiles.farmer_id"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(60))
    input_summary: Mapped[str] = mapped_column(Text)
    result_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class MarketPrice(Base):
    """One row per mandi price record fetched from AGMARKNET (data.gov.in).

    The GitHub Actions workflow (fetch_market_data.yml) populates this table
    daily. The market_analysis.py service reads from here at request time
    instead of hitting data.gov.in live — eliminating the IP-block and
    uptime problems with the government API.
    """
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    min_price: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    max_price: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    modal_price: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )



# -----------------------------
# Helpers
# -----------------------------

def init_db() -> None:
    """Create tables if they don't exist. Retries a few times because a
    suspended Neon database can take several seconds to wake up."""
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(engine)
            log.info("Database ready.")
            return
        except SQLAlchemyError as exc:
            log.warning("Database not ready (attempt %d/5): %s", attempt, exc)
            time.sleep(3)
    log.error("Could not reach the database at startup; requests will return 503 until it is reachable.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
