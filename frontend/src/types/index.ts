export interface DocumentFields {
  document_number?: string;
  name?: string;
  surname?: string;
  given_names?: string;
  nationality?: string;
  issuing_country?: string;
  date_of_birth?: string;
  sex?: string;
  date_of_expiry?: string;
  address?: string;
  [key: string]: any;
}

export interface ChecksumValidation {
  overall_valid: boolean;
  document_number_check?: boolean;
  dob_check?: boolean;
  expiry_check?: boolean;
  composite_check?: boolean;
  verhoeff_check?: boolean;
}

export interface BlacklistStatus {
  is_blacklisted: boolean;
  matched_list?: string;
  reason?: string;
  severity?: string;
}

export interface DocumentAnalysis {
  document_type: 'passport' | 'visa' | 'aadhaar' | string;
  format?: string;
  extracted_fields: DocumentFields;
  checksum_validation: ChecksumValidation;
  blacklist_status: BlacklistStatus;
  ocr_confidence?: number;
  field_validation?: {
    flags: string[];
    is_valid: boolean;
  };
  viz_mrz_cross_check?: {
    overall_match: boolean;
    confidence_score: number;
    field_matches: Record<string, {
      viz_value: string;
      mrz_value: string;
      similarity: number;
      matched: boolean;
    }>;
  };
  privacy_compliance?: {
    uidai_mandate_compliant: boolean;
    is_redacted: boolean;
    zero_disk_persistence: boolean;
    masked_document_number: string;
  };
  redacted_image_base64?: string;
  ai_recommendation?: 'CLEARED' | 'SECONDARY_INSPECTION' | 'DETAIN';
  allow_manual_override?: boolean;
}

export interface ELAForensics {
  verdict: string;
  tamper_suspicion: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  mean_error_level: number;
  ela_heatmap_base64?: string;
}

export interface GenAIDetection {
  verdict: string;
  ai_generated_probability: number;
  primary_model_score: number;
  fallback_heuristic_score: number;
}

export interface FacialBiometrics {
  face_match: boolean;
  distance: number;
  similarity_score: number;
  status: string;
  liveness_report?: {
    liveness_confirmed: boolean;
    blink_count: number;
    target_blinks: number;
    current_ear: number;
  };
  liveness_metric?: {
    face_detected: boolean;
    is_eye_closed: boolean;
    current_ear: number;
  };
}

export interface RelationalGraph {
  graph_consistency_score: number;
  discrepancy_conflicts: string[];
  nodes: Array<{
    id: string;
    doc_type: string;
    name?: string;
    dob?: string;
    sex?: string;
    doc_number?: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
    consistent: boolean;
  }>;
}

export interface LayerBreakdown {
  traditional_forensics_score: number;
  genai_artifacts_score: number;
  facial_biometrics_score: number;
  relational_consistency_score: number;
}

export interface RiskAssessment {
  composite_risk_score: number;
  verdict: 'ACCEPT' | 'MANUAL_REVIEW' | 'REJECT';
  risk_tier: 'LOW' | 'ELEVATED' | 'HIGH' | 'CRITICAL';
  layer_breakdown: LayerBreakdown;
  rule_audit_log: string[];
}

export interface BatchScreeningResponse {
  status: string;
  document_results: Record<string, DocumentAnalysis>;
  ela_forensics_results: Record<string, ELAForensics>;
  genai_detection_results: Record<string, GenAIDetection>;
  facial_biometrics?: FacialBiometrics;
  relational_graph: RelationalGraph;
  risk_assessment: RiskAssessment;
}

export interface SingleScreeningResponse {
  status: string;
  document_analysis: DocumentAnalysis;
  ela_forensics: ELAForensics;
  genai_detection: GenAIDetection;
  facial_biometrics?: FacialBiometrics;
  relational_graph: RelationalGraph;
  risk_assessment: RiskAssessment;
}

export interface OfficerDecisionRequest {
  validation_data: any;
  officer_id: string;
  checkpoint_id: string;
  final_decision: 'ENTRY_GRANTED' | 'SECONDARY_INSPECTION' | 'ENTRY_REFUSED' | 'DETAINED';
  override_reason_code?: string;
  override_justification?: string;
  supervisor_id?: string;
  incident_id?: string;
}

export interface OfficerDecisionResponse {
  status: string;
  block_index: number;
  log_id: string;
  incident_id: string;
  timestamp: string;
  officer_id: string;
  supervisor_id?: string;
  final_decision: string;
  is_override: boolean;
  override_reason_code?: string;
  override_justification?: string;
  legal_retention_tier: string;
  prev_hash: string;
  audit_sha256: string;
  message?: string;
}

export interface OverrideReason {
  code: string;
  category: 'APPROVE_OVERRIDE' | 'REJECT_OVERRIDE' | string;
  description: string;
}

export interface AuditLogEntry {
  block_index: number;
  log_id: string;
  incident_id: string;
  timestamp: string;
  officer_id: string;
  supervisor_id?: string;
  checkpoint_id: string;
  document_type?: string;
  document_number_masked?: string;
  ai_recommendation: string;
  final_decision: string;
  is_override: boolean | number;
  override_reason_code?: string;
  override_justification?: string;
  legal_retention_tier: string;
  prev_hash: string;
  audit_sha256: string;
}

export interface GovernanceMetrics {
  total_inspections_logged: number;
  total_overrides: number;
  total_agreed_decisions: number;
  override_rate_percentage: number;
  ai_human_agreement_rate_percentage: number;
  top_override_reasons: Record<string, number>;
}

export interface ChainVerificationResponse {
  chain_valid: boolean;
  total_blocks_verified: number;
  corrupted_block_index?: number;
  error_details?: string;
  latest_block_hash: string;
  verified_at: string;
}

export interface DPDPComplianceStatus {
  service: string;
  data_minimization_percentage: number;
  total_records_processed: number;
  purged_clean_records_count: number;
  active_evidentiary_investigation_holds: number;
  ram_zero_persistence_mode: boolean;
  status: string;
}
