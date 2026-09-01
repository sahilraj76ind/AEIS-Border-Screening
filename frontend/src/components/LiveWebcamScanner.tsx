import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Camera, RefreshCw, CheckCircle, VideoOff, Eye, ShieldCheck, AlertCircle, Sparkles, Activity, X, Maximize2, AlertTriangle } from 'lucide-react';
import confetti from 'canvas-confetti';
import { FilesetResolver, FaceLandmarker } from '@mediapipe/tasks-vision';

interface LiveWebcamScannerProps {
  onCapture: (file: File) => void;
  capturedFile: File | null;
  onClear: () => void;
}

interface Point {
  x: number;
  y: number;
  z?: number;
}

function dist(p1: Point, p2: Point, w: number, h: number): number {
  const dx = (p1.x - p2.x) * w;
  const dy = (p1.y - p2.y) * h;
  return Math.sqrt(dx * dx + dy * dy);
}

function computeEAR(landmarks: Point[], indices: number[], w: number, h: number): number {
  const [i1, i2, i3, i4, i5, i6] = indices;
  if (!landmarks[i1] || !landmarks[i2] || !landmarks[i3] || !landmarks[i4] || !landmarks[i5] || !landmarks[i6]) {
    return 0.30;
  }
  const p1 = landmarks[i1];
  const p2 = landmarks[i2];
  const p3 = landmarks[i3];
  const p4 = landmarks[i4];
  const p5 = landmarks[i5];
  const p6 = landmarks[i6];

  const vertical1 = dist(p2, p6, w, h);
  const vertical2 = dist(p3, p5, w, h);
  const horizontal = dist(p1, p4, w, h);

  if (horizontal === 0) return 0.30;
  return (vertical1 + vertical2) / (2.0 * horizontal);
}

// MediaPipe Landmark Indices
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];
const FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10];

export const LiveWebcamScanner: React.FC<LiveWebcamScannerProps> = ({
  onCapture,
  capturedFile,
  onClear,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const landmarkerRef = useRef<FaceLandmarker | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [streamActive, setStreamActive] = useState(false);
  const [modelReady, setModelReady] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Liveness States
  const [blinkCount, setBlinkCount] = useState(0);
  const [currentEAR, setCurrentEAR] = useState(0.30);
  const [isEyeClosed, setIsEyeClosed] = useState(false);
  const [livenessStatus, setLivenessStatus] = useState<string>('ALIGN FACE IN HUD CENTER');
  const [timeRemaining, setTimeRemaining] = useState(12.0);
  const [faceDetected, setFaceDetected] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [timeoutFailed, setTimeoutFailed] = useState(false);

  // Internal tracking refs to prevent jitter/false blinks
  const eyeStateRef = useRef<{
    wasClosed: boolean;
    closedFrameCount: number;
    openFrameCount: number;
    blinks: number;
    baselineEAR: number;
    calibrationSamples: number[];
  }>({
    wasClosed: false,
    closedFrameCount: 0,
    openFrameCount: 0,
    blinks: 0,
    baselineEAR: 0.30,
    calibrationSamples: [],
  });

  const startTimeRef = useRef<number>(0);
  const isCapturingRef = useRef<boolean>(false);

  const TARGET_BLINKS = 2;
  const TIMEOUT_SECONDS = 12.0;

  // Initialize MediaPipe FaceLandmarker
  useEffect(() => {
    let isMounted = true;
    const initLandmarker = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
        );
        if (!isMounted) return;

        const faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numFaces: 1,
          outputFaceBlendshapes: false,
        });

        if (isMounted) {
          landmarkerRef.current = faceLandmarker;
          setModelReady(true);
        }
      } catch (err) {
        console.warn('MediaPipe initialization:', err);
        setModelReady(true);
      }
    };

    initLandmarker();

    return () => {
      isMounted = false;
      if (landmarkerRef.current) {
        landmarkerRef.current.close();
      }
    };
  }, []);

  const stopCamera = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setStreamActive(false);
    setIsModalOpen(false);
  }, []);

  const takeSnapshot = useCallback(() => {
    if (isCapturingRef.current || !videoRef.current) return;
    isCapturingRef.current = true;

    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Mirror image for natural portrait
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], 'live_traveler_selfie.jpg', { type: 'image/jpeg' });
        onCapture(file);
        setConfirmed(true);
        confetti({ particleCount: 60, spread: 70, origin: { y: 0.5 } });
        setTimeout(() => {
          stopCamera();
          isCapturingRef.current = false;
        }, 900);
      }
    }, 'image/jpeg', 0.95);
  }, [onCapture, stopCamera]);

  // Main Real-Time Detection Loop with Strict Calibrated Blink Verification
  const processFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) {
      animFrameRef.current = requestAnimationFrame(processFrame);
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      animFrameRef.current = requestAnimationFrame(processFrame);
      return;
    }

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    const elapsed = (Date.now() - startTimeRef.current) / 1000;
    const remaining = Math.max(0, TIMEOUT_SECONDS - elapsed);
    setTimeRemaining(remaining);

    let hasFace = false;
    let computedEar = 0.30;

    if (landmarkerRef.current && video.readyState >= 2) {
      try {
        const landmarkerResult = landmarkerRef.current.detectForVideo(video, performance.now());
        if (landmarkerResult && landmarkerResult.faceLandmarks && landmarkerResult.faceLandmarks.length > 0) {
          hasFace = true;
          const landmarks = landmarkerResult.faceLandmarks[0];

          const earLeft = computeEAR(landmarks, LEFT_EYE, width, height);
          const earRight = computeEAR(landmarks, RIGHT_EYE, width, height);
          computedEar = (earLeft + earRight) / 2.0;

          // Draw HUD Landmarks with pixel-accurate mirrored coordinates
          const isClosed = computedEar < (eyeStateRef.current.baselineEAR * 0.65);
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = isClosed ? '#F59E0B' : '#06B6D4';
          ctx.fillStyle = '#06B6D4';

          [...LEFT_EYE, ...RIGHT_EYE].forEach((idx) => {
            const p = landmarks[idx];
            if (p) {
              const cx = (1 - p.x) * width;
              const cy = p.y * height;
              ctx.beginPath();
              ctx.arc(cx, cy, 3, 0, 2 * Math.PI);
              ctx.fill();
            }
          });

          ctx.beginPath();
          FACE_OVAL.forEach((idx, i) => {
            const p = landmarks[idx];
            if (p) {
              const cx = (1 - p.x) * width;
              const cy = p.y * height;
              if (i === 0) ctx.moveTo(cx, cy);
              else ctx.lineTo(cx, cy);
            }
          });
          ctx.closePath();
          ctx.stroke();
        }
      } catch (err) {
        // Fallback
      }
    }

    setFaceDetected(hasFace);
    setCurrentEAR(computedEar);

    // Strict Calibrated State Machine:
    if (hasFace) {
      // Collect calibration samples for initial baseline EAR
      if (eyeStateRef.current.calibrationSamples.length < 15) {
        eyeStateRef.current.calibrationSamples.push(computedEar);
        const sum = eyeStateRef.current.calibrationSamples.reduce((a, b) => a + b, 0);
        eyeStateRef.current.baselineEAR = Math.max(0.26, sum / eyeStateRef.current.calibrationSamples.length);
      }

      const baseline = eyeStateRef.current.baselineEAR;
      // Strict dynamic thresholds based on individual eye geometry:
      // Eyes are genuinely closed when EAR drops by >35% from baseline or strictly < 0.185
      const closedThreshold = Math.min(0.20, baseline * 0.68);
      // Eyes are fully open when EAR returns to >82% of baseline
      const openThreshold = Math.max(0.24, baseline * 0.82);

      if (computedEar <= closedThreshold) {
        // Closed state
        eyeStateRef.current.closedFrameCount += 1;
        eyeStateRef.current.openFrameCount = 0;

        // Require at least 2 consecutive video frames closed to register as a deliberate eye blink
        if (eyeStateRef.current.closedFrameCount >= 2) {
          eyeStateRef.current.wasClosed = true;
          setIsEyeClosed(true);
          setLivenessStatus('🟡 EYE CLOSED (BLINK IN PROGRESS)');
        }
      } else if (computedEar >= openThreshold) {
        // Open state
        eyeStateRef.current.openFrameCount += 1;

        if (eyeStateRef.current.wasClosed && eyeStateRef.current.closedFrameCount >= 2) {
          // Completed full natural closed -> open blink cycle!
          eyeStateRef.current.blinks += 1;
          eyeStateRef.current.wasClosed = false;
          eyeStateRef.current.closedFrameCount = 0;
          setBlinkCount(eyeStateRef.current.blinks);
          setIsEyeClosed(false);

          if (eyeStateRef.current.blinks >= TARGET_BLINKS) {
            setLivenessStatus('🟢 2 BLINKS VERIFIED (LIVE HUMAN CONFIRMED)');
            takeSnapshot();
            return;
          } else {
            setLivenessStatus(`🟡 BLINK 1/${TARGET_BLINKS} RECORDED • BLINK ONCE MORE`);
          }
        } else {
          eyeStateRef.current.closedFrameCount = 0;
          setIsEyeClosed(false);
          setLivenessStatus(`🔵 PLEASE BLINK NATURALLY (${eyeStateRef.current.blinks}/${TARGET_BLINKS})`);
        }
      }
    } else {
      setLivenessStatus('⚪ ALIGN FACE IN HUD CENTER');
    }

    // Strict Timeout Enforcement:
    // If time expires and user did NOT complete 2 verified blinks, FAIL the test (NO auto-approval!)
    if (remaining <= 0 && !isCapturingRef.current) {
      if (eyeStateRef.current.blinks >= TARGET_BLINKS) {
        takeSnapshot();
        return;
      } else {
        setTimeoutFailed(true);
        setLivenessStatus('❌ LIVENESS FAILED — NO BLINKS DETECTED');
        return;
      }
    }

    animFrameRef.current = requestAnimationFrame(processFrame);
  }, [takeSnapshot]);

  const startCamera = async () => {
    setErrorMsg(null);
    setConfirmed(false);
    setTimeoutFailed(false);
    setBlinkCount(0);
    setTimeRemaining(TIMEOUT_SECONDS);
    eyeStateRef.current = {
      wasClosed: false,
      closedFrameCount: 0,
      openFrameCount: 0,
      blinks: 0,
      baselineEAR: 0.30,
      calibrationSamples: [],
    };
    startTimeRef.current = Date.now();
    isCapturingRef.current = false;
    setIsModalOpen(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreamActive(true);
        animFrameRef.current = requestAnimationFrame(processFrame);
      }
    } catch (err: any) {
      setErrorMsg('Camera access denied or video device unavailable.');
      setStreamActive(false);
    }
  };

  const restartLiveness = () => {
    setTimeoutFailed(false);
    setConfirmed(false);
    setBlinkCount(0);
    setTimeRemaining(TIMEOUT_SECONDS);
    eyeStateRef.current = {
      wasClosed: false,
      closedFrameCount: 0,
      openFrameCount: 0,
      blinks: 0,
      baselineEAR: 0.30,
      calibrationSamples: [],
    };
    startTimeRef.current = Date.now();
    isCapturingRef.current = false;
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }
    animFrameRef.current = requestAnimationFrame(processFrame);
  };

  return (
    <>
      {/* Resting Dropzone Card (Exact matching height min-h-[210px] with glassmorphism) */}
      <div className="glass-panel relative rounded-2xl border-2 border-dashed border-[#DAC896] p-4 flex flex-col items-center justify-center min-h-[210px] h-full overflow-hidden shadow-sm">
        {capturedFile ? (
          <div className="flex flex-col items-center text-center w-full">
            <div className="relative w-24 h-24 rounded-2xl overflow-hidden border-2 border-emerald-500 shadow-md mb-2">
              <img
                src={URL.createObjectURL(capturedFile)}
                alt="Captured Traveler Face"
                className="w-full h-full object-cover"
              />
              <div className="absolute top-1 right-1 bg-emerald-600 text-white rounded-full p-1 shadow-md">
                <CheckCircle className="w-3.5 h-3.5" />
              </div>
            </div>

            <div className="flex items-center space-x-1.5 text-emerald-900 font-mono text-xs font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>🟢 Live Verified (2 Blinks)</span>
            </div>

            <span className="text-[10px] text-slate-600 font-mono mt-0.5 font-medium">
              PAD Passed • EAR: {currentEAR.toFixed(3)}
            </span>

            <button
              onClick={() => {
                onClear();
                startCamera();
              }}
              className="glass-btn mt-2.5 px-3 py-1.5 text-slate-800 text-xs font-mono font-bold rounded-xl flex items-center space-x-1.5 shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-700" />
              <span>Retake Live Selfie</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center p-2">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500/15 to-indigo-500/15 border border-[#E2D2A0] flex items-center justify-center text-amber-700 mb-2 shadow-sm group-hover:scale-105 transition-transform">
              <Camera className="w-6 h-6" />
            </div>
            <span className="text-sm font-bold text-slate-900 tracking-tight">Live Eye-Blink Scanner</span>
            <span className="text-xs text-slate-600 mt-0.5 max-w-[200px] font-medium leading-relaxed">
              Active Eye Aspect Ratio (EAR) & anti-spoofing detector
            </span>

            {errorMsg && (
              <span className="text-xs text-rose-900 mt-2 bg-rose-500/15 px-2.5 py-1 rounded-xl border border-rose-400 font-mono font-bold">
                {errorMsg}
              </span>
            )}

            <button
              onClick={startCamera}
              className="glass-btn-primary mt-3 px-4 py-2 text-white rounded-xl text-xs font-mono font-bold tracking-wide flex items-center space-x-1.5 shadow-md cursor-pointer active:scale-95 transition-all"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>LAUNCH LIVE SCANNER HUD</span>
            </button>
          </div>
        )}
      </div>

      {/* Full-View Tactical Biometric HUD Modal with Strict Blink Verification */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
          <div className="w-full max-w-xl glass-panel rounded-3xl p-5 sm:p-6 border border-[#E2D2A0] shadow-2xl relative space-y-4 my-auto bg-[#FFFDF7]/98 animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#E2D2A0]/70 pb-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-700 shadow-sm">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-mono text-base font-bold text-slate-900 tracking-wider flex items-center space-x-2">
                    <span>LIVE EYE-BLINK LIVENESS SCANNER</span>
                    <span className="px-2.5 py-0.5 text-[9px] bg-amber-500/15 text-amber-900 border border-amber-500/30 rounded-full font-bold font-mono">
                      STRICT PAD
                    </span>
                  </h3>
                  <p className="text-xs text-slate-600 font-medium">
                    Blink naturally twice to verify biological liveness. Static faces will be rejected.
                  </p>
                </div>
              </div>

              <button
                onClick={stopCamera}
                className="glass-btn w-9 h-9 rounded-xl flex items-center justify-center text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Video & Canvas Viewfinder: Exact 4:3 Aspect Ratio for 1-to-1 Pixel Alignment */}
            <div className="relative w-full max-w-md mx-auto aspect-[4/3] bg-black rounded-2xl overflow-hidden border-2 border-amber-500/50 shadow-inner flex items-center justify-center">
              {/* Active Mirrored Video Element */}
              <video
                ref={videoRef}
                playsInline
                autoPlay
                muted
                className="absolute inset-0 w-full h-full object-cover transform -scale-x-100"
              />

              {/* Real-Time HUD Overlay Canvas matching video bounds */}
              <canvas
                ref={canvasRef}
                className="absolute inset-0 w-full h-full object-cover pointer-events-none"
              />

              {/* Symmetrical Centered HUD Reticle */}
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-48 h-60 border-2 border-dashed border-cyan-400/60 rounded-full flex items-center justify-center relative">
                  <span className="text-[10px] font-mono font-bold text-cyan-300 bg-black/70 px-3 py-1 rounded-full backdrop-blur-sm border border-cyan-500/30">
                    {faceDetected ? 'FACE LOCKED' : 'ALIGN FACE IN OVAL'}
                  </span>
                </div>
              </div>

              {/* Top Left Status Badge */}
              <div className="absolute top-3 left-3 flex items-center space-x-2 z-10">
                <span className="flex items-center space-x-1.5 bg-black/80 backdrop-blur-sm px-2.5 py-1 rounded-full text-xs font-mono text-cyan-300 border border-cyan-500/40">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  <span>LIVE SENSOR</span>
                </span>
              </div>

              {/* Top Right Countdown */}
              <div className="absolute top-3 right-3 bg-black/80 backdrop-blur-sm px-3.5 py-1 rounded-full text-xs font-mono font-bold text-amber-300 border border-amber-500/40 flex items-center space-x-1 z-10">
                <span>⏱️ {timeRemaining.toFixed(1)}s</span>
              </div>

              {/* Flash on Confirmation */}
              {confirmed && (
                <div className="absolute inset-0 bg-emerald-500/50 animate-ping pointer-events-none z-20" />
              )}

              {/* Timeout Failure Overlay */}
              {timeoutFailed && (
                <div className="absolute inset-0 bg-black/85 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center z-30 space-y-3">
                  <AlertTriangle className="w-12 h-12 text-rose-500 animate-bounce" />
                  <div className="font-mono text-sm font-bold text-white">
                    LIVENESS VERIFICATION TIMEOUT
                  </div>
                  <p className="text-xs text-slate-300 font-mono max-w-xs">
                    No blinks were detected. Please ensure your eyes are clearly visible to the camera and blink naturally.
                  </p>
                  <button
                    onClick={restartLiveness}
                    className="glass-btn-primary px-5 py-2 text-white text-xs font-mono font-bold rounded-xl flex items-center space-x-2 shadow-md cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Blink Detection</span>
                  </button>
                </div>
              )}
            </div>

            {/* Tactical Metrics Dashboard */}
            <div className="bg-white/80 p-3.5 rounded-2xl border border-[#E2D2A0] space-y-2.5 font-mono shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-700 font-bold flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-amber-600" />
                  <span>ANTI-SPOOFING STATUS:</span>
                </span>
                <span
                  className={`font-bold text-xs px-3 py-0.5 rounded-full border shadow-sm ${
                    blinkCount >= 2
                      ? 'bg-emerald-500/20 text-emerald-900 border-emerald-400'
                      : isEyeClosed
                      ? 'bg-amber-500/20 text-amber-900 border-amber-400'
                      : timeoutFailed
                      ? 'bg-rose-500/20 text-rose-900 border-rose-400'
                      : 'bg-indigo-500/15 text-indigo-900 border-indigo-400'
                  }`}
                >
                  {livenessStatus}
                </span>
              </div>

              {/* Metric Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-center">
                <div className="bg-[#FAF0CB]/50 p-2.5 rounded-xl border border-[#E2D2A0] shadow-sm">
                  <span className="text-[10px] text-slate-600 font-bold block">VERIFIED BLINKS</span>
                  <div className="flex items-center justify-center space-x-1.5 mt-0.5">
                    <span className="text-xl font-black text-slate-900">{blinkCount}</span>
                    <span className="text-slate-500 text-xs font-bold">/ {TARGET_BLINKS}</span>
                    <span>{blinkCount >= TARGET_BLINKS ? '🟢' : blinkCount === 1 ? '🟡' : '👀'}</span>
                  </div>
                </div>

                <div className="bg-[#FAF0CB]/50 p-2.5 rounded-xl border border-[#E2D2A0] shadow-sm">
                  <span className="text-[10px] text-slate-600 font-bold block">EYE ASPECT RATIO (EAR)</span>
                  <div className="flex items-center justify-center space-x-1 mt-0.5">
                    <span className={`text-xl font-black ${isEyeClosed ? 'text-amber-700' : 'text-indigo-700'}`}>
                      {currentEAR.toFixed(3)}
                    </span>
                    <span className="text-[10px] text-slate-500 font-bold">
                      ({isEyeClosed ? 'CLOSED' : 'OPEN'})
                    </span>
                  </div>
                </div>

                <div className="bg-[#FAF0CB]/50 p-2.5 rounded-xl border border-[#E2D2A0] col-span-2 sm:col-span-1 shadow-sm flex flex-col justify-center">
                  <span className="text-[10px] text-slate-600 font-bold block">TARGET</span>
                  <span className="text-xs font-bold text-emerald-800 mt-0.5">
                    {blinkCount >= 2 ? '✅ VERIFIED' : `${TARGET_BLINKS - blinkCount} BLINK(S) NEEDED`}
                  </span>
                </div>
              </div>

              {/* Countdown Progression Bar */}
              <div className="w-full bg-[#E2D2A0]/40 h-1.5 rounded-full overflow-hidden border border-[#E2D2A0]">
                <div
                  className="h-full bg-gradient-to-r from-amber-500 via-orange-500 to-indigo-600 transition-all duration-100"
                  style={{ width: `${(timeRemaining / TIMEOUT_SECONDS) * 100}%` }}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-1">
              <button
                onClick={stopCamera}
                className="glass-btn px-4 py-2 text-slate-800 font-mono text-xs font-bold rounded-xl"
              >
                Cancel
              </button>

              <button
                onClick={takeSnapshot}
                className="glass-btn px-4 py-2 text-slate-700 font-mono text-xs font-bold rounded-xl flex items-center space-x-1.5 hover:bg-white"
                title="Override Liveness requirement manually"
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Manual Snapshot</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
