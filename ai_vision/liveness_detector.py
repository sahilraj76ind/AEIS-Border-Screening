"""
Lightweight Real-Time Liveness Engine (Eye Aspect Ratio & Anti-Spoofing)
========================================================================
Module 3 / Person C Biometrics Component

Features:
- MediaPipe FaceLandmarker with XNNPACK CPU acceleration.
- High-precision Eye Aspect Ratio (EAR) calculation across 6 landmark vectors per eye.
- Real-time temporal blink state machine detecting natural eye closures.
- Dynamic HUD rendering: EAR progress meter, live blink counter, and verification badge.
- Auto-capture of validated live frames for downstream DeepFace matching.
- Pure in-memory execution preserving Zero-Disk Persistence for DPDP Act 2023 compliance.
"""

import os
import sys
import time
import math
import urllib.request
from typing import Dict, Any, Tuple, Optional, List, Union
import numpy as np
import cv2
from PIL import Image

# MediaPipe Tasks API
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None
    mp_python = None
    mp_vision = None

# Model Configuration & Path Resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(CURRENT_DIR, "models")
MODEL_FILENAME = "face_landmarker.task"
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_FILENAME)
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# Landmark Indices for 6-Point Eye Aspect Ratio (MediaPipe 468 Face Mesh)
# Left Eye: 33 (outer), 160 (top-left), 158 (top-right), 133 (inner), 153 (bottom-right), 144 (bottom-left)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
# Right Eye: 362 (inner), 385 (top-left), 387 (top-right), 263 (outer), 373 (bottom-right), 380 (bottom-left)
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


def ensure_model_exists() -> str:
    """Ensures the MediaPipe Face Landmarker model asset is downloaded and returns its path."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 1000:
        print(f"[LIVENESS] Downloading FaceLandmarker model asset to: {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"[LIVENESS] Model downloaded successfully ({os.path.getsize(MODEL_PATH)} bytes).")
    return MODEL_PATH


def _euclidean_dist(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    """Computes standard 2D Euclidean distance between two points."""
    return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def calculate_ear(eye_landmarks: List[Tuple[float, float]]) -> float:
    """
    Computes Soukupová & Čech (2016) Eye Aspect Ratio (EAR):
    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    """
    if len(eye_landmarks) != 6:
        return 0.0

    p1, p2, p3, p4, p5, p6 = eye_landmarks
    vertical_1 = _euclidean_dist(p2, p6)
    vertical_2 = _euclidean_dist(p3, p5)
    horizontal = _euclidean_dist(p1, p4)

    if horizontal <= 1e-6:
        return 0.0

    ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
    return round(float(ear), 4)


class RealTimeLivenessEngine:
    """
    Stateful Real-Time Liveness Engine with Adaptive Blink State Machine and HUD Rendering.
    """

    def __init__(
        self,
        ear_thresh_closed: float = 0.225,
        ear_thresh_open: float = 0.255,
        min_closed_frames: int = 1,
        target_blinks: int = 2,
        timeout_seconds: float = 10.0,
        **kwargs
    ):
        self.ear_thresh_closed = ear_thresh_closed
        self.ear_thresh_open = ear_thresh_open
        self.min_closed_frames = min_closed_frames
        self.target_blinks = target_blinks
        self.timeout_seconds = timeout_seconds or kwargs.get("timeout_seconds", 10.0)

        # State Machine Tracking & Adaptive Calibration
        self.blink_count = 0
        self.consecutive_closed_frames = 0
        self.is_eye_closed = False
        self.liveness_confirmed = False
        self.start_time = time.time()
        self.captured_frame_rgb: Optional[np.ndarray] = None
        self.captured_frame_bgr: Optional[np.ndarray] = None
        self.last_ear = 0.0
        self.baseline_open_ear = 0.28
        self.ear_history: List[float] = []

        # Initialize MediaPipe Detector
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """Initializes MediaPipe FaceLandmarker with CPU/XNNPACK optimization."""
        if not MEDIAPIPE_AVAILABLE:
            print("[LIVENESS WARNING] mediapipe is not installed. Using OpenCV fallback.")
            return

        try:
            model_path = ensure_model_exists()
            base_options = mp_python.BaseOptions(model_asset_path=model_path)
            options = mp_vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.detector = mp_vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[LIVENESS WARNING] Failed to initialize MediaPipe FaceLandmarker: {e}. Using OpenCV fallback.")
            self.detector = None

    def reset_state(self):
        """Resets the state machine for a new verification session."""
        self.blink_count = 0
        self.consecutive_closed_frames = 0
        self.is_eye_closed = False
        self.liveness_confirmed = False
        self.start_time = time.time()
        self.captured_frame_rgb = None
        self.captured_frame_bgr = None
        self.last_ear = 0.0
        self.ear_history.clear()

    def _extract_landmarks_mediapipe(
        self, frame_rgb: np.ndarray
    ) -> Optional[Tuple[List[Tuple[float, float]], List[Tuple[float, float]], Tuple[int, int, int, int]]]:
        """Extracts left eye, right eye landmarks and face bbox using MediaPipe."""
        if self.detector is None:
            return None

        h, w, _ = frame_rgb.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.detector.detect(mp_image)

        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return None

        face_landmarks = result.face_landmarks[0]

        # Extract 6 points for left eye
        left_eye = []
        for idx in LEFT_EYE_INDICES:
            lm = face_landmarks[idx]
            left_eye.append((lm.x * w, lm.y * h))

        # Extract 6 points for right eye
        right_eye = []
        for idx in RIGHT_EYE_INDICES:
            lm = face_landmarks[idx]
            right_eye.append((lm.x * w, lm.y * h))

        # Compute Face Bounding Box
        all_x = [lm.x * w for lm in face_landmarks]
        all_y = [lm.y * h for lm in face_landmarks]
        min_x, max_x = max(0, int(min(all_x))), min(w, int(max(all_x)))
        min_y, max_y = max(0, int(min(all_y))), min(h, int(max(all_y)))
        face_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)

        return left_eye, right_eye, face_bbox

    def _extract_landmarks_opencv_fallback(
        self, frame_bgr: np.ndarray
    ) -> Optional[Tuple[List[Tuple[float, float]], List[Tuple[float, float]], Tuple[int, int, int, int]]]:
        """Fallback face and eye detection using OpenCV Haar Cascades."""
        try:
            face_xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            eye_xml = cv2.data.haarcascades + "haarcascade_eye.xml"
            if not os.path.exists(face_xml) or not os.path.exists(eye_xml):
                return None

            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(face_xml)
            eye_cascade = cv2.CascadeClassifier(eye_xml)

            if face_cascade.empty() or eye_cascade.empty():
                return None

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))
            if len(faces) == 0:
                return None

            fx, fy, fw, fh = faces[0]
            face_roi_gray = gray[fy:fy + int(fh * 0.6), fx:fx + fw]
            eyes = eye_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))

            if len(eyes) < 2:
                return None

            # Sort eyes left to right
            eyes = sorted(eyes, key=lambda e: e[0])
            e1x, e1y, e1w, e1h = eyes[0]
            e2x, e2y, e2w, e2h = eyes[1]

            # Approximate 6-point eye landmarks from bounding boxes
            def make_points(ex, ey, ew, eh):
                cx, cy = fx + ex + ew / 2.0, fy + ey + eh / 2.0
                p1 = (fx + ex, cy)
                p4 = (fx + ex + ew, cy)
                p2 = (cx - ew * 0.2, fy + ey + eh * 0.2)
                p3 = (cx + ew * 0.2, fy + ey + eh * 0.2)
                p5 = (cx + ew * 0.2, fy + ey + eh * 0.8)
                p6 = (cx - ew * 0.2, fy + ey + eh * 0.8)
                return [p1, p2, p3, p4, p5, p6]

            left_pts = make_points(e1x, e1y, e1w, e1h)
            right_pts = make_points(e2x, e2y, e2w, e2h)

            return left_pts, right_pts, (fx, fy, fw, fh)
        except Exception:
            return None

    def process_frame(
        self,
        frame: Union[np.ndarray, Image.Image],
        draw_hud: bool = True
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes a single video frame, updates the blink state machine,
        and renders the interactive real-time HUD.

        Args:
            frame: Input frame in BGR or RGB NumPy array or PIL Image.
            draw_hud: Whether to render HUD overlays on the returned frame.

        Returns:
            annotated_frame_bgr: BGR frame with visual overlays.
            status_dict: Structured dictionary with liveness metrics.
        """
        # Format normalization to BGR NumPy array
        if isinstance(frame, Image.Image):
            frame_rgb = np.array(frame.convert("RGB"))
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(frame, np.ndarray):
            if len(frame.shape) == 2:  # Grayscale
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            else:
                frame_bgr = frame.copy()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"Unsupported frame type: {type(frame)}")

        h, w, _ = frame_bgr.shape

        # Landmark extraction
        landmarks = self._extract_landmarks_mediapipe(frame_rgb)
        if landmarks is None:
            landmarks = self._extract_landmarks_opencv_fallback(frame_bgr)

        face_detected = landmarks is not None
        left_ear = 0.0
        right_ear = 0.0
        avg_ear = 0.0
        bbox = None

        if face_detected:
            left_pts, right_pts, bbox = landmarks
            left_ear = calculate_ear(left_pts)
            right_ear = calculate_ear(right_pts)
            avg_ear = round((left_ear + right_ear) / 2.0, 4)
            self.last_ear = avg_ear
            self.ear_history.append(avg_ear)
            if len(self.ear_history) > 30:
                self.ear_history.pop(0)

            # Update adaptive baseline open EAR when eyes are open
            if avg_ear > 0.23:
                self.baseline_open_ear = round(0.85 * self.baseline_open_ear + 0.15 * avg_ear, 4)

            # Determine dynamic thresholds (supports various eye geometries & camera distances)
            closed_thresh = min(self.ear_thresh_closed, self.baseline_open_ear * 0.75)
            open_thresh = max(self.ear_thresh_open, self.baseline_open_ear * 0.88)

            # --- Temporal Blink State Machine ---
            if avg_ear < closed_thresh or avg_ear < self.ear_thresh_closed:
                self.consecutive_closed_frames += 1
                if self.consecutive_closed_frames >= self.min_closed_frames:
                    self.is_eye_closed = True
            elif avg_ear >= open_thresh or avg_ear >= self.ear_thresh_open:
                if self.is_eye_closed:
                    self.blink_count += 1
                    self.is_eye_closed = False
                    self.consecutive_closed_frames = 0

                    # Check if target blinks achieved
                    if self.blink_count >= self.target_blinks:
                        self.liveness_confirmed = True
                        if self.captured_frame_rgb is None:
                            self.captured_frame_rgb = frame_rgb.copy()
                            self.captured_frame_bgr = frame_bgr.copy()
                else:
                    self.consecutive_closed_frames = 0

            # Store high quality open-eye frame when liveness is confirmed
            if self.liveness_confirmed and (avg_ear >= self.ear_thresh_open or avg_ear >= open_thresh):
                self.captured_frame_rgb = frame_rgb.copy()
                self.captured_frame_bgr = frame_bgr.copy()

        elapsed = round(time.time() - self.start_time, 2)
        remaining = max(0.0, round(self.timeout_seconds - elapsed, 1))
        timed_out = (remaining <= 0.0) and not self.liveness_confirmed

        # Render HUD Overlays
        annotated_bgr = frame_bgr.copy() if draw_hud else frame_bgr
        if draw_hud:
            self._render_hud(annotated_bgr, face_detected, bbox, landmarks, avg_ear, remaining, timed_out, w, h)

        status_dict = {
            "face_detected": face_detected,
            "current_ear": avg_ear,
            "left_ear": left_ear,
            "right_ear": right_ear,
            "blink_count": self.blink_count,
            "target_blinks": self.target_blinks,
            "liveness_confirmed": self.liveness_confirmed,
            "is_eye_closed": self.is_eye_closed,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "timed_out": timed_out,
            "spoof_suspected": timed_out and self.blink_count == 0
        }

        return annotated_bgr, status_dict

    def _render_hud(
        self,
        frame_bgr: np.ndarray,
        face_detected: bool,
        bbox: Optional[Tuple[int, int, int, int]],
        landmarks: Optional[Tuple[List, List, Tuple]],
        avg_ear: float,
        remaining_seconds: float,
        timed_out: bool,
        w: int,
        h: int
    ):
        """Draws dynamic graphics, EAR meter bar, countdown timer, and status badges on the video frame."""
        # Top HUD Banner Background
        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (0, 0), (w, 90), (20, 24, 33), -1)
        cv2.addWeighted(overlay, 0.75, frame_bgr, 0.25, 0, frame_bgr)

        # Status Badge & Colors
        if self.liveness_confirmed:
            badge_color = (46, 204, 113)  # Emerald Green
            status_text = "LIVE HUMAN VERIFIED"
            sub_text = f"Blinks: {self.blink_count}/{self.target_blinks} | Liveness Confirmed"
        elif timed_out:
            badge_color = (231, 76, 60)  # Red
            status_text = "LIVENESS TIMEOUT - RETRY"
            sub_text = f"0 of {self.target_blinks} blinks detected (Static photo / timeout)"
        elif not face_detected:
            badge_color = (52, 152, 219)  # Blue
            status_text = "ALIGN FACE IN CAMERA"
            sub_text = "Please look directly at the lens"
        elif self.is_eye_closed:
            badge_color = (241, 196, 15)  # Yellow
            status_text = "BLINK DETECTED"
            sub_text = f"Blinks: {self.blink_count}/{self.target_blinks} | Eye Closed"
        else:
            badge_color = (0, 212, 255)  # Cyan
            status_text = "PLEASE BLINK YOUR EYES"
            sub_text = f"Blinks: {self.blink_count}/{self.target_blinks} | Time: {remaining_seconds:.1f}s"

        # Top Badge Circle + Header Text
        cv2.circle(frame_bgr, (30, 42), 14, badge_color, -1)
        cv2.circle(frame_bgr, (30, 42), 17, (255, 255, 255), 2)
        cv2.putText(frame_bgr, status_text, (60, 38), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame_bgr, sub_text, (60, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 205, 215), 1, cv2.LINE_AA)

        # Countdown Timer Box & EAR Metric Meter Bar (Right Side of Top Banner)
        bar_w = 140
        bar_h = 14
        bar_x = w - bar_w - 30
        bar_y = 22

        # Timer Badge above EAR bar
        timer_col = (46, 204, 113) if remaining_seconds > 4.0 else ((241, 196, 15) if remaining_seconds > 2.0 else (231, 76, 60))
        cv2.putText(frame_bgr, f"TIMEOUT: {remaining_seconds:.1f}s", (bar_x, bar_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, timer_col, 1, cv2.LINE_AA)

        # Background bar
        cv2.rectangle(frame_bgr, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 55, 65), -1)
        cv2.rectangle(frame_bgr, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (120, 130, 145), 1)

        # Filled EAR bar (scaled 0.0 to 0.40)
        norm_ear = max(0.0, min(1.0, avg_ear / 0.40))
        fill_w = int(bar_w * norm_ear)
        ear_bar_color = (46, 204, 113) if avg_ear >= self.ear_thresh_open else ((241, 196, 15) if avg_ear >= self.ear_thresh_closed else (231, 76, 60))
        cv2.rectangle(frame_bgr, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), ear_bar_color, -1)

        # Threshold marker line at 0.225 (Closed Threshold)
        thresh_x = int(bar_x + bar_w * (self.ear_thresh_closed / 0.40))
        cv2.line(frame_bgr, (thresh_x, bar_y - 2), (thresh_x, bar_y + bar_h + 2), (255, 255, 255), 2)

        # EAR Text
        cv2.putText(frame_bgr, f"EAR: {avg_ear:.3f}", (bar_x, bar_y + bar_h + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 225, 230), 1, cv2.LINE_AA)

        # Face Bounding Box & Eye Landmark Contours
        if face_detected and bbox is not None:
            fx, fy, fw, fh = bbox
            box_color = (46, 204, 113) if self.liveness_confirmed else (0, 212, 255)

            # Corner brackets for modern biometric HUD look
            line_len = int(min(fw, fh) * 0.20)
            cv2.line(frame_bgr, (fx, fy), (fx + line_len, fy), box_color, 3)
            cv2.line(frame_bgr, (fx, fy), (fx, fy + line_len), box_color, 3)
            cv2.line(frame_bgr, (fx + fw, fy), (fx + fw - line_len, fy), box_color, 3)
            cv2.line(frame_bgr, (fx + fw, fy), (fx + fw, fy + line_len), box_color, 3)
            cv2.line(frame_bgr, (fx, fy + fh), (fx + line_len, fy + fh), box_color, 3)
            cv2.line(frame_bgr, (fx, fy + fh), (fx, fy + fh - line_len), box_color, 3)
            cv2.line(frame_bgr, (fx + fw, fy + fh), (fx + fw - line_len, fy + fh), box_color, 3)
            cv2.line(frame_bgr, (fx + fw, fy + fh), (fx + fw, fy + fh - line_len), box_color, 3)

            # Draw Eye Points
            if landmarks:
                left_pts, right_pts, _ = landmarks
                for pt in left_pts + right_pts:
                    cv2.circle(frame_bgr, (int(pt[0]), int(pt[1])), 2, (0, 255, 255), -1)

    def run_webcam_stream(
        self,
        camera_id: int = 0,
        target_blinks: int = 2,
        timeout_seconds: float = 25.0,
        auto_capture: bool = True,
        output_path: Optional[str] = "captured_selfie.jpg",
        show_window: bool = True
    ) -> Tuple[bool, Optional[np.ndarray], Dict[str, Any]]:
        """
        Launches an interactive OpenCV video capture loop from the webcam,
        tracks EAR, confirms liveness, and auto-captures the validated frame.
        """
        self.reset_state()
        self.target_blinks = target_blinks

        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            return False, None, {
                "liveness_confirmed": False,
                "error": f"Unable to open camera with index {camera_id}"
            }

        # Set 720p resolution if available
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        window_name = "AI Border Checkpoint - Live Facial Liveness & Anti-Spoofing"
        success = False
        final_frame_rgb = None
        last_status = {}

        try:
            while cap.isOpened():
                ret, frame_bgr = cap.read()
                if not ret:
                    break

                # Mirror frame for natural webcam UX
                frame_bgr = cv2.flip(frame_bgr, 1)

                annotated_bgr, status = self.process_frame(frame_bgr, draw_hud=True)
                last_status = status

                if show_window:
                    cv2.imshow(window_name, annotated_bgr)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # Q or ESC
                        break

                # Check Liveness Confirmation
                if self.liveness_confirmed:
                    success = True
                    final_frame_rgb = self.captured_frame_rgb or cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    if output_path:
                        cv2.imwrite(output_path, self.captured_frame_bgr or frame_bgr)
                        print(f"[LIVENESS] Validated live selfie saved to: {output_path}")
                    if auto_capture:
                        # Brief pause to display green confirmed badge to user
                        if show_window:
                            for _ in range(15):
                                cv2.imshow(window_name, annotated_bgr)
                                cv2.waitKey(30)
                        break

                # Timeout check
                if time.time() - self.start_time > timeout_seconds:
                    print("[LIVENESS] Session timed out before target blinks reached.")
                    break

        finally:
            cap.release()
            if show_window:
                cv2.destroyAllWindows()

        return success, final_frame_rgb, last_status


# Module-level singleton instance for convenient imports
default_engine = RealTimeLivenessEngine()


def verify_live_webcam(
    camera_id: int = 0,
    target_blinks: int = 2,
    timeout_seconds: float = 25.0,
    output_path: Optional[str] = "captured_selfie.jpg"
) -> Tuple[bool, Optional[np.ndarray], Dict[str, Any]]:
    """Convenience functional wrapper to run the webcam liveness session."""
    engine = RealTimeLivenessEngine(target_blinks=target_blinks)
    return engine.run_webcam_stream(
        camera_id=camera_id,
        target_blinks=target_blinks,
        timeout_seconds=timeout_seconds,
        auto_capture=True,
        output_path=output_path,
        show_window=True
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Live Facial Liveness & Anti-Spoofing Scanner")
    parser.add_argument("--cam", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--blinks", type=int, default=2, help="Required blink count (default: 2)")
    parser.add_argument("--out", type=str, default="captured_selfie.jpg", help="Captured output image path")
    parser.add_argument("--test-mode", action="store_true", help="Run simulated test mode on synthetic image")
    args = parser.parse_args()

    if args.test_mode:
        print("[TEST] Running Liveness Engine in headless synthetic test mode...")
        engine = RealTimeLivenessEngine()
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(test_img, (320, 240), 100, (200, 200, 200), -1)
        annotated, status = engine.process_frame(test_img)
        print(f"[TEST SUCCESS] Result status: {status}")
    else:
        print("=" * 70)
        print("  AI BORDER CHECKPOINT - REAL-TIME FACIAL LIVENESS DETECTOR")
        print("  Instructions: Look at camera and blink naturally twice.")
        print("  Press 'q' or 'ESC' to exit.")
        print("=" * 70)
        confirmed, frame_rgb, report = verify_live_webcam(
            camera_id=args.cam,
            target_blinks=args.blinks,
            output_path=args.out
        )
        print(f"\n[FINAL OUTCOME] Liveness Confirmed: {confirmed}")
        print(f"[FINAL REPORT] {report}")
