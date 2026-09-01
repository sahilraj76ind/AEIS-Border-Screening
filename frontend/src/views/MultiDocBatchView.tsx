import React, { useState } from 'react';
import {
  FileText,
  CreditCard,
  User,
  Play,
  Download,
  FileJson,
  Microscope,
  Bot,
  UserCheck,
  Network,
  Lock,
  Layers,
  AlertCircle,
  Sparkles,
  Camera,
  Upload
} from 'lucide-react';
import { FileDropzone } from '../components/FileDropzone';
import { LiveWebcamScanner } from '../components/LiveWebcamScanner';
import { RiskGaugeDial } from '../components/RiskGaugeDial';
import { OfficerDecisionConsole } from '../components/OfficerDecisionConsole';
import { DefenseHeroBar } from '../components/DefenseHeroBar';
import { DefenseSystemReadiness } from '../components/DefenseSystemReadiness';
import { DocumentResultInspector } from '../components/DocumentResultInspector';
import { RelationalGraphTable } from '../components/ForensicTabs/RelationalGraphTable';
import { screenBatchDocuments, downloadForensicPDF } from '../api/client';
import { BatchScreeningResponse } from '../types';

export const MultiDocBatchView: React.FC = () => {
  const [passportFile, setPassportFile] = useState<File | null>(null);
  const [visaFile, setVisaFile] = useState<File | null>(null);
  const [aadhaarFile, setAadhaarFile] = useState<File | null>(null);
  const [selfieFile, setSelfieFile] = useState<File | null>(null);
  const [selfieMode, setSelfieMode] = useState<'upload' | 'camera'>('upload');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [results, setResults] = useState<BatchScreeningResponse | null>(null);
  const [selectedDocKey, setSelectedDocKey] = useState<string>('passport');

  const handleScreening = async () => {
    if (!passportFile && !visaFile && !aadhaarFile) {
      setErrorMsg('Please upload at least one identity document (Passport, Visa, or Aadhaar).');
      return;
    }

    setErrorMsg(null);
    setLoading(true);
    try {
      const data = await screenBatchDocuments({
        passport: passportFile,
        visa: visaFile,
        aadhaar: aadhaarFile,
        selfie: selfieFile,
      });
      setResults(data);
      if (data.document_results) {
        const firstKey = Object.keys(data.document_results)[0] || 'passport';
        setSelectedDocKey(firstKey);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Screening pipeline execution failed.');
    } finally {
      setLoading(false);
    }
  };

  const hasResults = !!results;
  const docKeys = results?.document_results ? Object.keys(results.document_results) : [];
  const currentDoc = results?.document_results?.[selectedDocKey] || (docKeys.length > 0 ? results?.document_results?.[docKeys[0]] : null);

  const rawFileForSelected =
    selectedDocKey === 'passport'
      ? passportFile
      : selectedDocKey === 'visa'
      ? visaFile
      : aadhaarFile;

  const rawUrl = rawFileForSelected ? URL.createObjectURL(rawFileForSelected) : null;
  const selfieUrl = selfieFile ? URL.createObjectURL(selfieFile) : null;

  return (
    <div className="space-y-6">
      {/* Top Hero Telemetry & Interactive Presets Strip */}
      <DefenseHeroBar
        onLoadPreset={(preset) => {
          setPassportFile(preset.passport);
          setVisaFile(preset.visa);
          setAadhaarFile(preset.aadhaar);
          setSelfieFile(preset.selfie);
        }}
      />

      {/* Upload Bays Section */}
      <div className="glass-panel rounded-3xl p-6 relative overflow-hidden shadow-lg border border-[#E2D2A0]/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-mono font-bold text-slate-900 flex items-center space-x-2">
              <Layers className="w-5 h-5 text-amber-600" />
              <span>MULTI-DOCUMENT TRAVELER VERIFICATION BAY</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5 font-medium">
              Upload passport TD3, visa TD2, Aadhaar, and traveler live portrait for comprehensive cross-relational screening.
            </p>
          </div>

          {/* Selfie Mode Switcher in Header for Unified Grid Height Alignment */}
          <div className="flex items-center space-x-1.5 bg-white/80 p-1 rounded-2xl border border-[#E2D2A0] text-xs font-mono shadow-sm self-start sm:self-auto">
            <span className="text-[10px] text-slate-500 font-bold px-2 uppercase">Selfie Input:</span>
            <button
              type="button"
              onClick={() => setSelfieMode('upload')}
              className={`px-3 py-1.5 rounded-xl font-bold transition-all flex items-center space-x-1 ${
                selfieMode === 'upload'
                  ? 'bg-amber-500/20 text-amber-950 border border-amber-500/40 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Upload className="w-3.5 h-3.5 text-amber-700" />
              <span>Upload</span>
            </button>
            <button
              type="button"
              onClick={() => setSelfieMode('camera')}
              className={`px-3 py-1.5 rounded-xl font-bold transition-all flex items-center space-x-1 ${
                selfieMode === 'camera'
                  ? 'bg-amber-500/20 text-amber-950 border border-amber-500/40 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Camera className="w-3.5 h-3.5 text-amber-700" />
              <span>Live Camera</span>
            </button>
          </div>
        </div>

        {/* 4 Identically Aligned Dropzone Bays */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
          <FileDropzone
            label="Passport TD3"
            sublabel="ICAO 9303 Machine Readable Book"
            file={passportFile}
            onFileSelect={setPassportFile}
            icon={<FileText className="w-5 h-5 text-amber-600" />}
            isScanning={loading}
            hasResults={hasResults}
          />

          <FileDropzone
            label="Visa TD2 / Sticker"
            sublabel="Border Entry Visa Sticker"
            file={visaFile}
            onFileSelect={setVisaFile}
            icon={<CreditCard className="w-5 h-5 text-indigo-600" />}
            isScanning={loading}
            hasResults={hasResults}
          />

          <FileDropzone
            label="Aadhaar Card"
            sublabel="UIDAI 12-Digit Identity Card"
            file={aadhaarFile}
            onFileSelect={setAadhaarFile}
            icon={<CreditCard className="w-5 h-5 text-emerald-600" />}
            isScanning={loading}
            hasResults={hasResults}
          />

          {/* Symmetrical 4th Bay */}
          {selfieMode === 'upload' ? (
            <FileDropzone
              label="Traveler Live Selfie"
              sublabel="Presentation Attack Detection (PAD)"
              file={selfieFile}
              onFileSelect={setSelfieFile}
              icon={<User className="w-5 h-5 text-orange-600" />}
              isScanning={loading}
              hasResults={hasResults}
            />
          ) : (
            <LiveWebcamScanner
              capturedFile={selfieFile}
              onCapture={setSelfieFile}
              onClear={() => setSelfieFile(null)}
            />
          )}
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 bg-rose-500/15 border border-rose-500/40 text-rose-900 text-xs font-mono rounded-xl flex items-center space-x-2 shadow-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
            <span className="font-bold">{errorMsg}</span>
          </div>
        )}

        {/* Primary Action Button */}
        <div className="mt-5 space-y-3">
          <button
            onClick={handleScreening}
            disabled={loading}
            className="w-full py-4 px-6 rounded-2xl font-mono font-bold text-sm tracking-wider flex items-center justify-center space-x-2.5 glass-btn-primary text-white shadow-lg transition-all disabled:opacity-50 active:scale-[0.99] cursor-pointer"
          >
            <Play className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            <span>
              {loading
                ? 'AI FORENSIC PIPELINE PROCESSING...'
                : 'EXECUTE COMPREHENSIVE MULTI-LAYER SCREENING'}
            </span>
          </button>
        </div>
      </div>

      {/* Results Dashboard with Swapped Position */}
      {results && currentDoc ? (
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
                validationData={currentDoc}
                riskAssessment={results.risk_assessment}
              />
            </div>
          </div>

          {/* Document Specimen Selector Tabs (if multiple docs uploaded) */}
          {docKeys.length > 1 && (
            <div className="flex items-center space-x-2 bg-white/80 p-1.5 rounded-2xl border border-[#E2D2A0] shadow-sm text-xs font-mono">
              <span className="text-slate-500 px-2 font-bold uppercase">SELECT SPECIMEN:</span>
              {docKeys.map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setSelectedDocKey(k)}
                  className={`px-4 py-1.5 rounded-xl font-bold uppercase transition-all ${
                    selectedDocKey === k
                      ? 'bg-amber-500/20 text-amber-950 border border-amber-500/40 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {k} Specimen
                </button>
              ))}
            </div>
          )}

          {/* Main Reference-Style Document Result Inspector */}
          <DocumentResultInspector
            documentAnalysis={currentDoc}
            riskAssessment={results.risk_assessment}
            elaForensics={results.ela_forensics_results?.[selectedDocKey]}
            genaiDetection={results.genai_detection_results?.[selectedDocKey]}
            facialBiometrics={results.facial_biometrics}
            rawFileUrl={rawUrl}
            selfieUrl={selfieUrl}
            onRefresh={handleScreening}
          />

          {/* Relational Graph Alignment Card */}
          <div className="glass-panel rounded-3xl p-5 border border-[#E2D2A0]/80 shadow-md">
            <RelationalGraphTable graph={results.relational_graph} />
          </div>
        </div>
      ) : (
        <DefenseSystemReadiness />
      )}
    </div>
  );
};
