import React, { useState } from 'react';
import { Lock, ShieldCheck, Copy, Check, Link as LinkIcon } from 'lucide-react';
import { OfficerDecisionResponse, AuditLogEntry } from '../types';

interface CryptoSealCardProps {
  data: OfficerDecisionResponse | AuditLogEntry;
}

export const CryptoSealCard: React.FC<CryptoSealCardProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  const copyHash = () => {
    navigator.clipboard.writeText(data.audit_sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isEntryGranted = data.final_decision === 'ENTRY_GRANTED';
  const isSecondary = data.final_decision === 'SECONDARY_INSPECTION';
  const isDetained = data.final_decision === 'DETAINED' || data.final_decision === 'ENTRY_REFUSED';

  return (
    <div className="glass-panel rounded-2xl p-5 shadow-lg border-2 border-emerald-500/40 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E2D2A0]/70 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center text-emerald-700 shadow-sm">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <span className="font-mono text-sm font-bold text-slate-900">
              Genesis-Linked Audit Block #{data.block_index}
            </span>
            <div className="text-[10px] font-mono font-bold text-emerald-800">
              CRYPTOGRAPHICALLY SEALED (SHA-256)
            </div>
          </div>
        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-mono font-bold tracking-wider shadow-sm ${
            isEntryGranted
              ? 'bg-emerald-500/20 text-emerald-900 border border-emerald-500/50'
              : isSecondary
              ? 'bg-amber-500/20 text-amber-900 border border-amber-500/50'
              : 'bg-rose-500/20 text-rose-900 border border-rose-500/50'
          }`}
        >
          {data.final_decision}
        </span>
      </div>

      {/* Grid Attributes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
        <div className="bg-white/80 p-3 rounded-xl border border-[#E2D2A0] shadow-sm">
          <span className="text-slate-500 block text-[10px] font-bold">LOG & INCIDENT ID</span>
          <span className="text-slate-900 font-bold truncate block">
            {data.log_id || 'N/A'}
          </span>
        </div>

        <div className="bg-white/80 p-3 rounded-xl border border-[#E2D2A0] shadow-sm">
          <span className="text-slate-500 block text-[10px] font-bold">INSPECTING OFFICER</span>
          <span className="text-slate-900 font-bold truncate block">
            {data.officer_id}
          </span>
        </div>

        <div className="bg-white/80 p-3 rounded-xl border border-[#E2D2A0] shadow-sm">
          <span className="text-slate-500 block text-[10px] font-bold">DECISION STATUS</span>
          <span className="font-bold text-slate-900">
            {data.is_override ? '⚠️ Manual Officer Override' : '✅ Agreed with AI Recommendation'}
          </span>
        </div>

        <div className="bg-white/80 p-3 rounded-xl border border-[#E2D2A0] shadow-sm">
          <span className="text-slate-500 block text-[10px] font-bold">LEGAL RETENTION TIER</span>
          <span className="text-indigo-800 font-bold truncate block">
            {data.legal_retention_tier}
          </span>
        </div>

        {data.supervisor_id && (
          <div className="bg-white/80 p-3 rounded-xl border border-[#E2D2A0] col-span-1 sm:col-span-2 shadow-sm">
            <span className="text-slate-500 block text-[10px] font-bold">SUPERVISOR CO-SIGNATURE</span>
            <span className="text-amber-800 font-bold">{data.supervisor_id}</span>
          </div>
        )}

        {data.override_reason_code && (
          <div className="bg-amber-500/15 p-3 rounded-xl border border-amber-400 col-span-1 sm:col-span-2 shadow-sm">
            <span className="text-amber-900 block text-[10px] font-bold">OVERRIDE REASON & REMARKS</span>
            <span className="text-amber-950 text-xs font-semibold">
              <code>{data.override_reason_code}</code> — {data.override_justification || 'Standard officer discretion remarks'}
            </span>
          </div>
        )}
      </div>

      {/* Hashes */}
      <div className="mt-4 pt-3 border-t border-[#E2D2A0]/70 space-y-2 text-[11px] font-mono">
        <div>
          <span className="text-slate-600 flex items-center space-x-1 font-bold">
            <LinkIcon className="w-3 h-3 text-indigo-600" />
            <span>Previous Block Hash (prev_hash):</span>
          </span>
          <code className="text-indigo-800 font-bold break-all block mt-1 text-[10px] bg-white/90 p-2 rounded-xl border border-[#E2D2A0] shadow-sm">
            {data.prev_hash}
          </code>
        </div>

        <div>
          <div className="flex items-center justify-between text-slate-600 font-bold">
            <span className="flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Immutable SHA-256 Block Seal:</span>
            </span>
            <button
              onClick={copyHash}
              className="text-amber-800 hover:text-amber-950 flex items-center space-x-1 text-[10px] font-bold"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <code className="text-emerald-800 font-bold break-all block mt-1 text-[10px] bg-white/90 p-2 rounded-xl border border-[#E2D2A0] shadow-sm">
            {data.audit_sha256}
          </code>
        </div>
      </div>
    </div>
  );
};
