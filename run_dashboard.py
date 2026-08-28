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

ROOT_DIR = Path(__file__).resolve().parent
APP_PATH = ROOT_DIR / "orchestration_platform" / "app.py"

if __name__ == "__main__":
    print(f"🚀 Launching Streamlit Dashboard from: {APP_PATH}")
    cmd = [sys.executable, "-m", "streamlit", "run", str(APP_PATH)]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user.")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
