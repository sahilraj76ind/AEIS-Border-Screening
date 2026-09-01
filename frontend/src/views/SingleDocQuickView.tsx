import React, { useState } from 'react';
import {
  FileText,
  Play,
  Download,
  FileJson,
  ShieldAlert,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  User,
  Activity,
  Layers,
  Sparkles
} from 'lucide-react';
import { FileDropzone } from '../components/FileDropzone';
import { RiskGaugeDial } from '../components/RiskGaugeDial';
import { OfficerDecisionConsole } from '../components/OfficerDecisionConsole';
import { DefenseHeroBar } from '../components/DefenseHeroBar';
import { DefenseSystemReadiness } from '../components/DefenseSystemReadiness';
import { DocumentResultInspector } from '../components/DocumentResultInspector';
import { screenSingleDocument, downloadForensicPDF } from '../api/client';
import { SingleScreeningResponse } from '../types';

export const SingleDocQuickView: React.FC = () => {
  const [docFile, setDocFile] = useState<File | null>(null);
  const [selfieFile, setSelfieFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('auto');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [results, setResults] = useState<SingleScreeningResponse | null>(null);

  const handleInspect = async () => {
    if (!docFile) {
      setErrorMsg('Please upload a document image (Passport, Visa, or Aadhaar).');
      return;
    }

    setErrorMsg(null);
    setLoading(true);
    try {
      const data = await screenSingleDocument(docFile, selfieFile, docType);
      setResults(data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Single document screening failed.');
    } finally {
      setLoading(false);
    }
  };

  const analysis = results?.document_analysis;
  const hasResults = !!results;

  const docUrl = docFile ? URL.createObjectURL(docFile) : null;
  const selfieUrl = selfieFile ? URL.createObjectURL(selfieFile) : null;

  return (
    <div className="space-y-6">
      {/* Top Hero Telemetry & Interactive Presets Strip */}
      <DefenseHeroBar
        onLoadPreset={(preset) => {
          const file = preset.passport || preset.visa || preset.aadhaar;
          setDocFile(file);
          setSelfieFile(preset.selfie);
          if (preset.passport) setDocType('passport');
          else if (preset.visa) setDocType('visa');
          else if (preset.aadhaar) setDocType('aadhaar');
        }}
      />

      {/* Upload Section */}
      <div className="glass-panel rounded-3xl p-6 relative overflow-hidden shadow-lg border border-[#E2D2A0]/80">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-mono font-bold text-slate-900 flex items-center space-x-2">
              <FileText className="w-5 h-5 text-amber-600" />
              <span>SINGLE DOCUMENT QUICK INSPECTION BAY</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5 font-medium">
              Rapid forensic validation for Passports, Visas, and Aadhaar cards with instant MRZ & check digit verification.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold text-slate-700">DOCUMENT TYPE:</span>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="bg-white border border-[#E2D2A0] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-amber-900 focus:outline-none focus:border-amber-500 shadow-sm"
            >
              <option value="auto">Auto-Detect</option>
              <option value="passport">Passport (TD3)</option>
              <option value="visa">Visa (TD2)</option>
              <option value="aadhaar">Aadhaar Card</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FileDropzone
            label="Upload Identity Document"
            sublabel="Passport, Visa, or Aadhaar Image"
            file={docFile}
            onFileSelect={setDocFile}
            icon={<FileText className="w-5 h-5 text-amber-600" />}
            isScanning={loading}
            hasResults={hasResults}
          />

          <FileDropzone
            label="Optional Live Selfie"
            sublabel="For Facial Biometric Matching"
            file={selfieFile}
            onFileSelect={setSelfieFile}
            icon={<User className="w-5 h-5 text-indigo-600" />}
            isScanning={loading}
            hasResults={hasResults}
          />
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 bg-rose-500/15 border border-rose-500/40 text-rose-900 text-xs font-mono rounded-xl flex items-center space-x-2 shadow-sm">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
            <span className="font-bold">{errorMsg}</span>
          </div>
        )}

        <div className="mt-5">
          <button
            onClick={handleInspect}
            disabled={loading}
            className="w-full py-4 px-6 rounded-2xl font-mono font-bold text-sm tracking-wider flex items-center justify-center space-x-2.5 glass-btn-primary text-white shadow-lg transition-all disabled:opacity-50 active:scale-[0.99] cursor-pointer"
          >
            <Play className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'PROCESSING OPTICAL OCR & FORENSICS SCAN...' : 'INSPECT DOCUMENT NOW'}</span>
          </button>
        </div>
      </div>

      {/* Results Dashboard with Swapped Position */}
      {results && analysis ? (
        <div className="space-y-6">
          {/* Top Grid: Animated Score Gauge + Officer Sovereign Action Desk */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-5">
              <RiskGaugeDial
                score={results.risk_assessment.composite_risk_score}
                verdict={results.risk_assessment.verdict}
                tier={results.risk_assessment.risk_tier}
              />
            </div>

            <div className="lg:col-span-7">
              <OfficerDecisionConsole
                validationData={analysis}
                riskAssessment={results.risk_assessment}
              />
            </div>
          </div>

          {/* Main Reference-Style Document Result Inspector */}
          <DocumentResultInspector
            documentAnalysis={analysis}
            riskAssessment={results.risk_assessment}
            elaForensics={results.ela_forensics}
            genaiDetection={results.genai_detection}
            facialBiometrics={results.facial_biometrics}
            rawFileUrl={docUrl}
            selfieUrl={selfieUrl}
            onRefresh={handleInspect}
          />
        </div>
      ) : (
        <DefenseSystemReadiness />
      )}
    </div>
  );
};
