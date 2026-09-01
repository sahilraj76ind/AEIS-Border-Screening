import React, { useState, useEffect } from 'react';
import { Shield, Radio, Database, Lock, Clock, Sparkles, AlertTriangle, CheckCircle } from 'lucide-react';
import {
  loadCleanTravelerPreset,
  loadFraudTamperedPreset,
  loadInterpolWatchlistPreset,
  loadAadhaarPreset,
} from '../utils/sampleData';

interface DefenseHeroBarProps {
  onLoadPreset: (preset: {
    passport: File | null;
    visa: File | null;
    aadhaar: File | null;
    selfie: File | null;
  }) => void;
}

export const DefenseHeroBar: React.FC<DefenseHeroBarProps> = ({ onLoadPreset }) => {
  const [timeStr, setTimeStr] = useState('');
  const [utcStr, setUtcStr] = useState('');
  const [loadingPreset, setLoadingPreset] = useState<string | null>(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString());
      setUtcStr(now.toUTCString().split(' ')[4] + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handlePresetClick = async (name: string, loader: () => Promise<any>) => {
    setLoadingPreset(name);
    try {
      const data = await loader();
      onLoadPreset(data);
    } finally {
      setLoadingPreset(null);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-4 sm:p-5 shadow-lg relative overflow-hidden space-y-4 border border-[#E2D2A0]/80">
      {/* Background Accent Grid */}
      <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-amber-500/10 via-transparent to-transparent pointer-events-none" />

      {/* Top Telemetry Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2D2A0]/70 pb-3 text-xs font-mono">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-900 border border-emerald-500/30 font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="tracking-wider">TERMINAL 3 • BORDER GATE 04</span>
          </div>

          <div className="hidden md:flex items-center space-x-1 text-slate-600">
            <Clock className="w-3.5 h-3.5 text-amber-700" />
            <span className="font-bold">{timeStr}</span>
            <span className="text-slate-400">•</span>
            <span className="text-indigo-700 font-semibold">{utcStr}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-[11px]">
          <div className="flex items-center space-x-1.5 bg-white/70 px-3 py-1 rounded-full border border-[#E2D2A0] shadow-sm text-slate-700">
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            <span>INTERPOL SLTD: <strong className="text-emerald-700">12.4M ACTIVE</strong></span>
          </div>

          <div className="flex items-center space-x-1.5 bg-white/70 px-3 py-1 rounded-full border border-[#E2D2A0] shadow-sm text-slate-700">
            <Lock className="w-3.5 h-3.5 text-indigo-600" />
            <span>DPDP PRIVACY BUFFER: <strong className="text-indigo-700">VOLATILE RAM</strong></span>
          </div>
        </div>
      </div>

      {/* 1-Click Interactive Demo Presets Strip */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-slate-800 flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-amber-600 animate-spin" />
            <span>QUICK-LOAD SIMULATED TRAVELER SCENARIOS (1-CLICK TEST PRESETS):</span>
          </span>
          <span className="text-[10px] font-mono text-slate-500 hidden sm:inline">
            INSTANTLY GENERATES AUTHENTIC & TAMPERED TEST SPECIMENS
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <button
            onClick={() => handlePresetClick('clean', loadCleanTravelerPreset)}
            disabled={loadingPreset !== null}
            className="p-3 rounded-xl border text-left transition-all bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/40 text-emerald-950 flex items-center space-x-3 group shadow-sm hover:shadow-md hover:scale-[1.01]"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-700 group-hover:scale-110 transition-transform flex-shrink-0">
              <CheckCircle className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-mono text-xs font-bold truncate text-emerald-900">Clean Traveler Pass</div>
              <div className="text-[10px] text-emerald-700 truncate">Anna Eriksson (TD3 + Visa + Selfie)</div>
            </div>
          </button>

          <button
            onClick={() => handlePresetClick('tampered', loadFraudTamperedPreset)}
            disabled={loadingPreset !== null}
            className="p-3 rounded-xl border text-left transition-all bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/40 text-amber-950 flex items-center space-x-3 group shadow-sm hover:shadow-md hover:scale-[1.01]"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-700 group-hover:scale-110 transition-transform flex-shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-mono text-xs font-bold truncate text-amber-900">Fraud Tamper Attack</div>
              <div className="text-[10px] text-amber-700 truncate">MRZ/VIZ mismatch + ELA splice</div>
            </div>
          </button>

          <button
            onClick={() => handlePresetClick('stolen', loadInterpolWatchlistPreset)}
            disabled={loadingPreset !== null}
            className="p-3 rounded-xl border text-left transition-all bg-rose-500/10 hover:bg-rose-500/20 border-rose-500/40 text-rose-950 flex items-center space-x-3 group shadow-sm hover:shadow-md hover:scale-[1.01]"
          >
            <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-700 group-hover:scale-110 transition-transform flex-shrink-0">
              <Shield className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-mono text-xs font-bold truncate text-rose-900">Interpol SLTD Hit</div>
              <div className="text-[10px] text-rose-700 truncate">N87654321 Stolen Blank Flag</div>
            </div>
          </button>

          <button
            onClick={() => handlePresetClick('aadhaar', loadAadhaarPreset)}
            disabled={loadingPreset !== null}
            className="p-3 rounded-xl border text-left transition-all bg-indigo-500/10 hover:bg-indigo-500/20 border-indigo-500/40 text-indigo-950 flex items-center space-x-3 group shadow-sm hover:shadow-md hover:scale-[1.01]"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-700 group-hover:scale-110 transition-transform flex-shrink-0">
              <Lock className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-mono text-xs font-bold truncate text-indigo-900">UIDAI Aadhaar Pass</div>
              <div className="text-[10px] text-indigo-700 truncate">Verhoeff UID + 8-Digit Mask</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
