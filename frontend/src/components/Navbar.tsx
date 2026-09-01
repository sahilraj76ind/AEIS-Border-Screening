import React, { useEffect, useState } from 'react';
import { ShieldAlert, Cpu, ScrollText, Database, RefreshCw } from 'lucide-react';
import { checkHealth } from '../api/client';

interface NavbarProps {
  activeTab: 'batch' | 'single' | 'audit' | 'watchlist';
  setActiveTab: (tab: 'batch' | 'single' | 'audit' | 'watchlist') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const pingServer = async () => {
    setChecking(true);
    try {
      const data = await checkHealth();
      setIsHealthy(data.status === 'healthy');
    } catch {
      setIsHealthy(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    pingServer();
    const interval = setInterval(pingServer, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-[#FDF4D2]/85 backdrop-blur-xl border-b border-[#E2D2A0]/80 shadow-sm transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand Name A.E.I.S (Clean Gradient matching theme) */}
          <div className="flex items-center space-x-3 cursor-pointer select-none">
            <div className="w-11 h-11 rounded-2xl border border-[#E2D2A0] flex items-center justify-center shadow-md overflow-hidden p-1 transition-transform hover:scale-105">
              <img
                src="/navbar-logo.gif"
                alt="A.E.I.S Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <span className="font-mono text-2xl font-black tracking-widest bg-gradient-to-r from-amber-600 via-orange-600 to-indigo-600 bg-clip-text text-transparent drop-shadow-sm">
                A.E.I.S
              </span>
            </div>
          </div>

          {/* Navigation Tabs (Glassmorphism Pills) */}
          <nav className="flex items-center space-x-1 sm:space-x-2 bg-[#FAF0CB]/60 p-1 rounded-2xl border border-[#E2D2A0]/60 backdrop-blur-md">
            <button
              onClick={() => setActiveTab('batch')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'batch'
                  ? 'bg-white text-slate-900 shadow-md border border-[#E2D2A0] scale-[1.02]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <Cpu className="w-4 h-4 text-amber-600" />
              <span className="hidden md:inline">Multi-Doc Batch Desk</span>
              <span className="md:hidden">Batch</span>
            </button>

            <button
              onClick={() => setActiveTab('single')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'single'
                  ? 'bg-white text-slate-900 shadow-md border border-[#E2D2A0] scale-[1.02]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <ShieldAlert className="w-4 h-4 text-indigo-600" />
              <span className="hidden md:inline">Single Doc Quick Inspect</span>
              <span className="md:hidden">Quick</span>
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'audit'
                  ? 'bg-white text-slate-900 shadow-md border border-[#E2D2A0] scale-[1.02]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <ScrollText className="w-4 h-4 text-emerald-600" />
              <span className="hidden md:inline">Audit & DPDP Hub</span>
              <span className="md:hidden">Audit</span>
            </button>

            <button
              onClick={() => setActiveTab('watchlist')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'watchlist'
                  ? 'bg-white text-slate-900 shadow-md border border-[#E2D2A0] scale-[1.02]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <Database className="w-4 h-4 text-orange-600" />
              <span className="hidden md:inline">Watchlist</span>
              <span className="md:hidden">List</span>
            </button>
          </nav>

          {/* Backend Health Status Badge */}
          <div className="flex items-center space-x-2">
            <button
              onClick={pingServer}
              disabled={checking}
              className={`glass-panel flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold border transition-all ${
                isHealthy === true
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-900'
                  : isHealthy === false
                  ? 'bg-rose-500/15 border-rose-500/40 text-rose-900'
                  : 'bg-white/60 border-slate-300 text-slate-600'
              }`}
              title="FastAPI Gateway Status"
            >
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
              <span className="hidden sm:inline">
                {isHealthy === true ? 'FASTAPI: ONLINE' : isHealthy === false ? 'GATEWAY OFFLINE' : 'CHECKING...'}
              </span>
              <RefreshCw className={`w-3 h-3 text-slate-600 ${checking ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
