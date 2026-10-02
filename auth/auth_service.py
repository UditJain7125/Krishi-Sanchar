"""
KrishiSanchar auth service: signup, login, profile ("/me") and activity
history, backed by PostgreSQL.

Run locally with:
    uvicorn auth_service:app --port 8007
"""

import logging
import os
import re
import secrets
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from Database import FarmerProfile, HistoryEntry, get_db, init_db


load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth_service")


# -----------------------------
# Config
# -----------------------------

def _clean(value: str) -> str:
    """Trim whitespace and quote marks accidentally pasted around a value."""
    return value.strip().strip('"').strip("'").strip()


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value or not _clean(value):
        raise RuntimeError(
            f"{name} is missing. Set it in the Render dashboard "
            "(Environment tab) or in a local .env file."
        )

    return _clean(value)


JWT_SECRET = _require_env("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://uditjain7125.github.io"
    ).split(",")
    if origin.strip()
]


# -----------------------------
# Helpers: identifiers, passwords, tokens
# -----------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?\d{10,15}$")
_ID_ALPHABET = string.ascii_uppercase + string.digits


def normalize_identifier(raw: str) -> Optional[str]:
    """Return a canonical email or phone number."""
    value = (raw or "").strip()

    if "@" in value:
        value = value.lower()
        return (
            value
            if len(value) <= 254 and _EMAIL_RE.match(value)
            else None
        )

    phone = re.sub(r"[\s\-()]", "", value)

    return phone if _PHONE_RE.match(phone) else None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except ValueError:
        return False


# Used when the account doesn't exist so that incorrect
# usernames and passwords take approximately the same time.
_DUMMY_HASH = hash_password("not-a-real-password")


def new_farmer_id() -> str:
    return "KS-" + "".join(
        secrets.choice(_ID_ALPHABET)
        for _ in range(5)
    )


def create_token(farmer_id: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": farmer_id,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def profile_to_dict(p: FarmerProfile) -> dict:
    """Public view of a profile. Never includes the password hash."""

    return {
        "farmer_id": p.farmer_id,
        "full_name": p.full_name,
        "identifier": p.user_id,
        "location": p.location,
        "land_area_acres": p.land_area_acres,
        "soil_type": p.soil_type,
        "primary_crop": p.primary_crop,
        "irrigation_source": p.irrigation_source,
        "photo_url": p.photo_url,
        "is_registered": p.is_registered,
        "aadhaar_link": p.aadhaar_link,
        "created_at": (
            p.created_at.isoformat()
            if p.created_at
            else None
        ),
    }


# -----------------------------
# Request models
# -----------------------------

class SignupRequest(BaseModel):
    full_name: str
    identifier: str
    password: str
    location: Optional[str] = None
    land_area_acres: Optional[float] = None
    primary_crop: Optional[str] = None
    soil_type: Optional[str] = None
    irrigation_source: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        v = v.strip()

        if not 2 <= len(v) <= 120:
            raise ValueError(
                "Full name must be between 2 and 120 characters."
            )

        return v

    @field_validator("identifier")
    @classmethod
    def _check_identifier(cls, v: str) -> str:
        normalized = normalize_identifier(v)

        if normalized is None:
            raise ValueError(
                "Enter a valid email address or phone number."
            )

        return normalized

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError(
                "Password must be at least 8 characters."
            )

        if len(v.encode("utf-8")) > 72:
            raise ValueError(
                "Password is too long (maximum 72 bytes)."
            )

        return v

    @field_validator(
        "location",
        "primary_crop",
        "soil_type",
        "irrigation_source",
    )
    @classmethod
    def _check_optional_text(
        cls,
        v: Optional[str]
    ) -> Optional[str]:

        if v is None:
            return None

        v = v.strip()

        if not v:
            return None

        if len(v) > 255:
            raise ValueError(
                "Text field is too long (maximum 255 characters)."
            )

        return v

    @field_validator("land_area_acres")
    @classmethod
    def _check_area(
        cls,
        v: Optional[float]
    ) -> Optional[float]:

        if v is None:
            return None

        if not 0 <= v <= 100000:
            raise ValueError(
                "Land area must be between 0 and 100000 acres."
            )

        return v


class LoginRequest(BaseModel):
    identifier: str
    password: str


# -----------------------------
# App
# -----------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="KrishiSanchar Auth API",
    description="Signup, login and farmer profile (PostgreSQL + JWT)",
    version="1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Error handlers
# -----------------------------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
):
    """Return validation problems as one readable string."""

    first = exc.errors()[0]

    message = str(
        first.get("msg", "Invalid input")
    )

    if first.get("type") == "value_error":
        message = message.removeprefix("Value error, ")
    else:
        field = ".".join(
            str(part)
            for part in first.get("loc", [])
            if part != "body"
        )

        message = (
            f"{field}: {message}"
            if field
            else message
        )

    return JSONResponse(
        status_code=422,
        content={"detail": message},
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(
    request: Request,
    exc: SQLAlchemyError
):
    log.error("Database error: %s", exc)

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "The database is unavailable or waking up. "
                "Please try again in a few seconds."
            )
        },
    )


# -----------------------------
# Authentication
# -----------------------------

# This creates the security scheme used by Swagger.
# Swagger will now display the Authorize 🔒 button.
bearer_scheme = HTTPBearer()


def get_current_profile(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> FarmerProfile:

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
        )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token.",
        )

    farmer_id = payload.get("sub")

    profile = None

    if farmer_id:
        profile = db.scalar(
            select(FarmerProfile).where(
                FarmerProfile.farmer_id == farmer_id
            )
        )

    if profile is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token.",
        )

    return profile


# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "KrishiSanchar Auth API Running"
    }


@app.post("/signup", status_code=201)
def signup(
    body: SignupRequest,
    db: Session = Depends(get_db)
):
    def already_exists() -> bool:
        return (
            db.scalar(
                select(FarmerProfile.id).where(
                    FarmerProfile.user_id == body.identifier
                )
            )
            is not None
        )

    if already_exists():
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email/phone "
                "already exists."
            ),
        )

    password_hash = hash_password(body.password)

    for _ in range(5):

        profile = FarmerProfile(
            farmer_id=new_farmer_id(),
            user_id=body.identifier,
            full_name=body.full_name,
            password_hash=password_hash,
            location=body.location,
            land_area_acres=body.land_area_acres,
            soil_type=body.soil_type,
            primary_crop=body.primary_crop,
            irrigation_source=body.irrigation_source,
        )

        db.add(profile)

        try:
            db.commit()

        except IntegrityError:
            db.rollback()

            if already_exists():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "An account with this email/phone "
                        "already exists."
                    ),
                )

            continue

        return {
            "access_token": create_token(
                profile.farmer_id
            ),
            "token_type": "bearer",
            "farmer_id": profile.farmer_id,
        }

    raise HTTPException(
        status_code=500,
        detail=(
            "Could not create the account. "
            "Please try again."
        ),
    )


@app.post("/login")
def login(
    body: LoginRequest,
    db: Session = Depends(get_db)
):
    invalid = HTTPException(
        status_code=401,
        detail="Invalid email/phone or password.",
    )

    identifier = normalize_identifier(
        body.identifier
    )

    profile = None

    if identifier:
        profile = db.scalar(
            select(FarmerProfile).where(
                FarmerProfile.user_id == identifier
            )
        )

    password_ok = verify_password(
        body.password,
        profile.password_hash
        if profile
        else _DUMMY_HASH,
    )

    if profile is None or not password_ok:
        raise invalid

    return {
        "access_token": create_token(
            profile.farmer_id
        ),
        "token_type": "bearer",
        "farmer_id": profile.farmer_id,
    }


@app.get("/me")
def me(
    profile: FarmerProfile = Depends(
        get_current_profile
    )
):
    return profile_to_dict(profile)


# -----------------------------
# History
# -----------------------------

_VALID_ACTIVITY_TYPES = {
    "Disease Detection",
    "Crop Recommendation",
    "Fertilizer Recommendation",
    "Weather Check",
    "Market Analysis",
    "Yield Prediction",
    "AI Assistant",
}


class HistoryCreateRequest(BaseModel):
    activity_type: str
    input_summary: str
    result_summary: str

    @field_validator("activity_type")
    @classmethod
    def _check_activity_type(
        cls,
        v: str
    ) -> str:

        if v not in _VALID_ACTIVITY_TYPES:
            raise ValueError(
                "activity_type must be one of: "
                + ", ".join(
                    sorted(_VALID_ACTIVITY_TYPES)
                )
            )

        return v

    @field_validator(
        "input_summary",
        "result_summary",
    )
    @classmethod
    def _check_text(
        cls,
        v: str
    ) -> str:

        v = v.strip()

        if not v:
            raise ValueError(
                "This field cannot be empty."
            )

        if len(v) > 2000:
            raise ValueError(
                "This field is too long "
                "(maximum 2000 characters)."
            )

        return v


def history_entry_to_dict(
    entry: HistoryEntry
) -> dict:

    return {
        "id": entry.id,
        "activity_type": entry.activity_type,
        "input_summary": entry.input_summary,
        "result_summary": entry.result_summary,
        "created_at": (
            entry.created_at.isoformat()
            if entry.created_at
            else None
        ),
    }


@app.post("/history", status_code=201)
def create_history_entry(
    body: HistoryCreateRequest,
    profile: FarmerProfile = Depends(
        get_current_profile
    ),
    db: Session = Depends(get_db),
):
    entry = HistoryEntry(
        farmer_id=profile.farmer_id,
        activity_type=body.activity_type,
        input_summary=body.input_summary,
        result_summary=body.result_summary,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return history_entry_to_dict(entry)


@app.get("/history")
def list_history(
    profile: FarmerProfile = Depends(
        get_current_profile
    ),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    limit = max(1, min(limit, 200))

    rows = db.scalars(
        select(HistoryEntry)
        .where(
            HistoryEntry.farmer_id
            == profile.farmer_id
        )
        .order_by(
            HistoryEntry.created_at.desc()
        )
        .limit(limit)
    ).all()

    return [
        history_entry_to_dict(row)
        for row in rows
    ]

