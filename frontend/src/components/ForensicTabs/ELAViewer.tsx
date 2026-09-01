import React from 'react';
import { Microscope, AlertCircle, CheckCircle2 } from 'lucide-react';
import { ELAForensics } from '../../types';

interface ELAViewerProps {
  elaResults: Record<string, ELAForensics>;
}

export const ELAViewer: React.FC<ELAViewerProps> = ({ elaResults }) => {
  const entries = Object.entries(elaResults);

  if (entries.length === 0) {
    return <div className="text-slate-500 text-xs font-mono p-4">No ELA forensics data recorded.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-bold font-mono text-slate-900 flex items-center space-x-2">
            <Microscope className="w-4 h-4 text-amber-600" />
            <span>Error Level Analysis (ELA) Compression Heatmaps</span>
          </h4>
          <p className="text-xs text-slate-600 mt-0.5 font-medium">
            Detects digital splicing, copy-paste cloning, and resaved JPEG compression artifacts.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entries.map(([docKey, res]) => {
          const isClean = res.tamper_suspicion === 'LOW';
          return (
            <div
              key={docKey}
              className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold uppercase text-amber-800">
                    {docKey} Forensics
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold shadow-sm ${
                      isClean
                        ? 'bg-emerald-500/15 text-emerald-900 border border-emerald-500/30'
                        : 'bg-rose-500/15 text-rose-900 border border-rose-500/30 animate-pulse'
                    }`}
                  >
                    {res.tamper_suspicion} SUSPICION
                  </span>
                </div>

                {res.ela_heatmap_base64 ? (
                  <div className="w-full aspect-video rounded-xl overflow-hidden border border-[#E2D2A0] bg-black mb-3 shadow-inner">
                    <img
                      src={
                        res.ela_heatmap_base64.startsWith('data:')
                          ? res.ela_heatmap_base64
                          : `data:image/png;base64,${res.ela_heatmap_base64}`
                      }
                      alt={`${docKey} ELA Heatmap`}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ) : (
                  <div className="w-full aspect-video rounded-xl border border-dashed border-[#E2D2A0] bg-white/50 flex items-center justify-center text-xs text-slate-500 font-mono mb-3">
                    No Heatmap Generated
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-[#E2D2A0]/60 grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] block font-bold">MEAN ERROR LEVEL</span>
                  <span className="text-slate-900 font-bold">{res.mean_error_level.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-bold">VERDICT</span>
                  <span className="text-slate-900 font-bold truncate block">{res.verdict}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
