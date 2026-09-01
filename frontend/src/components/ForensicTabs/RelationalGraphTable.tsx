import React from 'react';
import { Network, CheckCircle2, AlertTriangle } from 'lucide-react';
import { RelationalGraph } from '../../types';

interface RelationalGraphTableProps {
  graph: RelationalGraph;
}

export const RelationalGraphTable: React.FC<RelationalGraphTableProps> = ({ graph }) => {
  const nodes = graph.nodes || [];
  const conflicts = graph.discrepancy_conflicts || [];
  const consistencyScore = (graph.graph_consistency_score * 100).toFixed(0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-bold font-mono text-slate-900 flex items-center space-x-2">
            <Network className="w-4 h-4 text-amber-600" />
            <span>Cross-Document Relational Identity Alignment Matrix</span>
          </h4>
          <p className="text-xs text-slate-600 mt-0.5 font-medium">
            Cross-checks Name, DOB, Sex, and Document Numbers across Passport, Visa, and Aadhaar to detect synthetic composite identities.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-white/80 px-3.5 py-1.5 rounded-xl border border-[#E2D2A0] shadow-sm">
          <span className="text-xs font-mono font-bold text-slate-600">GRAPH CONSISTENCY:</span>
          <span className="text-sm font-mono font-black text-amber-800">{consistencyScore}%</span>
        </div>
      </div>

      {conflicts.length > 0 && (
        <div className="p-3.5 bg-rose-500/15 border border-rose-500/40 rounded-2xl space-y-1 shadow-sm">
          <div className="flex items-center space-x-2 text-rose-900 font-mono text-xs font-bold">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            <span>RELATIONAL CONFLICTS DETECTED:</span>
          </div>
          {conflicts.map((c, i) => (
            <div key={i} className="text-xs font-mono text-rose-950 font-medium pl-6">
              • {c}
            </div>
          ))}
        </div>
      )}

      {nodes.length > 0 ? (
        <div className="overflow-x-auto rounded-2xl border border-[#E2D2A0] bg-white/80 shadow-sm">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#FAF0CB]/70 text-slate-700 border-b border-[#E2D2A0] uppercase text-[10px] tracking-wider font-bold">
              <tr>
                <th className="p-3">Document Entity</th>
                <th className="p-3">Extracted Name</th>
                <th className="p-3">Date of Birth</th>
                <th className="p-3">Sex</th>
                <th className="p-3">Doc Number</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2D2A0]/50 text-slate-900">
              {nodes.map((node, idx) => (
                <tr key={idx} className="hover:bg-white/95 transition-colors">
                  <td className="p-3 font-bold text-amber-800 uppercase">{node.doc_type}</td>
                  <td className="p-3 font-semibold">{node.name || 'N/A'}</td>
                  <td className="p-3 font-semibold">{node.dob || 'N/A'}</td>
                  <td className="p-3 font-semibold">{node.sex || 'N/A'}</td>
                  <td className="p-3 text-slate-600 font-semibold">{node.doc_number || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-slate-500 text-xs font-mono p-6 bg-white/60 rounded-2xl border border-dashed border-[#E2D2A0] text-center">
          Single document screened. Cross-document relational alignment activates when 2 or more documents are uploaded.
        </div>
      )}
    </div>
  );
};
