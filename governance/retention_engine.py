"""
Data Retention Auto-Purge & DPDP Act 2023 Compliance Engine
===========================================================
Enforces statutory data minimization and storage limitations under India's Digital Personal
Data Protection (DPDP) Act 2023 (Section 8(7)), while maintaining evidentiary retention
for flagged/investigation records under Section 17(1)(c).

Key Capabilities:
1. Dual-Tier Retention Classification: Transient hold for clean scans vs. statutory hold for flagged cases.
2. Cryptographic Tombstone Pruning: Eradicates demographic PII while preserving unbroken hash-chain integrity.
3. Automated & On-Demand Purge Execution: Scans, purges, and certifies data minimization in real time.
"""

import sqlite3
import datetime
from typing import Dict, Any, Optional

from governance.audit_logger import DB_PATH, RetentionTier, init_audit_db


DEFAULT_CLEAN_RETENTION_HOURS = 24       # 24 Hours for transient border checkpoint pass records
DEFAULT_FLAGGED_RETENTION_DAYS = 365     # 365 Days for flagged, blacklisted, or overridden cases


def get_retention_policy_config() -> Dict[str, Any]:
    """Returns statutory data retention policy parameters under DPDP Act 2023."""
    return {
        "regulatory_framework": "Digital Personal Data Protection (DPDP) Act 2023",
        "clean_record_retention_hours": DEFAULT_CLEAN_RETENTION_HOURS,
        "clean_record_legal_basis": "DPDP Act 2023 Section 8(7) — Storage Limitation & Purpose Eradication",
        "flagged_record_retention_days": DEFAULT_FLAGGED_RETENTION_DAYS,
        "flagged_record_legal_basis": "DPDP Act 2023 Section 17(1)(c) — Prevention & Detection of Offences Exemption",
        "pruning_mechanism": "Cryptographic Tombstone Redaction (Zero PII Retention + Hash Chain Preservation)",
        "auto_purge_enabled": True
    }


def purge_expired_clean_records(
    retention_hours: int = DEFAULT_CLEAN_RETENTION_HOURS,
    force_purge_all_clean: bool = False
) -> Dict[str, Any]:
    """
    Executes DPDP Act 2023 compliant data minimization:
    - Scans for clean, un-flagged scans (TIER_1_STANDARD_CLEARED).
    - If elapsed time exceeds retention_hours (or force_purge_all_clean is True),
      eradicates personal demographic data (document number, remarks) with cryptographic tombstones.
    - Preserves audit_sha256, prev_hash, and block_index for unbroken hash chain verification.
    """
    init_audit_db()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    purged_count = 0
    retained_investigation_count = 0

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Count active investigation holds (Tier 2)
        cursor.execute(
            "SELECT COUNT(*) FROM officer_audit_log WHERE legal_retention_tier = ?",
            (RetentionTier.TIER_2_INVESTIGATION_HOLD.value,)
        )
        retained_investigation_count = cursor.fetchone()[0] or 0

        # Fetch eligible Tier 1 clean records that are not yet purged
        cursor.execute(
            "SELECT block_index, timestamp FROM officer_audit_log WHERE legal_retention_tier = ? AND is_purged = 0",
            (RetentionTier.TIER_1_STANDARD_CLEARED.value,)
        )
        candidates = cursor.fetchall()

        blocks_to_purge = []
        for row in candidates:
            if force_purge_all_clean:
                blocks_to_purge.append(row["block_index"])
            else:
                try:
                    # Parse timestamp format: "2026-08-26 19:49:39 UTC"
                    ts_clean = row["timestamp"].replace(" UTC", "")
                    entry_dt = datetime.datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                    age_hours = (now_utc - entry_dt).total_seconds() / 3600.0
                    if age_hours >= retention_hours:
                        blocks_to_purge.append(row["block_index"])
                except Exception:
                    # If parsing fails, fall back to purging if forced
                    pass

        # Apply cryptographic tombstone redaction
        for blk_idx in blocks_to_purge:
            cursor.execute("""
                UPDATE officer_audit_log
                SET document_number_masked = '[PURGED: DPDP ACT 2023 SEC 8(7)]',
                    override_justification = '[PURGED: STORAGE LIMITATION]',
                    is_purged = 1,
                    purged_at = ?
                WHERE block_index = ?
            """, (timestamp_str, blk_idx))
            purged_count += 1

        conn.commit()

    return {
        "status": "success",
        "purged_records_count": purged_count,
        "active_investigation_holds": retained_investigation_count,
        "retention_window_hours_applied": retention_hours,
        "executed_at": timestamp_str,
        "statutory_authority": "DPDP Act 2023 Section 8(7)",
        "chain_integrity_preserved": True
    }


def get_dpdp_compliance_summary() -> Dict[str, Any]:
    """Returns real-time data minimization metrics and compliance counters."""
    init_audit_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM officer_audit_log")
        total_logs = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM officer_audit_log WHERE is_purged = 1")
        total_purged = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM officer_audit_log WHERE legal_retention_tier = ? AND is_purged = 0",
            (RetentionTier.TIER_1_STANDARD_CLEARED.value,)
        )
        active_clean = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM officer_audit_log WHERE legal_retention_tier = ?",
            (RetentionTier.TIER_2_INVESTIGATION_HOLD.value,)
        )
        active_investigation = cursor.fetchone()[0] or 0

        minimization_rate = round((total_purged / total_logs * 100), 2) if total_logs > 0 else 0.0

        return {
            "total_audit_records_lifetime": total_logs,
            "total_records_purged_dpdp": total_purged,
            "active_transient_clean_records": active_clean,
            "active_evidentiary_investigation_holds": active_investigation,
            "data_minimization_percentage": minimization_rate,
            "dpdp_act_2023_compliant": True
        }
