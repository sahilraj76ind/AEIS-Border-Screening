import React, { useState } from 'react';
import { LoadingScreen } from './components/LoadingScreen';
import { Navbar } from './components/Navbar';
import { MultiDocBatchView } from './views/MultiDocBatchView';
import { SingleDocQuickView } from './views/SingleDocQuickView';
import { AuditGovernanceView } from './views/AuditGovernanceView';
import { WatchlistIntelligenceView } from './views/WatchlistIntelligenceView';
import { Shield, Lock, Cpu, Sparkles } from 'lucide-react';

export function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'batch' | 'single' | 'audit' | 'watchlist'>('batch');

  return (
    <div className="min-h-screen text-slate-800 flex flex-col selection:bg-amber-400 selection:text-slate-950 transition-colors">
      {/* Initial Loading Screen with Clean Logo Video & Palette */}
      {isLoading && <LoadingScreen onFinish={() => setIsLoading(false)} />}

      {/* Top Navigation Bar */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'batch' && <MultiDocBatchView />}
        {activeTab === 'single' && <SingleDocQuickView />}
        {activeTab === 'audit' && <AuditGovernanceView />}
        {activeTab === 'watchlist' && <WatchlistIntelligenceView />}
      </main>

      {/* Luxury Glassmorphic Tactical Footer */}
      <footer className="border-t border-[#E2D2A0]/80 bg-[#FDF4D2]/85 backdrop-blur-md py-4 mt-auto shadow-inner">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs font-mono text-slate-600 gap-2">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1.5 text-amber-800 font-bold">
              <Shield className="w-4 h-4 text-amber-600" />
              <span>AEIS FORENSIC AI</span>
            </span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-600 font-medium">Neural Threat Model Pipeline (OCR + ELA + Biometrics + Deepfake Detection)</span>
          </div>

          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1 text-emerald-800 font-semibold">
              <Lock className="w-3.5 h-3.5 text-emerald-600" />
              <span>DPDP Act 2023 Compliant</span>
            </span>
            <span className="text-slate-400">•</span>
            <span className="flex items-center space-x-1 text-indigo-800 font-semibold">
              <Cpu className="w-3.5 h-3.5 text-indigo-600" />
              <span>FastAPI Gateway: :8000</span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
