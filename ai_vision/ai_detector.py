from transformers import pipeline

detector = pipeline("image-classification", model="Ateeqq/ai-vs-human-image-detector")

def detect_ai_generated(image_path: str) -> dict:
    results = detector(image_path)
    scores = {r['label'].lower(): r['score'] for r in results}
    ai_score = scores.get('ai', scores.get('fake', 0))
    return {
        "ai_generated_probability": round(ai_score, 4),
        "verdict": "AI_GENERATED" if ai_score > 0.6 else "LIKELY_REAL"
    }