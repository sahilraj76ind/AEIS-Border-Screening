from fastapi import FastAPI, UploadFile, File
from PIL import Image
import shutil, uuid, os
from ai_detector import detect_ai_generated
from face_verify import verify_face

app = FastAPI(title="Module 3 - AI Detection & Face Verification")
os.makedirs("temp", exist_ok=True)

def save_temp(file: UploadFile) -> str:
    raw_path = f"temp/{uuid.uuid4()}_{file.filename}"
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    jpg_path = raw_path.rsplit(".", 1)[0] + ".jpg"
    img = Image.open(raw_path).convert("RGB")
    img.save(jpg_path, "JPEG")
    if raw_path != jpg_path:
        os.remove(raw_path)
    return jpg_path

@app.get("/")
def health():
    return {"status": "Module 3 running"}

@app.post("/verify")
async def verify(document: UploadFile = File(...), selfie: UploadFile = File(...)):
    doc_path = save_temp(document)
    selfie_path = save_temp(selfie)

    ai_result = detect_ai_generated(doc_path)
    face_result = verify_face(doc_path, selfie_path)

    os.remove(doc_path)
    os.remove(selfie_path)

    risk_flag = (
        ai_result["verdict"] in ["AI_GENERATED", "SUSPICIOUS_REVIEW_RECOMMENDED"]
        or not face_result["face_match"]
    )

    return {
        "ai_generation_check": ai_result,
        "face_verification": face_result,
        "module_flag": risk_flag,
        "recommendation": "REJECT" if ai_result["verdict"] == "AI_GENERATED" and not face_result["face_match"]
                           else "REVIEW" if risk_flag
                           else "PASS"
    }