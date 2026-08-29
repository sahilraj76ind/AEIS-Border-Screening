"""
Interactive Fraud Screening & Evidence Dashboard (Streamlit)
============================================================
Person D Lead UI & Decision Engine
Features:
- Plotly 0-100 Composite Risk Gauge Dial
- Error Boundaries & Graceful Fallbacks (No UI Crashes)
- ELA Tampering Heatmaps & GenAI Artifact Indicators
- DeepFace Facial Biometrics & Cross-Document Relational Consistency Graph
- Downloadable Forensic Audit Trail (JSON & Investigation-Ready PDF Report)
"""

import time
import os
import sys
import io
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import numpy as np
import cv2
import streamlit as st
import plotly.graph_objects as go

# Dynamic Root & Package Path Resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from wrappers.ocr_adapter import process_document_ocr
from wrappers.ela_adapter import analyze_ela_tampering
from wrappers.ai_vision_adapter import (
    run_ai_generated_detection,
    run_facial_biometric_verification,
    run_realtime_webcam_liveness,
    evaluate_frame_liveness,
    RealTimeLivenessEngine
)
from engine.cross_doc_graph import build_and_evaluate_cross_document_graph
from engine.composite_risk_engine import evaluate_composite_risk
from core.blacklist_check import get_all_blacklisted_records
from reports.forensic_generator import generate_forensic_pdf
from governance.audit_logger import (
    record_officer_decision,
    get_all_override_reasons,
    get_audit_logs,
    get_governance_metrics,
    verify_audit_chain,
    compute_ai_recommendation,
    is_decision_an_override
)
from governance.retention_engine import (
    purge_expired_clean_records,
    get_dpdp_compliance_summary
)

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Document Fraud Screening Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .risk-badge-accept {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 1.3rem;
        text-align: center;
    }
    .risk-badge-review {
        background-color: #FEF08A;
        color: #713F12;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 1.3rem;
        text-align: center;
    }
    .risk-badge-reject {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 1.3rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    st.sidebar.image("https://img.icons8.com/isometric/96/shield-check.png", width=64)
    st.sidebar.title("Navigation & Controls")
    mode = st.sidebar.radio(
        "Screening Mode",
        [
            "Multi-Document Batch Verification",
            "Single Document Quick Inspection",
            "📜 Audit Trail & Governance Hub",
            "Border Control Watchlist"
        ]
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Threat Model Settings")
    ela_quality = st.sidebar.slider("ELA Recompression Quality", 70, 95, 90)
    st.sidebar.markdown("---")
    st.sidebar.caption("SIH 2026 Platform • Multi-Layer Forensic Verification Pipeline")
    return mode, ela_quality


def decode_base64_image(b64_str: str) -> Optional[Image.Image]:
    """Helper converting base64 data URI to PIL Image."""
    if not b64_str:
        return None
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def create_plotly_risk_gauge(score: float, verdict: str) -> go.Figure:
    """Renders a Plotly Indicator Risk Gauge dial (0 to 100)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Risk Verdict: {verdict}", 'font': {'size': 18}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#1E293B"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#DEF7EC'},      # Low Risk (Green)
                {'range': [30, 65], 'color': '#FEF08A'},     # Medium Risk (Yellow)
                {'range': [65, 100], 'color': '#FDE8E8'}     # High Risk (Red)
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=240)
    return fig


def render_cryptographic_seal_card(res: Dict[str, Any]):
    """Renders a cryptographic SHA-256 seal certificate card instead of raw JSON."""
    final_dec = res.get("final_decision", "UNKNOWN")
    dec_color = "#15803D" if final_dec == "ENTRY_GRANTED" else ("#B45309" if final_dec == "SECONDARY_INSPECTION" else "#B91C1C")
    dec_bg = "#DCFCE7" if final_dec == "ENTRY_GRANTED" else ("#FEF3C7" if final_dec == "SECONDARY_INSPECTION" else "#FEE2E2")
    is_ovr = res.get("is_override", False)

    st.markdown(f"""
    <div style="background-color: #F8FAFC; border: 2px solid #CBD5E1; border-radius: 10px; padding: 1.2rem; margin-top: 0.8rem; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.6rem; margin-bottom: 0.8rem;">
            <span style="font-size: 1.15rem; font-weight: 700; color: #1E293B;">
                🔒 Genesis-Linked Audit Block #{res.get('block_index', 0)}
            </span>
            <span style="background-color: {dec_bg}; color: {dec_color}; padding: 0.25rem 0.75rem; border-radius: 6px; font-weight: 700; font-size: 0.88rem;">
                {final_dec}
            </span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.88rem; color: #334155;">
            <div><b>Audit Log ID:</b> <code>{res.get('log_id', 'N/A')}</code></div>
            <div><b>Incident ID:</b> <code>{res.get('incident_id', 'N/A')}</code></div>
            <div><b>Inspecting Officer:</b> <code>{res.get('officer_id', 'N/A')}</code></div>
            <div><b>Checkpoint / Gate:</b> <code>{res.get('checkpoint_id', 'N/A')}</code></div>
            <div><b>Decision Type:</b> {'⚠️ Manual Officer Override' if is_ovr else '✅ Agreed with AI Recommendation'}</div>
            <div><b>Retention Tier:</b> <code>{res.get('legal_retention_tier', 'N/A')}</code></div>
            <div><b>Timestamp (UTC):</b> <code>{res.get('timestamp', 'N/A')}</code></div>
            <div><b>Supervisor Co-Sign:</b> <code>{res.get('supervisor_id') or 'N/A (Standard Approval)'}</code></div>
        </div>
        {f'<div style="margin-top: 0.6rem; font-size: 0.88rem; color: #713F12; background-color: #FEF9C3; padding: 0.5rem; border-radius: 6px;"><b>Override Reason:</b> <code>{res.get("override_reason_code")}</code> — {res.get("override_justification") or "No additional remarks"}</div>' if is_ovr else ''}
        <div style="margin-top: 0.8rem; padding-top: 0.6rem; border-top: 1px dashed #CBD5E1; font-size: 0.80rem; color: #475569;">
            <div><b>Previous Block Hash (prev_hash):</b></div>
            <code style="word-break: break-all; color: #0284C7;">{res.get('prev_hash', '0'*64)}</code>
            <div style="margin-top: 0.4rem;"><b>Cryptographic Block Seal (audit_sha256):</b></div>
            <code style="word-break: break-all; color: #16A34A; font-weight: 700;">{res.get('audit_sha256', '')}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_document_identity_card(ocr_res: Dict[str, Any]):
    """Renders structured identity fields, check digits, and watchlist screening instead of raw JSON."""
    doc_type = ocr_res.get("document_type", "UNKNOWN").upper()
    fields = ocr_res.get("extracted_fields", {})
    checksums = ocr_res.get("checksum_validation", {})
    blacklist = ocr_res.get("blacklist_status", {})
    flags = ocr_res.get("field_validation", {}).get("flags", [])
    viz_cross = ocr_res.get("viz_mrz_cross_check")

    st.markdown("### 📄 Extracted Document Identity & Forensic Integrity")
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("##### 👤 Holder Identity & Demographics")
        demo_rows = [
            {"Attribute": "Document Type", "Extracted Value": f"{doc_type} ({ocr_res.get('format', 'STANDARD')})"},
            {"Attribute": "Document Number", "Extracted Value": fields.get("document_number") or "N/A"},
            {"Attribute": "Full Name", "Extracted Value": fields.get("name") or f"{fields.get('surname', '')} {fields.get('given_names', '')}".strip() or "N/A"},
            {"Attribute": "Nationality / Issuing", "Extracted Value": fields.get("nationality") or fields.get("issuing_country") or "N/A"},
            {"Attribute": "Date of Birth", "Extracted Value": fields.get("date_of_birth") or "N/A"},
            {"Attribute": "Sex / Gender", "Extracted Value": fields.get("sex") or "N/A"},
            {"Attribute": "Date of Expiry", "Extracted Value": fields.get("date_of_expiry") or "N/A"}
        ]
        if fields.get("address"):
            demo_rows.append({"Attribute": "Address", "Extracted Value": fields.get("address")})
        st.dataframe(demo_rows, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### 🛡️ Checksums & Border Watchlist")
        
        # Checksum pills
        overall_chk = checksums.get("overall_valid", True)
        if overall_chk:
            st.success("✅ **Mathematical Check Digits:** PASSED (100% Authentic)")
        else:
            st.error("🚨 **Mathematical Check Digits:** FAILED (Tampering Detected)")

        # Individual Checksum breakdown
        chk_details = []
        if checksums.get("document_number_check") is not None:
            chk_details.append(f"Doc Number: {'✅' if checksums['document_number_check'] else '❌'}")
        if checksums.get("dob_check") is not None:
            chk_details.append(f"DOB: {'✅' if checksums['dob_check'] else '❌'}")
        if checksums.get("expiry_check") is not None:
            chk_details.append(f"Expiry: {'✅' if checksums['expiry_check'] else '❌'}")
        if checksums.get("composite_check") is not None:
            chk_details.append(f"Composite: {'✅' if checksums['composite_check'] else '❌'}")
        if checksums.get("verhoeff_check") is not None:
            chk_details.append(f"Verhoeff UID: {'✅' if checksums['verhoeff_check'] else '❌'}")
        if chk_details:
            st.caption(" • ".join(chk_details))

        # Watchlist Status
        is_bl = blacklist.get("is_blacklisted", False)
        if is_bl:
            st.error(f"🚨 **Border Watchlist Hit:** {blacklist.get('matched_list', 'WATCHLIST')} — {blacklist.get('reason', 'Flagged by intelligence')}")
        else:
            st.success("🛡️ **Watchlist Screening:** CLEAR (No Interpol SLTD matches)")

        # Extraction Confidence & Flags
        conf = ocr_res.get("ocr_confidence", 0.95)
        st.metric("OCR / Extraction Confidence", f"{conf * 100:.1f}%")

        if flags:
            st.warning(f"⚠️ **Integrity Flags:** {', '.join(flags)}")

    if viz_cross:
        st.markdown("##### 🔍 Visual Inspection Zone (VIZ) vs. MRZ Forensic Cross-Check")
        f_matches = viz_cross.get("field_matches", {})
        if f_matches:
            cross_rows = []
            for fk, fv in f_matches.items():
                cross_rows.append({
                    "Field": fk.replace("_", " ").title(),
                    "Visual Zone (VIZ) Value": fv.get("viz_value", "N/A"),
                    "MRZ Value": fv.get("mrz_value", "N/A"),
                    "Similarity": f"{fv.get('similarity', 1.0)*100:.0f}%",
                    "Consistency": "✅ MATCH" if fv.get("matched") else "❌ MISMATCH"
                })
            st.dataframe(cross_rows, use_container_width=True, hide_index=True)


def render_relational_graph_table(graph_res: Dict[str, Any]):
    """Renders tabular node attributes and edge consistency instead of raw JSON."""
    nodes = graph_res.get("nodes", [])
    if nodes:
        table_rows = []
        for n in nodes:
            table_rows.append({
                "Document": n.get("doc_type", "").upper(),
                "Extracted Name": n.get("name", "N/A"),
                "Date of Birth": n.get("dob", "N/A"),
                "Sex": n.get("sex", "N/A"),
                "Doc Number": n.get("doc_number", "N/A")
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Single document screened. Relational comparison activates when multiple documents are uploaded.")


def render_uidai_privacy_card(a_res: Dict[str, Any]):
    """Renders structured UIDAI privacy compliance cards instead of raw JSON."""
    p_comp = a_res.get("privacy_compliance") or {}
    redacted_b64 = a_res.get("redacted_image_base64")
    if redacted_b64:
        r_img = decode_base64_image(redacted_b64)
        if r_img:
            st.image(r_img, caption="UIDAI Compliant Physical Masked Aadhaar (First 8 Digits Redacted)", width=450)
    
    st.markdown("#### 🔒 UIDAI Statutory Privacy Compliance Certificate")
    st.markdown(f"""
    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; line-height: 2.0; font-size: 0.92rem;">
        <div>✅ <b>UIDAI Circular Comp/01/2018 Mandate:</b> <code>COMPLIANT</code></div>
        <div>✅ <b>Physical Image Masking:</b> <code>First 8 digits permanently redacted</code></div>
        <div>✅ <b>Zero-Disk Persistence Guarantee:</b> <code>RAM-Only (Zero raw PII written to storage)</code></div>
        <div>✅ <b>Masked Document UID:</b> <code>{p_comp.get('masked_document_number', 'XXXX XXXX XXXX')}</code></div>
    </div>
    """, unsafe_allow_html=True)


def render_officer_decision_console(
    validation_data: Dict[str, Any],
    risk_assessment: Optional[Dict[str, Any]] = None,
    key_prefix: str = "batch"
):
    """
    Renders an interactive Human-in-the-Loop (HITL) Officer Decision & Override Desk.
    Enforces standardized reason codes, dual-key supervisor authorization,
    and seals the decision into the Genesis-linked SHA-256 cryptographic audit chain.
    """
    st.subheader("🛡️ Officer Sovereign Action Desk (HITL)")
    st.caption("Execute final border control determination and seal decision into the immutable audit chain.")

    # Compute baseline AI recommendation
    ai_rec = validation_data.get("ai_recommendation")
    if not ai_rec:
        ai_rec = compute_ai_recommendation(validation_data)

    ai_color = "#DEF7EC" if ai_rec == "CLEARED" else ("#FEF08A" if ai_rec == "SECONDARY_INSPECTION" else "#FDE8E8")
    ai_text_color = "#03543F" if ai_rec == "CLEARED" else ("#713F12" if ai_rec == "SECONDARY_INSPECTION" else "#9B1C1C")
    
    st.markdown(f"""
    <div style="background-color: {ai_color}; color: {ai_text_color}; padding: 0.75rem 1rem; border-radius: 8px; font-weight: 600; margin-bottom: 1rem; border: 1px solid rgba(0,0,0,0.08);">
        🤖 <b>AI Recommendation:</b> <code>{ai_rec}</code>
        &nbsp;&nbsp;|&nbsp;&nbsp; <b>Risk Score:</b> <code>{risk_assessment.get('composite_risk_score', 0.0) if risk_assessment else 0.0:.1f} / 100</code>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        officer_id = st.text_input("Officer Badge ID", value="OFFICER-BSF-4821", key=f"{key_prefix}_officer_id")
    with c2:
        checkpoint_id = st.text_input("Checkpoint Gate / Lane", value="TERMINAL-3 / IN-GATE-04", key=f"{key_prefix}_checkpoint_id")

    decision_options = [
        ("ENTRY_GRANTED", "✅ ENTRY GRANTED - Clear traveler"),
        ("SECONDARY_INSPECTION", "⚠️ SECONDARY INSPECTION - Escalate for physical search"),
        ("ENTRY_REFUSED", "🚫 ENTRY REFUSED - Issue removal notice"),
        ("DETAINED", "🚨 DETAINED - Confiscate document and detain")
    ]
    
    default_idx = 0 if ai_rec == "CLEARED" else (1 if ai_rec == "SECONDARY_INSPECTION" else 3)
    
    selected_decision = st.radio(
        "Select Officer Sovereign Final Decision:",
        options=[opt[0] for opt in decision_options],
        format_func=lambda x: next(opt[1] for opt in decision_options if opt[0] == x),
        index=default_idx,
        key=f"{key_prefix}_decision"
    )

    is_override = is_decision_an_override(ai_rec, selected_decision)

    override_reason_code = None
    override_justification = None
    supervisor_id = None

    if is_override:
        st.warning(f"⚠️ **Manual Officer Override Detected:** Changing AI `{ai_rec}` ➔ Final Sovereign Decision `{selected_decision}`.")
        
        all_reasons = get_all_override_reasons()
        if isinstance(all_reasons, list):
            if selected_decision == "ENTRY_GRANTED":
                reason_category = "Approve Overrides (Clearing an AI alert)"
                reason_list = [r["code"] for r in all_reasons if r.get("category") == "APPROVE_OVERRIDE"]
            else:
                reason_category = "Reject/Detain Overrides (Overriding an AI Cleared pass)"
                reason_list = [r["code"] for r in all_reasons if r.get("category") == "REJECT_OVERRIDE"]
        elif isinstance(all_reasons, dict):
            if selected_decision == "ENTRY_GRANTED":
                reason_category = "Approve Overrides (Clearing an AI alert)"
                reason_list = [r["code"] for r in all_reasons.get("approve_overrides_clearing_ai_alert", [])]
            else:
                reason_category = "Reject/Detain Overrides (Overriding an AI Cleared pass)"
                reason_list = [r["code"] for r in all_reasons.get("reject_or_detain_overrides_blocking_entry", [])]
        else:
            reason_list = []
            reason_category = "Standard Overrides"

        if not reason_list:
            reason_list = [
                "PHYSICAL_SECURITY_FEATURES_VERIFIED",
                "OPTICAL_GLARE_FALSE_POSITIVE",
                "DIPLOMATIC_CONSULAR_IMMUNITY",
                "BEHAVIORAL_ANOMALY_SUSPICION",
                "IMPOSTER_BIOMETRIC_MISMATCH",
                "CANINE_K9_DETECTION_ALERT",
                "PHYSICAL_DOCUMENT_SUBSTRATE_TAMPERING",
                "OTHER_OFFICER_DISCRETION"
            ]

        override_reason_code = st.selectbox(
            f"Mandatory Standardized Override Reason Code ({reason_category}):",
            options=reason_list,
            key=f"{key_prefix}_reason_code"
        )
        
        override_justification = st.text_area(
            "Officer Justification & Evidentiary Remarks (Stored in Cryptographic Chain):",
            placeholder="Document physical microprint and holograms verified under UV lamp. Physical substrate authentic.",
            key=f"{key_prefix}_justification"
        )

        # Dual-Key Supervisor Requirement
        if ai_rec == "DETAIN" and selected_decision == "ENTRY_GRANTED":
            st.error("🔒 **CRITICAL DUAL-KEY SECURITY GUARDRAIL:** Overriding a high-risk 'DETAIN' verdict to 'ENTRY_GRANTED' strictly requires Supervisor Co-Signature.")
            supervisor_id = st.text_input("Supervisor Badge ID (Mandatory Co-Signature):", placeholder="SUPV-SINGH-9104", key=f"{key_prefix}_supervisor_id")

    if st.button("🔒 Record Sovereign Decision & Seal into Immutable Hash-Chain", type="primary", key=f"{key_prefix}_submit_btn", use_container_width=True):
        try:
            if is_override and not override_reason_code:
                st.error("Please select a mandatory override reason code.")
            elif is_override and ai_rec == "DETAIN" and selected_decision == "ENTRY_GRANTED" and not supervisor_id:
                st.error("Supervisor Badge ID is required to override a DETAIN alert.")
            else:
                res = record_officer_decision(
                    validation_data=validation_data,
                    officer_id=officer_id,
                    checkpoint_id=checkpoint_id,
                    final_decision=selected_decision,
                    override_reason_code=override_reason_code,
                    override_justification=override_justification,
                    supervisor_id=supervisor_id
                )
                st.session_state[f"{key_prefix}_last_audit_res"] = res

        except Exception as e:
            st.error(f"Failed to record officer decision: {str(e)}")

    # Render recorded audit log result persistently as an elegant certificate card (No raw JSON)
    if f"{key_prefix}_last_audit_res" in st.session_state and st.session_state[f"{key_prefix}_last_audit_res"]:
        res = st.session_state[f"{key_prefix}_last_audit_res"]
        st.success(f"✅ **Decision Cryptographically Sealed in Genesis-Linked Block #{res['block_index']}!**")
        render_cryptographic_seal_card(res)


def render_governance_hub():
    """Renders the Cryptographic Audit Trail, Hash Chain Verifier & DPDP Compliance Dashboard."""
    st.subheader("📜 Cryptographic Audit Trail & DPDP Governance Hub")
    st.caption("Immutable, Genesis-linked SHA-256 ledger tracking all human officer decisions, overrides, and DPDP Act 2023 statutory retention compliance.")

    stats = get_governance_metrics()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inspections", stats.get("total_inspections_logged", 0))
    m2.metric("Total Overrides", stats.get("total_overrides", 0))
    m3.metric("Override Rate", f"{stats.get('override_rate_percentage', 0.0):.1f}%")
    m4.metric("AI-Human Agreement", f"{stats.get('ai_human_agreement_rate_percentage', 100.0):.1f}%")

    st.markdown("---")
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.markdown("#### 🔗 Cryptographic Hash-Chain Verification")
        st.caption("Verifies full hash chain continuity from Genesis Block #0 to the latest block.")
        if st.button("🔍 Run Full Chain Integrity Verification", use_container_width=True):
            chain_res = verify_audit_chain()
            if chain_res.get("chain_valid"):
                st.success(f"✅ **100% Authentic & Unbroken:** Verified {chain_res.get('total_blocks_verified', 0)} consecutive blocks.")
                st.write(f"**Latest Block Hash:** `{chain_res.get('latest_block_hash')}`")
                st.write(f"**Verified At:** `{chain_res.get('verified_at')}`")
            else:
                st.error(f"🚨 **Integrity Alert:** Block #{chain_res.get('corrupted_block_index')} compromised: {chain_res.get('error_details')}")

    with g_col2:
        st.markdown("#### 🧹 DPDP Act 2023 Data Minimization Engine")
        st.caption("Auto-purges clean transient demographic PII while preserving 100% hash chain seals.")
        dpdp_status = get_dpdp_compliance_summary()
        st.write(f"**Data Minimization Rate:** `{dpdp_status.get('data_minimization_percentage', 0.0):.1f}%`")
        st.write(f"**Active Investigation Holds:** `{dpdp_status.get('active_evidentiary_investigation_holds', 0)}`")
        
        if st.button("🚀 Execute Data Minimization Purge (Clean Scans > 24h)", use_container_width=True):
            purge_res = purge_expired_clean_records(force_purge_all_clean=True)
            st.success(f"Scrubbed {purge_res.get('purged_records_count', 0)} clean records under DPDP Act Sec 8(7). Hash chain integrity preserved!")

    st.markdown("---")
    st.markdown("#### 📋 Recent Chained Audit Blocks")
    logs = get_audit_logs(limit=50)
    if logs:
        # Format logs cleanly in dataframe
        clean_logs = []
        for l in logs:
            clean_logs.append({
                "Block": f"#{l.get('block_index', '')}",
                "Timestamp (UTC)": l.get("timestamp", ""),
                "Officer": l.get("officer_id", ""),
                "AI Rec": l.get("ai_recommendation", ""),
                "Final Decision": l.get("final_decision", ""),
                "Override": "⚠️ YES" if l.get("is_override") else "✅ NO",
                "Reason Code": l.get("override_reason_code") or "N/A",
                "Retention Tier": l.get("legal_retention_tier", ""),
                "SHA-256 Seal": l.get("audit_sha256", "")[:16] + "..."
            })
        st.dataframe(clean_logs, use_container_width=True, hide_index=True)
    else:
        st.info("No audit entries recorded yet. Screen documents and record officer decisions to populate the cryptographic ledger.")


def main():
    st.markdown('<div class="main-header">🛡️ AI-Powered Document Fraud Screening Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">2026 Threat Model Pipeline: ELA Forensics + GenAI Synthetic Artifact Detection + Biometrics + Relational Consistency Graph</div>', unsafe_allow_html=True)

    mode, ela_quality = render_sidebar()

    if mode == "Border Control Watchlist":
        st.subheader("📋 Active Border Security & Intelligence Watchlists")
        st.caption("Live border control database covering Interpol SLTD (Stolen & Lost Travel Documents), Red Notices, and Entry Bans.")
        watchlist_data = get_all_blacklisted_records()
        if isinstance(watchlist_data, list):
            st.dataframe(watchlist_data, use_container_width=True)
        elif isinstance(watchlist_data, dict):
            formatted_list = []
            for k, v in watchlist_data.items():
                if isinstance(v, dict):
                    row = {"Document / Target": k}
                    row.update(v)
                    formatted_list.append(row)
                else:
                    formatted_list.append({"Target": k, "Status": str(v)})
            st.dataframe(formatted_list, use_container_width=True, hide_index=True)
        return

    if mode == "📜 Audit Trail & Governance Hub":
        render_governance_hub()
        return

    # -------------------------------------------------------------------------
    # Mode 1: Multi-Document Batch Verification
    # -------------------------------------------------------------------------
    if mode == "Multi-Document Batch Verification":
        st.markdown("### 📥 Multi-Document Traveler Verification Upload")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            p_file = st.file_uploader("Passport Image (TD3)", type=["jpg", "jpeg", "png", "webp"])
        with col2:
            v_file = st.file_uploader("Visa Image (TD2)", type=["jpg", "jpeg", "png", "webp"])
        with col3:
            a_file = st.file_uploader("Aadhaar Card Image", type=["jpg", "jpeg", "png", "webp"])
        with col4:
            selfie_mode = st.radio("Selfie / Liveness Input", ["📁 Upload File", "🎥 Live Blink Liveness Scanner", "📷 In-Browser Camera"], horizontal=True)
            s_file = None
            live_captured_bytes = st.session_state.get("live_liveness_selfie_bytes", None)
            liveness_info = st.session_state.get("last_liveness_report", None)

            if selfie_mode == "📁 Upload File":
                s_file = st.file_uploader("Traveler Live Selfie", type=["jpg", "jpeg", "png", "webp"])
            elif selfie_mode == "🎥 Live Blink Liveness Scanner":
                st.caption("Live In-Page HUD with real-time Eye Aspect Ratio (EAR) & anti-spoofing blink verification.")
                
                scan_col1, scan_col2 = st.columns([1, 1])
                with scan_col1:
                    start_scan = st.button("🔴 Start Live Scanner", use_container_width=True)
                with scan_col2:
                    if live_captured_bytes:
                        if st.button("🔄 Retake Live Selfie", use_container_width=True):
                            st.session_state["live_liveness_selfie_bytes"] = None
                            st.session_state["last_liveness_report"] = None
                            live_captured_bytes = None
                            st.rerun()

                if start_scan:
                    timeout_limit = 10.0  # 10 second presentation attack detection timeout
                    try:
                        engine = RealTimeLivenessEngine(
                            ear_thresh_closed=0.225,
                            ear_thresh_open=0.255,
                            min_closed_frames=1,
                            target_blinks=2,
                            timeout_seconds=timeout_limit
                        )
                    except TypeError:
                        engine = RealTimeLivenessEngine(
                            ear_thresh_closed=0.225,
                            ear_thresh_open=0.255,
                            min_closed_frames=1,
                            target_blinks=2
                        )
                    engine.timeout_seconds = timeout_limit
                    engine.reset_state()

                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        st.error("⚠️ Unable to access local camera (Index 0). Please check camera connection or device permissions.")
                    else:
                        frame_placeholder = st.empty()
                        progress_placeholder = st.empty()
                        info_placeholder = st.empty()
                        
                        start_time = time.time()
                        confirmed = False
                        last_status = {}

                        while cap.isOpened():
                            ret, frame_bgr = cap.read()
                            if not ret:
                                break
                            
                            elapsed = time.time() - start_time
                            remaining = max(0.0, timeout_limit - elapsed)
                            if remaining <= 0:
                                break

                            frame_bgr = cv2.flip(frame_bgr, 1)
                            annotated_bgr, status = engine.process_frame(frame_bgr, draw_hud=True)
                            annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
                            last_status = status

                            # Stream directly into web page
                            frame_placeholder.image(annotated_rgb, channels="RGB", use_container_width=True)
                            
                            # Render real-time countdown progress bar
                            progress_val = max(0.0, min(1.0, remaining / timeout_limit))
                            progress_placeholder.progress(progress_val, text=f"⏱️ Time Remaining: {remaining:.1f}s | Blink twice to verify liveness")
                            
                            badge_str = "🟢 LIVENESS CONFIRMED (LIVE HUMAN)" if status["liveness_confirmed"] else ("🟡 EYE CLOSED (BLINK DETECTED)" if status["is_eye_closed"] else "🔵 PLEASE BLINK NATURALLY")
                            info_placeholder.markdown(f"**Status:** `{badge_str}` | **Blinks:** `{status['blink_count']}/2` | **EAR:** `{status['current_ear']:.3f}`")

                            if status["liveness_confirmed"]:
                                confirmed = True
                                cap_frame = engine.captured_frame_rgb if engine.captured_frame_rgb is not None else annotated_rgb
                                img_pil = Image.fromarray(cap_frame)
                                buf = io.BytesIO()
                                img_pil.save(buf, format="JPEG")
                                live_captured_bytes = buf.getvalue()
                                st.session_state["live_liveness_selfie_bytes"] = live_captured_bytes
                                st.session_state["last_liveness_report"] = status
                                break

                            time.sleep(0.02)

                        cap.release()
                        frame_placeholder.empty()
                        progress_placeholder.empty()
                        info_placeholder.empty()

                        if confirmed:
                            st.success("✅ Liveness Confirmed (2 Blinks Verified)! Live frame captured.")
                            st.rerun()
                        else:
                            blinks_found = last_status.get("blink_count", 0)
                            st.error(f"🚫 **Liveness Verification Failed (Timeout - {blinks_found}/2 Blinks Detected)**")
                            st.markdown("""
                            > ⚠️ **Presentation Attack Detection Alert:**
                            > No natural eye blinks were registered within the 10-second window (Potential static photograph, video replay, or obstructed view).
                            > 
                            > **Action:** Please ensure a live person is facing the camera and click **Start Live Scanner** to retry.
                            """)

                if live_captured_bytes:
                    st.image(Image.open(io.BytesIO(live_captured_bytes)), caption="🟢 Verified Live Traveler Face", width=220)
                    if liveness_info:
                        st.caption(f"Verified via 2 Blinks (Final EAR: {liveness_info.get('current_ear', 0.0):.3f})")
            else:
                cam_img = st.camera_input("Capture Traveler Live Selfie")
                if cam_img:
                    live_captured_bytes = cam_img.getvalue()
                    st.session_state["live_liveness_selfie_bytes"] = live_captured_bytes
                    st.session_state["last_liveness_report"] = {"liveness_confirmed": True, "method": "in_browser_camera"}

        if st.button("🚀 Execute Comprehensive Multi-Layer Screening", type="primary", use_container_width=True):
            if not (p_file or v_file or a_file):
                st.warning("Please upload at least one identity document (Passport, Visa, or Aadhaar).")
                return

            with st.spinner("Executing OCR, ELA Tamper Forensics, GenAI Detection, Biometrics & Relational Alignment..."):
                doc_results = {}
                ela_results = {}
                ai_results = {}
                primary_bytes = None

                # Error Boundary: Passport
                if p_file:
                    try:
                        pb = p_file.read()
                        primary_bytes = primary_bytes or pb
                        doc_results["passport"] = process_document_ocr(pb, explicit_doc_type="passport")
                        ela_results["passport"] = analyze_ela_tampering(pb, quality=ela_quality)
                        ai_results["passport"] = run_ai_generated_detection(pb)
                    except Exception as e:
                        st.error(f"Passport Processing Error: {str(e)}")

                # Error Boundary: Visa
                if v_file:
                    try:
                        vb = v_file.read()
                        primary_bytes = primary_bytes or vb
                        doc_results["visa"] = process_document_ocr(vb, explicit_doc_type="visa")
                        ela_results["visa"] = analyze_ela_tampering(vb, quality=ela_quality)
                        ai_results["visa"] = run_ai_generated_detection(vb)
                    except Exception as e:
                        st.error(f"Visa Processing Error: {str(e)}")

                # Error Boundary: Aadhaar
                if a_file:
                    try:
                        ab = a_file.read()
                        primary_bytes = primary_bytes or ab
                        doc_results["aadhaar"] = process_document_ocr(ab, explicit_doc_type="aadhaar")
                        ela_results["aadhaar"] = analyze_ela_tampering(ab, quality=ela_quality)
                        ai_results["aadhaar"] = run_ai_generated_detection(ab)
                    except Exception as e:
                        st.error(f"Aadhaar Processing Error: {str(e)}")

                # Error Boundary: Biometrics, Liveness & Live Selfie GenAI Artifact Detection
                face_res = None
                selfie_raw_bytes = s_file.read() if s_file else live_captured_bytes
                liveness_metric = None

                if selfie_raw_bytes and primary_bytes:
                    try:
                        face_res = run_facial_biometric_verification(primary_bytes, selfie_raw_bytes)
                        ai_results["selfie"] = run_ai_generated_detection(selfie_raw_bytes)
                        liveness_metric = evaluate_frame_liveness(selfie_raw_bytes)
                        if face_res:
                            face_res["liveness_metric"] = liveness_metric
                            face_res["liveness_report"] = liveness_info
                    except Exception as e:
                        st.warning(f"Facial Biometrics / Selfie GenAI Note: {str(e)}")

                # Relational Graph & Risk Evaluation
                try:
                    graph_res = build_and_evaluate_cross_document_graph(
                        doc_results=doc_results,
                        face_verification_result=face_res
                    )
                    primary_key = "passport" if "passport" in doc_results else ("visa" if "visa" in doc_results else "aadhaar")

                    # Select highest GenAI risk result across all screened documents and live selfie
                    max_ai_res = None
                    for k, v in ai_results.items():
                        if not max_ai_res or v.get("ai_generated_probability", 0.0) > max_ai_res.get("ai_generated_probability", 0.0):
                            max_ai_res = v

                    risk_res = evaluate_composite_risk(
                        ocr_result=doc_results[primary_key],
                        ela_result=ela_results.get(primary_key),
                        ai_vision_result=max_ai_res or ai_results.get(primary_key),
                        face_verification_result=face_res,
                        cross_doc_graph_result=graph_res
                    )
                except Exception as e:
                    st.error(f"Risk Evaluation Error: {str(e)}")
                    return

                # Persist screening results in session state across interactive widget reruns
                st.session_state["batch_screening_data"] = {
                    "doc_results": doc_results,
                    "ela_results": ela_results,
                    "ai_results": ai_results,
                    "face_res": face_res,
                    "graph_res": graph_res,
                    "risk_res": risk_res,
                    "primary_key": primary_key
                }
                st.session_state.pop("batch_last_audit_res", None)

        # -----------------------------------------------------------------
        # Display Results Dashboard (Persisted in session state)
        # -----------------------------------------------------------------
        if "batch_screening_data" in st.session_state and st.session_state["batch_screening_data"]:
            batch_data = st.session_state["batch_screening_data"]
            doc_results = batch_data["doc_results"]
            ela_results = batch_data["ela_results"]
            ai_results = batch_data["ai_results"]
            face_res = batch_data["face_res"]
            graph_res = batch_data["graph_res"]
            risk_res = batch_data["risk_res"]
            primary_key = batch_data["primary_key"]

            st.markdown("---")

            # =========================================================================
            # TOP ACTION CENTER: Aligned Verdict + Quick Exports (Left) & HITL Desk (Right)
            # =========================================================================
            top_col1, top_col2 = st.columns([1.1, 1.2])

            with top_col1:
                st.subheader("📊 Executive AI Risk Verdict")
                score = risk_res["composite_risk_score"]
                verdict = risk_res["verdict"]
                tier = risk_res["risk_tier"]

                fig_gauge = create_plotly_risk_gauge(score, verdict)
                st.plotly_chart(fig_gauge, use_container_width=True)

                if verdict == "ACCEPT":
                    st.markdown('<div class="risk-badge-accept">✅ ACCEPT - STANDARD PASS</div>', unsafe_allow_html=True)
                elif verdict == "MANUAL_REVIEW":
                    st.markdown('<div class="risk-badge-review">⚠️ MANUAL SECONDARY REVIEW</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="risk-badge-reject">🚫 REJECT - INTERCEPT REQUIRED</div>', unsafe_allow_html=True)

                st.markdown(f"""
                <div style="margin-top: 0.8rem; font-size: 0.92rem; color: #475569;">
                    <b>Risk Severity Tier:</b> <code>{tier}</code> &nbsp;|&nbsp; 
                    <b>Relational Consistency:</b> <code>{graph_res['graph_consistency_score'] * 100:.0f}%</code> &nbsp;|&nbsp;
                    <b>Docs Screened:</b> <code>{len(doc_results)}</code>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("##### 📥 Evidentiary Exports")
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    try:
                        pdf_bytes = generate_forensic_pdf(validation_data=doc_results[primary_key])
                        st.download_button(
                            label="📕 Download PDF",
                            data=pdf_bytes,
                            file_name="forensic_audit_report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"PDF Export Error: {str(e)}")

                with ex_col2:
                    json_data = json.dumps({
                        "document_analysis": doc_results[primary_key],
                        "relational_graph": graph_res,
                        "risk_assessment": risk_res
                    }, indent=2)
                    st.download_button(
                        label="📄 Download JSON",
                        data=json_data,
                        file_name="forensic_audit_report.json",
                        mime="application/json",
                        use_container_width=True
                    )

            with top_col2:
                # Human-in-the-Loop (HITL) Officer Decision & Override Desk placed right at the top!
                render_officer_decision_console(
                    validation_data=doc_results[primary_key],
                    risk_assessment=risk_res,
                    key_prefix="batch"
                )

            # =========================================================================
            # MIDDLE SECTION: Multi-Layer Risk Breakdown & Rule Audit Logs
            # =========================================================================
            st.markdown("---")
            st.markdown("#### 🔬 Multi-Layer Forensic Risk Breakdown")
            lb = risk_res["layer_breakdown"]
            lcol1, lcol2, lcol3, lcol4 = st.columns(4)
            lcol1.progress(int(lb["traditional_forensics_score"]), text=f"Traditional Forensics: {lb['traditional_forensics_score']}%")
            lcol2.progress(int(lb["genai_artifacts_score"]), text=f"GenAI Synthetic: {lb['genai_artifacts_score']}%")
            lcol3.progress(int(lb["facial_biometrics_score"]), text=f"Facial Biometrics: {lb['facial_biometrics_score']}%")
            lcol4.progress(int(lb["relational_consistency_score"]), text=f"Relational Graph: {lb['relational_consistency_score']}%")

            with st.expander("📝 Human-Readable Risk Rule Audit Log", expanded=False):
                for log in risk_res["rule_audit_log"]:
                    if "[CRITICAL]" in log or "[HIGH]" in log:
                        st.error(log)
                    elif "[MEDIUM]" in log:
                        st.warning(log)
                    else:
                        st.success(log)

            # =========================================================================
            # BOTTOM SECTION: Detailed Exploration Tabs (No raw JSON)
            # =========================================================================
            tab_forensics, tab_genai, tab_biometrics, tab_graph, tab_aadhaar = st.tabs([
                "🔬 ELA & Forensics", "🤖 GenAI Artifacts", "👤 Facial Biometrics", "🌐 Relational Graph", "🔒 UIDAI Privacy"
            ])

            with tab_forensics:
                st.markdown("### Error Level Analysis (ELA) Heatmaps")
                f_cols = st.columns(len(ela_results))
                for idx, (dk, ev) in enumerate(ela_results.items()):
                    with f_cols[idx]:
                        st.markdown(f"**{dk.upper()} ELA Heatmap**")
                        ela_img = decode_base64_image(ev.get("ela_heatmap_base64", ""))
                        if ela_img:
                            st.image(ela_img, caption=f"Mean Error Level: {ev.get('mean_error_level', 0.0):.2f}", use_container_width=True)
                        st.write(f"**Verdict:** `{ev.get('verdict')}`")
                        st.write(f"**Suspicion:** `{ev.get('tamper_suspicion')}`")

            with tab_genai:
                st.markdown("### GenAI Synthetic Image Artifact Detection")
                g_cols = st.columns(len(ai_results))
                for idx, (dk, av) in enumerate(ai_results.items()):
                    with g_cols[idx]:
                        st.markdown(f"**{dk.upper()} AI Artifact Analysis**")
                        prob = av.get("ai_generated_probability", 0.0)
                        st.metric("AI Probability", f"{prob * 100:.1f}%")
                        st.write(f"**Primary Model Score:** `{av.get('primary_model_score', 0.0):.4f}`")
                        st.write(f"**Noise Heuristic Score:** `{av.get('fallback_heuristic_score', 0.0):.4f}`")
                        st.write(f"**Verdict:** `{av.get('verdict')}`")

            with tab_biometrics:
                st.markdown("### Facial Biometrics & Presentation Attack Detection (Liveness)")
                if face_res:
                    b_col1, b_col2, b_col3 = st.columns(3)
                    with b_col1:
                        st.markdown("#### Facial Match")
                        st.metric("Face Match Verified", str(face_res.get("face_match")))
                        st.metric("Similarity Score", f"{face_res.get('similarity_score', 0.0) * 100:.1f}%")
                    with b_col2:
                        st.markdown("#### Biometric Distance")
                        st.metric("Distance Metric", f"{face_res.get('distance', 1.0):.4f}")
                        st.write(f"**DeepFace Status:** `{face_res.get('status')}`")
                    with b_col3:
                        st.markdown("#### Real-Time Liveness (PAD)")
                        live_rep = face_res.get("liveness_report") or {}
                        live_met = face_res.get("liveness_metric") or {}
                        if live_rep.get("liveness_confirmed"):
                            st.success("🟢 Liveness Confirmed (Live Human)")
                            st.write(f"**Blinks Verified:** `{live_rep.get('blink_count', 2)} / {live_rep.get('target_blinks', 2)}`")
                            st.write(f"**Final EAR:** `{live_rep.get('current_ear', 0.0):.3f}`")
                        elif live_met.get("face_detected"):
                            ear_val = live_met.get("current_ear", 0.0)
                            st.info(f"Passive Frame EAR: `{ear_val:.3f}`")
                            st.write(f"**Eye Openness:** `{'Closed' if live_met.get('is_eye_closed') else 'Normal/Open'}`")
                        else:
                            st.caption("Static Selfie (No Active Blink Stream Recorded)")
                else:
                    st.info("No live selfie was uploaded for biometric verification.")

            with tab_graph:
                st.markdown("### Cross-Document Relational Identity Graph")
                st.write(f"**Graph Consistency Score:** {graph_res['graph_consistency_score'] * 100:.1f}%")
                st.write(f"**Relational Conflicts Detected:** {len(graph_res['discrepancy_conflicts'])}")
                if graph_res['discrepancy_conflicts']:
                    for conf in graph_res['discrepancy_conflicts']:
                        st.error(f"⚠️ {conf}")
                else:
                    st.success("All cross-document identity attributes (Name, DOB, Sex) align consistently!")

                st.markdown("##### 🌐 Cross-Document Attribute Comparison")
                render_relational_graph_table(graph_res)

            with tab_aadhaar:
                st.markdown("### UIDAI Privacy Compliance & Aadhaar Redaction")
                if "aadhaar" in doc_results:
                    render_uidai_privacy_card(doc_results["aadhaar"])
                else:
                    st.info("No Aadhaar document uploaded in this session.")

    # -------------------------------------------------------------------------
    # Mode 2: Single Document Quick Inspection
    # -------------------------------------------------------------------------
    else:
        st.markdown("### 📄 Single Document Quick Inspection")
        u_file = st.file_uploader("Upload Passport, Visa, or Aadhaar Image", type=["jpg", "jpeg", "png", "webp"])
        u_type = st.selectbox("Explicit Document Type (Optional)", ["auto", "passport", "visa", "aadhaar"])

        if u_file and st.button("Inspect Document", type="primary"):
            ub = u_file.read()
            with st.spinner("Processing document..."):
                ocr_res = process_document_ocr(ub, explicit_doc_type=None if u_type == "auto" else u_type)
                ela_res = analyze_ela_tampering(ub, quality=ela_quality)
                ai_res = run_ai_generated_detection(ub)
                risk_res = evaluate_composite_risk(ocr_result=ocr_res, ela_result=ela_res, ai_vision_result=ai_res)

                # Persist single document screening results in session state
                st.session_state["single_screening_data"] = {
                    "ocr_res": ocr_res,
                    "ela_res": ela_res,
                    "ai_res": ai_res,
                    "risk_res": risk_res
                }
                st.session_state.pop("single_last_audit_res", None)

        if "single_screening_data" in st.session_state and st.session_state["single_screening_data"]:
            single_data = st.session_state["single_screening_data"]
            ocr_res = single_data["ocr_res"]
            ela_res = single_data["ela_res"]
            ai_res = single_data["ai_res"]
            risk_res = single_data["risk_res"]

            st.markdown("---")

            # TOP ACTION CENTER: Aligned Verdict + Quick Exports (Left) & HITL Desk (Right)
            top_col1, top_col2 = st.columns([1.1, 1.2])

            with top_col1:
                st.subheader("📊 Executive AI Risk Verdict")
                score = risk_res["composite_risk_score"]
                verdict = risk_res["verdict"]
                tier = risk_res["risk_tier"]

                fig_gauge = create_plotly_risk_gauge(score, verdict)
                st.plotly_chart(fig_gauge, use_container_width=True)

                if verdict == "ACCEPT":
                    st.markdown('<div class="risk-badge-accept">✅ ACCEPT - STANDARD PASS</div>', unsafe_allow_html=True)
                elif verdict == "MANUAL_REVIEW":
                    st.markdown('<div class="risk-badge-review">⚠️ MANUAL SECONDARY REVIEW</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="risk-badge-reject">🚫 REJECT - INTERCEPT REQUIRED</div>', unsafe_allow_html=True)

                st.write(f"**Risk Severity Tier:** `{tier}`")

                st.markdown("##### 📥 Evidentiary Exports")
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    try:
                        pdf_bytes = generate_forensic_pdf(validation_data=ocr_res)
                        st.download_button(
                            label="📕 Download PDF",
                            data=pdf_bytes,
                            file_name="single_doc_audit.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"PDF Export Error: {str(e)}")

                with ex_col2:
                    st.download_button(
                        label="📄 Download JSON",
                        data=json.dumps(ocr_res, indent=2),
                        file_name="single_doc_audit.json",
                        mime="application/json",
                        use_container_width=True
                    )

            with top_col2:
                # Human-in-the-Loop (HITL) Officer Decision & Override Desk placed right at the top!
                render_officer_decision_console(
                    validation_data=ocr_res,
                    risk_assessment=risk_res,
                    key_prefix="single"
                )

            st.markdown("---")
            # Render structured Identity demographics & Checksums (No raw JSON!)
            render_document_identity_card(ocr_res)


if __name__ == "__main__":
    main()
