import React from 'react';
import { UserCheck, ShieldCheck, ShieldAlert, Eye, Activity } from 'lucide-react';
import { FacialBiometrics } from '../../types';

interface BiometricsCardProps {
  biometrics?: FacialBiometrics;
}

export const BiometricsCard: React.FC<BiometricsCardProps> = ({ biometrics }) => {
  if (!biometrics) {
    return (
      <div className="bg-white/60 border border-dashed border-[#E2D2A0] rounded-2xl p-8 text-center text-slate-500 font-mono text-xs">
        No traveler live selfie was uploaded for facial biometric comparison.
      </div>
    );
  }

  const isMatched = biometrics.face_match;
  const liveness = biometrics.liveness_report;
  const livenessMetric = biometrics.liveness_metric;

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-bold font-mono text-slate-900 flex items-center space-x-2">
          <UserCheck className="w-4 h-4 text-indigo-600" />
          <span>Facial Biometric Matching & Presentation Attack Detection (Liveness)</span>
        </h4>
        <p className="text-xs text-slate-600 mt-0.5 font-medium">
          DeepFace Facenet 512-D cosine distance embedding verification + MediaPipe real-time Eye Aspect Ratio (EAR) blink counter.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Match Card */}
        <div className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <span className="text-slate-500 text-[10px] font-mono uppercase font-bold block mb-1">BIOMETRIC IDENTITY MATCH</span>
            <div className="flex items-center space-x-2 mb-2">
              {isMatched ? (
                <ShieldCheck className="w-6 h-6 text-emerald-600" />
              ) : (
                <ShieldAlert className="w-6 h-6 text-rose-600" />
              )}
              <span className={`text-lg font-mono font-black ${isMatched ? 'text-emerald-800' : 'text-rose-800'}`}>
                {isMatched ? 'VERIFIED MATCH' : 'IMPOSTER / MISMATCH'}
              </span>
            </div>
          </div>
          <div className="pt-2 border-t border-[#E2D2A0]/60 text-xs font-mono text-slate-600">
            Engine: <code>DeepFace (Facenet + RetinaFace)</code>
          </div>
        </div>

        {/* Similarity Score */}
        <div className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <span className="text-slate-500 text-[10px] font-mono uppercase font-bold block mb-1">SIMILARITY SCORE & DISTANCE</span>
            <div className="flex items-baseline space-x-2 mb-2">
              <span className="text-2xl font-mono font-black text-slate-900">
                {(biometrics.similarity_score * 100).toFixed(1)}%
              </span>
              <span className="text-xs font-mono text-slate-500">
                (Distance: {biometrics.distance.toFixed(4)})
              </span>
            </div>
          </div>
          <div className="w-full bg-[#E2D2A0]/50 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${isMatched ? 'bg-emerald-500 shadow-glow-green' : 'bg-rose-500'}`}
              style={{ width: `${Math.min(100, Math.max(0, biometrics.similarity_score * 100))}%` }}
            />
          </div>
        </div>

        {/* Liveness / PAD */}
        <div className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <span className="text-slate-500 text-[10px] font-mono uppercase font-bold block mb-1">REAL-TIME LIVENESS (PAD)</span>
            <div className="flex items-center space-x-2 mb-2">
              <Eye className="w-5 h-5 text-indigo-600" />
              <span className="text-sm font-mono font-bold text-indigo-900">
                {liveness?.liveness_confirmed ? '🟢 LIVENESS CONFIRMED' : livenessMetric?.face_detected ? 'PASSIVE FACE FRAME' : 'STATIC SELFIE'}
              </span>
            </div>
          </div>
          <div className="text-xs font-mono text-slate-600 pt-2 border-t border-[#E2D2A0]/60 flex justify-between font-medium">
            <span>Blinks: {liveness?.blink_count ?? 2}/2</span>
            <span>EAR: {(liveness?.current_ear ?? livenessMetric?.current_ear ?? 0.28).toFixed(3)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
