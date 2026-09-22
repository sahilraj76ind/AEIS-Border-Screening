import axios from 'axios';
import {
  BatchScreeningResponse,
  SingleScreeningResponse,
  OfficerDecisionRequest,
  OfficerDecisionResponse,
  OverrideReason,
  AuditLogEntry,
  GovernanceMetrics,
  ChainVerificationResponse,
  DPDPComplianceStatus
} from '../types';

const API_BASE = 'https://aeis-border-screening.onrender.com';
const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
});

export const checkHealth = async () => {
  const res = await api.get('/health');
  return res.data;
};

export const getWatchlist = async () => {
  const res = await api.get('/api/v1/watchlist');
  return res.data;
};

export const screenBatchDocuments = async (files: {
  passport?: File | Blob | null;
  visa?: File | Blob | null;
  aadhaar?: File | Blob | null;
  selfie?: File | Blob | null;
}): Promise<BatchScreeningResponse> => {
  const formData = new FormData();
  if (files.passport) formData.append('passport', files.passport);
  if (files.visa) formData.append('visa', files.visa);
  if (files.aadhaar) formData.append('aadhaar', files.aadhaar);
  if (files.selfie) formData.append('selfie', files.selfie);

  const res = await api.post<BatchScreeningResponse>('/api/v1/screen-batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const screenSingleDocument = async (
  documentFile: File | Blob,
  selfieFile?: File | Blob | null,
  docType?: string
): Promise<SingleScreeningResponse> => {
  const formData = new FormData();
  formData.append('document', documentFile);
  if (selfieFile) formData.append('selfie', selfieFile);
  if (docType && docType !== 'auto') formData.append('doc_type', docType);

  const res = await api.post<SingleScreeningResponse>('/api/v1/screen-single', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const getOverrideReasons = async (): Promise<OverrideReason[]> => {
  const res = await api.get<OverrideReason[]>('/api/v1/override-reasons');
  return res.data;
};

export const submitOfficerDecision = async (
  payload: OfficerDecisionRequest
): Promise<OfficerDecisionResponse> => {
  const res = await api.post<OfficerDecisionResponse>('/api/v1/submit-officer-decision', payload);
  return res.data;
};

export const getAuditLogs = async (limit: number = 50): Promise<AuditLogEntry[]> => {
  const res = await api.get<AuditLogEntry[]>(`/api/v1/audit-logs?limit=${limit}`);
  return res.data;
};

export const getGovernanceMetrics = async (): Promise<GovernanceMetrics> => {
  const res = await api.get<GovernanceMetrics>('/api/v1/audit-logs/stats');
  return res.data;
};

export const verifyAuditChain = async (): Promise<ChainVerificationResponse> => {
  const res = await api.get<ChainVerificationResponse>('/api/v1/audit-logs/verify-chain');
  return res.data;
};

export const getDPDPStatus = async (): Promise<DPDPComplianceStatus> => {
  const res = await api.get<DPDPComplianceStatus>('/api/v1/compliance/dpdp-status');
  return res.data;
};

export const purgeExpiredRecords = async (forceAll: boolean = true) => {
  const res = await api.post(`/api/v1/compliance/purge-expired?force_all=${forceAll}`);
  return res.data;
};

export const downloadForensicPDF = async (validationData: any) => {
  const res = await api.post('/api/v1/export-pdf', validationData, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'forensic_audit_report.pdf');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
