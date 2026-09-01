import React, { useState, useEffect } from 'react';
import { Database, Search, ShieldAlert, AlertTriangle, RefreshCw, FileText } from 'lucide-react';
import { getWatchlist } from '../api/client';

export const WatchlistIntelligenceView: React.FC = () => {
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await getWatchlist();
      if (Array.isArray(data)) {
        setWatchlist(data);
      } else if (typeof data === 'object' && data !== null) {
        const list = Object.entries(data).map(([k, v]: any) => {
          if (typeof v === 'object') {
            return { document_number: k, ...v };
          }
          return { document_number: k, status: String(v) };
        });
        setWatchlist(list);
      }
    } catch {
      setWatchlist([
        { document_number: 'N87654321', category: 'INTERPOL_SLTD_LOST', reason: 'Reported lost in transit by issuing authority', severity: 'CRITICAL' },
        { document_number: 'Z98765432', category: 'INTERPOL_SLTD_STOLEN', reason: 'Stolen blank document bulletin 2026/A', severity: 'CRITICAL' },
        { document_number: 'F55443322', category: 'UN_SECURITY_COUNCIL_BAN', reason: 'Targeted international sanctions travel restriction', severity: 'HIGH' },
        { document_number: 'M11223344', category: 'INTERPOL_RED_NOTICE', reason: 'Extradition bulletin for financial fraud', severity: 'CRITICAL' },
        { document_number: 'E99887766', category: 'NATIONAL_BORDER_WATCHLIST', reason: 'Flagged for secondary physical interview', severity: 'ELEVATED' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredList = watchlist.filter((item) => {
    const term = searchTerm.toLowerCase();
    const docNum = (item.document_number || item.doc_number || item.Target || '').toLowerCase();
    const reason = (item.reason || item.category || '').toLowerCase();
    return docNum.includes(term) || reason.includes(term);
  });

  return (
    <div className="space-y-6">
      <div className="glass-panel rounded-3xl p-6 relative overflow-hidden shadow-lg border border-[#E2D2A0]/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-mono font-bold text-slate-900 flex items-center space-x-2">
              <Database className="w-5 h-5 text-amber-600" />
              <span>BORDER SECURITY & INTERPOL SLTD WATCHLIST DATABASE</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5 font-medium">
              Simulated Interpol Stolen & Lost Travel Documents (SLTD) database and intelligence bulletins.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="relative w-72">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search Document Number..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-white border border-[#E2D2A0] rounded-xl pl-9 pr-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-500 shadow-sm"
              />
            </div>

            <button
              onClick={loadData}
              disabled={loading}
              className="glass-btn p-2.5 text-slate-700 rounded-xl"
              title="Refresh Watchlist"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="glass-panel rounded-2xl p-5 border border-[#E2D2A0]/80 shadow-md">
        {filteredList.length > 0 ? (
          <div className="overflow-x-auto rounded-2xl border border-[#E2D2A0]/80 bg-white/75 shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#FAF0CB]/70 text-slate-700 border-b border-[#E2D2A0] uppercase text-[10px] tracking-wider font-bold">
                <tr>
                  <th className="p-3">Target / Document #</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Intelligence Reason</th>
                  <th className="p-3">Threat Severity</th>
                  <th className="p-3">Interception Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2D2A0]/50 text-slate-900">
                {filteredList.map((item, idx) => {
                  const docNum = item.document_number || item.doc_number || item.Target || 'UNKNOWN';
                  const cat = item.category || 'SLTD_FLAGGED';
                  const reason = item.reason || 'Flagged in border security bulletin';
                  const sev = item.severity || 'HIGH';

                  return (
                    <tr key={idx} className="hover:bg-white/90 transition-colors">
                      <td className="p-3 font-black text-amber-900 flex items-center space-x-2">
                        <FileText className="w-3.5 h-3.5 text-amber-600" />
                        <span>{docNum}</span>
                      </td>
                      <td className="p-3 font-mono font-semibold text-slate-800">{cat}</td>
                      <td className="p-3 text-slate-600 max-w-xs truncate font-medium">{reason}</td>
                      <td className="p-3">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold shadow-sm ${
                            sev === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-900 border border-rose-400'
                              : 'bg-amber-500/20 text-amber-900 border border-amber-400'
                          }`}
                        >
                          {sev}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className="text-[10px] text-rose-900 font-bold bg-rose-500/15 px-2.5 py-1 rounded-full border border-rose-500/30 shadow-sm">
                          MANDATORY INTERCEPT
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 text-xs font-mono p-8 text-center bg-white/50 rounded-2xl border border-dashed border-[#E2D2A0]">
            No watchlist entries match your query.
          </div>
        )}
      </div>
    </div>
  );
};
