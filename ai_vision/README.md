# Module 3: Generative AI Detection, Biometrics & Real-Time Liveness Engine

Part of the **AI-Powered Document Fraud Screening & Verification Platform (Smart India Hackathon)**.

---

## 🎯 What Module 3 Does

Module 3 delivers comprehensive visual security, generative AI forgery detection, biometric face matching, and presentation attack detection (PAD):

1. **Generative AI & Synthetic ID Detection (`ai_detector.py`)**:
   - Analyzes submitted travel documents to determine whether they were generated or manipulated by AI tools (Midjourney, Stable Diffusion, DALL-E, GAN inpainting) vs. physical optical scans.
   - Dual-layer inspection: Combines a pretrained **Vision Transformer (ViT)** (`Ateeqq/ai-vs-human-image-detector`) with a **Laplacian Spatial Noise Uniformity Heuristic** ($\sigma_{\text{spatial}}$).
   - Returns calibrated three-tier verdicts: `AI_GENERATED`, `SUSPICIOUS_REVIEW_RECOMMENDED`, or `LIKELY_REAL`.

2. **Facial Biometric Verification (`face_verify.py`)**:
   - Isolates the traveler's photo from the document (Passport VIZ or Aadhaar) using **RetinaFace** facial landmark alignment.
   - Generates 512-dimensional deep feature embeddings using **Facenet / ArcFace** and computes cosine distance ($d < 0.40$ match threshold) against the verified live traveler selfie.

3. **Real-Time Presentation Attack Detection (PAD / Liveness Engine) (`liveness_detector.py`)**:
   - **MediaPipe 468-Point Mesh**: CPU/XNNPACK-accelerated facial landmark tracking.
   - **Soukupová-Čech Eye Aspect Ratio (EAR)**: Computes 6-point eye landmark vector ratios with **Adaptive Baseline Open-Eye Calibration**.
   - **Interactive 30 FPS HUD Overlay**: In-screen live video HUD with dynamic EAR gauge bar, live blink counter (`Blinks: X / 2`), and real-time status badges (`🟡 PLEASE BLINK` $\to$ `🟢 LIVE HUMAN VERIFIED`).
   - **10-Second Anti-Spoofing Deadline**: Defeats static 2D photo print attacks or frozen video replays by terminating with a PAD timeout alert if no natural blinks occur within 10 seconds.
   - **Auto-Capture**: Freezes and outputs the validated open-eye live frame for downstream DeepFace matching.

---

## 🛠️ Tech Stack

- **FastAPI & Uvicorn**: High-performance asynchronous microservice layer.
- **Hugging Face Transformers & PyTorch**: Vision Transformer (ViT) patch attention classifier.
- **MediaPipe Tasks Vision**: 468-point 3D facial landmark mesh with XNNPACK acceleration.
- **DeepFace & RetinaFace**: Deep facial embedding extraction and spatial alignment.
- **OpenCV & Pillow**: Real-time video processing, in-memory image streaming, and HUD rendering.

---

## 🚀 Running Module 3 Standalone

### 1. Run the Interactive Real-Time Liveness HUD Scanner
```bash
python ai_vision/liveness_detector.py
```
*Instructions: Look at the webcam and blink naturally twice within the 10-second window. Press `q` or `ESC` to exit.*

### 2. Run Headless Unit Tests
```bash
python test_liveness.py
```

### 3. Launch the Module 3 FastAPI Microservice
```bash
uvicorn ai_vision.main:app --reload --port 8001
```
Interactive Swagger Documentation: `http://localhost:8001/docs`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/verify` | Compares document image vs live selfie + computes AI generation probability |
| `POST` | `/liveness/check-frame` | Evaluates a single frame for face presence and Eye Aspect Ratio (EAR) |
| `POST` | `/liveness/trigger-webcam` | Initiates an interactive local webcam liveness session |
| `GET` | `/` | Microservice health and capability status |
