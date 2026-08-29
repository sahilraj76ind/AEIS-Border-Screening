import io
import os
import shutil
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from PIL import Image
import numpy as np
import cv2

from ai_detector import detect_ai_generated
from face_verify import verify_face
from liveness_detector import RealTimeLivenessEngine, default_engine, calculate_ear

app = FastAPI(
    title="Module 3 - AI Detection, Face Biometrics & Real-Time Liveness",
    description="Biometric identity screening and anti-spoofing engine for border checkpoints."
)

os.makedirs("temp", exist_ok=True)


def save_temp_safe(file: UploadFile) -> str:
    """Helper ensuring temp image file creation with robust cleanup."""
    raw_path = f"temp/{uuid.uuid4()}_{file.filename}"
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    jpg_path = raw_path.rsplit(".", 1)[0] + ".jpg"
    img = Image.open(raw_path).convert("RGB")
    img.save(jpg_path, "JPEG")
    if raw_path != jpg_path and os.path.exists(raw_path):
        os.remove(raw_path)
    return jpg_path


@app.get("/")
def health():
    return {
        "status": "Module 3 running",
        "features": [
            "AI Generated Document Detection",
            "DeepFace Facial Biometrics Verification",
            "MediaPipe Real-Time Liveness & Blink Engine"
        ]
    }


@app.post("/verify")
async def verify(document: UploadFile = File(...), selfie: UploadFile = File(...)):
    """
    Standard verification comparing uploaded document and selfie with corrected decision matrix.
    """
    doc_path = save_temp_safe(document)
    selfie_path = save_temp_safe(selfie)

    try:
        ai_result = detect_ai_generated(doc_path)
        face_result = verify_face(doc_path, selfie_path)

        # Corrected Strict Decision Matrix (Immigration Veto Rules)
        if ai_result["verdict"] == "AI_GENERATED":
            recommendation = "REJECT"
            risk_flag = True
        elif not face_result.get("face_match", False):
            recommendation = "REJECT"
            risk_flag = True
        elif ai_result["verdict"] == "SUSPICIOUS_REVIEW_RECOMMENDED":
            recommendation = "REVIEW"
            risk_flag = True
        else:
            recommendation = "PASS"
            risk_flag = False

        return {
            "ai_generation_check": ai_result,
            "face_verification": face_result,
            "module_flag": risk_flag,
            "recommendation": recommendation
        }
    finally:
        if os.path.exists(doc_path):
            try:
                os.remove(doc_path)
            except Exception:
                pass
        if os.path.exists(selfie_path):
            try:
                os.remove(selfie_path)
            except Exception:
                pass


@app.post("/liveness/check-frame")
async def check_frame_liveness(frame: UploadFile = File(...)):
    """
    Evaluates a single captured camera frame for face presence and Eye Aspect Ratio (EAR).
    """
    frame_bytes = await frame.read()
    img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    annotated_bgr, status = default_engine.process_frame(img, draw_hud=False)

    return {
        "face_detected": status["face_detected"],
        "eye_aspect_ratio": status["current_ear"],
        "left_ear": status["left_ear"],
        "right_ear": status["right_ear"],
        "is_eye_closed": status["is_eye_closed"]
    }


@app.post("/liveness/trigger-webcam")
def trigger_webcam_session(camera_id: int = 0, target_blinks: int = 2, timeout_seconds: float = 25.0):
    """
    Launches a local interactive webcam HUD session on the host machine.
    """
    engine = RealTimeLivenessEngine(target_blinks=target_blinks)
    confirmed, frame_rgb, report = engine.run_webcam_stream(
        camera_id=camera_id,
        target_blinks=target_blinks,
        timeout_seconds=timeout_seconds,
        auto_capture=True,
        show_window=True
    )
    return {
        "liveness_confirmed": confirmed,
        "session_report": report
    }