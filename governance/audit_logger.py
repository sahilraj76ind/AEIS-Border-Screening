"""
Human-in-the-Loop (HITL) Officer Override & Accountability Subsystem
====================================================================
Tracks officer decisions, enforces structured reason codes on manual overrides,
maintains an append-only cryptographic audit trail, and aggregates governance analytics.
"""

import os
import json
import uuid
import sqlite3
import hashlib
import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class OverrideReason(str, Enum):
    # Override to APPROVE (Clearing an AI alert)
    PHYSICAL_SECURITY_FEATURES_VERIFIED = "PHYSICAL_SECURITY_FEATURES_VERIFIED"
    DIPLOMATIC_CONSULAR_IMMUNITY = "DIPLOMATIC_CONSULAR_IMMUNITY"
    HUMANITARIAN_EMERGENCY_ENTRY = "HUMANITARIAN_EMERGENCY_ENTRY"
    OPTICAL_GLARE_FALSE_POSITIVE = "OPTICAL_GLARE_FALSE_POSITIVE"
    VALID_PHYSICAL_VISA_ATTACHED = "VALID_PHYSICAL_VISA_ATTACHED"
    SUPERVISOR_DISCRETIONARY_APPROVAL = "SUPERVISOR_DISCRETIONARY_APPROVAL"

    # Override to REJECT / DETAIN (Overriding an AI Cleared pass)
    BEHAVIORAL_ANOMALY_SUSPICION = "BEHAVIORAL_ANOMALY_SUSPICION"
    CANINE_K9_DETECTION_ALERT = "CANINE_K9_DETECTION_ALERT"
    IMPOSTER_BIOMETRIC_MISMATCH = "IMPOSTER_BIOMETRIC_MISMATCH"
    INTELLIGENCE_BULLETIN_UNINDEXED = "INTELLIGENCE_BULLETIN_UNINDEXED"
    PHYSICAL_DOCUMENT_SUBSTRATE_TAMPERING = "PHYSICAL_DOCUMENT_SUBSTRATE_TAMPERING"
    OTHER_OFFICER_DISCRETION = "OTHER_OFFICER_DISCRETION"


# Path to SQLite Audit Database
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "audit_log.db")


def init_audit_db():
    """Initializes the append-only SQLite table for officer accountability logs."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officer_audit_log (
                log_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                officer_id TEXT NOT NULL,
                supervisor_id TEXT,
                checkpoint_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                document_number_masked TEXT NOT NULL,
                ai_recommendation TEXT NOT NULL,
                final_decision TEXT NOT NULL,
                is_override INTEGER NOT NULL,
                override_reason_code TEXT,
                override_justification TEXT,
                audit_sha256 TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON officer_audit_log (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_override ON officer_audit_log (is_override)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_officer ON officer_audit_log (officer_id)")
        conn.commit()


def compute_ai_recommendation(validation_data: Dict[str, Any]) -> str:
    """
    Determines the system's baseline recommendation from validation outcomes:
    - 'DETAIN' (Blacklisted or broken checksum)
    - 'SECONDARY_INSPECTION' (Expired, VIZ-MRZ discrepancy, or flags)
    - 'CLEARED' (Valid mathematical checks & no flags)
    """
    blacklist = validation_data.get("blacklist_status", {})
    checksums = validation_data.get("checksum_validation", {})
    flags = validation_data.get("field_validation", {}).get("flags", [])
    cross_check = validation_data.get("viz_mrz_cross_check")
    
    if blacklist.get("is_blacklisted", False) or not checksums.get("overall_valid", True):
        return "DETAIN"
    elif flags or (cross_check and not cross_check.get("is_consistent", True)):
        return "SECONDARY_INSPECTION"
    return "CLEARED"


def is_decision_an_override(ai_recommendation: str, final_decision: str) -> bool:
    """
    Evaluates whether the human officer's decision contradicts the AI recommendation.
    """
    norm_ai = ai_recommendation.upper()
    norm_human = final_decision.upper()

    # If AI said CLEARED, but human refused or detained -> Override
    if norm_ai == "CLEARED" and norm_human in ("ENTRY_REFUSED", "DETAINED", "SECONDARY_INSPECTION"):
        return True

    # If AI said DETAIN, but human granted entry or sent to standard secondary -> Override
    if norm_ai == "DETAIN" and norm_human in ("ENTRY_GRANTED", "SECONDARY_INSPECTION"):
        return True

    # If AI said SECONDARY_INSPECTION, but human directly granted entry without secondary -> Override
    if norm_ai == "SECONDARY_INSPECTION" and norm_human == "ENTRY_GRANTED":
        return True

    return False


def record_officer_decision(
    validation_data: Dict[str, Any],
    officer_id: str,
    checkpoint_id: str,
    final_decision: str,
    override_reason_code: Optional[str] = None,
    override_justification: Optional[str] = None,
    supervisor_id: Optional[str] = None,
    incident_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enforces accountability rules and records an immutable log entry in the audit database.
    """
    init_audit_db()
    
    ai_recommendation = compute_ai_recommendation(validation_data)
    is_override = is_decision_an_override(ai_recommendation, final_decision)

    # 1. Enforce Mandatory Reason Code on Override
    if is_override:
        if not override_reason_code:
            raise ValueError(
                f"Officer override detected (AI: {ai_recommendation} -> Final: {final_decision}). "
                "A mandatory 'override_reason_code' is required."
            )
            
        # Verify reason code is in standard taxonomy
        valid_reasons = [r.value for r in OverrideReason]
        if override_reason_code not in valid_reasons:
            raise ValueError(
                f"Invalid override_reason_code '{override_reason_code}'. Must be one of: {valid_reasons}"
            )

        # 2. Critical Alert Override (Clearing a DETAIN alert) requires supervisor co-sign
        if ai_recommendation == "DETAIN" and final_decision == "ENTRY_GRANTED" and not supervisor_id:
            raise ValueError(
                "CRITICAL GOVERNANCE ALERT: Overriding a 'DETAIN' status to 'ENTRY_GRANTED' "
                "strictly requires a valid 'supervisor_id' co-signature."
            )

    # 2. Generate Audit Metadata
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    doc_fields = validation_data.get("extracted_fields", {})
    masked_doc_no = doc_fields.get("document_number") or "N/A"
    doc_type = validation_data.get("document_type", "unknown").upper()
    
    rand_suffix = uuid.uuid4().hex[:6].upper()
    if not incident_id:
        incident_id = f"INSP-{now_utc.strftime('%Y%m%d%H%M%S')}-{rand_suffix}"
        
    log_id = f"AUDIT-{now_utc.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"

    # 3. Compute Tamper-Evident SHA-256 Audit Seal
    audit_payload = {
        "log_id": log_id,
        "incident_id": incident_id,
        "timestamp": timestamp_str,
        "officer_id": officer_id,
        "supervisor_id": supervisor_id,
        "checkpoint_id": checkpoint_id,
        "document_type": doc_type,
        "document_number_masked": masked_doc_no,
        "ai_recommendation": ai_recommendation,
        "final_decision": final_decision,
        "is_override": is_override,
        "override_reason_code": override_reason_code,
        "override_justification": override_justification
    }
    audit_sha256 = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode("utf-8")).hexdigest()
    audit_payload["audit_sha256"] = audit_sha256

    # 4. Persist into SQLite DB
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO officer_audit_log (
                log_id, incident_id, timestamp, officer_id, supervisor_id,
                checkpoint_id, document_type, document_number_masked,
                ai_recommendation, final_decision, is_override,
                override_reason_code, override_justification, audit_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, incident_id, timestamp_str, officer_id, supervisor_id,
            checkpoint_id, doc_type, masked_doc_no,
            ai_recommendation, final_decision, 1 if is_override else 0,
            override_reason_code, override_justification, audit_sha256
        ))
        conn.commit()

    return audit_payload


def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    is_override: Optional[bool] = None,
    officer_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves paginated audit log entries with optional override/officer filtering."""
    init_audit_db()
    query = "SELECT log_id, incident_id, timestamp, officer_id, supervisor_id, checkpoint_id, document_type, document_number_masked, ai_recommendation, final_decision, is_override, override_reason_code, override_justification, audit_sha256 FROM officer_audit_log WHERE 1=1"
    params = []

    if is_override is not None:
        query += " AND is_override = ?"
        params.append(1 if is_override else 0)

    if officer_id:
        query += " AND officer_id = ?"
        params.append(officer_id)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "log_id": r["log_id"],
                "incident_id": r["incident_id"],
                "timestamp": r["timestamp"],
                "officer_id": r["officer_id"],
                "supervisor_id": r["supervisor_id"],
                "checkpoint_id": r["checkpoint_id"],
                "document_type": r["document_type"],
                "document_number_masked": r["document_number_masked"],
                "ai_recommendation": r["ai_recommendation"],
                "final_decision": r["final_decision"],
                "is_override": bool(r["is_override"]),
                "override_reason_code": r["override_reason_code"],
                "override_justification": r["override_justification"],
                "audit_sha256": r["audit_sha256"]
            }
            for r in rows
        ]


def get_governance_metrics() -> Dict[str, Any]:
    """
    Computes statistical governance and accountability metrics:
    - Total decisions logged
    - Total overrides count & override rate (%)
    - AI-Human agreement rate (%)
    - Breakdown by reason code
    """
    init_audit_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Total counts
        cursor.execute("SELECT COUNT(*), SUM(is_override) FROM officer_audit_log")
        total_decisions, total_overrides = cursor.fetchone()
        total_decisions = total_decisions or 0
        total_overrides = total_overrides or 0
        
        agreed_count = total_decisions - total_overrides
        override_rate = round((total_overrides / total_decisions * 100), 2) if total_decisions > 0 else 0.0
        agreement_rate = round((agreed_count / total_decisions * 100), 2) if total_decisions > 0 else 100.0

        # Breakdown by Reason Code
        cursor.execute("""
            SELECT override_reason_code, COUNT(*) as count 
            FROM officer_audit_log 
            WHERE is_override = 1 
            GROUP BY override_reason_code 
            ORDER BY count DESC
        """)
        reason_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_inspections_logged": total_decisions,
            "total_overrides": total_overrides,
            "total_agreed_decisions": agreed_count,
            "override_rate_percentage": override_rate,
            "ai_human_agreement_rate_percentage": agreement_rate,
            "top_override_reasons": reason_breakdown
        }


def get_all_override_reasons() -> List[Dict[str, str]]:
    """Returns the full list of standardized reason codes with category labels."""
    return [
        {
            "code": r.value,
            "category": "APPROVE_OVERRIDE" if r in (
                OverrideReason.PHYSICAL_SECURITY_FEATURES_VERIFIED,
                OverrideReason.DIPLOMATIC_CONSULAR_IMMUNITY,
                OverrideReason.HUMANITARIAN_EMERGENCY_ENTRY,
                OverrideReason.OPTICAL_GLARE_FALSE_POSITIVE,
                OverrideReason.VALID_PHYSICAL_VISA_ATTACHED,
                OverrideReason.SUPERVISOR_DISCRETIONARY_APPROVAL
            ) else "REJECT_OVERRIDE",
            "description": r.name.replace("_", " ").title()
        }
        for r in OverrideReason
    ]
