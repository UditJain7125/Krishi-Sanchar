"""
Single entry point that combines all 7 KrishiSanchar FastAPI services into
one app, so Render (or any single-port host) can run everything together.

Each original service file is untouched — this just loads each one's
`app` object from its file path and mounts it under its own prefix.

Run with:
    uvicorn main:app --host 0.0.0.0 --port $PORT

IMPORTANT: Adjust the folder paths in SERVICES below to match your actual
repo layout (they're set to match your docker-compose.yml working_dir
values). If a path is wrong, this file will print a warning and skip that
service instead of crashing the whole app.
"""

import sys
import importlib.util
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent


def load_app(module_path: Path, module_name: str):
    """Load a FastAPI `app` object from a .py file at an arbitrary path,
    without needing that file's folder on sys.path (handles folder names
    with spaces, like 'Crop recommendation')."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.app


# Root app — this is what Render actually runs.
app = FastAPI(title="KrishiSanchar Combined API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your GitHub Pages origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "KrishiSanchar combined API running"}


# prefix, file path (relative to this file), name for the loaded module
SERVICES = [
    ("/api/crop",       BASE_DIR / "Crop recommendation" / "app.py",               "crop_app"),
    ("/api/fertilizer", BASE_DIR / "Fertilizer recommendation" / "Fertilizer.py",  "fertilizer_app"),
    ("/api/yield",      BASE_DIR / "Yield Prediction" / "Yield_prediction.py",     "yield_app"),
    ("/api/market",     BASE_DIR / "market_analysis.py",                          "market_app"),
    ("/api/weather",    BASE_DIR / "weather_service.py",                          "weather_app"),
    ("/api/assistant",  BASE_DIR / "ai_assistant.py",                             "assistant_app"),
    ("/api/disease",    BASE_DIR / "plant disease" / "plant_disease_detection.py","disease_app"),
]

for prefix, path, name in SERVICES:
    if not path.exists():
        print(f"WARNING: {path} not found — skipping mount at {prefix}. "
              f"Fix the path in main.py's SERVICES list if this is wrong.")
        continue
    try:
        sub_app = load_app(path, name)
        app.mount(prefix, sub_app)
        print(f"Mounted {path.name} at {prefix}")
    except Exception as e:
        print(f"ERROR loading {path} for {prefix}: {e}")