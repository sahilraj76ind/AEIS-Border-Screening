from deepface import DeepFace
import traceback

def verify_face(doc_image_path: str, selfie_image_path: str) -> dict:
    try:
        result = DeepFace.verify(
            img1_path=doc_image_path,
            img2_path=selfie_image_path,
            model_name="Facenet",
            detector_backend="retinaface",
            enforce_detection=False
        )
        return {
            "face_match": bool(result["verified"]),
            "distance": round(result["distance"], 4),
            "similarity_score": round(1 - result["distance"], 4),
            "status": "OK"
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "face_match": False,
            "similarity_score": 0.0,
            "status": "FACE_NOT_DETECTED",
            "error": str(e)
        }