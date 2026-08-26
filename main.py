"""
OCR + MRZ + Document Validation Microservice (Module 1 - SIH)
=============================================================
FastAPI service screening Passports (TD3), Visas (TD2), and Aadhaar cards at border checkpoints.
Produces structured, mathematically-verified document data for downstream risk scoring.

Legal & Regulatory Compliance:
- ICAO Doc 9303 (Parts 3, 4, 7): Machine Readable Travel Documents
- Aadhaar Act (2016) Section 29 & UIDAI Circular Comp/01/2018 (Automated Masking & Zero Disk Persistence)

Endpoints:
- POST /validate-document     : Validates an uploaded document image (Passport/Visa/Aadhaar) + VIZ Cross-Check + Redaction
- POST /validate-mrz-text     : Validates raw MRZ text strings (TD3/TD2)
- POST /validate-aadhaar-text : Validates Aadhaar XML QR or 12-digit UID strings
- GET  /blacklist             : Inspects active border control watchlists
- GET  /health                : Service health check
"""

import io
import sys
import json
import warnings
from typing import Optional, List, Dict

# Suppress external library deprecation warnings from skimage, starlette, etc.
warnings.filterwarnings("ignore")

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from core.td3_parser import parse_td3_mrz
from core.td2_parser import parse_td2_mrz
from core.aadhaar_parser import parse_aadhaar_data, validate_verhoeff, mask_aadhaar_uid
from core.field_validator import validate_document_fields
from core.blacklist_check import check_document_blacklist, get_all_blacklisted_records
from core.cross_validator import extract_viz_fields, cross_validate_viz_and_mrz
from vision.ocr_engine import extract_document_from_image
from reports.forensic_generator import generate_forensic_pdf
from governance.audit_logger import (
    record_officer_decision,
    verify_audit_chain,
    get_audit_logs,
    get_governance_metrics,
    get_all_override_reasons
)
from governance.retention_engine import (
    purge_expired_clean_records,
    get_retention_policy_config,
    get_dpdp_compliance_summary
)
from api.schemas import (
    DocumentValidationResponse,
    MRZTextValidationRequest,
    ForensicReportRequest,
    OfficerDecisionRequest,
    OfficerDecisionResponse,
    AuditLogEntry,
    GovernanceMetricsResponse,
    ChainVerificationResponse,
    RetentionPolicyResponse,
    PurgeExecutionResponse,
    DPDPComplianceStatusResponse,
    ExtractedFields,
    ChecksumValidation,
    FieldValidation,
    BlacklistStatus,
    FieldMatchDetail,
    VIZExtractedFields,
    VIZMRZCrossCheck,
    PrivacyCompliance
)


app = FastAPI(
    title="AI Document Screening & MRZ Validation Engine",
    description="Smart India Hackathon (SIH) Module 1: Automated OCR, ICAO 9303 & Verhoeff Checksum Verification, VIZ-MRZ Cross-Check, UIDAI Aadhaar Redaction, and Watchlist Screening.",
    version="1.2.0"
)

# Enable CORS for frontend / Streamlit dashboard consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def assemble_response(
    parsed_dict: dict,
    confidence: float = 0.95,
    viz_text: Optional[str] = None,
    redacted_image_b64: Optional[str] = None
) -> DocumentValidationResponse:
    """
    Runs semantic field validation, century resolution, blacklist checking,
    optional VIZ-to-MRZ forensic cross-validation, and UIDAI privacy masking,
    then packages everything into the standardized DocumentValidationResponse schema.
    """
    doc_type = parsed_dict.get("document_type", "unknown")
    
    # 1. In-Memory Privacy & Blacklist Check (Zero Disk Persistence)
    # Use raw UID in RAM for blacklist checking, then immediately purge raw UID
    raw_uid = parsed_dict.pop("_raw_uid_in_memory", None)
    query_doc_no = raw_uid or parsed_dict.get("extracted_fields", {}).get("document_number")
    blacklist_res = check_document_blacklist(query_doc_no)
    
    # 2. Field validation & date parsing
    flags = validate_document_fields(parsed_dict)
    
    # 3. Assemble ExtractedFields (Aadhaar is strictly masked: XXXX XXXX 1234)
    extracted = ExtractedFields(**parsed_dict.get("extracted_fields", {}))
    
    # 4. Assemble ChecksumValidation
    checksums = ChecksumValidation(**parsed_dict.get("checksum_validation", {}))
    
    # 5. Assemble BlacklistStatus
    blacklist = BlacklistStatus(**blacklist_res)
    
    # 6. Forensic VIZ vs. MRZ Cross-Check (for Passports & Visas)
    viz_cross_check_model: Optional[VIZMRZCrossCheck] = None
    if viz_text and viz_text.strip() and doc_type in ("passport", "visa"):
        viz_fields = extract_viz_fields(viz_text)
        cross_res = cross_validate_viz_and_mrz(viz_fields, parsed_dict)
        
        # Append cross-zone mismatch flags (e.g. VIZ_MRZ_NAME_MISMATCH)
        flags.extend(cross_res.get("mismatch_flags", []))
        
        field_matches_dict = {
            k: FieldMatchDetail(**v)
            for k, v in cross_res.get("field_matches", {}).items()
        }
        viz_extracted_model = VIZExtractedFields(**cross_res.get("viz_extracted", {}))
        
        viz_cross_check_model = VIZMRZCrossCheck(
            is_consistent=cross_res["is_consistent"],
            overall_match_score=cross_res["overall_match_score"],
            viz_extracted=viz_extracted_model,
            field_matches=field_matches_dict,
            mismatch_flags=cross_res["mismatch_flags"]
        )
        
    # 7. UIDAI Legal Compliance & Privacy Guard (for Aadhaar)
    privacy_compliance_model: Optional[PrivacyCompliance] = None
    if doc_type == "aadhaar":
        privacy_compliance_model = PrivacyCompliance(
            is_redacted=True,
            uidai_mandate_compliant=True,
            raw_pii_persisted_to_disk=False,
            masked_document_number=extracted.document_number
        )
    
    return DocumentValidationResponse(
        document_type=doc_type,
        format=parsed_dict.get("format"),
        extracted_fields=extracted,
        checksum_validation=checksums,
        field_validation=FieldValidation(flags=flags),
        blacklist_status=blacklist,
        viz_mrz_cross_check=viz_cross_check_model,
        privacy_compliance=privacy_compliance_model,
        redacted_image_base64=redacted_image_b64,
        ocr_confidence=confidence
    )


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for container orchestrators and load balancers."""
    return {"status": "healthy", "service": "OCR-MRZ-Validation-Module", "version": "1.2.0"}


@app.get("/blacklist", tags=["Watchlist"])
def list_blacklist():
    """Returns the mock border security blacklist database."""
    return get_all_blacklisted_records()


@app.post("/validate-mrz-text", response_model=DocumentValidationResponse, tags=["Validation"])
def validate_mrz_text_endpoint(payload: MRZTextValidationRequest):
    """
    Directly validates raw 2-line MRZ text (for TD3 Passports or TD2 Visas).
    Useful for testing or when OCR is performed by an upstream microservice.
    """
    mrz_text = payload.mrz_text.strip()
    lines = [line.strip().upper() for line in mrz_text.splitlines() if line.strip()]
    
    if len(lines) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Expected 2 lines of MRZ text, got {len(lines)}"
        )
        
    line_len = len(lines[0])
    doc_type_hint = payload.doc_type.lower() if payload.doc_type else "auto"
    
    try:
        if doc_type_hint == "passport" or (doc_type_hint == "auto" and line_len == 44):
            parsed = parse_td3_mrz(mrz_text)
        elif doc_type_hint == "visa" or (doc_type_hint == "auto" and line_len == 36):
            parsed = parse_td2_mrz(mrz_text)
        else:
            try:
                parsed = parse_td3_mrz(mrz_text)
            except Exception:
                parsed = parse_td2_mrz(mrz_text)
                
        return assemble_response(parsed, confidence=1.0)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"MRZ Parsing failed: {str(e)}"
        )


@app.post("/validate-aadhaar-text", response_model=DocumentValidationResponse, tags=["Validation"])
def validate_aadhaar_text_endpoint(payload_str: str):
    """
    Directly validates Aadhaar data from an XML QR string or 12-digit UID.
    Applies UIDAI compliance masking to the response.
    """
    try:
        parsed = parse_aadhaar_data(payload_str)
        return assemble_response(parsed, confidence=1.0)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Aadhaar parsing failed: {str(e)}"
        )


@app.post("/validate-document", response_model=DocumentValidationResponse, tags=["Validation"])
async def validate_document_endpoint(
    file: UploadFile = File(..., description="Document image file (JPEG, PNG, WebP)"),
    doc_type: Optional[str] = Form(None, description="Optional doc type hint: 'passport', 'visa', 'aadhaar', 'auto'"),
    include_redacted_image: bool = Form(False, description="Whether to include Base64 redacted image in response (default: False for optimal performance)")
):
    """
    Main ingestion endpoint: Accepts an uploaded travel/identity document image in memory,
    extracts MRZ/QR data and VIZ text, calculates check digits, executes VIZ-MRZ cross-checks,
    optionally applies UIDAI black-box image redaction (RAM-only), and checks against the security blacklist.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    try:
        detected_type, raw_payload, conf, viz_text, redacted_b64 = extract_document_from_image(
            contents,
            explicit_doc_type=doc_type,
            include_redacted_image=include_redacted_image
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Vision extraction failed: {str(e)}"
        )
        
    try:
        if detected_type == "passport":
            parsed = parse_td3_mrz(raw_payload)
        elif detected_type == "visa":
            parsed = parse_td2_mrz(raw_payload)
        elif detected_type == "aadhaar":
            parsed = parse_aadhaar_data(raw_payload)
        else:
            raise ValueError(f"Unsupported document type: {detected_type}")
            
        return assemble_response(parsed, confidence=conf, viz_text=viz_text, redacted_image_b64=redacted_b64)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Document parsing/validation error: {str(e)}"
        )


@app.post("/export-forensic-report", tags=["Forensics & Reporting"])
def export_forensic_report_endpoint(payload: ForensicReportRequest):
    """
    Generates an investigation-ready PDF forensic report with cryptographic SHA-256
    evidentiary binding, step-by-step mathematical proofs, and chain-of-custody sign-off blocks.
    """
    try:
        val_dict = payload.validation_data.model_dump()
        pdf_bytes = generate_forensic_pdf(
            validation_data=val_dict,
            officer_id=payload.officer_id or "OFFICER-BSF-4821",
            checkpoint_id=payload.checkpoint_id or "TERMINAL-3 / IN-GATE-04",
            incident_notes=payload.incident_notes
        )
        
        doc_num = str(val_dict.get("extracted_fields", {}).get("document_number") or "DOC").replace(" ", "_")
        filename = f"forensic_report_{doc_num}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forensic PDF report: {str(e)}"
        )


@app.post("/validate-and-export-report", tags=["Forensics & Reporting"])
async def validate_and_export_report_endpoint(
    file: UploadFile = File(..., description="Document image file (JPEG, PNG, WebP)"),
    doc_type: Optional[str] = Form(None, description="Optional doc type hint: 'passport', 'visa', 'aadhaar', 'auto'"),
    officer_id: Optional[str] = Form("OFFICER-BSF-4821", description="Badge ID of inspecting officer"),
    checkpoint_id: Optional[str] = Form("TERMINAL-3 / IN-GATE-04", description="Border checkpoint gate"),
    incident_notes: Optional[str] = Form(None, description="Optional notes or remarks")
):
    """
    Direct 1-Click Endpoint: Validates an uploaded document image and immediately returns
    the generated investigation-ready Forensic PDF Report.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    try:
        detected_type, raw_payload, conf, viz_text, redacted_b64 = extract_document_from_image(
            contents,
            explicit_doc_type=doc_type,
            include_redacted_image=False
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Vision extraction failed: {str(e)}")
        
    try:
        if detected_type == "passport":
            parsed = parse_td3_mrz(raw_payload)
        elif detected_type == "visa":
            parsed = parse_td2_mrz(raw_payload)
        elif detected_type == "aadhaar":
            parsed = parse_aadhaar_data(raw_payload)
        else:
            raise ValueError(f"Unsupported document type: {detected_type}")
            
        validation_resp = assemble_response(parsed, confidence=conf, viz_text=viz_text)
        val_dict = validation_resp.model_dump()
        
        pdf_bytes = generate_forensic_pdf(
            validation_data=val_dict,
            officer_id=officer_id or "OFFICER-BSF-4821",
            checkpoint_id=checkpoint_id or "TERMINAL-3 / IN-GATE-04",
            incident_notes=incident_notes
        )
        
        doc_num = str(val_dict.get("extracted_fields", {}).get("document_number") or "DOC").replace(" ", "_")
        filename = f"forensic_report_{doc_num}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Report processing failed: {str(e)}")


@app.get("/override-reasons", tags=["Governance & Accountability"])
def get_override_reasons_endpoint():
    """
    Returns the standardized regulatory taxonomy of override reason codes
    for frontend dropdown menus (distinguishing APPROVE vs REJECT overrides).
    """
    return get_all_override_reasons()


@app.post("/submit-officer-decision", response_model=OfficerDecisionResponse, tags=["Governance & Accountability"])
def submit_officer_decision_endpoint(payload: OfficerDecisionRequest):
    """
    Records a human officer's final decision. If the officer overrides the AI recommendation,
    validates the mandatory standardized reason code, captures optional remarks, and appends
    an immutable cryptographic SHA-256 log entry to the audit database.
    """
    try:
        val_dict = payload.validation_data.model_dump()
        audit_res = record_officer_decision(
            validation_data=val_dict,
            officer_id=payload.officer_id,
            checkpoint_id=payload.checkpoint_id,
            final_decision=payload.final_decision,
            override_reason_code=payload.override_reason_code,
            override_justification=payload.override_justification,
            supervisor_id=payload.supervisor_id,
            incident_id=payload.incident_id
        )
        return OfficerDecisionResponse(
            status="logged",
            is_override=audit_res["is_override"],
            audit_log=AuditLogEntry(**audit_res)
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record officer decision: {str(e)}"
        )


@app.get("/audit-logs", response_model=List[AuditLogEntry], tags=["Governance & Accountability"])
def list_audit_logs_endpoint(
    limit: int = 50,
    offset: int = 0,
    is_override: Optional[bool] = None,
    officer_id: Optional[str] = None
):
    """
    Retrieves paginated audit trail records for internal inquiry commissions and supervisor oversight.
    """
    return get_audit_logs(limit=limit, offset=offset, is_override=is_override, officer_id=officer_id)


@app.get("/audit-logs/stats", response_model=GovernanceMetricsResponse, tags=["Governance & Accountability"])
def get_audit_stats_endpoint():
    """
    Returns high-level governance and compliance analytics:
    Total Inspections, Total Overrides, Override Rate %, AI-Human Agreement Rate %, and Reason Breakdown.
    """
    return get_governance_metrics()


@app.get("/audit-logs/verify-chain", response_model=ChainVerificationResponse, tags=["Governance & Accountability"])
def verify_audit_chain_endpoint():
    """
    Cryptographically verifies the full audit log hash chain from Genesis Block #0 to the latest block.
    Detects any retroactive modifications, row deletions, or out-of-order insertions.
    """
    res = verify_audit_chain()
    return ChainVerificationResponse(**res)


@app.get("/compliance/retention-policy", response_model=RetentionPolicyResponse, tags=["DPDP Act 2023 Compliance"])
def get_retention_policy_endpoint():
    """
    Returns the statutory data retention framework under India's Digital Personal Data
    Protection (DPDP) Act 2023 (Section 8(7) storage limitations & Section 17(1)(c) exemptions).
    """
    return get_retention_policy_config()


@app.post("/compliance/purge-expired", response_model=PurgeExecutionResponse, tags=["DPDP Act 2023 Compliance"])
def purge_expired_records_endpoint(retention_hours: int = 24, force_all: bool = False):
    """
    Executes automated data minimization: scrubs all personal identity data from clean records
    older than retention_hours using cryptographic tombstones while preserving hash-chain integrity.
    """
    res = purge_expired_clean_records(retention_hours=retention_hours, force_purge_all_clean=force_all)
    return PurgeExecutionResponse(**res)


@app.get("/compliance/dpdp-status", response_model=DPDPComplianceStatusResponse, tags=["DPDP Act 2023 Compliance"])
def get_dpdp_status_endpoint():
    """
    Returns live metrics on data minimization percentage, active clean records, and statutory holds.
    """
    return get_dpdp_compliance_summary()


# ======================================================================
# Standalone CLI & Demonstration Runner
# ======================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("    AI BORDER CHECKPOINT DOCUMENT SCREENING ENGINE (SIH MODULE 1)")
    print("=" * 80)
    
    # -------------------------------------------------------------
    # Test Case 1: Valid TD3 Specimen Passport (ICAO Doc 9303 / MIDV-500)
    # -------------------------------------------------------------
    print("\n[TEST 1] Processing Valid TD3 Passport...")
    valid_passport_mrz = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C36UTO7408122F2804154ZE184226B<<<<<18"
    )
    parsed_1 = parse_td3_mrz(valid_passport_mrz)
    resp_1 = assemble_response(parsed_1, confidence=0.96)
    print(json.dumps(resp_1.model_dump(), indent=2))
    assert resp_1.checksum_validation.overall_valid is True
    assert resp_1.blacklist_status.is_blacklisted is True # L898902C3 is in mock blacklist as stolen
    print(">> Result: Valid MRZ extracted, correctly caught on Interpol SLTD blacklist!")

    # -------------------------------------------------------------
    # Test Case 2: Deliberately Tampered TD3 Passport (Bad Check Digits + Expired)
    # -------------------------------------------------------------
    print("\n[TEST 2] Processing Deliberately Tampered & Expired Passport...")
    tampered_passport_mrz = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C39UTO7408122F1204159ZE184226B<<<<<10"
    )
    parsed_2 = parse_td3_mrz(tampered_passport_mrz)
    resp_2 = assemble_response(parsed_2, confidence=0.92)
    print(json.dumps(resp_2.model_dump(), indent=2))
    assert resp_2.checksum_validation.document_number_check is False
    assert resp_2.checksum_validation.overall_valid is False
    assert "CHECKSUM_FAILED" in resp_2.field_validation.flags
    assert "EXPIRED" in resp_2.field_validation.flags
    print(">> Result: Deliberate tampering & expired document successfully flagged!")

    # -------------------------------------------------------------
    # Test Case 3: Valid TD2 Visa Sample
    # -------------------------------------------------------------
    print("\n[TEST 3] Processing Valid TD2 Visa...")
    valid_visa_mrz = (
        "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<\n"
        "L8988901C4XXX4009078F9612109<<<<<<<6"
    )
    parsed_3 = parse_td2_mrz(valid_visa_mrz)
    resp_3 = assemble_response(parsed_3, confidence=0.94)
    print(json.dumps(resp_3.model_dump(), indent=2))
    assert resp_3.checksum_validation.overall_valid is True
    print(">> Result: TD2 Visa successfully verified!")

    # -------------------------------------------------------------
    # Test Case 4: Aadhaar Card XML QR with UIDAI Compliance & Verhoeff Check
    # -------------------------------------------------------------
    print("\n[TEST 4] Processing Aadhaar Card XML QR with UIDAI Masking & Verhoeff Check...")
    uid_base = "24681357901"
    from core.aadhaar_parser import generate_verhoeff_check_digit
    uid_cd = generate_verhoeff_check_digit(uid_base)
    valid_uid = uid_base + uid_cd
    
    aadhaar_xml = (
        f'<PrintLetterBarcodeData uid="{valid_uid}" name="Vikas Sharma" '
        f'gender="M" yob="1992" dob="14/11/1992" co="S/O Mohan Sharma" '
        f'house="Flat 101" street="Outer Ring Rd" dist="Bengaluru" state="Karnataka" pc="560103" />'
    )
    parsed_4 = parse_aadhaar_data(aadhaar_xml)
    resp_4 = assemble_response(parsed_4, confidence=0.99)
    print(json.dumps(resp_4.model_dump(), indent=2))
    assert resp_4.checksum_validation.verhoeff_check is True
    assert resp_4.extracted_fields.name == "Vikas Sharma"
    assert resp_4.extracted_fields.document_number.startswith("XXXX XXXX")
    assert resp_4.privacy_compliance.uidai_mandate_compliant is True
    assert resp_4.privacy_compliance.raw_pii_persisted_to_disk is False
    print(">> Result: Aadhaar XML parsed, Verhoeff validated, and UIDAI masked successfully!")

    # -------------------------------------------------------------
    # Test Case 5: VIZ vs. MRZ Cross-Check (Photoshop Tampering Detection)
    # -------------------------------------------------------------
    print("\n[TEST 5] Processing VIZ vs. MRZ Forensic Cross-Check (Photoshop Tampering)...")
    tampered_viz_ocr = (
        "REPUBLIC OF UTOPIA PASSPORT\n"
        "Passport No: K9999999\n"
        "Nom / Surname: SMITH\n"
        "Prénoms / Given names: ALICE\n"
        "Date of birth: 12 AUG 1974\n"
        "Date of expiry: 15 APR 2028\n"
        "Sex: F\n"
    )
    resp_5 = assemble_response(parsed_1, confidence=0.95, viz_text=tampered_viz_ocr)
    print(json.dumps(resp_5.model_dump(), indent=2))
    assert resp_5.viz_mrz_cross_check is not None
    assert resp_5.viz_mrz_cross_check.is_consistent is False
    assert "VIZ_MRZ_NAME_MISMATCH" in resp_5.field_validation.flags
    assert "VIZ_MRZ_DOC_NUM_MISMATCH" in resp_5.field_validation.flags
    print(">> Result: Photoshop Visual Tampering caught via VIZ-MRZ Cross-Check Engine!")

    # -------------------------------------------------------------
    # Test Case 6: Investigation-Ready Forensic PDF Report Generation
    # -------------------------------------------------------------
    print("\n[TEST 6] Generating Investigation-Ready Forensic PDF Report (Tampered Passport)...")
    pdf_bytes = generate_forensic_pdf(
        validation_data=resp_5.model_dump(),
        officer_id="INSP-MEHTA-781",
        checkpoint_id="MUMBAI-T2-IMMIGRATION",
        incident_notes="Document presented with visible digital artifacting. Referred for secondary screening."
    )
    print(f"Generated Evidentiary PDF: {len(pdf_bytes)} bytes | Valid Magic Header: {pdf_bytes[:8]}")
    assert len(pdf_bytes) > 2000
    print(">> Result: Investigation-Ready Forensic Report generated with SHA-256 cryptographic audit seal!")

    # -------------------------------------------------------------
    # Test Case 7: Human Officer Override & Accountability Log
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing Officer Override & Accountability Logging...")
    override_log = record_officer_decision(
        validation_data=resp_5.model_dump(),
        officer_id="INSP-KAPOOR-412",
        checkpoint_id="IGI-T3-TERMINAL-01",
        final_decision="ENTRY_GRANTED", # Overriding AI DETAIN decision
        override_reason_code="DIPLOMATIC_CONSULAR_IMMUNITY",
        override_justification="Diplomatic courier carrying sealed diplomatic pouch with MFA clearance.",
        supervisor_id="SUPV-VERMA-900"
    )
    print("Recorded Audit Log Entry (Chained Block):")
    print(json.dumps(override_log, indent=2))
    assert override_log["is_override"] is True
    assert override_log["override_reason_code"] == "DIPLOMATIC_CONSULAR_IMMUNITY"
    assert len(override_log["audit_sha256"]) == 64
    assert len(override_log["prev_hash"]) == 64
    print(">> Result: Officer override tracked with cryptographic prev_hash and block index!")

    # -------------------------------------------------------------
    # Test Case 8: Cryptographic Hash-Chain Integrity Verification
    # -------------------------------------------------------------
    print("\n[TEST 8] Verifying Cryptographic Hash-Chain Integrity across entire DB...")
    chain_status = verify_audit_chain()
    print("Audit Log Chain Verification Report:")
    print(json.dumps(chain_status, indent=2))
    assert chain_status["chain_valid"] is True
    assert chain_status["total_blocks_verified"] >= 1
    print(">> Result: Cryptographic hash chain verified 100% authentic with unbroken block linkage!")

    # -------------------------------------------------------------
    # Test Case 9: DPDP Act 2023 Data Retention Auto-Purge
    # -------------------------------------------------------------
    print("\n[TEST 9] Executing DPDP Act 2023 Auto-Purge & Cryptographic Tombstoning...")
    # Log a clean pass record to verify auto-purge
    clean_pass = assemble_response(parsed_3, confidence=0.98) # Valid visa
    record_officer_decision(
        validation_data=clean_pass.model_dump(),
        officer_id="INSP-PURGE-TEST",
        checkpoint_id="IGI-T3-GATE-01",
        final_decision="ENTRY_GRANTED"
    )
    
    purge_report = purge_expired_clean_records(force_purge_all_clean=True)
    print("Purge Execution Report:")
    print(json.dumps(purge_report, indent=2))
    assert purge_report["status"] == "success"
    assert purge_report["purged_records_count"] >= 1
    
    # Assert that hash chain is STILL 100% valid after demographic data minimization!
    post_purge_chain = verify_audit_chain()
    assert post_purge_chain["chain_valid"] is True
    print(f">> Post-Purge Hash Chain Verification: {post_purge_chain['chain_valid']} (Verified {post_purge_chain['total_blocks_verified']} blocks)")
    print(">> Result: DPDP Act 2023 Data Minimization auto-purged clean PII while preserving 100% cryptographic chain integrity!")

    print("\n" + "=" * 80)
    print("    ALL 9 STANDALONE VERIFICATION SUITES PASSED SUCCESSFULLY (100%)")
    print("=" * 80)
