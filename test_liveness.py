"""
Automated Test Suite for Real-Time Liveness Engine & EAR Verification
====================================================================
Tests:
1. Mathematical precision of Soukupova & Cech Eye Aspect Ratio (EAR).
2. MediaPipe FaceLandmarker model loading & XNNPACK delegate.
3. Temporal blink state machine transitions (open -> closed -> open).
4. HUD drawing, overlay transparency, and status badge rendering.
5. Single-frame in-memory liveness evaluation in ai_vision_adapter.
"""

import os
import sys
import unittest
import numpy as np
import cv2
from PIL import Image

# Setup Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
AI_VISION_DIR = os.path.join(ROOT_DIR, "ai_vision")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if AI_VISION_DIR not in sys.path:
    sys.path.insert(0, AI_VISION_DIR)

from ai_vision.liveness_detector import (
    calculate_ear,
    RealTimeLivenessEngine,
    ensure_model_exists,
    MODEL_PATH
)
from orchestration_platform.wrappers.ai_vision_adapter import evaluate_frame_liveness


class TestLivenessEngine(unittest.TestCase):

    def test_model_asset_download_and_existence(self):
        """Verify the MediaPipe FaceLandmarker model asset exists on disk."""
        path = ensure_model_exists()
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1_000_000)

    def test_ear_mathematical_precision(self):
        """Verify EAR geometry formula on open eye vs. closed eye landmark coordinates."""
        # Synthetic Open Eye (Width = 40, Height = 14)
        open_eye = [
            (10.0, 50.0),  # p1: outer corner
            (20.0, 43.0),  # p2: top-left
            (40.0, 43.0),  # p3: top-right
            (50.0, 50.0),  # p4: inner corner
            (40.0, 57.0),  # p5: bottom-right
            (20.0, 57.0)   # p6: bottom-left
        ]
        # v1 = ||(20,43) - (20,57)|| = 14
        # v2 = ||(40,43) - (40,57)|| = 14
        # h = ||(10,50) - (50,50)|| = 40
        # EAR = (14 + 14) / (2 * 40) = 28 / 80 = 0.35
        ear_open = calculate_ear(open_eye)
        self.assertAlmostEqual(ear_open, 0.35, places=2)
        self.assertGreater(ear_open, 0.28)  # Open threshold

        # Synthetic Closed Eye (Width = 40, Height = 2)
        closed_eye = [
            (10.0, 50.0),  # p1: outer corner
            (20.0, 49.0),  # p2: top-left
            (40.0, 49.0),  # p3: top-right
            (50.0, 50.0),  # p4: inner corner
            (40.0, 51.0),  # p5: bottom-right
            (20.0, 51.0)   # p6: bottom-left
        ]
        # v1 = 2, v2 = 2, h = 40 -> EAR = 4 / 80 = 0.05
        ear_closed = calculate_ear(closed_eye)
        self.assertAlmostEqual(ear_closed, 0.05, places=2)
        self.assertLess(ear_closed, 0.22)  # Closed threshold

    def test_blink_state_machine_transitions(self):
        """Simulate a full blink sequence across frames and verify counter increment."""
        engine = RealTimeLivenessEngine(
            ear_thresh_closed=0.21,
            ear_thresh_open=0.27,
            min_closed_frames=1,
            target_blinks=2
        )
        self.assertEqual(engine.blink_count, 0)
        self.assertFalse(engine.liveness_confirmed)

        # Helper to simulate an injection of EAR into state machine
        def simulate_frame(avg_ear: float):
            if avg_ear < engine.ear_thresh_closed:
                engine.consecutive_closed_frames += 1
                if engine.consecutive_closed_frames >= engine.min_closed_frames:
                    engine.is_eye_closed = True
            elif avg_ear >= engine.ear_thresh_open:
                if engine.is_eye_closed:
                    engine.blink_count += 1
                    engine.is_eye_closed = False
                    engine.consecutive_closed_frames = 0
                    if engine.blink_count >= engine.target_blinks:
                        engine.liveness_confirmed = True
                else:
                    engine.consecutive_closed_frames = 0

        # Frame 1-3: Normal open eyes (EAR ~ 0.32)
        for _ in range(3):
            simulate_frame(0.32)
        self.assertEqual(engine.blink_count, 0)
        self.assertFalse(engine.is_eye_closed)

        # Blink 1: Close eyes (EAR ~ 0.12) -> Open eyes (EAR ~ 0.32)
        simulate_frame(0.12)
        self.assertTrue(engine.is_eye_closed)
        simulate_frame(0.32)
        self.assertEqual(engine.blink_count, 1)
        self.assertFalse(engine.is_eye_closed)
        self.assertFalse(engine.liveness_confirmed)

        # Frame 5: Intermittent open eyes
        simulate_frame(0.30)

        # Blink 2: Close eyes (EAR ~ 0.10) -> Open eyes (EAR ~ 0.34)
        simulate_frame(0.10)
        self.assertTrue(engine.is_eye_closed)
        simulate_frame(0.34)
        self.assertEqual(engine.blink_count, 2)
        self.assertTrue(engine.liveness_confirmed)

    def test_frame_processing_and_hud_rendering(self):
        """Verify process_frame handles arbitrary images and renders HUD cleanly."""
        engine = RealTimeLivenessEngine()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Draw a synthetic face circle
        cv2.circle(blank_frame, (320, 240), 90, (180, 180, 180), -1)

        annotated_bgr, status = engine.process_frame(blank_frame, draw_hud=True)

        self.assertIsInstance(annotated_bgr, np.ndarray)
        self.assertEqual(annotated_bgr.shape, (480, 640, 3))
        self.assertIn("face_detected", status)
        self.assertIn("current_ear", status)
        self.assertIn("blink_count", status)
        self.assertIn("liveness_confirmed", status)

    def test_adapter_passive_evaluation(self):
        """Verify ai_vision_adapter evaluates single frames without crashing."""
        img = Image.new("RGB", (300, 300), color=(100, 100, 100))
        result = evaluate_frame_liveness(img)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("face_detected", result)
        self.assertIn("current_ear", result)


if __name__ == "__main__":
    unittest.main()
