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

import os
import sys
import io
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
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
from wrappers.ai_vision_adapter import run_ai_generated_detection, run_facial_biometric_verification
from engine.cross_doc_graph import build_and_evaluate_cross_document_graph
from engine.composite_risk_engine import evaluate_composite_risk
from core.blacklist_check import get_all_blacklisted_records
from reports.forensic_generator import generate_forensic_pdf

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
        ["Multi-Document Batch Verification", "Single Document Quick Inspection", "Border Control Watchlist"]
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


def main():
    st.markdown('<div class="main-header">🛡️ AI-Powered Document Fraud Screening Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">2026 Threat Model Pipeline: ELA Forensics + GenAI Synthetic Artifact Detection + Biometrics + Relational Consistency Graph</div>', unsafe_allow_html=True)

    mode, ela_quality = render_sidebar()

    if mode == "Border Control Watchlist":
        st.subheader("📋 Active Border Security & Intelligence Watchlists")
        watchlist_data = get_all_blacklisted_records()
        st.json(watchlist_data)
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
            s_file = st.file_uploader("Traveler Live Selfie", type=["jpg", "jpeg", "png", "webp"])

        if st.button("🚀 Execute Comprehensive Multi-Layer Screening", type="primary", use_container_width=True):
            if not (p_file or v_file or a_file):
                st.warning("Please upload at least one identity document (Passport, Visa, or Aadhaar).")
                return

            with st.spinner("Executing OCR, ELA Tamper Forensics, GenAI Detection & Relational Graph Alignment..."):
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

                # Error Boundary: Biometrics & Live Selfie GenAI Artifact Detection
                face_res = None
                if s_file and primary_bytes:
                    try:
                        sb = s_file.read()
                        face_res = run_facial_biometric_verification(primary_bytes, sb)
                        ai_results["selfie"] = run_ai_generated_detection(sb)
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

            # Save results in session state for PDF/JSON export
            st.session_state["last_verification_data"] = doc_results[primary_key]
            st.session_state["last_risk_res"] = risk_res
            st.session_state["last_graph_res"] = graph_res

            # -----------------------------------------------------------------
            # Display Results Dashboard
            # -----------------------------------------------------------------
            st.markdown("---")
            st.subheader("📊 Executive Risk Score & Decision Verdict")

            score = risk_res["composite_risk_score"]
            verdict = risk_res["verdict"]
            tier = risk_res["risk_tier"]

            g_col1, g_col2 = st.columns([1.2, 1])
            with g_col1:
                fig_gauge = create_plotly_risk_gauge(score, verdict)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with g_col2:
                st.markdown("#### Operational Verdict")
                if verdict == "ACCEPT":
                    st.markdown('<div class="risk-badge-accept">✅ ACCEPT - STANDARD PASS</div>', unsafe_allow_html=True)
                elif verdict == "MANUAL_REVIEW":
                    st.markdown('<div class="risk-badge-review">⚠️ MANUAL SECONDARY REVIEW</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="risk-badge-reject">🚫 REJECT - INTERCEPT REQUIRED</div>', unsafe_allow_html=True)

                st.write(f"**Risk Severity Tier:** `{tier}`")
                st.write(f"**Relational Consistency:** `{graph_res['graph_consistency_score'] * 100:.0f}%`")
                st.write(f"**Documents Screened:** `{len(doc_results)}`")

            # Risk Breakdown Progress Bars
            st.markdown("#### Multi-Layer Risk Breakdown")
            lb = risk_res["layer_breakdown"]
            lcol1, lcol2, lcol3, lcol4 = st.columns(4)
            lcol1.progress(int(lb["traditional_forensics_score"]), text=f"Traditional Forensics: {lb['traditional_forensics_score']}%")
            lcol2.progress(int(lb["genai_artifacts_score"]), text=f"GenAI Synthetic: {lb['genai_artifacts_score']}%")
            lcol3.progress(int(lb["facial_biometrics_score"]), text=f"Facial Biometrics: {lb['facial_biometrics_score']}%")
            lcol4.progress(int(lb["relational_consistency_score"]), text=f"Relational Graph: {lb['relational_consistency_score']}%")

            # Human Readable Audit Logs
            with st.expander("📝 Human-Readable Risk Rule Audit Log", expanded=True):
                for log in risk_res["rule_audit_log"]:
                    if "[CRITICAL]" in log or "[HIGH]" in log:
                        st.error(log)
                    elif "[MEDIUM]" in log:
                        st.warning(log)
                    else:
                        st.success(log)

            # Detailed Exploration Tabs
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
                        st.write(f"**Verdict:** {ev.get('verdict')}")
                        st.write(f"**Suspicion:** {ev.get('tamper_suspicion')}")

            with tab_genai:
                st.markdown("### GenAI Synthetic Image Artifact Detection")
                g_cols = st.columns(len(ai_results))
                for idx, (dk, av) in enumerate(ai_results.items()):
                    with g_cols[idx]:
                        st.markdown(f"**{dk.upper()} AI Artifact Analysis**")
                        prob = av.get("ai_generated_probability", 0.0)
                        st.metric("AI Probability", f"{prob * 100:.1f}%")
                        st.write(f"**Primary Model Score:** {av.get('primary_model_score', 0.0):.4f}")
                        st.write(f"**Noise Heuristic Score:** {av.get('fallback_heuristic_score', 0.0):.4f}")
                        st.write(f"**Verdict:** {av.get('verdict')}")

            with tab_biometrics:
                st.markdown("### DeepFace Facial Biometrics Verification")
                if face_res:
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        st.metric("Face Match Verified", str(face_res.get("face_match")))
                        st.metric("Similarity Score", f"{face_res.get('similarity_score', 0.0) * 100:.1f}%")
                    with b_col2:
                        st.metric("Distance Metric", f"{face_res.get('distance', 1.0):.4f}")
                        st.write(f"**Status:** {face_res.get('status')}")
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

                with st.expander("Inspect Graph Nodes & Edges"):
                    st.json({"nodes": graph_res["nodes"], "edges": graph_res["edges"]})

            with tab_aadhaar:
                st.markdown("### UIDAI Privacy Compliance & Aadhaar Redaction")
                if "aadhaar" in doc_results:
                    a_res = doc_results["aadhaar"]
                    redacted_b64 = a_res.get("redacted_image_base64")
                    if redacted_b64:
                        r_img = decode_base64_image(redacted_b64)
                        if r_img:
                            st.image(r_img, caption="UIDAI Compliant Physical Masked Aadhaar (First 8 Digits Redacted)", width=450)
                    st.json(a_res.get("privacy_compliance", {}))
                else:
                    st.info("No Aadhaar document uploaded in this session.")

            # -----------------------------------------------------------------
            # Task 4: Documentation & Audit Export
            # -----------------------------------------------------------------
            st.markdown("---")
            st.subheader("📥 Export Forensic Audit Trail & Evidentiary Documentation")
            ex_col1, ex_col2 = st.columns(2)

            with ex_col1:
                json_data = json.dumps({
                    "document_analysis": doc_results[primary_key],
                    "relational_graph": graph_res,
                    "risk_assessment": risk_res
                }, indent=2)
                st.download_button(
                    label="📄 Download Complete Audit Trail (JSON)",
                    data=json_data,
                    file_name="forensic_audit_report.json",
                    mime="application/json",
                    use_container_width=True
                )

            with ex_col2:
                try:
                    pdf_bytes = generate_forensic_pdf(validation_data=doc_results[primary_key])
                    st.download_button(
                        label="📕 Download Forensic Inspection PDF Report",
                        data=pdf_bytes,
                        file_name="forensic_audit_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF Export Error: {str(e)}")

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

            st.markdown("---")
            fig_gauge = create_plotly_risk_gauge(risk_res['composite_risk_score'], risk_res['verdict'])
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.write(f"**Verdict:** {risk_res['verdict']} ({risk_res['risk_tier']})")
            st.json(ocr_res)

            # Export options
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.download_button(
                    label="📄 Download Audit JSON",
                    data=json.dumps(ocr_res, indent=2),
                    file_name="single_doc_audit.json",
                    mime="application/json",
                    use_container_width=True
                )
            with ex_col2:
                try:
                    pdf_bytes = generate_forensic_pdf(validation_data=ocr_res)
                    st.download_button(
                        label="📕 Download PDF Inspection Report",
                        data=pdf_bytes,
                        file_name="single_doc_audit.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF Export Error: {str(e)}")


if __name__ == "__main__":
    main()
