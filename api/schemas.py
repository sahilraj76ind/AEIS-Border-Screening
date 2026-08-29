"""
Pydantic Data Contracts & API Schemas
======================================
Defines strict type models for the document validation API response,
ensuring seamless integration with downstream modules (Module 4 Risk Scoring Dashboard).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExtractedFields(BaseModel):
    name: Optional[str] = Field(None, description="Full name of document holder")
    surname: Optional[str] = Field(None, description="Surname/Primary identifier")
    given_names: Optional[str] = Field(None, description="Given names/Secondary identifiers")
    document_type_code: Optional[str] = Field(None, description="2-char document code e.g. 'P<', 'V<'")
    document_number: Optional[str] = Field(None, description="Passport, Visa, or Masked Aadhaar number")
    nationality: Optional[str] = Field(None, description="3-letter ISO/ICAO country code")
    issuing_country: Optional[str] = Field(None, description="3-letter ISO/ICAO issuing country")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in ISO YYYY-MM-DD format")
    sex: Optional[str] = Field(None, description="Gender (M, F, X, or UNSPECIFIED)")
    date_of_expiry: Optional[str] = Field(None, description="Date of expiry in ISO YYYY-MM-DD format")
    optional_data: Optional[str] = Field(None, description="Personal number or optional MRZ metadata")
    address: Optional[str] = Field(None, description="Address (if available, e.g. Aadhaar)")
    state: Optional[str] = Field(None, description="State (if available, e.g. Aadhaar)")
    pincode: Optional[str] = Field(None, description="Pincode (if available, e.g. Aadhaar)")


class ChecksumValidation(BaseModel):
    document_number_check: Optional[bool] = Field(None, description="ICAO 9303 check digit on document number")
    dob_check: Optional[bool] = Field(None, description="ICAO 9303 check digit on date of birth")
    expiry_check: Optional[bool] = Field(None, description="ICAO 9303 check digit on expiry date")
    optional_data_check: Optional[bool] = Field(None, description="ICAO 9303 check digit on optional data")
    composite_check: Optional[bool] = Field(None, description="ICAO 9303 composite check digit")
    verhoeff_check: Optional[bool] = Field(None, description="Verhoeff check on Aadhaar 12-digit UID")
    overall_valid: bool = Field(..., description="True if all applicable mathematical check digits pass")


class FieldValidation(BaseModel):
    flags: List[str] = Field(
        default_factory=list,
        description="Flags raised (e.g. 'EXPIRED', 'INVALID_DOB', 'CHECKSUM_FAILED', 'VIZ_MRZ_NAME_MISMATCH')"
    )


class BlacklistStatus(BaseModel):
    is_blacklisted: bool = Field(..., description="Whether document number matches a security watchlist")
    matched_list: Optional[str] = Field(None, description="Category of watchlist (e.g. 'LOST_STOLEN_TRAVEL_DOCS')")
    reason: Optional[str] = Field(None, description="Reason for watchlist flagging")
    severity: Optional[str] = Field(None, description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")


class FieldMatchDetail(BaseModel):
    viz_value: Optional[str] = Field(None, description="Value extracted from Visual Inspection Zone")
    mrz_value: Optional[str] = Field(None, description="Value extracted from MRZ / Barcode")
    matched: bool = Field(..., description="Whether the two zone values match within tolerance")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity score (0.0 to 1.0)")


class VIZExtractedFields(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    document_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_expiry: Optional[str] = None
    sex: Optional[str] = None
    nationality: Optional[str] = None
    issuing_country: Optional[str] = None


class VIZMRZCrossCheck(BaseModel):
    is_consistent: bool = Field(..., description="True if VIZ text matches MRZ data with high fidelity")
    overall_match_score: float = Field(..., ge=0.0, le=1.0, description="Aggregate cross-zone match score")
    viz_extracted: Optional[VIZExtractedFields] = Field(None, description="Demographic fields read from visual zone")
    field_matches: Dict[str, FieldMatchDetail] = Field(
        default_factory=dict,
        description="Per-field comparison breakdown between VIZ and MRZ"
    )
    mismatch_flags: List[str] = Field(
        default_factory=list,
        description="Flags raised for visual vs MRZ discrepancies (e.g. 'VIZ_MRZ_NAME_MISMATCH')"
    )


class PrivacyCompliance(BaseModel):
    is_redacted: bool = Field(..., description="Whether automated PII redaction has been applied")
    uidai_mandate_compliant: bool = Field(..., description="Full compliance with UIDAI masking directives (Aadhaar Act 2016)")
    raw_pii_persisted_to_disk: bool = Field(False, description="Strictly False: Zero-disk persistence guarantee (RAM only)")
    masked_document_number: Optional[str] = Field(None, description="Masked UID string (e.g. 'XXXX XXXX 1234')")


class DocumentValidationResponse(BaseModel):
    document_type: str = Field(..., description="Document type: 'passport', 'visa', or 'aadhaar'")
    format: Optional[str] = Field(None, description="Format variant: 'TD3', 'TD2', 'AADHAAR_QR', 'AADHAAR_CARD', etc.")
    extracted_fields: ExtractedFields = Field(..., description="Parsed identity fields")
    checksum_validation: ChecksumValidation = Field(..., description="Mathematical check-digit outcomes")
    field_validation: FieldValidation = Field(..., description="Semantic integrity and date validation flags")
    blacklist_status: BlacklistStatus = Field(..., description="Border control watchlist query result")
    viz_mrz_cross_check: Optional[VIZMRZCrossCheck] = Field(
        None,
        description="Visual Inspection Zone vs MRZ forensic cross-check (detects Photoshop tampering)"
    )
    privacy_compliance: Optional[PrivacyCompliance] = Field(
        None,
        description="UIDAI legal compliance, privacy guard certificate, and masking verification"
    )
    redacted_image_base64: Optional[str] = Field(
        None,
        description="Base64 encoded URI of the sanitized image with physical PII black-box redaction applied"
    )
    ocr_confidence: float = Field(..., ge=0.0, le=1.0, description="Estimated OCR / extraction confidence")
    ai_recommendation: str = Field(
        "CLEARED",
        description="AI baseline recommendation: 'CLEARED', 'SECONDARY_INSPECTION', or 'DETAIN'"
    )
    allow_manual_override: bool = Field(
        True,
        description="Whether human officer manual override is permitted against the AI recommendation"
    )


class MRZTextValidationRequest(BaseModel):
    mrz_text: str = Field(..., description="Raw 2-line MRZ string (e.g. 2x44 or 2x36)")
    doc_type: Optional[str] = Field(None, description="Optional doc type hint: 'passport', 'visa', 'auto'")


class ForensicReportRequest(BaseModel):
    validation_data: DocumentValidationResponse = Field(..., description="Validation outcome payload from /validate-document")
    officer_id: Optional[str] = Field("OFFICER-BSF-4821", description="Badge/Identifier of the inspecting officer")
    checkpoint_id: Optional[str] = Field("TERMINAL-3 / IN-GATE-04", description="Border checkpoint gate or terminal ID")
    incident_notes: Optional[str] = Field(None, description="Optional notes or remarks by inspecting officer")


class OfficerDecisionRequest(BaseModel):
    validation_data: DocumentValidationResponse = Field(..., description="AI Validation outcome payload")
    officer_id: str = Field("OFFICER-BSF-4821", description="Badge ID of inspecting officer")
    checkpoint_id: str = Field("TERMINAL-3 / IN-GATE-04", description="Border checkpoint gate or lane ID")
    final_decision: str = Field(
        ...,
        description="Officer's final verdict: 'ENTRY_GRANTED', 'SECONDARY_INSPECTION', 'ENTRY_REFUSED', 'DETAINED'"
    )
    override_reason_code: Optional[str] = Field(
        None,
        description="Standardized reason code if human decision differs from AI recommendation"
    )
    override_justification: Optional[str] = Field(
        None,
        description="Optional officer remarks or notes"
    )
    supervisor_id: Optional[str] = Field(
        None,
        description="Supervisor badge ID required for overriding high-risk DETAIN alerts"
    )
    incident_id: Optional[str] = Field(
        None,
        description="Optional pre-existing incident ID"
    )


class AuditLogEntry(BaseModel):
    block_index: int = Field(..., description="Sequential block index in cryptographic hash chain (0 = Genesis)")
    log_id: str
    incident_id: str
    timestamp: str
    officer_id: str
    supervisor_id: Optional[str] = None
    checkpoint_id: str
    document_type: str
    document_number_masked: str
    ai_recommendation: str
    final_decision: str
    is_override: bool
    override_reason_code: Optional[str] = None
    override_justification: Optional[str] = None
    legal_retention_tier: str = Field(..., description="DPDP retention tier: TIER_1_STANDARD_CLEARED or TIER_2_INVESTIGATION_HOLD")
    is_purged: bool = Field(False, description="Whether personal demographic data has been auto-purged under DPDP Act 2023")
    purged_at: Optional[str] = Field(None, description="Timestamp when data minimization tombstone was applied")
    prev_hash: str = Field(..., description="SHA-256 hash of the preceding block in the chain")
    audit_sha256: str = Field(..., description="Cryptographic SHA-256 seal for this block")


class OfficerDecisionResponse(BaseModel):
    status: str = Field("logged", description="Status of decision logging")
    is_override: bool = Field(..., description="Whether this decision overrode the AI recommendation")
    audit_log: AuditLogEntry = Field(..., description="Immutable cryptographic audit record")


class GovernanceMetricsResponse(BaseModel):
    total_inspections_logged: int
    total_overrides: int
    total_agreed_decisions: int
    override_rate_percentage: float
    ai_human_agreement_rate_percentage: float
    top_override_reasons: Dict[str, int]


class ChainVerificationResponse(BaseModel):
    chain_valid: bool = Field(..., description="Whether cryptographic hash chain is unbroken and 100% authentic")
    total_blocks_verified: int = Field(..., description="Total blocks inspected and verified from genesis")
    corrupted_block_index: Optional[int] = Field(None, description="Index of corrupted or altered block, if any")
    error_details: Optional[str] = Field(None, description="Diagnostic error details if chain failed")
    latest_block_hash: Optional[str] = Field(None, description="SHA-256 seal of the latest block")
    verified_at: str = Field(..., description="UTC verification timestamp")


class RetentionPolicyResponse(BaseModel):
    regulatory_framework: str
    clean_record_retention_hours: int
    clean_record_legal_basis: str
    flagged_record_retention_days: int
    flagged_record_legal_basis: str
    pruning_mechanism: str
    auto_purge_enabled: bool


class PurgeExecutionResponse(BaseModel):
    status: str
    purged_records_count: int
    active_investigation_holds: int
    retention_window_hours_applied: int
    executed_at: str
    statutory_authority: str
    chain_integrity_preserved: bool


class DPDPComplianceStatusResponse(BaseModel):
    total_audit_records_lifetime: int
    total_records_purged_dpdp: int
    active_transient_clean_records: int
    active_evidentiary_investigation_holds: int
    data_minimization_percentage: float
    dpdp_act_2023_compliant: bool




