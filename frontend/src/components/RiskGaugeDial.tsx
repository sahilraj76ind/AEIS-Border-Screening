import React, { useEffect, useState } from 'react';
import { ShieldCheck, AlertTriangle, ShieldAlert, Sparkles, Activity } from 'lucide-react';

interface RiskGaugeDialProps {
  score: number;
  verdict: 'ACCEPT' | 'MANUAL_REVIEW' | 'REJECT' | string;
  tier: 'LOW' | 'ELEVATED' | 'HIGH' | 'CRITICAL' | string;
}

export const RiskGaugeDial: React.FC<RiskGaugeDialProps> = ({ score, verdict, tier }) => {
  const [animatedScore, setAnimatedScore] = useState(0);
  const normalizedScore = Math.max(0, Math.min(100, score));

  // Smooth count-up animation on score change
  useEffect(() => {
    let startTimestamp: number | null = null;
    const duration = 1400; // ms
    const startScore = 0;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(startScore + (normalizedScore - startScore) * easeOut);

      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };

    window.requestAnimationFrame(step);
  }, [normalizedScore]);

  // Calculate needle angle (-90deg to +90deg)
  const needleAngle = -90 + (animatedScore / 100) * 180;

  const isAccept = verdict === 'ACCEPT';
  const isReview = verdict === 'MANUAL_REVIEW';
  const isReject = verdict === 'REJECT';

  // Dynamic theme colors for score
  const scoreColor =
    normalizedScore > 65
      ? '#EF4444'
      : normalizedScore > 30
      ? '#F59E0B'
      : '#10B981';

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col items-center justify-center relative overflow-hidden border border-[#E2D2A0]/70 shadow-lg">
      {/* Background Subtle Radar Grid & Ambient Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-500/10 via-transparent to-transparent pointer-events-none" />

      {/* Top Header Badge */}
      <div className="w-full flex items-center justify-between mb-2 text-xs font-mono">
        <span className="flex items-center space-x-1 text-slate-700 font-bold">
          <Activity className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
          <span>NEURAL RISK TELEMETRY</span>
        </span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-800 border border-amber-500/30">
          REAL-TIME GAUGE
        </span>
      </div>

      {/* SVG Semi-Circle Gauge */}
      <div className="relative w-64 h-36 flex items-center justify-center">
        <svg viewBox="0 0 200 120" className="w-full h-full drop-shadow-md">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="40%" stopColor="#10B981" />
              <stop offset="65%" stopColor="#F59E0B" />
              <stop offset="85%" stopColor="#EF4444" />
              <stop offset="100%" stopColor="#DC2626" />
            </linearGradient>

            <filter id="needleGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            <filter id="arcGlow" x="-10%" y="-10%" width="120%" height="120%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Arc Track */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#E2D2A0"
            strokeWidth="14"
            strokeLinecap="round"
            opacity="0.4"
          />

          {/* Value Gradient Track */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray="251.2"
            strokeDashoffset="0"
            filter="url(#arcGlow)"
          />

          {/* Gauge Ticks */}
          <text x="20" y="115" fill="#64748B" fontSize="9" textAnchor="middle" fontFamily="monospace" fontWeight="bold">0</text>
          <text x="100" y="24" fill="#64748B" fontSize="9" textAnchor="middle" fontFamily="monospace" fontWeight="bold">50</text>
          <text x="180" y="115" fill="#64748B" fontSize="9" textAnchor="middle" fontFamily="monospace" fontWeight="bold">100</text>

          {/* Center Pivot Base */}
          <circle cx="100" cy="100" r="10" fill="#FFFDF7" stroke="#CBD5E1" strokeWidth="2" />
          <circle cx="100" cy="100" r="6" fill="#1E293B" />

          {/* Needle Pointer with Smooth Animation */}
          <g
            transform={`rotate(${needleAngle} 100 100)`}
            className="transition-transform duration-300 ease-out"
            filter="url(#needleGlow)"
          >
            <polygon points="97,100 103,100 100,20" fill={scoreColor} />
            <circle cx="100" cy="100" r="3.5" fill="#FFFFFF" />
          </g>
        </svg>

        {/* Center Score Readout */}
        <div className="absolute bottom-1 flex flex-col items-center">
          <span
            className="text-3xl font-mono font-black tracking-tight"
            style={{ color: scoreColor }}
          >
            {animatedScore.toFixed(1)}
          </span>
          <span className="text-[9px] uppercase font-mono tracking-widest text-slate-600 font-bold">
            COMPOSITE RISK / 100
          </span>
        </div>
      </div>

      {/* Operational Verdict Banner */}
      <div className="mt-3 w-full">
        {isAccept && (
          <div className="flex items-center justify-center space-x-2 py-2 px-4 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-800 shadow-sm backdrop-blur-md">
            <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span className="font-bold text-xs sm:text-sm tracking-wide">ACCEPT — STANDARD ENTRY PASS</span>
          </div>
        )}
        {isReview && (
          <div className="flex items-center justify-center space-x-2 py-2 px-4 rounded-xl bg-amber-500/20 border border-amber-500/50 text-amber-900 shadow-sm backdrop-blur-md">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 animate-bounce" />
            <span className="font-bold text-xs sm:text-sm tracking-wide">MANUAL SECONDARY REVIEW</span>
          </div>
        )}
        {isReject && (
          <div className="flex items-center justify-center space-x-2 py-2 px-4 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-900 shadow-sm backdrop-blur-md animate-pulse">
            <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span className="font-bold text-xs sm:text-sm tracking-wide">REJECT — INTERCEPT & DETAIN</span>
          </div>
        )}
      </div>

      {/* Risk Tier Badge */}
      <div className="mt-3 flex items-center space-x-2 text-xs font-mono text-slate-600">
        <span className="font-bold">SEVERITY TIER:</span>
        <span
          className={`px-2.5 py-0.5 rounded-full font-bold shadow-sm ${
            tier === 'CRITICAL'
              ? 'bg-rose-500/20 text-rose-800 border border-rose-400'
              : tier === 'HIGH'
              ? 'bg-orange-500/20 text-orange-800 border border-orange-400'
              : tier === 'ELEVATED'
              ? 'bg-amber-500/20 text-amber-800 border border-amber-400'
              : 'bg-emerald-500/20 text-emerald-800 border border-emerald-400'
          }`}
        >
          {tier}
        </span>
      </div>
    </div>
  );
};
