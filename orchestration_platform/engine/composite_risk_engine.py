"""
Explainable Composite Fraud Risk Engine
=======================================
Combines multi-layered forensic, GenAI artifact, facial biometric, and
cross-document relational signals into a 0-100 explainable risk score.

Weights:
- Traditional Tamper Forensics (ELA + VIZ/MRZ + Checksums): 25%
- GenAI Synthetic Artifact Detection (Diffusion/GAN probability): 30%
- Facial Biometrics (Selfie vs Document Face Similarity): 25%
- Relational Consistency & Watchlist Screening: 20%
"""

from typing import Dict, Any, List, Optional


def evaluate_composite_risk(
    ocr_result: Dict[str, Any],
    ela_result: Optional[Dict[str, Any]] = None,
    ai_vision_result: Optional[Dict[str, Any]] = None,
    face_verification_result: Optional[Dict[str, Any]] = None,
    cross_doc_graph_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes a 0-100 explainable risk score with itemized breakdown.

    Args:
        ocr_result: Output from wrappers.ocr_adapter.process_document_ocr
        ela_result: Output from wrappers.ela_adapter.analyze_ela_tampering
        ai_vision_result: Output from wrappers.ai_vision_adapter.run_ai_generated_detection
        face_verification_result: Output from wrappers.ai_vision_adapter.run_facial_biometric_verification
        cross_doc_graph_result: Output from engine.cross_doc_graph.build_and_evaluate_cross_document_graph

    Returns:
        Dict:
            composite_risk_score: float (0.0 to 100.0)
            risk_tier: str ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
            verdict: str ('ACCEPT', 'MANUAL_REVIEW', 'REJECT')
            layer_breakdown: dict of normalized 0-100 scores per layer
            rule_audit_log: list of human-readable explainability logs
    """
    rule_audit_log: List[str] = []

    # -------------------------------------------------------------
    # LAYER 1: Traditional Forensics (25%)
    # -------------------------------------------------------------
    traditional_risk = 0.0

    # 1A. Checksum Failures
    checksums = ocr_result.get("checksum_validation", {})
    if checksums and not checksums.get("overall_valid", True):
        traditional_risk += 40.0
        rule_audit_log.append("[HIGH] Checksum Validation Failed: Check digits do not match ICAO 9303 / Verhoeff rules.")

    # 1B. Field Semantic Flags (Expired, Invalid DOB, etc.)
    flags = ocr_result.get("field_validation", {}).get("flags", [])
    if "EXPIRED" in flags:
        traditional_risk += 30.0
        rule_audit_log.append("[HIGH] Document Expired: Expiry date is in the past.")
    if "INVALID_DOB" in flags:
        traditional_risk += 20.0
        rule_audit_log.append("[MEDIUM] Invalid DOB: Date of birth is outside valid range.")
    if "INVALID_NATIONALITY" in flags:
        traditional_risk += 20.0
        rule_audit_log.append("[MEDIUM] Invalid Nationality Code: Country code is not in ISO 3166-1 / ICAO database.")

    # 1C. VIZ vs MRZ Cross-Check Mismatches
    viz_cross = ocr_result.get("viz_mrz_cross_check")
    if viz_cross and not viz_cross.get("is_consistent", True):
        traditional_risk += 35.0
        mismatches = viz_cross.get("mismatch_flags", [])
        rule_audit_log.append(f"[HIGH] VIZ-MRZ Mismatch: Discrepancy between Visual Zone & MRZ ({', '.join(mismatches)}).")

    # 1D. ELA Recompression Noise Variance
    if ela_result and ela_result.get("status") == "SUCCESS":
        ela_diff = ela_result.get("mean_error_level", 0.0)
        suspicion = ela_result.get("tamper_suspicion", "LOW")
        if suspicion == "HIGH":
            traditional_risk += 35.0
            rule_audit_log.append(f"[HIGH] ELA Tamper Alert: High error level noise variance ({ela_diff:.2f}) indicates possible Photoshop splicing.")
        elif suspicion == "MEDIUM":
            traditional_risk += 15.0
            rule_audit_log.append(f"[MEDIUM] ELA Recompression Alert: Elevated noise variance ({ela_diff:.2f}).")

    traditional_score = min(100.0, traditional_risk)

    # -------------------------------------------------------------
    # LAYER 2: GenAI Synthetic Artifact Detection (30%)
    # -------------------------------------------------------------
    genai_risk = 0.0
    if ai_vision_result and ai_vision_result.get("status") in ("SUCCESS", "FALLBACK"):
        ai_prob = ai_vision_result.get("ai_generated_probability", 0.0)
        verdict_ai = ai_vision_result.get("verdict", "")

        genai_risk = ai_prob * 100.0

        if verdict_ai == "AI_GENERATED":
            rule_audit_log.append(f"[CRITICAL] Synthetic Image Artifact Detected: {ai_prob * 100:.1f}% probability document is GenAI/Diffusion generated.")
        elif verdict_ai == "SUSPICIOUS_REVIEW_RECOMMENDED":
            rule_audit_log.append(f"[MEDIUM] Suspicious Texture Uniformity: {ai_prob * 100:.1f}% AI artifact risk score.")

    genai_score = min(100.0, genai_risk)

    # -------------------------------------------------------------
    # LAYER 3: Facial Biometrics (25%)
    # -------------------------------------------------------------
    biometric_risk = 0.0
    if face_verification_result:
        face_match = face_verification_result.get("face_match", False)
        status_f = face_verification_result.get("status", "OK")
        sim_score = face_verification_result.get("similarity_score", 0.0)

        if status_f in ("FACE_NOT_DETECTED", "MODEL_UNAVAILABLE"):
            biometric_risk = 25.0
            rule_audit_log.append("[MEDIUM] Face Detection Note: Face detection unconfirmed or model operating in standard mode.")
        elif not face_match:
            biometric_risk = 85.0
            rule_audit_log.append(f"[CRITICAL] Facial Match Mismatch: Selfie does not match document photo (Similarity: {sim_score * 100:.1f}%).")
        else:
            biometric_risk = max(0.0, (1.0 - sim_score) * 40.0)
            rule_audit_log.append(f"[PASS] Facial Match Verified: Selfie matches document photo with {sim_score * 100:.1f}% similarity.")
    else:
        # If no selfie was uploaded, neutral biometric score
        biometric_risk = 0.0

    biometric_score = min(100.0, biometric_risk)

    # -------------------------------------------------------------
    # LAYER 4: Relational Consistency & Border Watchlist (20%)
    # -------------------------------------------------------------
    relational_risk = 0.0

    # 4A. Border Security Blacklist Check
    blacklist = ocr_result.get("blacklist_status", {})
    if blacklist and blacklist.get("is_blacklisted"):
        relational_risk += 100.0
        rule_audit_log.append(f"[CRITICAL] BORDER WATCHLIST MATCH: Document number matched '{blacklist.get('matched_list')}' ({blacklist.get('reason')}).")

    # 4B. Cross-Document Graph Discrepancies
    if cross_doc_graph_result:
        graph_score = cross_doc_graph_result.get("graph_consistency_score", 1.0)
        conflicts = cross_doc_graph_result.get("discrepancy_conflicts", [])

        relational_risk += (1.0 - graph_score) * 80.0
        for conflict in conflicts:
            if "Watchlist" not in conflict:
                rule_audit_log.append(f"[HIGH] Cross-Document Mismatch: {conflict}")

    relational_score = min(100.0, relational_risk)

    # -------------------------------------------------------------
    # COMPOSITE SCORE CALCULATION & HARD TRIGGERS
    # -------------------------------------------------------------
    weights = {
        "traditional_forensics": 0.25,
        "genai_artifacts": 0.30,
        "facial_biometrics": 0.25,
        "relational_consistency": 0.20
    }

    base_score = (
        (traditional_score * weights["traditional_forensics"]) +
        (genai_score * weights["genai_artifacts"]) +
        (biometric_score * weights["facial_biometrics"]) +
        (relational_score * weights["relational_consistency"])
    )

    composite_score = base_score

    # Hard Trigger 1: ELA Tamper Alert ([HIGH]) -> Add +40 risk points or ensure score > 45 (MANUAL_REVIEW)
    if ela_result and ela_result.get("tamper_suspicion") == "HIGH":
        composite_score = max(composite_score + 40.0, 48.0)

    # Hard Trigger 2: Relational Consistency Mismatches -> Add +20 risk points per [HIGH] mismatch or (100 - consistency_pct) * 0.5
    if cross_doc_graph_result:
        graph_score_pct = cross_doc_graph_result.get("graph_consistency_score", 1.0) * 100.0
        conflicts = cross_doc_graph_result.get("discrepancy_conflicts", [])
        high_mismatches = [c for c in conflicts if "Watchlist" not in c]
        if high_mismatches:
            mismatch_penalty = max(len(high_mismatches) * 20.0, (100.0 - graph_score_pct) * 0.5)
            composite_score = max(composite_score + mismatch_penalty, 55.0)

    # Hard Trigger 3: GenAI Synthetic Artifact Detection -> If AI Probability > 70%, add +60 risk points (forcing REJECT / HIGH RISK)
    if ai_vision_result and ai_vision_result.get("ai_generated_probability", 0.0) > 0.70:
        composite_score = max(composite_score + 60.0, 75.0)

    composite_score = round(min(100.0, composite_score), 1)

    # Dynamic Verdict Threshold Mapping
    # Score < 25 -> ACCEPT (LOW)
    # 25 <= Score < 65 -> MANUAL_REVIEW (MEDIUM)
    # Score >= 65 -> REJECT (HIGH / CRITICAL)
    if composite_score >= 80.0 or (blacklist and blacklist.get("is_blacklisted")):
        risk_tier = "CRITICAL"
        verdict = "REJECT"
    elif composite_score >= 65.0:
        risk_tier = "HIGH"
        verdict = "REJECT"
    elif composite_score >= 25.0:
        risk_tier = "MEDIUM"
        verdict = "MANUAL_REVIEW"
    else:
        risk_tier = "LOW"
        verdict = "ACCEPT"

    return {
        "composite_risk_score": composite_score,
        "risk_tier": risk_tier,
        "verdict": verdict,
        "layer_breakdown": {
            "traditional_forensics_score": round(traditional_score, 1),
            "genai_artifacts_score": round(genai_score, 1),
            "facial_biometrics_score": round(biometric_score, 1),
            "relational_consistency_score": round(relational_score, 1)
        },
        "rule_audit_log": rule_audit_log
    }
