import React, { useRef, useState } from 'react';
import { UploadCloud, FileCheck, X, Scan, CheckCircle2, Sparkles } from 'lucide-react';

interface FileDropzoneProps {
  label: string;
  sublabel: string;
  file: File | null;
  onFileSelect: (file: File | null) => void;
  accept?: string;
  icon?: React.ReactNode;
  isScanning?: boolean;
  hasResults?: boolean;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  label,
  sublabel,
  file,
  onFileSelect,
  accept = 'image/jpeg,image/png,image/webp,image/jpg',
  icon,
  isScanning = false,
  hasResults = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  const previewUrl = file ? URL.createObjectURL(file) : null;

  // Show document scanning animation when file is loaded and either explicitly scanning OR results have not arrived yet
  const showScanAnimation = file && !hasResults;

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current?.click()}
      className={`glass-panel relative rounded-2xl border-2 border-dashed p-4 transition-all flex flex-col items-center justify-center min-h-[210px] cursor-pointer overflow-hidden ${
        isDragOver
          ? 'border-amber-500 bg-amber-500/15 shadow-glow-amber scale-[1.01]'
          : file
          ? 'border-emerald-600/50 bg-white/80 cursor-default shadow-md'
          : 'border-[#DAC896] hover:border-amber-500/80 hover:bg-white/90 hover:shadow-md'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="hidden"
      />

      {file ? (
        <div className="flex flex-col items-center w-full relative">
          {/* Top Remove File Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onFileSelect(null);
            }}
            className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-rose-500 hover:bg-rose-600 text-white flex items-center justify-center shadow-md transition-transform hover:scale-110 z-20"
            title="Remove File"
          >
            <X className="w-3.5 h-3.5" />
          </button>

          {/* Document Preview Card with Dynamic Holographic Scanning Beam */}
          {previewUrl && (
            <div className="relative w-28 h-28 sm:w-38 sm:h-32 rounded-xl overflow-hidden border border-[#E2D2A0] bg-slate-900/5 mb-2 flex items-center justify-center shadow-inner">
              <img
                src={previewUrl}
                alt="Document Preview"
                className="w-full h-full object-cover"
              />

              {/* Scanning Animation Overlay (sweeps vertically above the document image until results arrive) */}
              {showScanAnimation && (
                <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
                  {/* Subtle Scanning Holographic Grid */}
                  <div className="absolute inset-0 bg-[linear-gradient(to_right,#06b6d415_1px,transparent_1px),linear-gradient(to_bottom,#06b6d415_1px,transparent_1px)] bg-[size:12px_12px]" />

                  {/* High-Tech Glowing Laser Scan Beam */}
                  <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_12px_#06b6d4] animate-scan-beam" />

                  {/* Soft Light Trail Behind the Laser */}
                  <div className="absolute inset-x-0 h-10 bg-gradient-to-b from-cyan-400/20 to-transparent animate-scan-beam" />

                  {/* Holographic HUD Corner Reticles */}
                  <div className="absolute top-1 left-1 w-2.5 h-2.5 border-t-2 border-l-2 border-cyan-400" />
                  <div className="absolute top-1 right-1 w-2.5 h-2.5 border-t-2 border-r-2 border-cyan-400" />
                  <div className="absolute bottom-1 left-1 w-2.5 h-2.5 border-b-2 border-l-2 border-cyan-400" />
                  <div className="absolute bottom-1 right-1 w-2.5 h-2.5 border-b-2 border-r-2 border-cyan-400" />
                </div>
              )}

              {/* Verified Result Badge Overlay (when scanning is complete) */}
              {hasResults && (
                <div className="absolute bottom-1.5 right-1.5 bg-emerald-600/90 text-white rounded-full p-1 shadow-md flex items-center justify-center">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          )}

          {/* File Information & Status */}
          <div className="flex items-center space-x-1.5 text-emerald-800 font-mono text-xs font-bold max-w-[220px] truncate">
            <FileCheck className="w-4 h-4 flex-shrink-0 text-emerald-600" />
            <span className="truncate">{file.name}</span>
          </div>

          <div className="flex items-center space-x-2 mt-1">
            <span className="text-[10px] text-slate-500 font-mono">
              {(file.size / 1024).toFixed(1)} KB
            </span>
            <span className="text-slate-300">•</span>
            {showScanAnimation ? (
              <span className="flex items-center space-x-1 text-[10px] font-mono font-bold text-cyan-700 bg-cyan-500/15 px-2 py-0.5 rounded-full border border-cyan-500/30">
                <Scan className="w-3 h-3 animate-spin text-cyan-600" />
                <span>OPTICAL SCAN ACTIVE</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 text-[10px] font-mono font-bold text-emerald-800 bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/30">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>INSPECTED</span>
              </span>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center text-center py-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500/15 to-indigo-500/15 border border-[#E2D2A0] flex items-center justify-center text-amber-700 mb-2 shadow-sm group-hover:scale-110 transition-transform">
            {icon || <UploadCloud className="w-6 h-6" />}
          </div>
          <span className="text-sm font-bold text-slate-800 tracking-tight">{label}</span>
          <span className="text-xs text-slate-500 mt-0.5 max-w-[190px] font-medium leading-relaxed">{sublabel}</span>
          <span className="mt-2.5 text-[10px] font-mono font-bold text-amber-800 bg-amber-500/15 px-2.5 py-1 rounded-full border border-amber-500/30 tracking-wider shadow-sm">
            CLICK OR DRAG DOCUMENT
          </span>
        </div>
      )}
    </div>
  );
};
