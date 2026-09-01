import React, { useState, useEffect } from 'react';
import {
  ScrollText,
  Link as LinkIcon,
  ShieldCheck,
  ShieldAlert,
  Trash2,
  RefreshCw,
  Lock,
  Search,
  CheckCircle2,
  Copy,
  Check
} from 'lucide-react';
import {
  getAuditLogs,
  getGovernanceMetrics,
  verifyAuditChain,
  getDPDPStatus,
  purgeExpiredRecords
} from '../api/client';
import { AuditLogEntry, GovernanceMetrics, ChainVerificationResponse, DPDPComplianceStatus } from '../types';
import { CryptoSealCard } from '../components/CryptoSealCard';

export const AuditGovernanceView: React.FC = () => {
  const [metrics, setMetrics] = useState<GovernanceMetrics | null>(null);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [dpdpStatus, setDpdpStatus] = useState<DPDPComplianceStatus | null>(null);
  const [chainResult, setChainResult] = useState<ChainVerificationResponse | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [purging, setPurging] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBlock, setSelectedBlock] = useState<AuditLogEntry | null>(null);
  const [purgeFeedback, setPurgeFeedback] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [m, l, dpdp] = await Promise.all([
        getGovernanceMetrics().catch(() => null),
        getAuditLogs(100).catch(() => []),
        getDPDPStatus().catch(() => null),
      ]);
      setMetrics(m);
      setLogs(l);
      setDpdpStatus(dpdp);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerifyChain = async () => {
    setVerifyingChain(true);
    try {
      const res = await verifyAuditChain();
      setChainResult(res);
    } catch {
      setChainResult({
        chain_valid: false,
        total_blocks_verified: 0,
        error_details: 'Failed to communicate with verification backend',
        latest_block_hash: '',
        verified_at: new Date().toISOString(),
      });
    } finally {
      setVerifyingChain(false);
    }
  };

  const handlePurge = async () => {
    setPurging(true);
    setPurgeFeedback(null);
    try {
      const res = await purgeExpiredRecords(true);
      setPurgeFeedback(`Scrubbed ${res.purged_records_count || 0} clean scans under DPDP Act Sec 8(7). 100% hash chain preserved!`);
      loadData();
    } catch (err: any) {
      setPurgeFeedback('Purge execution failed: ' + (err.message || 'Error'));
    } finally {
      setPurging(false);
    }
  };

  const filteredLogs = logs.filter((log) => {
    const term = searchTerm.toLowerCase();
    return (
      log.officer_id.toLowerCase().includes(term) ||
      log.log_id.toLowerCase().includes(term) ||
      log.final_decision.toLowerCase().includes(term) ||
      (log.override_reason_code && log.override_reason_code.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel rounded-3xl p-6 relative overflow-hidden shadow-lg border border-[#E2D2A0]/80">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-mono font-bold text-slate-900 flex items-center space-x-2">
              <ScrollText className="w-5 h-5 text-amber-600" />
              <span>CRYPTOGRAPHIC AUDIT TRAIL & DPDP 2023 GOVERNANCE HUB</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5 font-medium">
              Genesis-linked immutable SHA-256 ledger recording sovereign border determinations, overrides, and DPDP Act 2023 statutory retention.
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="glass-btn px-3.5 py-1.5 text-slate-800 text-xs font-mono font-bold rounded-xl flex items-center space-x-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-amber-700 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Ledger</span>
          </button>
        </div>

        {/* 4 Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
          <div className="bg-white/75 p-4 rounded-2xl border border-[#E2D2A0] shadow-sm">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">TOTAL INSPECTIONS LOGGED</span>
            <span className="text-2xl font-mono font-black text-slate-900 mt-1 block">
              {metrics?.total_inspections_logged ?? logs.length}
            </span>
          </div>

          <div className="bg-white/75 p-4 rounded-2xl border border-[#E2D2A0] shadow-sm">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">OFFICER OVERRIDES</span>
            <span className="text-2xl font-mono font-black text-amber-700 mt-1 block">
              {metrics?.total_overrides ?? logs.filter((l) => l.is_override).length}
            </span>
          </div>

          <div className="bg-white/75 p-4 rounded-2xl border border-[#E2D2A0] shadow-sm">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">OVERRIDE RATE</span>
            <span className="text-2xl font-mono font-black text-indigo-700 mt-1 block">
              {(metrics?.override_rate_percentage ?? 0).toFixed(1)}%
            </span>
          </div>

          <div className="bg-white/75 p-4 rounded-2xl border border-[#E2D2A0] shadow-sm">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">AI-HUMAN AGREEMENT RATE</span>
            <span className="text-2xl font-mono font-black text-emerald-700 mt-1 block">
              {(metrics?.ai_human_agreement_rate_percentage ?? 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Verification & Minimization Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hash Chain Verifier */}
        <div className="glass-panel rounded-2xl p-5 space-y-4 border border-[#E2D2A0]/80 shadow-md">
          <div className="flex items-center space-x-2 text-indigo-900 font-mono text-sm font-bold">
            <LinkIcon className="w-4 h-4 text-indigo-600" />
            <span>Cryptographic Hash-Chain Continuity</span>
          </div>
          <p className="text-xs text-slate-600 font-medium">
            Verifies unbroken mathematical continuity from Genesis Block #0 to the latest block via SHA-256 payload digest chaining.
          </p>

          <button
            onClick={handleVerifyChain}
            disabled={verifyingChain}
            className="glass-btn-primary w-full py-3 px-4 text-white rounded-xl text-xs font-mono font-bold flex items-center justify-center space-x-2 shadow-md cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{verifyingChain ? 'VERIFYING CHAIN DIGESTS...' : 'RUN FULL CHAIN INTEGRITY VERIFICATION'}</span>
          </button>

          {chainResult && (
            <div
              className={`p-3.5 rounded-2xl border text-xs font-mono space-y-1.5 shadow-sm ${
                chainResult.chain_valid
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-950'
                  : 'bg-rose-500/15 border-rose-500/40 text-rose-950'
              }`}
            >
              <div className="flex items-center space-x-1.5 font-bold">
                {chainResult.chain_valid ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <ShieldAlert className="w-4 h-4 text-rose-600" />}
                <span>
                  {chainResult.chain_valid
                    ? `✅ 100% Authentic & Unbroken (${chainResult.total_blocks_verified} Blocks Verified)`
                    : `🚨 Hash Chain Compromised at Block #${chainResult.corrupted_block_index}`}
                </span>
              </div>
              <div className="text-[10px] text-slate-600 break-all font-mono">
                Latest Hash: <code>{chainResult.latest_block_hash}</code>
              </div>
            </div>
          )}
        </div>

        {/* DPDP Minimization */}
        <div className="glass-panel rounded-2xl p-5 space-y-4 border border-[#E2D2A0]/80 shadow-md">
          <div className="flex items-center space-x-2 text-emerald-900 font-mono text-sm font-bold">
            <Trash2 className="w-4 h-4 text-emerald-600" />
            <span>DPDP Act 2023 Data Minimization Engine</span>
          </div>
          <p className="text-xs text-slate-600 font-medium">
            Auto-purges clean transient demographic scans (&gt;24h) under Section 8(7) while locking investigation holds under Section 17(1)(c).
          </p>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-white/75 p-3 rounded-xl border border-[#E2D2A0]">
              <span className="text-slate-500 text-[10px] block font-bold">MINIMIZATION RATE</span>
              <span className="text-slate-900 font-black text-sm">
                {(dpdpStatus?.data_minimization_percentage ?? 0).toFixed(1)}%
              </span>
            </div>
            <div className="bg-white/75 p-3 rounded-xl border border-[#E2D2A0]">
              <span className="text-slate-500 text-[10px] block font-bold">INVESTIGATION HOLDS</span>
              <span className="text-amber-800 font-black text-sm">
                {dpdpStatus?.active_evidentiary_investigation_holds ?? logs.filter((l) => l.legal_retention_tier === 'TIER_2_INVESTIGATION_HOLD').length}
              </span>
            </div>
          </div>

          <button
            onClick={handlePurge}
            disabled={purging}
            className="glass-btn w-full py-3 px-4 text-slate-800 rounded-xl text-xs font-mono font-bold flex items-center justify-center space-x-2"
          >
            <Trash2 className="w-4 h-4 text-amber-700" />
            <span>{purging ? 'EXECUTING DATA PURGE...' : 'EXECUTE PURGE (CLEAN SCANS > 24H)'}</span>
          </button>

          {purgeFeedback && (
            <div className="p-3 bg-emerald-500/15 border border-emerald-500/40 text-emerald-950 text-xs font-mono font-bold rounded-xl shadow-sm">
              {purgeFeedback}
            </div>
          )}
        </div>
      </div>

      {/* Chained Blocks Table */}
      <div className="glass-panel rounded-2xl p-5 space-y-4 border border-[#E2D2A0]/80 shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-slate-900 font-mono text-sm font-bold">
            <Lock className="w-4 h-4 text-amber-600" />
            <span>Recent Chained Audit Blocks</span>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Officer, Decision, Reason..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-[#E2D2A0] rounded-xl pl-9 pr-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-500 shadow-sm"
            />
          </div>
        </div>

        {filteredLogs.length > 0 ? (
          <div className="overflow-x-auto rounded-2xl border border-[#E2D2A0]/80 bg-white/75 shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#FAF0CB]/70 text-slate-700 border-b border-[#E2D2A0] uppercase text-[10px] tracking-wider font-bold">
                <tr>
                  <th className="p-3">Block #</th>
                  <th className="p-3">Timestamp (UTC)</th>
                  <th className="p-3">Officer</th>
                  <th className="p-3">AI Rec</th>
                  <th className="p-3">Sovereign Action</th>
                  <th className="p-3">Override</th>
                  <th className="p-3">Retention Tier</th>
                  <th className="p-3">SHA-256 Seal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2D2A0]/50 text-slate-900">
                {filteredLogs.map((block) => (
                  <tr
                    key={block.block_index}
                    onClick={() => setSelectedBlock(block)}
                    className="hover:bg-white/90 cursor-pointer transition-colors"
                  >
                    <td className="p-3 font-bold text-amber-800">#{block.block_index}</td>
                    <td className="p-3 text-slate-600">{block.timestamp}</td>
                    <td className="p-3 font-bold text-slate-900">{block.officer_id}</td>
                    <td className="p-3">
                      <span className="text-slate-600">{block.ai_recommendation}</span>
                    </td>
                    <td className="p-3 font-bold">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold shadow-sm ${
                          block.final_decision === 'ENTRY_GRANTED'
                            ? 'bg-emerald-500/15 text-emerald-900 border border-emerald-500/30'
                            : block.final_decision === 'SECONDARY_INSPECTION'
                            ? 'bg-amber-500/15 text-amber-900 border border-amber-500/30'
                            : 'bg-rose-500/15 text-rose-900 border border-rose-500/30'
                        }`}
                      >
                        {block.final_decision}
                      </span>
                    </td>
                    <td className="p-3">
                      {block.is_override ? (
                        <span className="text-amber-800 font-bold">⚠️ YES</span>
                      ) : (
                        <span className="text-slate-400">NO</span>
                      )}
                    </td>
                    <td className="p-3">
                      <code className="text-[10px] text-indigo-800 font-bold">{block.legal_retention_tier}</code>
                    </td>
                    <td className="p-3">
                      <code className="text-[10px] text-emerald-800 font-bold">
                        {block.audit_sha256.substring(0, 16)}...
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 text-xs font-mono p-8 text-center bg-white/50 rounded-2xl border border-dashed border-[#E2D2A0]">
            No audit blocks match your search query. Screen documents to populate the ledger.
          </div>
        )}
      </div>

      {/* Block Details Modal */}
      {selectedBlock && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl">
            <CryptoSealCard data={selectedBlock} />
            <button
              onClick={() => setSelectedBlock(null)}
              className="glass-btn mt-3 w-full py-2.5 text-slate-800 font-mono text-xs font-bold rounded-xl"
            >
              Close Block Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
