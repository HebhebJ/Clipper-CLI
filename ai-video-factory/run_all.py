import subprocess
import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent

services = [
    ("script-service", ROOT / "script_service" / "main.py", int(os.environ.get("SCRIPT_PORT", "8001"))),
    ("voice-service", ROOT / "voice_service" / "main.py", int(os.environ.get("VOICE_PORT", "8002"))),
    ("render-service", ROOT / "render_service" / "main.py", int(os.environ.get("RENDER_PORT", "8003"))),
    ("orchestrator", ROOT / "orchestrator" / "main.py", int(os.environ.get("ORCH_PORT", "8000"))),
]

procs = []

try:
    for name, main_path, port in services:
        cmd = [
            sys.executable, "-m", "uvicorn",
            f"{main_path.stem}:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ]
        print(f"Starting {name} on port {port}...")
        p = subprocess.Popen(cmd, cwd=str(main_path.parent))
        procs.append(p)

    print("All services started. Press Ctrl+C to stop.")
    # Wait forever (until Ctrl+C)
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\nStopping all services...")
finally:
    for p in procs:
        if p.poll() is None:
            p.terminate()
