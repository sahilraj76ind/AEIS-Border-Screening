"""
AI Vision & Face Verification Adapter (Person C Integration Wrapper)
===================================================================
Safely wraps Sahil's AI generated image detection (ai_detector.py) and
DeepFace facial biometrics verification (face_verify.py) in ai_vision/
without modifying any original teammate files.
"""

import io
import os
import sys
import uuid
import shutil
import tempfile
import numpy as np
from typing import Dict, Any, Union, Optional, Tuple
from PIL import Image

# Ensure root directory and ai_vision directory are on python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ai_vision_dir = os.path.join(root_dir, "ai_vision")
for p in [root_dir, ai_vision_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from ai_vision.ai_detector import detect_ai_generated
except ImportError:
    try:
        from ai_detector import detect_ai_generated
    except ImportError:
        detect_ai_generated = None

try:
    from ai_vision.face_verify import verify_face
except ImportError:
    try:
        from face_verify import verify_face
    except ImportError:
        verify_face = None


def _write_temp_image(image_input: Union[str, bytes, Image.Image]) -> Tuple[str, bool]:
    """
    Helper function ensuring image is saved as a temporary JPEG file path
    for downstream model consumption, returning (file_path, is_temp).
    """
    if isinstance(image_input, str) and os.path.isfile(image_input):
        return image_input, False

    temp_dir = os.path.join(root_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"wrapper_temp_{uuid.uuid4().hex}.jpg")

    if isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input)).convert("RGB")
        img.save(temp_path, "JPEG")
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
        img.save(temp_path, "JPEG")
    else:
        raise ValueError(f"Invalid image input type: {type(image_input)}")

    return temp_path, True


def run_ai_generated_detection(
    image_input: Union[str, bytes, Image.Image]
) -> Dict[str, Any]:
    """
    Safely calls Sahil's detect_ai_generated model.
    Handles fallbacks gracefully if deep learning model loading or network access fails.
    """
    temp_path, is_temp = _write_temp_image(image_input)
    try:
        if detect_ai_generated is not None:
            try:
                res = detect_ai_generated(temp_path)
                res["status"] = "SUCCESS"
                return res
            except Exception:
                pass

        # Fallback to Sahil's noise uniformity heuristic
        try:
            img_l = Image.open(temp_path).convert("L").resize((256, 256))
            arr = np.array(img_l, dtype=np.float32)
            laplacian_like = float(np.abs(np.diff(arr, axis=0)).std() + np.abs(np.diff(arr, axis=1)).std())
            fallback_score = round(max(0.0, min(1.0, (20.0 - laplacian_like) / 20.0)), 4)
        except Exception:
            fallback_score = 0.0

        verdict = "AI_GENERATED" if fallback_score > 0.75 else ("SUSPICIOUS_REVIEW_RECOMMENDED" if fallback_score > 0.5 else "LIKELY_REAL")

        return {
            "status": "FALLBACK",
            "ai_generated_probability": fallback_score,
            "primary_model_score": 0.0,
            "fallback_heuristic_score": fallback_score,
            "verdict": verdict,
            "model_available": False
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error_message": f"AI detection failed: {str(e)}",
            "ai_generated_probability": 0.0,
            "verdict": "UNKNOWN",
            "model_available": False
        }
    finally:
        if is_temp and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def run_facial_biometric_verification(
    doc_image_input: Union[str, bytes, Image.Image],
    selfie_image_input: Union[str, bytes, Image.Image]
) -> Dict[str, Any]:
    """
    Safely calls Sahil's verify_face DeepFace model comparing document face against selfie.
    """
    doc_path, is_temp_doc = _write_temp_image(doc_image_input)
    selfie_path, is_temp_selfie = _write_temp_image(selfie_image_input)
    try:
        if verify_face is not None:
            res = verify_face(doc_path, selfie_path)
            res["status"] = res.get("status", "SUCCESS")
            return res
        else:
            return {
                "face_match": False,
                "similarity_score": 0.0,
                "distance": 1.0,
                "status": "MODEL_UNAVAILABLE",
                "error": "face_verify module could not be imported"
            }
    except Exception as e:
        return {
            "face_match": False,
            "similarity_score": 0.0,
            "distance": 1.0,
            "status": "FACE_VERIFICATION_ERROR",
            "error": str(e)
        }
    finally:
        for p, is_t in [(doc_path, is_temp_doc), (selfie_path, is_temp_selfie)]:
            if is_t and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
