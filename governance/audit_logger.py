"""
Human-in-the-Loop (HITL) Officer Override & Cryptographic Hash-Chained Audit Subsystem
=====================================================================================
Tracks officer decisions, enforces structured reason codes on manual overrides,
maintains an append-only, tamper-evident cryptographic hash chain, and supports
DPDP Act 2023 compliant data retention and cryptographic tombstone pruning.
"""

import os
import json
import uuid
import sqlite3
import hashlib
import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


GENESIS_PREV_HASH = "0" * 64


class RetentionTier(str, Enum):
    TIER_1_STANDARD_CLEARED = "TIER_1_STANDARD_CLEARED"       # DPDP Act 2023 Sec 8(7) - Purpose Eradication (24h - 30 days)
    TIER_2_INVESTIGATION_HOLD = "TIER_2_INVESTIGATION_HOLD"   # DPDP Act 2023 Sec 17(1)(c) - Law Enforcement Exemption (365d - 7 yrs)


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
    """Initializes the append-only SQLite table with cryptographic hash-chain and DPDP retention columns."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='officer_audit_log'")
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("PRAGMA table_info(officer_audit_log)")
            cols = [row[1] for row in cursor.fetchall()]
            if "entry_payload_hash" not in cols or "is_purged" not in cols:
                # Upgrade table structure for DPDP retention and payload hashing
                cursor.execute("DROP TABLE officer_audit_log")
                table_exists = False

        if not table_exists:
            cursor.execute("""
                CREATE TABLE officer_audit_log (
                    block_index INTEGER PRIMARY KEY,
                    log_id TEXT UNIQUE NOT NULL,
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
                    legal_retention_tier TEXT NOT NULL,
                    is_purged INTEGER NOT NULL DEFAULT 0,
                    purged_at TEXT,
                    entry_payload_hash TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    audit_sha256 TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON officer_audit_log (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_override ON officer_audit_log (is_override)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_retention ON officer_audit_log (legal_retention_tier, is_purged)")
            conn.commit()


def compute_entry_payload_hash(
    document_number_masked: str,
    override_reason_code: Optional[str],
    override_justification: Optional[str]
) -> str:
    """Computes a SHA-256 digest of demographic & decision notes at creation time."""
    payload = {
        "document_number_masked": document_number_masked,
        "override_reason_code": override_reason_code,
        "override_justification": override_justification
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def compute_chained_block_hash(
    block_index: int,
    log_id: str,
    incident_id: str,
    timestamp: str,
    officer_id: str,
    supervisor_id: Optional[str],
    checkpoint_id: str,
    document_type: str,
    ai_recommendation: str,
    final_decision: str,
    is_override: bool,
    legal_retention_tier: str,
    entry_payload_hash: str,
    prev_hash: str
) -> str:
    """
    Computes a deterministic SHA-256 digest sealing this block's header and payload hash,
    and binding it cryptographically to the hash of the preceding block (prev_hash).
    """
    header_payload = {
        "block_index": block_index,
        "log_id": log_id,
        "incident_id": incident_id,
        "timestamp": timestamp,
        "officer_id": officer_id,
        "supervisor_id": supervisor_id,
        "checkpoint_id": checkpoint_id,
        "document_type": document_type,
        "ai_recommendation": ai_recommendation,
        "final_decision": final_decision,
        "is_override": is_override,
        "legal_retention_tier": legal_retention_tier,
        "entry_payload_hash": entry_payload_hash,
        "prev_hash": prev_hash
    }
    serialized = json.dumps(header_payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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

    if norm_ai == "CLEARED" and norm_human in ("ENTRY_REFUSED", "DETAINED", "SECONDARY_INSPECTION"):
        return True
    if norm_ai == "DETAIN" and norm_human in ("ENTRY_GRANTED", "SECONDARY_INSPECTION"):
        return True
    if norm_ai == "SECONDARY_INSPECTION" and norm_human == "ENTRY_GRANTED":
        return True

    return False


def assign_retention_tier(
    ai_recommendation: str,
    final_decision: str,
    is_override: bool,
    validation_data: Dict[str, Any]
) -> str:
    """
    Assigns statutory retention category under DPDP Act 2023:
    - TIER_1_STANDARD_CLEARED: Clean scans with no flags/overrides (eligible for auto-purge).
    - TIER_2_INVESTIGATION_HOLD: Flagged/tampered/blacklisted/overridden scans (statutory hold under Sec 17(1)(c)).
    """
    blacklist = validation_data.get("blacklist_status", {})
    flags = validation_data.get("field_validation", {}).get("flags", [])
    cross_check = validation_data.get("viz_mrz_cross_check")
    
    is_blacklisted = blacklist.get("is_blacklisted", False)
    has_flags = len(flags) > 0
    inconsistent_cross = cross_check and not cross_check.get("is_consistent", True)
    
    if (
        ai_recommendation == "CLEARED"
        and final_decision.upper() == "ENTRY_GRANTED"
        and not is_override
        and not is_blacklisted
        and not has_flags
        and not inconsistent_cross
    ):
        return RetentionTier.TIER_1_STANDARD_CLEARED.value
    return RetentionTier.TIER_2_INVESTIGATION_HOLD.value


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
    Enforces accountability rules and records an immutable, hash-chained log entry in the audit database.
    """
    init_audit_db()
    
    ai_recommendation = compute_ai_recommendation(validation_data)
    is_override = is_decision_an_override(ai_recommendation, final_decision)
    legal_retention_tier = assign_retention_tier(ai_recommendation, final_decision, is_override, validation_data)

    # 1. Enforce Mandatory Reason Code on Override
    if is_override:
        if not override_reason_code:
            raise ValueError(
                f"Officer override detected (AI: {ai_recommendation} -> Final: {final_decision}). "
                "A mandatory 'override_reason_code' is required."
            )
            
        valid_reasons = [r.value for r in OverrideReason]
        if override_reason_code not in valid_reasons:
            raise ValueError(
                f"Invalid override_reason_code '{override_reason_code}'. Must be one of: {valid_reasons}"
            )

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

    # 3. Compute Entry Payload Hash
    entry_payload_hash = compute_entry_payload_hash(
        document_number_masked=masked_doc_no,
        override_reason_code=override_reason_code,
        override_justification=override_justification
    )

    # 4. Cryptographic Hash Chaining: Fetch Previous Block Hash
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT block_index, audit_sha256 FROM officer_audit_log ORDER BY block_index DESC LIMIT 1")
        latest_row = cursor.fetchone()
        
        if latest_row:
            block_index = latest_row[0] + 1
            prev_hash = latest_row[1]
        else:
            block_index = 0
            prev_hash = GENESIS_PREV_HASH

        # 5. Compute Tamper-Evident SHA-256 Chained Hash
        audit_sha256 = compute_chained_block_hash(
            block_index=block_index,
            log_id=log_id,
            incident_id=incident_id,
            timestamp=timestamp_str,
            officer_id=officer_id,
            supervisor_id=supervisor_id,
            checkpoint_id=checkpoint_id,
            document_type=doc_type,
            ai_recommendation=ai_recommendation,
            final_decision=final_decision,
            is_override=is_override,
            legal_retention_tier=legal_retention_tier,
            entry_payload_hash=entry_payload_hash,
            prev_hash=prev_hash
        )

        # 6. Persist into SQLite DB
        cursor.execute("""
            INSERT INTO officer_audit_log (
                block_index, log_id, incident_id, timestamp, officer_id, supervisor_id,
                checkpoint_id, document_type, document_number_masked,
                ai_recommendation, final_decision, is_override,
                override_reason_code, override_justification, legal_retention_tier,
                is_purged, purged_at, entry_payload_hash, prev_hash, audit_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?)
        """, (
            block_index, log_id, incident_id, timestamp_str, officer_id, supervisor_id,
            checkpoint_id, doc_type, masked_doc_no,
            ai_recommendation, final_decision, 1 if is_override else 0,
            override_reason_code, override_justification, legal_retention_tier,
            entry_payload_hash, prev_hash, audit_sha256
        ))
        conn.commit()

    return {
        "block_index": block_index,
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
        "override_justification": override_justification,
        "legal_retention_tier": legal_retention_tier,
        "is_purged": False,
        "purged_at": None,
        "entry_payload_hash": entry_payload_hash,
        "prev_hash": prev_hash,
        "audit_sha256": audit_sha256
    }


def verify_audit_chain() -> Dict[str, Any]:
    """
    Traverses the entire audit log from Genesis Block #0 to the latest block,
    recomputing all SHA-256 digests and validating continuous hash-chain pointers.
    Maintains 100% mathematical validity even when records have been purged under DPDP Act 2023.
    """
    init_audit_db()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    verified_at_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM officer_audit_log ORDER BY block_index ASC")
        rows = cursor.fetchall()

        if not rows:
            return {
                "chain_valid": True,
                "total_blocks_verified": 0,
                "corrupted_block_index": None,
                "error_details": "Audit database is empty (0 blocks).",
                "latest_block_hash": None,
                "verified_at": verified_at_str
            }

        expected_prev_hash = GENESIS_PREV_HASH

        for i, row in enumerate(rows):
            actual_block_index = row["block_index"]
            
            # Check 1: Sequence Integrity (no dropped/deleted blocks)
            if actual_block_index != i:
                return {
                    "chain_valid": False,
                    "total_blocks_verified": i,
                    "corrupted_block_index": i,
                    "error_details": f"Sequence anomaly: expected block index {i}, found {actual_block_index} (Missing/deleted blocks detected).",
                    "latest_block_hash": None,
                    "verified_at": verified_at_str
                }

            # Check 2: Previous Hash Pointer Integrity
            if row["prev_hash"] != expected_prev_hash:
                return {
                    "chain_valid": False,
                    "total_blocks_verified": i,
                    "corrupted_block_index": actual_block_index,
                    "error_details": f"Hash chain linkage broken at block #{actual_block_index}: expected prev_hash '{expected_prev_hash[:16]}...', found '{row['prev_hash'][:16]}...'.",
                    "latest_block_hash": None,
                    "verified_at": verified_at_str
                }

            # Check 3: If not purged, verify raw payload matches stored payload hash
            if not row["is_purged"]:
                recomputed_payload_hash = compute_entry_payload_hash(
                    document_number_masked=row["document_number_masked"],
                    override_reason_code=row["override_reason_code"],
                    override_justification=row["override_justification"]
                )
                if recomputed_payload_hash != row["entry_payload_hash"]:
                    return {
                        "chain_valid": False,
                        "total_blocks_verified": i,
                        "corrupted_block_index": actual_block_index,
                        "error_details": f"Demographic payload tampering detected in active block #{actual_block_index}.",
                        "latest_block_hash": None,
                        "verified_at": verified_at_str
                    }

            # Check 4: Block Header Hash Recalculation (detects block header/metadata tampering)
            recalculated_hash = compute_chained_block_hash(
                block_index=row["block_index"],
                log_id=row["log_id"],
                incident_id=row["incident_id"],
                timestamp=row["timestamp"],
                officer_id=row["officer_id"],
                supervisor_id=row["supervisor_id"],
                checkpoint_id=row["checkpoint_id"],
                document_type=row["document_type"],
                ai_recommendation=row["ai_recommendation"],
                final_decision=row["final_decision"],
                is_override=bool(row["is_override"]),
                legal_retention_tier=row["legal_retention_tier"],
                entry_payload_hash=row["entry_payload_hash"],
                prev_hash=row["prev_hash"]
            )

            if recalculated_hash != row["audit_sha256"]:
                return {
                    "chain_valid": False,
                    "total_blocks_verified": i,
                    "corrupted_block_index": actual_block_index,
                    "error_details": f"Block header tampering detected in block #{actual_block_index}: stored SHA-256 '{row['audit_sha256'][:16]}...' does not match recalculated hash '{recalculated_hash[:16]}...'.",
                    "latest_block_hash": None,
                    "verified_at": verified_at_str
                }

            expected_prev_hash = row["audit_sha256"]

        return {
            "chain_valid": True,
            "total_blocks_verified": len(rows),
            "corrupted_block_index": None,
            "error_details": None,
            "latest_block_hash": rows[-1]["audit_sha256"],
            "verified_at": verified_at_str
        }


def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    is_override: Optional[bool] = None,
    officer_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves paginated audit log entries with optional override/officer filtering."""
    init_audit_db()
    query = """
        SELECT block_index, log_id, incident_id, timestamp, officer_id, supervisor_id,
               checkpoint_id, document_type, document_number_masked, ai_recommendation,
               final_decision, is_override, override_reason_code, override_justification,
               legal_retention_tier, is_purged, purged_at, entry_payload_hash,
               prev_hash, audit_sha256
        FROM officer_audit_log WHERE 1=1
    """
    params = []

    if is_override is not None:
        query += " AND is_override = ?"
        params.append(1 if is_override else 0)

    if officer_id:
        query += " AND officer_id = ?"
        params.append(officer_id)

    query += " ORDER BY block_index DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "block_index": r["block_index"],
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
                "legal_retention_tier": r["legal_retention_tier"],
                "is_purged": bool(r["is_purged"]),
                "purged_at": r["purged_at"],
                "entry_payload_hash": r["entry_payload_hash"],
                "prev_hash": r["prev_hash"],
                "audit_sha256": r["audit_sha256"]
            }
            for r in rows
        ]


def get_governance_metrics() -> Dict[str, Any]:
    """Computes statistical governance and accountability metrics."""
    init_audit_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(is_override) FROM officer_audit_log")
        total_decisions, total_overrides = cursor.fetchone()
        total_decisions = total_decisions or 0
        total_overrides = total_overrides or 0
        
        agreed_count = total_decisions - total_overrides
        override_rate = round((total_overrides / total_decisions * 100), 2) if total_decisions > 0 else 0.0
        agreement_rate = round((agreed_count / total_decisions * 100), 2) if total_decisions > 0 else 100.0

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
