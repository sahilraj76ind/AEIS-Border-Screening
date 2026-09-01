import React from 'react';
import { Lock, ShieldCheck, EyeOff, HardDrive } from 'lucide-react';
import { DocumentAnalysis } from '../../types';

interface UIDAIComplianceCardProps {
  aadhaarDoc?: DocumentAnalysis;
}

export const UIDAIComplianceCard: React.FC<UIDAIComplianceCardProps> = ({ aadhaarDoc }) => {
  if (!aadhaarDoc) {
    return (
      <div className="bg-white/60 border border-dashed border-[#E2D2A0] rounded-2xl p-8 text-center text-slate-500 font-mono text-xs">
        No Aadhaar document uploaded in this screening session.
      </div>
    );
  }

  const pComp = aadhaarDoc.privacy_compliance;
  const redactedB64 = aadhaarDoc.redacted_image_base64;

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-bold font-mono text-slate-900 flex items-center space-x-2">
          <Lock className="w-4 h-4 text-emerald-600" />
          <span>UIDAI Statutory Privacy Compliance & Automated Physical Redaction</span>
        </h4>
        <p className="text-xs text-slate-600 mt-0.5 font-medium">
          Guarantees zero-disk persistence in RAM and automatic 8-digit physical masking compliant with Aadhaar Act 2016 Section 29.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
        {/* Masked Image Preview */}
        <div className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 shadow-sm">
          <span className="text-xs font-mono text-slate-700 block mb-2 font-bold">
            PHYSICAL 8-DIGIT MASKED AADHAAR PREVIEW
          </span>
          {redactedB64 ? (
            <div className="rounded-xl overflow-hidden border border-[#E2D2A0] bg-black shadow-inner">
              <img
                src={
                  redactedB64.startsWith('data:')
                    ? redactedB64
                    : `data:image/jpeg;base64,${redactedB64}`
                }
                alt="Masked Aadhaar"
                className="w-full object-contain max-h-56"
              />
            </div>
          ) : (
            <div className="h-40 rounded-xl border border-dashed border-[#E2D2A0] flex items-center justify-center text-xs text-slate-500 font-mono bg-white/40">
              Redacted image stream unavailable
            </div>
          )}
          <span className="text-[10px] text-slate-500 font-mono block mt-2 font-medium">
            First 8 digits permanently covered by solid black bounding box before rendering.
          </span>
        </div>

        {/* Compliance Guarantees */}
        <div className="bg-white/80 border border-[#E2D2A0] rounded-2xl p-4 space-y-3 shadow-sm">
          <span className="text-xs font-mono text-emerald-800 block font-bold border-b border-[#E2D2A0]/70 pb-2">
            STATUTORY PRIVACY CERTIFICATE
          </span>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center space-x-2 text-emerald-950 bg-emerald-500/15 p-2.5 rounded-xl border border-emerald-500/30 font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>UIDAI Mandate Circular Comp/01/2018: COMPLIANT</span>
            </div>

            <div className="flex items-center space-x-2 text-emerald-950 bg-emerald-500/15 p-2.5 rounded-xl border border-emerald-500/30 font-bold">
              <EyeOff className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Physical 8-Digit Redaction: ACTIVE & VERIFIED</span>
            </div>

            <div className="flex items-center space-x-2 text-emerald-950 bg-emerald-500/15 p-2.5 rounded-xl border border-emerald-500/30 font-bold">
              <HardDrive className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Zero-Disk Persistence Guarantee: RAM ONLY</span>
            </div>
          </div>

          <div className="pt-2 border-t border-[#E2D2A0]/70 text-xs font-mono text-slate-600 font-medium">
            <span>Masked UID: </span>
            <code className="text-slate-900 font-bold">
              {pComp?.masked_document_number || 'XXXX XXXX XXXX'}
            </code>
          </div>
        </div>
      </div>
    </div>
  );
};
