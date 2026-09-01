"""
Master Launcher for AI Document Screening Platform (FastAPI + React Frontend)
=============================================================================
Launches:
1. Master FastAPI Orchestration Server (Port 8000)
2. React Vite Frontend Dashboard (Port 5173)

Usage:
    python run_platform.py
"""

import sys
import os
import time
import subprocess
import webbrowser
from pathlib import Path

# Fix Windows console UTF-8 charmap encoding issues
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"

def main():
    print("=" * 70)
    print("🛡️  AURA-SHIELD: AI DOCUMENT SCREENING PLATFORM LAUNCHER")
    print("=" * 70)
    print("[1/2] Starting FastAPI Backend Orchestration Server on http://localhost:8000 ...")

    server_cmd = [
        sys.executable, "-m", "uvicorn",
        "orchestration_platform.server.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    backend_proc = subprocess.Popen(server_cmd, cwd=str(ROOT_DIR))

    print("[2/2] Starting React Vite Frontend Dashboard on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(FRONTEND_DIR))

    time.sleep(2)
    print("\n" + "=" * 70)
    print("🚀 PLATFORM IS LIVE:")
    print("   • React Dashboard:    http://localhost:5173")
    print("   • FastAPI Swagger API: http://localhost:8000/docs")
    print("=" * 70)
    print("Press Ctrl+C to terminate both servers.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Terminating servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("[SHUTDOWN] Done.")

if __name__ == "__main__":
    main()
