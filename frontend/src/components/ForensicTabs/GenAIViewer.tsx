import React from 'react';
import { Bot, Sparkles, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { GenAIDetection } from '../../types';

interface GenAIViewerProps {
  aiResults: Record<string, GenAIDetection>;
}

export const GenAIViewer: React.FC<GenAIViewerProps> = ({ aiResults }) => {
  const entries = Object.entries(aiResults);

  if (entries.length === 0) {
    return <div className="text-slate-500 text-xs font-mono p-4">No GenAI detection data recorded.</div>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-bold font-mono text-slate-900 flex items-center space-x-2">
          <Bot className="w-4 h-4 text-orange-600" />
          <span>GenAI Synthetic Image & Deepfake Artifact Detection</span>
        </h4>
        <p className="text-xs text-slate-600 mt-0.5 font-medium">
          Dual-engine neural classifier & high-frequency spectral noise heuristic detecting Midjourney, Stable Diffusion, and GAN generations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entries.map(([docKey, res]) => {
          const prob = res.ai_generated_probability;
          const isHighRisk = prob > 0.5;

          return (
            <div
              key={docKey}
              className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xs font-bold uppercase text-slate-900">
                    {docKey} AI Evaluation
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold shadow-sm ${
                      isHighRisk
                        ? 'bg-rose-500/15 text-rose-900 border border-rose-500/30 animate-pulse'
                        : 'bg-emerald-500/15 text-emerald-900 border border-emerald-500/30'
                    }`}
                  >
                    {isHighRisk ? 'SYNTHETIC ARTIFACT' : 'AUTHENTIC OPTICAL'}
                  </span>
                </div>

                {/* Probability Meter */}
                <div className="bg-[#FAF0CB]/50 p-3 rounded-xl border border-[#E2D2A0] mb-3">
                  <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                    <span className="text-slate-600 font-bold">AI GENERATION PROBABILITY</span>
                    <span className={`font-black ${isHighRisk ? 'text-rose-700' : 'text-emerald-700'}`}>
                      {(prob * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-[#E2D2A0]/50 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isHighRisk ? 'bg-rose-500 shadow-glow-red' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, prob * 100))}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-[#E2D2A0]/60 grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] block font-bold">PRIMARY MODEL SCORE</span>
                  <span className="text-slate-900 font-bold">{res.primary_model_score.toFixed(4)}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-bold">NOISE HEURISTIC</span>
                  <span className="text-slate-900 font-bold">{res.fallback_heuristic_score.toFixed(4)}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
