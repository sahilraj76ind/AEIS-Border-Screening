import React from 'react';
import { Layers, Microscope, Bot, UserCheck, ShieldCheck, Activity, HardDrive, Cpu, CheckCircle2 } from 'lucide-react';

export const DefenseSystemReadiness: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* 4 Forensic Architecture Pillars Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-amber-600" />
            <span>4-Pillar Multi-Layer Security Architecture</span>
          </h3>
          <span className="text-[10px] font-mono font-bold text-amber-900 bg-amber-500/15 px-3 py-1 rounded-full border border-amber-500/30 shadow-sm">
            ALL ENGINES READY • WAITING FOR TRAVELER SCAN
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Pillar 1 */}
          <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden group hover:border-amber-500/60 transition-all hover:shadow-md">
            <div>
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-700 mb-3 shadow-sm group-hover:scale-110 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <h4 className="font-mono text-xs font-bold text-slate-900 mb-1">
                Pillar 1: OCR & MRZ Engine
              </h4>
              <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                ICAO Doc 9303 modulo-10 check digit verification (TD3 Passports, TD2 Visas) + Verhoeff $D_5$ Aadhaar algorithm.
              </p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-[#E2D2A0]/60 flex items-center justify-between text-[10px] font-mono text-emerald-800 font-bold">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>ONLINE</span>
              </span>
              <span className="text-slate-500">Weights: 7-3-1</span>
            </div>
          </div>

          {/* Pillar 2 */}
          <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden group hover:border-amber-500/60 transition-all hover:shadow-md">
            <div>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-700 mb-3 shadow-sm group-hover:scale-110 transition-transform">
                <Microscope className="w-5 h-5" />
              </div>
              <h4 className="font-mono text-xs font-bold text-slate-900 mb-1">
                Pillar 2: ELA Tamper Forensics
              </h4>
              <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                90% JPEG recompression delta matrix detecting digital pixel splicing, copy-paste cloning, and Photoshop edits.
              </p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-[#E2D2A0]/60 flex items-center justify-between text-[10px] font-mono text-emerald-800 font-bold">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>ONLINE</span>
              </span>
              <span className="text-slate-500">Scale: 255/max</span>
            </div>
          </div>

          {/* Pillar 3 */}
          <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden group hover:border-amber-500/60 transition-all hover:shadow-md">
            <div>
              <div className="w-10 h-10 rounded-xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-orange-700 mb-3 shadow-sm group-hover:scale-110 transition-transform">
                <Bot className="w-5 h-5" />
              </div>
              <h4 className="font-mono text-xs font-bold text-slate-900 mb-1">
                Pillar 3: GenAI Deepfake Shield
              </h4>
              <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                High-frequency spectral Laplacian noise heuristic + PyTorch transformer classifier catching Midjourney & GANs.
              </p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-[#E2D2A0]/60 flex items-center justify-between text-[10px] font-mono text-emerald-800 font-bold">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>ONLINE</span>
              </span>
              <span className="text-slate-500">Dual-Heuristic</span>
            </div>
          </div>

          {/* Pillar 4 */}
          <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden group hover:border-amber-500/60 transition-all hover:shadow-md">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-700 mb-3 shadow-sm group-hover:scale-110 transition-transform">
                <UserCheck className="w-5 h-5" />
              </div>
              <h4 className="font-mono text-xs font-bold text-slate-900 mb-1">
                Pillar 4: Biometrics & Liveness
              </h4>
              <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                DeepFace Facenet 512-D cosine distance matching + MediaPipe real-time Eye Aspect Ratio (EAR) blink counter.
              </p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-[#E2D2A0]/60 flex items-center justify-between text-[10px] font-mono text-emerald-800 font-bold">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>ONLINE</span>
              </span>
              <span className="text-slate-500">Threshold: 0.40</span>
            </div>
          </div>
        </div>
      </div>

      {/* Checkpoint Telemetry & Compliance Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="glass-panel rounded-2xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-amber-800 font-bold">
            <Activity className="w-4 h-4 text-amber-600" />
            <span>TERMINAL 3 BIO-GATE TELEMETRY</span>
          </div>
          <div className="space-y-1 text-slate-600 text-[11px]">
            <div className="flex justify-between">
              <span>Today's Total Clearances:</span>
              <strong className="text-slate-900">1,428 Pax</strong>
            </div>
            <div className="flex justify-between">
              <span>Autonomous AI Clean Pass:</span>
              <strong className="text-emerald-700">94.2%</strong>
            </div>
            <div className="flex justify-between">
              <span>Officer Secondary Reviews:</span>
              <strong className="text-amber-700">82 Incidents</strong>
            </div>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-indigo-800 font-bold">
            <ShieldCheck className="w-4 h-4 text-indigo-600" />
            <span>STATUTORY SOVEREIGN GOVERNANCE</span>
          </div>
          <div className="space-y-1 text-slate-600 text-[11px]">
            <div className="flex justify-between">
              <span>EU AI Act Article 22:</span>
              <strong className="text-emerald-700 font-bold">ENFORCED</strong>
            </div>
            <div className="flex justify-between">
              <span>Dual-Key High-Risk Override:</span>
              <strong className="text-indigo-700">ACTIVE</strong>
            </div>
            <div className="flex justify-between">
              <span>Immutable Audit Chain:</span>
              <strong className="text-emerald-700">SHA-256 SEALED</strong>
            </div>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-emerald-800 font-bold">
            <HardDrive className="w-4 h-4 text-emerald-600" />
            <span>DPDP ACT 2023 PRIVACY SAFEGUARDS</span>
          </div>
          <div className="space-y-1 text-slate-600 text-[11px]">
            <div className="flex justify-between">
              <span>Data Retention Limit:</span>
              <strong className="text-slate-900">24 Hours (Sec 8(7))</strong>
            </div>
            <div className="flex justify-between">
              <span>Zero-Disk Storage:</span>
              <strong className="text-emerald-700">VOLATILE RAM</strong>
            </div>
            <div className="flex justify-between">
              <span>UIDAI 8-Digit Masking:</span>
              <strong className="text-emerald-700">AUTOMATIC</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
