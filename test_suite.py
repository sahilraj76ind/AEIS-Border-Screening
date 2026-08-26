"""
Comprehensive Unit & Integration Test Suite
===========================================
Executes rigorous verification of ICAO 9303 check digits, Verhoeff D_5 algorithm,
TD3 Passports, TD2 Visas, Aadhaar QR payloads, Field Validation, Watchlist screening,
and VIZ vs. MRZ Cross-Consistency Forensics.
"""

import unittest
import json
from datetime import date

from core.mrz_utils import compute_mrz_check_digit, verify_mrz_check_digit, char_to_mrz_value
from core.td3_parser import parse_td3_mrz
from core.td2_parser import parse_td2_mrz
from core.aadhaar_parser import validate_verhoeff, generate_verhoeff_check_digit, parse_aadhaar_data, mask_aadhaar_uid
from core.field_validator import validate_document_fields, parse_mrz_date
from core.blacklist_check import check_document_blacklist
from core.cross_validator import extract_viz_fields, cross_validate_viz_and_mrz, normalize_viz_date
import sqlite3
from reports.forensic_generator import generate_forensic_pdf, compute_report_hash
from governance.audit_logger import (
    record_officer_decision,
    verify_audit_chain,
    get_audit_logs,
    get_governance_metrics,
    compute_ai_recommendation,
    is_decision_an_override,
    assign_retention_tier,
    RetentionTier,
    GENESIS_PREV_HASH,
    DB_PATH
)
from governance.retention_engine import (
    purge_expired_clean_records,
    get_retention_policy_config,
    get_dpdp_compliance_summary,
    DEFAULT_CLEAN_RETENTION_HOURS
)
from main import assemble_response


class TestICAO9303Checksum(unittest.TestCase):
    """Verifies pure-Python ICAO Doc 9303 modulo-10 algorithm."""
    
    def test_char_mapping(self):
        self.assertEqual(char_to_mrz_value('<'), 0)
        self.assertEqual(char_to_mrz_value('0'), 0)
        self.assertEqual(char_to_mrz_value('9'), 9)
        self.assertEqual(char_to_mrz_value('A'), 10)
        self.assertEqual(char_to_mrz_value('Z'), 35)
        with self.assertRaises(ValueError):
            char_to_mrz_value('#')

    def test_official_icao_samples(self):
        # ICAO Doc 9303 Part 3 sample: L898902C3 -> 6
        self.assertEqual(compute_mrz_check_digit("L898902C3"), "6")
        self.assertTrue(verify_mrz_check_digit("L898902C3", "6"))
        
        # DOB 740812 -> 2
        self.assertEqual(compute_mrz_check_digit("740812"), "2")
        self.assertTrue(verify_mrz_check_digit("740812", "2"))
        
        # Expiry 120415 -> 9
        self.assertEqual(compute_mrz_check_digit("120415"), "9")
        self.assertTrue(verify_mrz_check_digit("120415", "9"))

    def test_tampering_detection(self):
        # Substitution error
        self.assertFalse(verify_mrz_check_digit("L898902C4", "6"))
        # Adjacent transposition: 740812 -> 470812
        self.assertFalse(verify_mrz_check_digit("470812", "2"))


class TestVerhoeffAlgorithm(unittest.TestCase):
    """Verifies Dihedral Group D_5 Verhoeff checksum algorithm for Aadhaar."""
    
    def test_verhoeff_generation_and_validation(self):
        base = "236"
        cd = generate_verhoeff_check_digit(base)
        self.assertEqual(cd, "3")
        self.assertTrue(validate_verhoeff("2363"))
        
    def test_aadhaar_12_digit_uid(self):
        # Generate 12-digit valid Aadhaar UID
        base_11 = "54321098765"
        cd = generate_verhoeff_check_digit(base_11)
        valid_uid = base_11 + cd
        self.assertTrue(validate_verhoeff(valid_uid))
        
        # Single digit substitution error
        tampered_uid = valid_uid[:-1] + ("1" if valid_uid[-1] != "1" else "2")
        self.assertFalse(validate_verhoeff(tampered_uid))
        
        # Adjacent transposition error
        transposed_uid = valid_uid[:3] + valid_uid[4] + valid_uid[3] + valid_uid[5:]
        self.assertFalse(validate_verhoeff(transposed_uid))


class TestTD3PassportParser(unittest.TestCase):
    """Verifies TD3 Passport parsing and check digit calculations."""
    
    def setUp(self):
        self.valid_td3 = (
            "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
            "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
        )
        
    def test_valid_passport(self):
        res = parse_td3_mrz(self.valid_td3)
        self.assertEqual(res["document_type"], "passport")
        self.assertEqual(res["extracted_fields"]["surname"], "ERIKSSON")
        self.assertEqual(res["extracted_fields"]["given_names"], "ANNA MARIA")
        self.assertEqual(res["extracted_fields"]["document_number"], "L898902C3")
        self.assertEqual(res["extracted_fields"]["nationality"], "UTO")
        self.assertTrue(res["checksum_validation"]["document_number_check"])
        self.assertTrue(res["checksum_validation"]["dob_check"])
        self.assertTrue(res["checksum_validation"]["expiry_check"])
        self.assertTrue(res["checksum_validation"]["composite_check"])
        self.assertTrue(res["checksum_validation"]["overall_valid"])

    def test_tampered_passport(self):
        # Alter document number: L898902C3 -> L898902C9 (check digit still 6)
        tampered = (
            "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
            "L898902C96UTO7408122F1204159ZE184226B<<<<<10"
        )
        res = parse_td3_mrz(tampered)
        self.assertFalse(res["checksum_validation"]["document_number_check"])
        self.assertFalse(res["checksum_validation"]["composite_check"])
        self.assertFalse(res["checksum_validation"]["overall_valid"])


class TestTD2VisaParser(unittest.TestCase):
    """Verifies TD2 Visa parsing and check digits."""
    
    def setUp(self):
        self.valid_td2 = (
            "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<\n"
            "L8988901C4XXX4009078F9612109<<<<<<<6"
        )
        
    def test_valid_visa(self):
        res = parse_td2_mrz(self.valid_td2)
        self.assertEqual(res["document_type"], "visa")
        self.assertEqual(res["extracted_fields"]["document_number"], "L8988901C")
        self.assertTrue(res["checksum_validation"]["overall_valid"])


class TestFieldValidatorAndBlacklist(unittest.TestCase):
    """Verifies date pivot logic, semantic flags, and watchlist hits."""
    
    def test_expiry_and_blacklist(self):
        expired_mrz = (
            "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
            "L898902C36UTO7408122F1004159ZE184226B<<<<<18"
        )
        parsed = parse_td3_mrz(expired_mrz)
        ref_today = date(2026, 8, 25)
        flags = validate_document_fields(parsed, reference_date=ref_today)
        self.assertIn("EXPIRED", flags)
        
        bl_res = check_document_blacklist("L898902C3")
        self.assertTrue(bl_res["is_blacklisted"])
        self.assertEqual(bl_res["matched_list"], "LOST_STOLEN_TRAVEL_DOCS")


class TestVIZMRZCrossValidator(unittest.TestCase):
    """Verifies Visual Inspection Zone (VIZ) vs MRZ cross-consistency engine."""

    def test_multilingual_date_normalization(self):
        self.assertEqual(normalize_viz_date("01 JANI JAN 98"), "1998-01-01")
        self.assertEqual(normalize_viz_date("29 JUINI JUN 30"), "2030-06-29")
        self.assertEqual(normalize_viz_date("15/08/1990"), "1990-08-15")
        self.assertEqual(normalize_viz_date("12 AUG 1974"), "1974-08-12")

    def test_authentic_cross_validation(self):
        viz_ocr = (
            "PASSEPORT\n"
            "REPUBLIQUE DU MALI\n"
            "Passport No: PP0000000\n"
            "Nom / Surname: DRAMANE\n"
            "Prénoms / Given names: MAMMADOU\n"
            "Date de naissance / Date of birth: 01 JANI JAN 98\n"
            "Date d'expiration / Date of expiry: 29 JUINI JUN 30\n"
            "Sexe / Sex: M\n"
        )
        viz_data = extract_viz_fields(viz_ocr)
        mrz_data = {
            "extracted_fields": {
                "name": "MAMMADOU DRAMANE",
                "document_number": "PP0000000",
                "date_of_birth": "1998-01-01",
                "date_of_expiry": "2030-06-29",
                "sex": "M"
            }
        }
        res = cross_validate_viz_and_mrz(viz_data, mrz_data)
        self.assertTrue(res["is_consistent"])
        self.assertEqual(len(res["mismatch_flags"]), 0)
        self.assertGreaterEqual(res["overall_match_score"], 0.95)

    def test_photoshop_tampered_name(self):
        # Attacker photoshops name to 'ALICE SMITH' in visual zone
        viz_data = {
            "name": "ALICE SMITH",
            "document_number": "PP0000000",
            "date_of_birth": "1998-01-01",
            "date_of_expiry": "2030-06-29",
            "sex": "M"
        }
        mrz_data = {
            "extracted_fields": {
                "name": "MAMMADOU DRAMANE",
                "document_number": "PP0000000",
                "date_of_birth": "1998-01-01",
                "date_of_expiry": "2030-06-29",
                "sex": "M"
            }
        }
        res = cross_validate_viz_and_mrz(viz_data, mrz_data)
        self.assertFalse(res["is_consistent"])
        self.assertIn("VIZ_MRZ_NAME_MISMATCH", res["mismatch_flags"])

    def test_tampered_dob_and_doc_number(self):
        viz_data = {
            "name": "MAMMADOU DRAMANE",
            "document_number": "K1234567",
            "date_of_birth": "1980-05-20",
            "date_of_expiry": "2030-06-29",
            "sex": "M"
        }
        mrz_data = {
            "extracted_fields": {
                "name": "MAMMADOU DRAMANE",
                "document_number": "PP0000000",
                "date_of_birth": "1998-01-01",
                "date_of_expiry": "2030-06-29",
                "sex": "M"
            }
        }
        res = cross_validate_viz_and_mrz(viz_data, mrz_data)
        self.assertFalse(res["is_consistent"])
        self.assertIn("VIZ_MRZ_DOC_NUM_MISMATCH", res["mismatch_flags"])
        self.assertIn("VIZ_MRZ_DOB_MISMATCH", res["mismatch_flags"])


class TestAadhaarRedactionAndCompliance(unittest.TestCase):
    """Verifies UIDAI-mandated masking, physical redaction, and privacy compliance."""
    
    def test_aadhaar_masking_transformer(self):
        self.assertEqual(mask_aadhaar_uid("246813579019", formatted=True), "XXXX XXXX 9019")
        self.assertEqual(mask_aadhaar_uid("246813579019", formatted=False), "XXXXXXXX9019")
        self.assertEqual(mask_aadhaar_uid("999988887777"), "XXXX XXXX 7777")
        
    def test_in_memory_redaction_and_base64_generation(self):
        import numpy as np
        from vision.redaction_engine import redact_aadhaar_image
        
        # Create synthetic canvas in RAM
        canvas = np.ones((400, 600, 3), dtype=np.uint8) * 255
        redacted_canvas, b64_uri = redact_aadhaar_image(canvas, raw_uid="246813579019")
        
        self.assertIsInstance(redacted_canvas, np.ndarray)
        self.assertTrue(b64_uri.startswith("data:image/jpeg;base64,"))
        self.assertGreater(len(b64_uri), 500)
        
    def test_aadhaar_api_response_privacy_compliance(self):
        # Sample Aadhaar XML with valid Verhoeff
        uid_base = "24681357901"
        cd = generate_verhoeff_check_digit(uid_base)
        valid_uid = uid_base + cd
        
        xml_payload = f'<PrintLetterBarcodeData uid="{valid_uid}" name="Vikas Sharma" dob="14/11/1992" gender="M" />'
        parsed = parse_aadhaar_data(xml_payload)
        
        # Assemble response
        resp = assemble_response(parsed, confidence=0.98, redacted_image_b64="data:image/jpeg;base64,mock")
        
        # Verify strict masking and privacy compliance
        self.assertEqual(resp.extracted_fields.document_number, f"XXXX XXXX {valid_uid[-4:]}")
        self.assertIsNotNone(resp.privacy_compliance)
        self.assertTrue(resp.privacy_compliance.is_redacted)
        self.assertTrue(resp.privacy_compliance.uidai_mandate_compliant)
        self.assertFalse(resp.privacy_compliance.raw_pii_persisted_to_disk)
        self.assertEqual(resp.privacy_compliance.masked_document_number, f"XXXX XXXX {valid_uid[-4:]}")
        self.assertEqual(resp.redacted_image_base64, "data:image/jpeg;base64,mock")


class TestForensicReportGeneration(unittest.TestCase):
    """Verifies evidentiary forensic PDF report generation and cryptographic audit hashing."""
    
    def setUp(self):
        self.passport_val_data = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "ANNA MARIA ERIKSSON",
                "surname": "ERIKSSON",
                "given_names": "ANNA MARIA",
                "document_number": "L898902C3",
                "nationality": "UTO",
                "issuing_country": "UTO",
                "date_of_birth": "1974-08-12",
                "sex": "F",
                "date_of_expiry": "2028-04-15",
                "optional_data": "ZE184226B"
            },
            "checksum_validation": {
                "document_number_check": True,
                "dob_check": True,
                "expiry_check": True,
                "optional_data_check": True,
                "composite_check": True,
                "verhoeff_check": None,
                "overall_valid": True
            },
            "field_validation": {
                "flags": []
            },
            "blacklist_status": {
                "is_blacklisted": False,
                "matched_list": None,
                "reason": None,
                "severity": None
            },
            "viz_mrz_cross_check": {
                "is_consistent": True,
                "overall_match_score": 1.0,
                "field_matches": {
                    "document_number": {"viz_value": "L898902C3", "mrz_value": "L898902C3", "matched": True, "similarity": 1.0},
                    "name": {"viz_value": "ANNA MARIA ERIKSSON", "mrz_value": "ANNA MARIA ERIKSSON", "matched": True, "similarity": 1.0}
                },
                "mismatch_flags": []
            },
            "ocr_confidence": 0.96
        }

    def test_pdf_binary_structure(self):
        pdf_bytes = generate_forensic_pdf(
            validation_data=self.passport_val_data,
            officer_id="TEST-OFFICER-01",
            checkpoint_id="GATE-1"
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1."))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_sha256_cryptographic_audit_digest(self):
        hash1 = compute_report_hash("INSP-01", "2026-08-27", "OFF-1", "GATE-1", self.passport_val_data)
        self.assertEqual(len(hash1), 64) # SHA-256 is 64 hex characters
        
        # Tamper validation data and verify hash completely changes (collision resistance)
        tampered_data = json.loads(json.dumps(self.passport_val_data))
        tampered_data["extracted_fields"]["document_number"] = "FORGED999"
        hash2 = compute_report_hash("INSP-01", "2026-08-27", "OFF-1", "GATE-1", tampered_data)
        
        self.assertNotEqual(hash1, hash2)

    def test_aadhaar_report_generation(self):
        aadhaar_val_data = {
            "document_type": "aadhaar",
            "format": "AADHAAR_CARD",
            "extracted_fields": {
                "name": "Rajesh Kumar",
                "document_number": "XXXX XXXX 9019",
                "nationality": "IND",
                "date_of_birth": "1990-08-15",
                "sex": "M"
            },
            "checksum_validation": {
                "verhoeff_check": True,
                "overall_valid": True
            },
            "field_validation": {"flags": []},
            "blacklist_status": {"is_blacklisted": False},
            "privacy_compliance": {
                "is_redacted": True,
                "uidai_mandate_compliant": True,
                "raw_pii_persisted_to_disk": False,
                "masked_document_number": "XXXX XXXX 9019"
            },
            "ocr_confidence": 0.95
        }
        pdf_bytes = generate_forensic_pdf(aadhaar_val_data)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1."))


class TestOfficerAccountabilityGovernance(unittest.TestCase):
    """Verifies officer decision logging, mandatory override reason codes, and governance metrics."""

    def setUp(self):
        self.clean_val_data = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "JOHN DOE",
                "document_number": "J12345678"
            },
            "checksum_validation": {"overall_valid": True},
            "field_validation": {"flags": []},
            "blacklist_status": {"is_blacklisted": False}
        }
        self.tampered_val_data = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "SUSPECT PASSENGER",
                "document_number": "S99999999"
            },
            "checksum_validation": {"overall_valid": False},
            "field_validation": {"flags": ["CHECKSUM_FAILED"]},
            "blacklist_status": {"is_blacklisted": True}
        }

    def test_ai_recommendation_classification(self):
        self.assertEqual(compute_ai_recommendation(self.clean_val_data), "CLEARED")
        self.assertEqual(compute_ai_recommendation(self.tampered_val_data), "DETAIN")

    def test_override_detection_logic(self):
        self.assertFalse(is_decision_an_override("CLEARED", "ENTRY_GRANTED"))
        self.assertTrue(is_decision_an_override("CLEARED", "DETAINED"))
        self.assertTrue(is_decision_an_override("DETAIN", "ENTRY_GRANTED"))

    def test_standard_agreement_logging(self):
        res = record_officer_decision(
            validation_data=self.clean_val_data,
            officer_id="INSP-01",
            checkpoint_id="GATE-01",
            final_decision="ENTRY_GRANTED"
        )
        self.assertFalse(res["is_override"])
        self.assertIsNone(res["override_reason_code"])
        self.assertEqual(len(res["audit_sha256"]), 64)

    def test_override_without_reason_code_fails(self):
        with self.assertRaises(ValueError) as ctx:
            record_officer_decision(
                validation_data=self.tampered_val_data,
                officer_id="INSP-01",
                checkpoint_id="GATE-01",
                final_decision="ENTRY_GRANTED" # Overriding DETAIN to ENTRY_GRANTED without reason
            )
        self.assertIn("override_reason_code", str(ctx.exception))

    def test_critical_detain_override_requires_supervisor(self):
        with self.assertRaises(ValueError) as ctx:
            record_officer_decision(
                validation_data=self.tampered_val_data,
                officer_id="INSP-01",
                checkpoint_id="GATE-01",
                final_decision="ENTRY_GRANTED",
                override_reason_code="DIPLOMATIC_CONSULAR_IMMUNITY"
                # supervisor_id is missing!
            )
        self.assertIn("supervisor_id", str(ctx.exception))

    def test_valid_override_with_supervisor_and_optional_notes(self):
        res = record_officer_decision(
            validation_data=self.tampered_val_data,
            officer_id="INSP-01",
            checkpoint_id="GATE-01",
            final_decision="ENTRY_GRANTED",
            override_reason_code="DIPLOMATIC_CONSULAR_IMMUNITY",
            override_justification="Diplomatic waiver from Ministry of External Affairs.",
            supervisor_id="SUPV-RAO-901"
        )
        self.assertTrue(res["is_override"])
        self.assertEqual(res["supervisor_id"], "SUPV-RAO-901")
        self.assertEqual(res["override_reason_code"], "DIPLOMATIC_CONSULAR_IMMUNITY")

    def test_governance_metrics_computation(self):
        metrics = get_governance_metrics()
        self.assertIn("total_inspections_logged", metrics)
        self.assertIn("override_rate_percentage", metrics)
        self.assertIn("ai_human_agreement_rate_percentage", metrics)
        self.assertIn("top_override_reasons", metrics)


class TestCryptographicHashChain(unittest.TestCase):
    """Verifies sequential Merkle-style hash chaining, continuous pointer linkage, and tamper detection."""

    def setUp(self):
        self.doc_val = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "TEST PASSENGER",
                "document_number": "T11223344"
            },
            "checksum_validation": {"overall_valid": True},
            "field_validation": {"flags": []},
            "blacklist_status": {"is_blacklisted": False}
        }

    def test_hash_chain_continuity_and_verification(self):
        # 1. Log two decisions
        log1 = record_officer_decision(
            validation_data=self.doc_val,
            officer_id="INSP-CHAIN-01",
            checkpoint_id="LANE-A",
            final_decision="ENTRY_GRANTED"
        )
        log2 = record_officer_decision(
            validation_data=self.doc_val,
            officer_id="INSP-CHAIN-02",
            checkpoint_id="LANE-B",
            final_decision="ENTRY_GRANTED"
        )

        # Assert log2 prev_hash points to log1 audit_sha256
        self.assertEqual(log2["prev_hash"], log1["audit_sha256"])
        self.assertEqual(log2["block_index"], log1["block_index"] + 1)

        # Verify chain validity across the database
        report = verify_audit_chain()
        self.assertTrue(report["chain_valid"])
        self.assertIsNone(report["corrupted_block_index"])
        self.assertGreaterEqual(report["total_blocks_verified"], 2)

    def test_tamper_detection_on_database_alteration(self):
        # 1. Ensure at least one entry exists
        record_officer_decision(
            validation_data=self.doc_val,
            officer_id="INSP-TAMPER-TEST",
            checkpoint_id="LANE-C",
            final_decision="ENTRY_GRANTED"
        )

        # 2. Directly mutate a record in SQLite to simulate a malicious database edit
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT block_index, final_decision FROM officer_audit_log ORDER BY block_index DESC LIMIT 1")
            target_block_idx, orig_decision = cursor.fetchone()
            
            # Tamper the decision without recomputing the SHA-256
            forged_decision = "DETAINED" if orig_decision == "ENTRY_GRANTED" else "ENTRY_GRANTED"
            cursor.execute("UPDATE officer_audit_log SET final_decision = ? WHERE block_index = ?", (forged_decision, target_block_idx))
            conn.commit()

            # 3. Verify that chain verification immediately catches the forgery!
            report = verify_audit_chain()
            self.assertFalse(report["chain_valid"])
            self.assertEqual(report["corrupted_block_index"], target_block_idx)
            self.assertIn("tampering detected", report["error_details"].lower())

            # 4. Clean up / restore the record
            cursor.execute("UPDATE officer_audit_log SET final_decision = ? WHERE block_index = ?", (orig_decision, target_block_idx))
            conn.commit()


class TestDPDPDataRetentionCompliance(unittest.TestCase):
    """Verifies DPDP Act 2023 data minimization, dual-tier retention, and cryptographic tombstoning."""

    def setUp(self):
        self.clean_val = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "CITIZEN CLEAN",
                "document_number": "C12345678"
            },
            "checksum_validation": {"overall_valid": True},
            "field_validation": {"flags": []},
            "blacklist_status": {"is_blacklisted": False}
        }
        self.flagged_val = {
            "document_type": "passport",
            "format": "TD3",
            "extracted_fields": {
                "name": "SUSPECTED FORGER",
                "document_number": "F99999999"
            },
            "checksum_validation": {"overall_valid": False},
            "field_validation": {"flags": ["CHECKSUM_FAILED"]},
            "blacklist_status": {"is_blacklisted": True}
        }

    def test_retention_tier_assignment(self):
        tier_clean = assign_retention_tier("CLEARED", "ENTRY_GRANTED", False, self.clean_val)
        tier_flagged = assign_retention_tier("DETAIN", "ENTRY_GRANTED", True, self.flagged_val)
        
        self.assertEqual(tier_clean, RetentionTier.TIER_1_STANDARD_CLEARED.value)
        self.assertEqual(tier_flagged, RetentionTier.TIER_2_INVESTIGATION_HOLD.value)

    def test_auto_purge_scrubs_clean_demographics(self):
        # 1. Log a clean pass entry
        log_entry = record_officer_decision(
            validation_data=self.clean_val,
            officer_id="INSP-PURGE-UNIT",
            checkpoint_id="LANE-01",
            final_decision="ENTRY_GRANTED"
        )
        self.assertEqual(log_entry["legal_retention_tier"], RetentionTier.TIER_1_STANDARD_CLEARED.value)

        # 2. Trigger auto-purge
        purge_res = purge_expired_clean_records(force_purge_all_clean=True)
        self.assertEqual(purge_res["status"], "success")
        self.assertGreaterEqual(purge_res["purged_records_count"], 1)

        # 3. Verify SQLite demographic field is tombstoned
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM officer_audit_log WHERE block_index = ?", (log_entry["block_index"],))
            purged_row = cursor.fetchone()
            
            self.assertEqual(purged_row["is_purged"], 1)
            self.assertEqual(purged_row["document_number_masked"], "[PURGED: DPDP ACT 2023 SEC 8(7)]")
            self.assertIsNotNone(purged_row["purged_at"])

    def test_purge_preserves_investigation_holds(self):
        # 1. Log a flagged entry (Tier 2 hold)
        flagged_log = record_officer_decision(
            validation_data=self.flagged_val,
            officer_id="INSP-HOLD-UNIT",
            checkpoint_id="LANE-02",
            final_decision="DETAINED",
            override_reason_code="BEHAVIORAL_ANOMALY_SUSPICION"
        )
        self.assertEqual(flagged_log["legal_retention_tier"], RetentionTier.TIER_2_INVESTIGATION_HOLD.value)

        # 2. Run purge
        purge_expired_clean_records(force_purge_all_clean=True)

        # 3. Assert Tier 2 record was NOT purged
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM officer_audit_log WHERE block_index = ?", (flagged_log["block_index"],))
            held_row = cursor.fetchone()
            
            self.assertEqual(held_row["is_purged"], 0)
            self.assertEqual(held_row["document_number_masked"], "F99999999")

    def test_purge_preserves_100_percent_hash_chain_integrity(self):
        # Even after purging multiple clean records, the cryptographic chain MUST be 100% valid!
        chain_report = verify_audit_chain()
        self.assertTrue(chain_report["chain_valid"])
        self.assertIsNone(chain_report["corrupted_block_index"])

    def test_dpdp_compliance_summary(self):
        summary = get_dpdp_compliance_summary()
        self.assertIn("total_records_purged_dpdp", summary)
        self.assertIn("data_minimization_percentage", summary)
        self.assertTrue(summary["dpdp_act_2023_compliant"])


if __name__ == "__main__":
    print("Running AI Document Screening Test Suite...")
    unittest.main(verbosity=2)
