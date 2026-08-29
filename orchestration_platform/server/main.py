"""
Master Backend Orchestration Server (FastAPI)
==============================================
Asynchronously coordinates:
1. Module 1 (OCR, MRZ TD3/TD2, Aadhaar Verhoeff, VIZ Cross-Check, Blacklist)
2. Module 2 (Error Level Analysis - ELA)
3. Module 3 (GenAI Artifact Detection & DeepFace Biometrics)
4. Person D (Cross-Document Relational Graph & Composite Risk Engine)
"""

import os
import sys
import io
import json
import warnings
from pathlib import Path
from typing import Optional, List, Dict, Any

warnings.filterwarnings("ignore")

# Dynamic Root & Package Path Resolution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from wrappers.ocr_adapter import process_document_ocr
from wrappers.ela_adapter import analyze_ela_tampering
from wrappers.ai_vision_adapter import run_ai_generated_detection, run_facial_biometric_verification
from engine.cross_doc_graph import build_and_evaluate_cross_document_graph
from engine.composite_risk_engine import evaluate_composite_risk
from core.blacklist_check import get_all_blacklisted_records
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
    OfficerDecisionRequest,
    OfficerDecisionResponse,
    AuditLogEntry,
    GovernanceMetricsResponse,
    ChainVerificationResponse,
    RetentionPolicyResponse,
    PurgeExecutionResponse,
    DPDPComplianceStatusResponse
)

app = FastAPI(
    title="AI Document Fraud Screening & Verification Platform",
    description="Master Backend Orchestration API combining traditional ELA tamper forensics, GenAI synthetic artifact detection, facial biometric matching, cross-document relational consistency graph, and explainable 0-100 composite risk scoring.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Returns platform health status and integration layer version."""
    return {
        "status": "healthy",
        "service": "AI-Document-Fraud-Screening-Platform",
        "version": "2.0.0",
        "modules": {
            "module_1_ocr_mrz": "ONLINE",
            "module_2_ela_forensics": "ONLINE",
            "module_3_genai_biometrics": "ONLINE",
            "person_d_risk_graph_engine": "ONLINE"
        }
    }


@app.get("/api/v1/watchlist", tags=["Watchlist"])
def get_watchlist():
    """Returns active border control watchlists."""
    return get_all_blacklisted_records()


@app.post("/api/v1/screen-single", tags=["Screening"])
async def screen_single_document(
    document: UploadFile = File(...),
    selfie: Optional[UploadFile] = File(None),
    doc_type: Optional[str] = Form(None)
):
    """
    Screens a single uploaded document image (Passport, Visa, or Aadhaar Card)
    and optional traveler selfie image.
    Returns complete multi-layered verification analysis and 0-100 composite risk score.
    """
    try:
        doc_bytes = await document.read()
        if not doc_bytes:
            raise HTTPException(status_code=400, detail="Uploaded document file is empty.")

        # 1. OCR & MRZ Parsing
        ocr_res = process_document_ocr(
            image_bytes=doc_bytes,
            explicit_doc_type=doc_type,
            include_redacted_image=True
        )

        # 2. Error Level Analysis (ELA)
        ela_res = analyze_ela_tampering(doc_bytes)

        # 3. GenAI Artifact Detection
        ai_res = run_ai_generated_detection(doc_bytes)

        # 4. Facial Biometrics & Selfie GenAI Detection (if selfie provided)
        face_res = None
        if selfie:
            selfie_bytes = await selfie.read()
            if selfie_bytes:
                face_res = run_facial_biometric_verification(doc_bytes, selfie_bytes)
                selfie_ai = run_ai_generated_detection(selfie_bytes)
                if selfie_ai.get("ai_generated_probability", 0.0) > ai_res.get("ai_generated_probability", 0.0):
                    ai_res = selfie_ai

        # 5. Build Relational Consistency Graph (single document baseline)
        graph_res = build_and_evaluate_cross_document_graph(
            doc_results={"primary_doc": ocr_res},
            face_verification_result=face_res
        )

        # 6. Composite Risk Score Evaluation
        risk_res = evaluate_composite_risk(
            ocr_result=ocr_res,
            ela_result=ela_res,
            ai_vision_result=ai_res,
            face_verification_result=face_res,
            cross_doc_graph_result=graph_res
        )

        return {
            "status": "SUCCESS",
            "document_analysis": ocr_res,
            "ela_forensics": ela_res,
            "genai_detection": ai_res,
            "facial_biometrics": face_res,
            "relational_graph": graph_res,
            "risk_assessment": risk_res
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Single Document Screening Failed: {str(e)}"
        )


@app.post("/api/v1/screen-batch", tags=["Screening"])
async def screen_batch_documents(
    passport: Optional[UploadFile] = File(None),
    visa: Optional[UploadFile] = File(None),
    aadhaar: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None)
):
    """
    Multi-document batch verification endpoint.
    Processes Passport, Visa, Aadhaar, and Selfie concurrently.
    Evaluates cross-document relational consistency graph and overall composite risk score.
    """
    try:
        doc_results: Dict[str, Dict[str, Any]] = {}
        ela_results: Dict[str, Dict[str, Any]] = {}
        ai_results: Dict[str, Dict[str, Any]] = {}

        primary_doc_bytes: Optional[bytes] = None

        # 1. Process Passport
        if passport:
            p_bytes = await passport.read()
            if p_bytes:
                primary_doc_bytes = primary_doc_bytes or p_bytes
                doc_results["passport"] = process_document_ocr(p_bytes, explicit_doc_type="passport")
                ela_results["passport"] = analyze_ela_tampering(p_bytes)
                ai_results["passport"] = run_ai_generated_detection(p_bytes)

        # 2. Process Visa
        if visa:
            v_bytes = await visa.read()
            if v_bytes:
                primary_doc_bytes = primary_doc_bytes or v_bytes
                doc_results["visa"] = process_document_ocr(v_bytes, explicit_doc_type="visa")
                ela_results["visa"] = analyze_ela_tampering(v_bytes)
                ai_results["visa"] = run_ai_generated_detection(v_bytes)

        # 3. Process Aadhaar
        if aadhaar:
            a_bytes = await aadhaar.read()
            if a_bytes:
                primary_doc_bytes = primary_doc_bytes or a_bytes
                doc_results["aadhaar"] = process_document_ocr(a_bytes, explicit_doc_type="aadhaar")
                ela_results["aadhaar"] = analyze_ela_tampering(a_bytes)
                ai_results["aadhaar"] = run_ai_generated_detection(a_bytes)

        if not doc_results:
            raise HTTPException(status_code=400, detail="At least one document (Passport, Visa, or Aadhaar) must be uploaded.")

        # 4. Process Facial Biometrics & Selfie GenAI Detection
        face_res = None
        if selfie and primary_doc_bytes:
            s_bytes = await selfie.read()
            if s_bytes:
                face_res = run_facial_biometric_verification(primary_doc_bytes, s_bytes)
                ai_results["selfie"] = run_ai_generated_detection(s_bytes)

        # 5. Build Cross-Document Relational Graph
        graph_res = build_and_evaluate_cross_document_graph(
            doc_results=doc_results,
            face_verification_result=face_res
        )

        # 6. Aggregate Composite Risk Score across all uploaded documents
        # Select representative primary doc result for risk evaluation
        primary_key = "passport" if "passport" in doc_results else ("visa" if "visa" in doc_results else "aadhaar")
        primary_ocr = doc_results[primary_key]
        primary_ela = ela_results.get(primary_key)
        
        max_ai_res = None
        for k, v in ai_results.items():
            if not max_ai_res or v.get("ai_generated_probability", 0.0) > max_ai_res.get("ai_generated_probability", 0.0):
                max_ai_res = v

        risk_res = evaluate_composite_risk(
            ocr_result=primary_ocr,
            ela_result=primary_ela,
            ai_vision_result=max_ai_res or ai_results.get(primary_key),
            face_verification_result=face_res,
            cross_doc_graph_result=graph_res
        )

        return {
            "status": "SUCCESS",
            "document_results": doc_results,
            "ela_forensics_results": ela_results,
            "genai_detection_results": ai_results,
            "facial_biometrics": face_res,
            "relational_graph": graph_res,
            "risk_assessment": risk_res
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch Document Screening Failed: {str(e)}"
        )


# =============================================================================
# Governance, Human-in-the-Loop & Officer Decision Endpoints
# =============================================================================

@app.get("/api/v1/override-reasons", tags=["Governance & Accountability"])
def get_override_reasons_endpoint():
    """Returns standardized regulatory taxonomy of override reason codes."""
    return get_all_override_reasons()


@app.post("/api/v1/submit-officer-decision", response_model=OfficerDecisionResponse, tags=["Governance & Accountability"])
def submit_officer_decision_endpoint(payload: OfficerDecisionRequest):
    """
    Records a human officer's final decision. Validates mandatory reason code on overrides,
    enforces dual-key supervisor authorization for high-risk DETAIN overrides,
    and appends an immutable cryptographic SHA-256 block to the hash-chained audit database.
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
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record officer decision: {str(e)}")


@app.get("/api/v1/audit-logs", response_model=List[AuditLogEntry], tags=["Governance & Accountability"])
def list_audit_logs_endpoint(
    limit: int = 50,
    offset: int = 0,
    is_override: Optional[bool] = None,
    officer_id: Optional[str] = None
):
    """Retrieves paginated audit trail records for supervisory oversight."""
    return get_audit_logs(limit=limit, offset=offset, is_override=is_override, officer_id=officer_id)


@app.get("/api/v1/audit-logs/stats", response_model=GovernanceMetricsResponse, tags=["Governance & Accountability"])
def get_audit_stats_endpoint():
    """Returns governance analytics: Total Inspections, Total Overrides, Override Rate %, AI-Human Agreement %."""
    return get_governance_metrics()


@app.get("/api/v1/audit-logs/verify-chain", response_model=ChainVerificationResponse, tags=["Governance & Accountability"])
def verify_audit_chain_endpoint():
    """Cryptographically verifies the full audit log hash chain from Genesis Block #0."""
    res = verify_audit_chain()
    return ChainVerificationResponse(**res)


@app.get("/api/v1/compliance/retention-policy", response_model=RetentionPolicyResponse, tags=["DPDP Act 2023 Compliance"])
def get_retention_policy_endpoint():
    """Returns statutory data retention policy under DPDP Act 2023."""
    return get_retention_policy_config()


@app.post("/api/v1/compliance/purge-expired", response_model=PurgeExecutionResponse, tags=["DPDP Act 2023 Compliance"])
def purge_expired_records_endpoint(retention_hours: int = 24, force_all: bool = False):
    """Executes automated DPDP data minimization auto-purge on clean records."""
    res = purge_expired_clean_records(retention_hours=retention_hours, force_purge_all_clean=force_all)
    return PurgeExecutionResponse(**res)


@app.get("/api/v1/compliance/dpdp-status", response_model=DPDPComplianceStatusResponse, tags=["DPDP Act 2023 Compliance"])
def get_dpdp_status_endpoint():
    """Returns live DPDP Act compliance summary and minimization percentage."""
    return get_dpdp_compliance_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
