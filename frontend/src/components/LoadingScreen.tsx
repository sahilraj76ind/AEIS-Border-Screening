import React, { useEffect, useRef, useState } from 'react';

interface LoadingScreenProps {
  onFinish?: () => void;
  minDurationMs?: number;
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({
  onFinish,
  minDurationMs = 2800,
}) => {
  const [isFadingOut, setIsFadingOut] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const finishedRef = useRef(false);

  const completeLoading = () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setIsFadingOut(true);
    setTimeout(() => {
      onFinish?.();
    }, 600); // match transition duration
  };

  useEffect(() => {
    // Attempt auto-play
    if (videoRef.current) {
      videoRef.current.play().catch(() => {
        // Fallback for browser autoplay policy
      });
    }

    // Safety timeout ensuring smooth transition even if video playback has latency
    const timer = setTimeout(() => {
      completeLoading();
    }, minDurationMs);

    return () => clearTimeout(timer);
  }, [minDurationMs]);

  return (
    <div
      className={`fixed inset-0 z-[9999] flex items-center justify-center transition-opacity duration-600 ease-in-out select-none ${
        isFadingOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{
        background: '#FDF4D2',
      }}
    >
      <div className="relative w-full max-w-2xl px-4 sm:px-6 flex items-center justify-center">
          <img src="/logo-gemini-clean.gif" alt="AEIS Logo Animation" className="w-full h-full object-contain rounded-2xl" />

        {/* <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          onEnded={completeLoading}
          className="w-full h-auto max-h-[85vh] object-contain rounded-2xl drop-shadow-2xl"
        >
           <source src="/logo-gemini-clean.mp4" type="video/mp4" />
          <source src="/logo-gemini.mp4" type="video/mp4" /> 
          Fallback image 
        </video> */}
      </div>
    </div>
  );
};
