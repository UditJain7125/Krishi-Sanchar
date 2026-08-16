"""
Starts every KrishiSanchar backend service at once, each on the port
web.js already expects — even when each service lives in its own folder.

Edit the SERVICES list below so `folder` points at the directory
containing each .py file (relative to wherever you run this script from,
or an absolute path).

Usage:
    python run_all.py

Press Ctrl+C once to stop all services together.
"""

import subprocess
import sys
import time
from pathlib import Path

# folder: directory containing that service's .py file
# target: "module_name:app_variable" (module_name = filename without .py)
# port:   must match the API config at the top of web.js
SERVICES = [
    {"folder": "Crop recommendation",  "target": "app:app",                 "port": 8000},
    {"folder": "Fertilizer recommendation","target": "Fertilizer:app",          "port": 8001},
    {"folder": "Yield Prediction",     "target": "Yield_prediction:app",    "port": 8002},
    {"folder": ".",                    "target": "market_analysis:app",     "port": 8003},
    {"folder": ".",                    "target": "weather_service:app",     "port": 8004},
    {"folder": ".",                    "target": "ai_assistant:app",        "port": 8005},
    {"folder": "plant disease",        "target": "plant_disease_detection:app", "port": 8006},
]

processes = []

def main():
    for svc in SERVICES:
        folder = Path(svc["folder"]).resolve()
        if not folder.is_dir():
            print(f"SKIPPING {svc['target']}: folder not found — {folder}")
            print(f"  Update the 'folder' path in run_all.py's SERVICES list.")
            continue

        module_name = svc["target"].split(":")[0]
        script_path = folder / f"{module_name}.py"
        if not script_path.exists():
            print(f"SKIPPING {svc['target']}: {script_path} not found")
            continue

        print(f"Starting {svc['target']} on port {svc['port']} (cwd={folder})...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", svc["target"], "--port", str(svc["port"])],
            cwd=str(folder),
        )
        processes.append((svc["target"], proc))
        time.sleep(0.5)  # stagger startup so logs don't interleave too badly

    if not processes:
        print("\nNo services started — check the folder paths in SERVICES above.")
        return

    print("\nAll services launching. Press Ctrl+C to stop all of them.\n")

    try:
        # Wait on all processes; if any exits on its own, report it.
        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"[{name}] exited with code {code} — check its "
                          f"output above for the error (missing .pkl file, "
                          f"missing env var, bad import, etc.)")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for name, proc in processes:
            proc.terminate()
        for name, proc in processes:
            proc.wait()
        print("All services stopped.")

if __name__ == "__main__":
    main()