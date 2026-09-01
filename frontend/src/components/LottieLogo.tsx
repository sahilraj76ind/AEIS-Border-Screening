import React, { useEffect, useRef } from 'react';
import lottie, { type AnimationItem } from 'lottie-web/build/player/lottie_light';

interface LottieLogoProps {
  className?: string;
  loop?: boolean;
  autoplay?: boolean;
  speed?: number;
  onComplete?: () => void;
}

export const LottieLogo: React.FC<LottieLogoProps> = ({
  className = 'w-full h-full',
  loop = false,
  autoplay = true,
  speed = 1,
  onComplete,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<AnimationItem | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy existing animation before creating a new one
    if (animRef.current) {
      animRef.current.destroy();
    }

    const anim = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop: loop,
      autoplay: autoplay,
      path: '/Scene.json',
    });

    anim.setSpeed(speed);

    if (onComplete) {
      anim.addEventListener('complete', onComplete);
    }

    animRef.current = anim;

    return () => {
      anim.destroy();
      animRef.current = null;
    };
  }, [loop, autoplay, speed, onComplete]);

  return <div ref={containerRef} className={className} />;
};
