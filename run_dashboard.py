"""
Launcher Script for Streamlit Dashboard
=======================================
Launches the AI-Powered Document Fraud Screening & Verification Platform.
Usage:
    python run_dashboard.py
OR:
    streamlit run orchestration_platform/app.py
"""

import sys
import subprocess
from pathlib import Path

# Fix Windows console UTF-8 charmap encoding issues
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
APP_PATH = ROOT_DIR / "orchestration_platform" / "app.py"

if __name__ == "__main__":
    print(f"[LAUNCH] Launching Streamlit Dashboard from: {APP_PATH}")
    cmd = [sys.executable, "-m", "streamlit", "run", str(APP_PATH)]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n[STOP] Dashboard stopped by user.")
    except Exception as e:
        print(f"[ERROR] Error launching dashboard: {e}")
