from transformers import pipeline
from PIL import Image
import numpy as np

detector = pipeline("image-classification", model="Ateeqq/ai-vs-human-image-detector")

def _noise_uniformity_heuristic(image_path: str) -> float:
    try:
        img = Image.open(image_path).convert("L").resize((256, 256))
        arr = np.array(img, dtype=np.float32)
        laplacian_like = np.abs(np.diff(arr, axis=0)).std() + np.abs(np.diff(arr, axis=1)).std()
        score = max(0.0, min(1.0, (20 - laplacian_like) / 20))
        return round(float(score), 4)
    except Exception:
        return 0.0

def detect_ai_generated(image_path: str) -> dict:
    try:
        results = detector(image_path)
        scores = {r['label'].lower(): r['score'] for r in results}
        ai_score = scores.get('ai', scores.get('fake', 0))
        model_used = True
    except Exception:
        ai_score = 0.0
        model_used = False

    fallback_score = _noise_uniformity_heuristic(image_path)

    if model_used:
        combined = round((ai_score * 0.85) + (fallback_score * 0.15), 4)
    else:
        combined = fallback_score

    if combined > 0.75:
        verdict = "AI_GENERATED"
    elif combined > 0.5:
        verdict = "SUSPICIOUS_REVIEW_RECOMMENDED"
    else:
        verdict = "LIKELY_REAL"

    return {
        "ai_generated_probability": combined,
        "primary_model_score": round(ai_score, 4),
        "fallback_heuristic_score": fallback_score,
        "verdict": verdict,
        "model_available": model_used
    }