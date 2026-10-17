import base64
import io
import json
import os
import re
from typing import Optional

import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
from ai_edge_litert.interpreter import Interpreter

load_dotenv()

app = FastAPI(
    title="Plant Disease Detection API",
    description="CNN (trained in plant_disease_detection.ipynb) + Gemini powered leaf diagnosis",
    version="1.0",
)

# Allow the KrishiSanchar frontend (served from a different origin/port)
# to call this API from the browser — same pattern as market_analysis.py
# and weather_service.py.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://uditjain7125.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Config
# -----------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

IMG_SIZE = 224  # must match img_size used during training in the notebook

# The .tflite file is produced by running convert_to_tflite.py locally
# (once) against the .h5 file from plant_disease_detection.ipynb — see that
# script's docstring. class_indices.json still comes straight from the
# notebook (cell 24), unchanged.
#
# The .tflite file itself (182MB+) is too large for a normal git push
# (GitHub blocks files over 100MB) and Render's ephemeral filesystem
# doesn't persist uploads between deploys anyway, so instead of committing
# it, we download it from a GitHub Release asset at startup. Upload the
# file as a release asset on GitHub (Releases -> Draft a new release ->
# attach file, up to 2GB, no Git LFS needed), then set
# PLANT_DISEASE_MODEL_URL to that asset's direct download URL — it looks
# like:
#   https://github.com/<user>/<repo>/releases/download/<tag>/<filename>
MODEL_URL = os.getenv("PLANT_DISEASE_MODEL_URL")
MODEL_PATH = os.getenv("PLANT_DISEASE_MODEL_PATH", "plant_disease_prediction_model.tflite")
CLASS_INDICES_PATH = os.getenv("PLANT_DISEASE_CLASS_INDICES_PATH", "class_indices.json")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB, matches the frontend's stated limit


def _ensure_model_downloaded() -> None:
    """Download the .tflite model from MODEL_URL if it isn't already on
    disk. Render's filesystem is ephemeral, so this runs on every fresh
    deploy/restart — it's a one-time ~tens-of-MB download at startup, not
    per-request."""
    if os.path.exists(MODEL_PATH):
        return

    if not MODEL_URL:
        raise RuntimeError(
            f"Model file '{MODEL_PATH}' not found locally and "
            "PLANT_DISEASE_MODEL_URL is not set. Either place the .tflite "
            "file next to this script, or set PLANT_DISEASE_MODEL_URL to "
            "a GitHub Release asset URL for it."
        )

    print(f"Downloading model from {MODEL_URL} ...")
    response = requests.get(MODEL_URL, stream=True, timeout=120)
    response.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
            f.write(chunk)
    print(f"Model downloaded to {MODEL_PATH}")


# -----------------------------
# Load model + class map once at startup
# -----------------------------

try:
    _ensure_model_downloaded()
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    _input_details = interpreter.get_input_details()
    _output_details = interpreter.get_output_details()
except Exception as e:
    raise RuntimeError(
        f"Could not load plant disease model from '{MODEL_PATH}'. "
        "Run convert_to_tflite.py locally first to produce this .tflite "
        f"file from your trained .h5 model, or set PLANT_DISEASE_MODEL_PATH. "
        f"Original error: {e}"
    )

try:
    with open(CLASS_INDICES_PATH) as f:
        # Saved as {index_int: class_name} by the notebook (json.dump of
        # class_indices), but JSON keys always round-trip as strings.
        class_indices = {int(k): v for k, v in json.load(f).items()}
except Exception as e:
    raise RuntimeError(
        f"Could not load class_indices.json from '{CLASS_INDICES_PATH}'. "
        "This file is written by cell 24 of plant_disease_detection.ipynb. "
        f"Original error: {e}"
    )


# -----------------------------
# Crop index mapping for hybrid verification
# -----------------------------

CROP_ALIAS_MAP = {
    "apple": "apple",
    "blueberry": "blueberry",
    "cherry": "cherry",
    "corn": "corn",
    "maize": "corn",
    "grape": "grape",
    "orange": "orange",
    "citrus": "orange",
    "peach": "peach",
    "pepper": "pepper",
    "bell pepper": "pepper",
    "capsicum": "pepper",
    "potato": "potato",
    "raspberry": "raspberry",
    "soybean": "soybean",
    "squash": "squash",
    "strawberry": "strawberry",
    "tomato": "tomato",
}


def _normalize_crop(name: str) -> str:
    if not name:
        return ""
    name_clean = re.sub(r"[^a-z]", " ", name.lower()).strip()
    for alias, standard in CROP_ALIAS_MAP.items():
        if alias in name_clean:
            return standard
    return ""


# Pre-group all 38 classes by crop so we can constrain search space dynamically
CROP_TO_INDICES: dict[str, list[int]] = {}
for idx, label in class_indices.items():
    crop_raw = label.split("___")[0]
    norm_key = _normalize_crop(crop_raw)
    if norm_key:
        CROP_TO_INDICES.setdefault(norm_key, []).append(idx)


llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.2,
    max_output_tokens=400,
    google_api_key=GEMINI_API_KEY,
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
# Simple in-memory cache
# -----------------------------
# The Gemini write-up (about/treatment/prevention) only depends on the
# predicted label, not the specific photo, so we cache per-label instead of
# calling the LLM on every single upload.

_advice_cache: dict[str, dict] = {}


# -----------------------------
# Helpers
# -----------------------------

def _format_label(raw_label: str) -> dict:
    """PlantVillage labels look like 'Tomato___Early_blight' or
    'Apple___healthy'. Split that into crop / disease / healthy flag."""

    parts = raw_label.split("___")
    crop = parts[0].replace("_", " ").strip()
    condition_raw = parts[1] if len(parts) > 1 else "Unknown"

    healthy = condition_raw.strip().lower() == "healthy"
    disease = "Healthy" if healthy else condition_raw.replace("_", " ").strip()

    return {"crop": crop, "disease": disease, "healthy": healthy}


def _load_and_preprocess_image(file_bytes: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": "Uploaded file is not a readable image."},
        )

    img = img.resize((IMG_SIZE, IMG_SIZE))
    img_array = np.array(img).astype("float32") / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def _get_disease_advice(crop: str, disease: str, healthy: bool) -> dict:
    cache_key = f"{crop.lower()}::{disease.lower()}"
    cached = _advice_cache.get(cache_key)
    if cached:
        return cached

    if healthy:
        fallback = {
            "scientific_name": "N/A",
            "about": f"This {crop} leaf shows no visible signs of disease.",
            "treatment": ["No treatment needed."],
            "prevention": [
                "Keep monitoring leaves regularly.",
                "Maintain balanced watering and fertilization.",
                "Avoid leaf injury and overcrowding of plants.",
            ],
        }
        _advice_cache[cache_key] = fallback
        return fallback

    prompt = f"""You are a plant pathologist advising a farmer.

Crop: {crop}
Detected condition: {disease}

Respond with ONLY a valid JSON object, no markdown, no code fences, no
preamble, no explanation outside the JSON. Use exactly these keys:

{{
  "scientific_name": "<pathogen's scientific name, or 'N/A' if not applicable>",
  "about": "<1-2 sentences describing the disease and its visible symptoms, under 40 words>",
  "treatment": ["<short actionable treatment step>", "<...>", "<...>"],
  "prevention": ["<short actionable prevention step>", "<...>", "<...>"]
}}

Give 3 items each for "treatment" and "prevention". Do not include any text
before or after the JSON object.
"""

    try:
        result = llm.invoke(prompt)
        raw = _content_to_text(result.content).strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        advice = json.loads(raw)

        # Make sure the shape is always usable by the frontend even if the
        # model drops a key.
        advice.setdefault("scientific_name", "N/A")
        advice.setdefault("about", "")
        advice.setdefault("treatment", [])
        advice.setdefault("prevention", [])

    except Exception as e:
        advice = {
            "scientific_name": "N/A",
            "about": f"{disease} detected on {crop}. Automated advice generation failed: {e}",
            "treatment": [],
            "prevention": [],
        }

    _advice_cache[cache_key] = advice
    return advice


def _validate_and_identify_crop_with_gemini(file_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Verifies that the image is a plant leaf, and identifies the plant/crop species
    to cross-verify with the CNN model.

    Returns {"is_leaf": bool, "crop": str}.
    """
    if not GEMINI_API_KEY:
        return {"is_leaf": True, "crop": ""}

    try:
        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        mime = content_type if content_type and content_type.startswith("image/") else "image/jpeg"

        prompt = """You are an agricultural plant pathologist and image validator.
Examine this image carefully:
1. Is this a genuine photograph of a plant leaf or agricultural crop? (If it is anime/cartoon, starry sky, wallpaper, scenery, person, animal, vehicle, indoor object, or anything other than a plant leaf/crop, set is_leaf to false).
2. What plant/crop species is this leaf from? Identify the plant if possible (Choose from: Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper bell, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato, or Other).

Respond with ONLY valid JSON:
{
  "is_leaf": true,
  "crop": "<crop name or 'Unknown'>"
}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": b64_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 60,
            },
        }

        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                text_clean = re.sub(r"```json|```", "", text_part).strip()
                parsed = json.loads(text_clean)
                return {
                    "is_leaf": bool(parsed.get("is_leaf", True)),
                    "crop": str(parsed.get("crop", "")).strip(),
                }
        return {"is_leaf": True, "crop": ""}
    except Exception as e:
        print(f"Gemini leaf/crop analysis warning: {e}")
        return {"is_leaf": True, "crop": ""}


# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def home():
    return {"message": "Plant Disease Detection API Running"}


@app.post("/predict-disease")
async def predict_disease(file: UploadFile = File(...)):

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Please upload an image file (JPG, PNG, JPEG)."},
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail={"error": "Image is larger than the 5MB limit."},
        )

    # 1. Dual validation & crop identification with Gemini Vision
    vision_check = _validate_and_identify_crop_with_gemini(file_bytes, file.content_type)
    if not vision_check.get("is_leaf", True):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "The uploaded image does not appear to be a plant leaf or crop. Please upload a clear photo of a crop leaf.",
                "reason": "not_a_leaf",
            },
        )

    img_array = _load_and_preprocess_image(file_bytes)

    try:
        # Note: the interpreter isn't safe to call from multiple requests
        # truly concurrently. That's fine here since Render's free tier
        # runs a single worker (WEB_CONCURRENCY=1) and FastAPI processes
        # this synchronous block without yielding mid-inference.
        interpreter.set_tensor(_input_details[0]["index"], img_array)
        interpreter.invoke()
        predictions = interpreter.get_tensor(_output_details[0]["index"])[0]
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"error": "Model inference failed", "details": str(e)},
        )

    # Base prediction from CNN global argmax
    predicted_index = int(np.argmax(predictions))
    confidence = float(predictions[predicted_index]) * 100

    # 2. Hybrid Crop Cross-Verification:
    # If Gemini Vision identified a known PlantVillage crop, verify against CNN
    detected_crop = vision_check.get("crop", "")
    crop_norm = _normalize_crop(detected_crop)

    if crop_norm and crop_norm in CROP_TO_INDICES:
        candidate_indices = CROP_TO_INDICES[crop_norm]
        cnn_raw_label = class_indices.get(predicted_index, "")
        cnn_crop_norm = _normalize_crop(cnn_raw_label.split("___")[0])

        # If CNN's crop differs from visually verified crop (e.g. Cherry vs Potato):
        if cnn_crop_norm != crop_norm:
            best_idx = max(candidate_indices, key=lambda idx: predictions[idx])
            predicted_index = best_idx
            candidate_probs = [predictions[idx] for idx in candidate_indices]
            sum_probs = sum(candidate_probs)
            if sum_probs > 0:
                confidence = float(predictions[best_idx] / sum_probs) * 100
            else:
                confidence = float(predictions[best_idx]) * 100

    raw_label = class_indices.get(predicted_index)
    if raw_label is None:
        raise HTTPException(
            status_code=502,
            detail={"error": f"Predicted class index {predicted_index} not found in class_indices.json"},
        )

    formatted = _format_label(raw_label)
    advice = _get_disease_advice(formatted["crop"], formatted["disease"], formatted["healthy"])

    return {
        "raw_label": raw_label,
        "crop": formatted["crop"],
        "disease": formatted["disease"],
        "healthy": formatted["healthy"],
        "confidence": round(confidence, 2),
        **advice,
    }