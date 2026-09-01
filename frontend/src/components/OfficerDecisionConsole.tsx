import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Lock, CheckCircle2, UserCheck, ShieldAlert } from 'lucide-react';
import confetti from 'canvas-confetti';
import { submitOfficerDecision, getOverrideReasons } from '../api/client';
import { DocumentAnalysis, RiskAssessment, OverrideReason, OfficerDecisionResponse } from '../types';
import { CryptoSealCard } from './CryptoSealCard';

interface OfficerDecisionConsoleProps {
  validationData: DocumentAnalysis;
  riskAssessment?: RiskAssessment;
}

export const OfficerDecisionConsole: React.FC<OfficerDecisionConsoleProps> = ({
  validationData,
  riskAssessment,
}) => {
  const [officerId, setOfficerId] = useState('OFFICER-BSF-4821');
  const [checkpointId, setCheckpointId] = useState('TERMINAL-3 / IN-GATE-04');
  const [finalDecision, setFinalDecision] = useState<'ENTRY_GRANTED' | 'SECONDARY_INSPECTION' | 'ENTRY_REFUSED' | 'DETAINED'>('ENTRY_GRANTED');
  const [overrideReasonCode, setOverrideReasonCode] = useState('');
  const [overrideJustification, setOverrideJustification] = useState('');
  const [supervisorId, setSupervisorId] = useState('');
  
  const [allReasons, setAllReasons] = useState<OverrideReason[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sealedBlock, setSealedBlock] = useState<OfficerDecisionResponse | null>(null);

  const aiRec = validationData.ai_recommendation || 'CLEARED';

  // Determine default decision based on AI recommendation
  useEffect(() => {
    if (aiRec === 'CLEARED') {
      setFinalDecision('ENTRY_GRANTED');
    } else if (aiRec === 'SECONDARY_INSPECTION') {
      setFinalDecision('SECONDARY_INSPECTION');
    } else {
      setFinalDecision('DETAINED');
    }
  }, [aiRec]);

  // Load override reasons
  useEffect(() => {
    getOverrideReasons()
      .then((reasons) => {
        if (Array.isArray(reasons)) {
          setAllReasons(reasons);
        }
      })
      .catch(() => {
        setAllReasons([
          { code: 'PHYSICAL_SECURITY_FEATURES_VERIFIED', category: 'APPROVE_OVERRIDE', description: 'Physical Security Features Verified' },
          { code: 'DIPLOMATIC_CONSULAR_IMMUNITY', category: 'APPROVE_OVERRIDE', description: 'Diplomatic Consular Immunity' },
          { code: 'BEHAVIORAL_ANOMALY_SUSPICION', category: 'REJECT_OVERRIDE', description: 'Behavioral Anomaly Suspicion' },
          { code: 'IMPOSTER_BIOMETRIC_MISMATCH', category: 'REJECT_OVERRIDE', description: 'Imposter Biometric Mismatch' },
          { code: 'CANINE_K9_DETECTION_ALERT', category: 'REJECT_OVERRIDE', description: 'Canine K9 Detection Alert' },
          { code: 'PHYSICAL_DOCUMENT_SUBSTRATE_TAMPERING', category: 'REJECT_OVERRIDE', description: 'Physical Document Substrate Tampering' },
        ]);
      });
  }, []);

  const isOverride =
    (aiRec === 'CLEARED' && finalDecision !== 'ENTRY_GRANTED') ||
    (aiRec === 'SECONDARY_INSPECTION' && finalDecision === 'ENTRY_GRANTED') ||
    (aiRec === 'DETAIN' && finalDecision === 'ENTRY_GRANTED');

  const requiresSupervisor = aiRec === 'DETAIN' && finalDecision === 'ENTRY_GRANTED';

  const filteredReasons = allReasons.filter((r) =>
    finalDecision === 'ENTRY_GRANTED' ? r.category === 'APPROVE_OVERRIDE' : r.category === 'REJECT_OVERRIDE'
  );

  useEffect(() => {
    if (isOverride && filteredReasons.length > 0 && !overrideReasonCode) {
      setOverrideReasonCode(filteredReasons[0].code);
    }
  }, [isOverride, finalDecision, filteredReasons]);

  const handleSubmit = async () => {
    setErrorMsg(null);
    if (isOverride && !overrideReasonCode) {
      setErrorMsg('Please select a mandatory standardized override reason code.');
      return;
    }
    if (requiresSupervisor && !supervisorId.trim()) {
      setErrorMsg('Supervisor Badge ID is strictly required to override a DETAIN alert.');
      return;
    }

    setLoading(true);
    try {
      const res = await submitOfficerDecision({
        validation_data: validationData,
        officer_id: officerId,
        checkpoint_id: checkpointId,
        final_decision: finalDecision,
        override_reason_code: isOverride ? overrideReasonCode : undefined,
        override_justification: isOverride ? overrideJustification : undefined,
        supervisor_id: requiresSupervisor ? supervisorId : undefined,
      });
      setSealedBlock(res);
      confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } });
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to record sovereign decision.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-[#E2D2A0]/80 shadow-md relative flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E2D2A0]/70 pb-3 mb-4">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-amber-600" />
            <h3 className="font-mono text-sm font-bold text-slate-900 tracking-wider">
              OFFICER SOVEREIGN ACTION DESK (HITL)
            </h3>
          </div>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-900 border border-amber-500/30">
            ARTICLE 22 HITL GUARANTEE
          </span>
        </div>

        {/* AI Baseline Indicator */}
        <div
          className={`p-3 rounded-xl border text-xs font-mono font-bold mb-4 flex items-center justify-between shadow-sm ${
            aiRec === 'CLEARED'
              ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-950'
              : aiRec === 'SECONDARY_INSPECTION'
              ? 'bg-amber-500/15 border-amber-500/40 text-amber-950'
              : 'bg-rose-500/15 border-rose-500/40 text-rose-950'
          }`}
        >
          <div className="flex items-center space-x-2">
            <span>🤖 AI Baseline Recommendation:</span>
            <span className="underline uppercase tracking-wide">{aiRec}</span>
          </div>
          <span>Risk: {riskAssessment?.composite_risk_score.toFixed(1) || 0}/100</span>
        </div>

        {/* Officer Credentials Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-[11px] font-mono font-bold text-slate-600 mb-1">INSPECTING OFFICER ID</label>
            <input
              type="text"
              value={officerId}
              onChange={(e) => setOfficerId(e.target.value)}
              className="w-full bg-white/80 border border-[#E2D2A0] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 focus:outline-none focus:border-amber-500 shadow-sm"
            />
          </div>
          <div>
            <label className="block text-[11px] font-mono font-bold text-slate-600 mb-1">BORDER CHECKPOINT GATE</label>
            <input
              type="text"
              value={checkpointId}
              onChange={(e) => setCheckpointId(e.target.value)}
              className="w-full bg-white/80 border border-[#E2D2A0] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 focus:outline-none focus:border-amber-500 shadow-sm"
            />
          </div>
        </div>

        {/* Decision Options */}
        <div className="space-y-2 mb-4">
          <label className="block text-[11px] font-mono font-bold text-slate-700">SELECT SOVEREIGN DETERMINATION</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {[
              { id: 'ENTRY_GRANTED', label: '✅ ENTRY GRANTED', desc: 'Clear traveler pass' },
              { id: 'SECONDARY_INSPECTION', label: '⚠️ SECONDARY REVIEW', desc: 'Escalate to interview' },
              { id: 'ENTRY_REFUSED', label: '🚫 ENTRY REFUSED', desc: 'Issue refusal notice' },
              { id: 'DETAINED', label: '🚨 DETAINED', desc: 'Transfer to custody' },
            ].map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setFinalDecision(opt.id as any)}
                className={`p-3 rounded-xl border text-left transition-all shadow-sm ${
                  finalDecision === opt.id
                    ? opt.id === 'ENTRY_GRANTED'
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-950 font-bold scale-[1.01]'
                      : opt.id === 'SECONDARY_INSPECTION'
                      ? 'bg-amber-500/20 border-amber-500 text-amber-950 font-bold scale-[1.01]'
                      : 'bg-rose-500/20 border-rose-500 text-rose-950 font-bold scale-[1.01]'
                    : 'bg-white/70 border-[#E2D2A0] text-slate-600 hover:border-amber-400 hover:bg-white'
                }`}
              >
                <div className="font-mono text-xs font-bold">{opt.label}</div>
                <div className="text-[10px] text-slate-500">{opt.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Override Fields */}
        {isOverride && (
          <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-500/40 space-y-3 mb-4 shadow-sm">
            <div className="flex items-center space-x-1.5 text-amber-900 text-xs font-mono font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>Manual Officer Override Protocol Triggered</span>
            </div>

            <div>
              <label className="block text-[10px] font-mono font-bold text-amber-900 mb-1">
                MANDATORY REGULATORY REASON CODE:
              </label>
              <select
                value={overrideReasonCode}
                onChange={(e) => setOverrideReasonCode(e.target.value)}
                className="w-full bg-white border border-amber-400 rounded-xl px-3 py-2 text-xs font-mono font-bold text-amber-950 focus:outline-none focus:border-amber-600 shadow-sm"
              >
                {filteredReasons.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.code} — {r.description}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-mono font-bold text-amber-900 mb-1">
                OFFICER EVIDENTIARY REMARKS:
              </label>
              <textarea
                value={overrideJustification}
                onChange={(e) => setOverrideJustification(e.target.value)}
                rows={2}
                placeholder="Physical microprint and holograms verified under UV lamp. Physical substrate authentic."
                className="w-full bg-white border border-amber-400 rounded-xl p-2.5 text-xs font-mono text-slate-900 focus:outline-none focus:border-amber-600 shadow-sm"
              />
            </div>

            {requiresSupervisor && (
              <div className="pt-2 border-t border-amber-400/40">
                <div className="flex items-center space-x-1 text-rose-900 text-xs font-bold mb-1">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  <span>DUAL-KEY SUPERVISOR CO-SIGNATURE MANDATED</span>
                </div>
                <input
                  type="text"
                  value={supervisorId}
                  onChange={(e) => setSupervisorId(e.target.value)}
                  placeholder="SUPV-SINGH-9104"
                  className="w-full bg-white border border-rose-400 rounded-xl px-3 py-2 text-xs font-mono font-bold text-rose-950 focus:outline-none shadow-sm"
                />
              </div>
            )}
          </div>
        )}

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-950 text-xs font-mono font-bold mb-3 shadow-sm">
            🚨 {errorMsg}
          </div>
        )}
      </div>

      <div className="mt-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-3.5 px-4 rounded-xl font-mono font-bold text-xs tracking-wider flex items-center justify-center space-x-2 glass-btn-primary text-white shadow-md transition-all disabled:opacity-50 active:scale-[0.99] cursor-pointer"
        >
          <Lock className="w-4 h-4" />
          <span>{loading ? 'SEALING BLOCK IN SHA-256 LEDGER...' : 'RECORD SOVEREIGN DECISION & SEAL HASH-CHAIN'}</span>
        </button>

        {sealedBlock && (
          <div className="mt-4">
            <CryptoSealCard data={sealedBlock} />
          </div>
        )}
      </div>
    </div>
  );
};
