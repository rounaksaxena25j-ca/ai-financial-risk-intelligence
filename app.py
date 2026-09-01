import streamlit as st
import pandas as pd
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.units import mm

# ============================================================
# ============================================================
# FINANCIAL ENGINE IMPORTS
# ============================================================
from financial_engine.extraction import (
    extract_financial_data,
    detect_company_name,
)
from financial_engine.risk_engine import (
    generate_financial_intelligence,
)# ============================================================
# PAGE CONFIGURATION & STYLING
# ============================================================

st.set_page_config(
    page_title="AI Financial Risk Intelligence",
    page_icon="💡",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC !important; font-family: 'Inter', system-ui, sans-serif !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 3rem; max-width: 95% !important; }
    #MainMenu, footer, header { visibility: hidden; }

    /* Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, #0A1128 0%, #101F42 50%, #0F172A 100%);
        border-radius: 16px;
        padding: 24px 32px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
    }
    .hero-title { font-size: 2rem; font-weight: 800; color: #FFFFFF; }
    .hero-title-gradient {
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle { color: #94A3B8; font-size: 0.95rem; }

    /* Landing Card Styling */
    .landing-box {
        background: #FFFFFF;
        border: 2px dashed #CBD5E1;
        border-radius: 16px;
        padding: 40px;
        text-align: center;
        margin: 30px auto;
        max-width: 700px;
    }

    /* Health Cards Grid */
    .health-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-top: 10px;
        margin-bottom: 24px;
    }
    .health-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .health-title { font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase; }
    .health-value { font-size: 1.25rem; font-weight: 800; color: #0F172A; margin: 4px 0; }
    .status-pill {
        font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 12px; display: inline-block;
    }
    .pill-green { background: #DCFCE7; color: #166534; }
    .pill-yellow { background: #FEF9C3; color: #854D0E; }
    .pill-red { background: #FEE2E2; color: #991B1B; }

    /* Risk Box Cards */
    .risk-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .risk-high { border-top: 5px solid #DC2626; }
    .risk-moderate { border-top: 5px solid #EA580C; }
    .risk-minor { border-top: 5px solid #EAB308; }
    .risk-low { border-top: 5px solid #16A34A; }

    .risk-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .risk-card-title { font-weight: 700; font-size: 0.95rem; color: #0F172A; }
    .risk-card-desc { font-size: 0.8rem; color: #475569; margin-bottom: 8px; line-height: 1.3; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_ratio(a, b):
    try:
        if a is None or b is None or pd.isna(a) or pd.isna(b) or float(b) == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None

def yoy(current, previous):
    try:
        if current is None or previous is None or pd.isna(current) or pd.isna(previous) or float(previous) == 0:
            return None
        return ((float(current) - float(previous)) / abs(float(previous))) * 100
    except Exception:
        return None

def fmt_pct(value):
    if value is None or pd.isna(value): return "N/A"
    try: return f"{float(value):+.1f}%"
    except Exception: return "N/A"

def fmt_num(value):
    if value is None or pd.isna(value): return "N/A"
    try: return f"${float(value):,.2f}"
    except Exception: return "N/A"

def fmt_ratio(value):
    if value is None or pd.isna(value): return "N/A"
    try: return f"{float(value):.2f}x"
    except Exception: return "N/A"

def clean_pdf_text(value):
    if value is None: return "Not Available"
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def get_value(data, key):
    if not isinstance(data, dict): return None
    value = data.get(key)
    if value is None or pd.isna(value): return None
    try: return float(value)
    except Exception: return None

def calculate_change_label(change):
    if change is None: return "INSUFFICIENT DATA"
    if change > 10: return "SIGNIFICANT INCREASE"
    if change > 3: return "INCREASE"
    if change < -10: return "SIGNIFICANT DECREASE"
    if change < -3: return "DECREASE"
    return "STABLE"


# ============================================================
# PDF REPORT GENERATOR (SAFE TYPE-CHECKING)
# ============================================================

def create_pdf_report(company_name, financial_data, intelligence, health_score, trend_rows, ratio_rows, risks):
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=10)
    heading_style = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontSize=12, leading=16, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=8, leading=11, spaceAfter=4)
    small_style = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=7, leading=10)

    story = []
    story.append(Paragraph("AI FINANCIAL RISK INTELLIGENCE & AUDIT REPORT", title_style))
    story.append(Paragraph(f"Company Target: <b>{clean_pdf_text(company_name)}</b>", heading_style))
    story.append(Spacer(1, 8))

    overall_lvl = "HIGH"
    if isinstance(intelligence, dict):
        overall_risk = intelligence.get("overall_risk")
        if isinstance(overall_risk, dict):
            overall_lvl = overall_risk.get("level", "HIGH")
        elif isinstance(overall_risk, str):
            overall_lvl = overall_risk

    summary_table = Table(
        [
            [Paragraph("<b>Financial Health Score</b>", small_style), Paragraph("<b>Overall Risk Level</b>", small_style), Paragraph("<b>Status Assessment</b>", small_style)],
            [Paragraph(f"{health_score}/100", small_style), Paragraph(clean_pdf_text(overall_lvl), small_style), Paragraph("Requires Investigation", small_style)],
        ],
        colWidths=[55 * mm, 55 * mm, 55 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Key Financial Movements", heading_style))
    move_data = [["Metric", "Current", "Previous", "YoY Change", "Signal"]]
    for row in trend_rows:
        if isinstance(row, dict):
            move_data.append([
                clean_pdf_text(row.get("Metric")),
                clean_pdf_text(row.get("Current Year")),
                clean_pdf_text(row.get("Previous Year")),
                clean_pdf_text(row.get("Change")),
                clean_pdf_text(row.get("Signal")),
            ])
    t_move = Table(move_data, repeatRows=1, colWidths=[35 * mm, 32 * mm, 32 * mm, 28 * mm, 38 * mm])
    t_move.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))
    story.append(t_move)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Priority Risk Findings & Investigation Directives", heading_style))
    for r in risks:
        if isinstance(r, dict):
            r_title = clean_pdf_text(r.get("title", "Risk Item"))
            r_level = clean_pdf_text(r.get("level", "Unspecified"))
            r_why = clean_pdf_text(r.get("why_it_matters", "N/A"))
            r_check = clean_pdf_text(r.get("what_to_check", "N/A"))
            p_text = f"<b>[{r_level.upper()}] {r_title}</b><br/>• <i>Why Flagged:</i> {clean_pdf_text(r.get('flagged_reason'))}<br/>• <i>Impact:</i> {r_why}<br/>• <i>Audit Checkpoint:</i> {r_check}"
        else:
            p_text = f"<b>[FLAGGED RISK]</b> {clean_pdf_text(r)}"
        
        story.append(Paragraph(p_text, body_style))
        story.append(Spacer(1, 4))

    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# ============================================================
# STATE CONTROL: UPLOAD TRACKING
# ============================================================
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "analysis_in_progress" not in st.session_state:
    st.session_state.analysis_in_progress = False
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "company_name" not in st.session_state:
    st.session_state.company_name = None
if "financial_data" not in st.session_state:
    st.session_state.financial_data = None
if "validation_report" not in st.session_state:
    st.session_state.validation_report = None
if "intelligence" not in st.session_state:
    st.session_state.intelligence = None
# ============================================================# INTERFACE 1: INITIAL UPLOAD LANDING VIEW
# ============================================================
if not st.session_state.analysis_complete:
    st.markdown("""
    <style>
    /* ========================================================
       FIRST PAGE — HERO
       ======================================================== */
    .hero-v2 {
        position: relative;
        overflow: hidden;
        min-height: 345px;
        padding: 26px 42px 20px 42px;
        border-radius: 0 0 2px 2px;
        color: white;
        background:
            radial-gradient(circle at 78% 42%, rgba(35,118,255,.18), transparent 25%),
            linear-gradient(135deg, #061438 0%, #0A1D49 52%, #0B2B59 100%);
        box-shadow: 0 12px 35px rgba(8,28,65,.20);
        box-sizing: border-box;
    }
    .hero-v2:before {
        content: "";
        position: absolute;
        width: 420px;
        height: 420px;
        right: 60px;
        top: -180px;
        border-radius: 50%;
        border: 1px solid rgba(44,191,255,.12);
        box-shadow:
            0 0 0 35px rgba(44,191,255,.025),
            0 0 0 75px rgba(44,191,255,.02);
    }
    .brand-row-v2 {
        display: flex;
        align-items: center;
        gap: 12px;
        position: relative;
        z-index: 5;
    }
    .brand-shield-v2 {
        width: 35px;
        height: 39px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 21px;
        border-radius: 9px;
        background: linear-gradient(145deg,#1D78D7,#13C7D4);
        border: 1px solid rgba(255,255,255,.25);
        box-shadow: 0 0 18px rgba(19,199,212,.25);
    }
    .brand-name-v2 {
        font-size: 15px;
        font-weight: 800;
        letter-spacing: -.2px;
        color: #FFFFFF;
    }
    .enterprise-badge-v2 {
        margin-left: 8px;
        padding: 6px 11px;
        border-radius: 7px;
        background: #19BFF2;
        color: #05214B;
        font-size: 9px;
        font-weight: 900;
        letter-spacing: .4px;
    }
    .hero-actions-v2 {
        position: absolute;
        top: 26px;
        right: 42px;
        display: flex;
        gap: 12px;
        z-index: 6;
    }
    .hero-action-v2 {
        min-width: 150px;
        padding: 10px 15px;
        border-radius: 9px;
        background: rgba(43,78,145,.40);
        border: 1px solid rgba(108,157,238,.08);
        color: #FFFFFF;
        font-size: 10px;
        font-weight: 800;
        line-height: 13px;
    }
    .hero-action-v2 span {
        display: block;
        color: #9FB2D1;
        font-size: 8px;
        font-weight: 500;
    }
    .hero-content-v2 {
        position: relative;
        z-index: 4;
        margin-top: 44px;
        width: 57%;
    }
    .hero-heading-v2 {
        margin: 0;
        font-size: 35px;
        line-height: 1.14;
        font-weight: 850;
        letter-spacing: -.8px;
        color: #FFFFFF;
    }
    .hero-gradient-v2 {
        background: linear-gradient(90deg,#19E0E8 0%,#38B9FF 48%,#7778FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-sub-v2 {
        margin-top: 15px;
        color: #B3C3DC;
        font-size: 13px;
        line-height: 20px;
        max-width: 570px;
    }
    /* ========================================================
       HERO ANALYTICS ILLUSTRATION
       ======================================================== */
    .analytics-scene-v2 {
        position: absolute;
        right: 70px;
        top: 75px;
        width: 390px;
        height: 225px;
        z-index: 2;
    }
    .dashboard-panel-v2 {
        position: absolute;
        right: 35px;
        top: 10px;
        width: 270px;
        height: 170px;
        padding: 17px;
        border-radius: 13px;
        transform: perspective(700px) rotateY(-7deg) rotateX(2deg);
        background: linear-gradient(145deg,rgba(20,53,107,.95),rgba(12,35,77,.95));
        border: 1px solid rgba(86,158,241,.35);
        box-shadow: 0 18px 35px rgba(0,0,0,.28);
        box-sizing: border-box;
    }
    .chart-line-v2 {
        position: absolute;
        left: 25px;
        top: 55px;
        width: 130px;
        height: 65px;
        border-top: 3px solid #19D5EA;
        transform: skewY(-15deg) rotate(-7deg);
        box-shadow: 28px 17px 0 -26px #19D5EA,
                    58px 2px 0 -26px #19D5EA,
                    90px -20px 0 -26px #19D5EA,
                    120px -3px 0 -26px #19D5EA;
    }
    .bars-v2 {
        position: absolute;
        left: 28px;
        bottom: 20px;
        display: flex;
        align-items: end;
        gap: 9px;
        height: 57px;
    }
    .bar-v2 {
        width: 16px;
        background: linear-gradient(to top,#159CEB,#38D4F4);
        border-radius: 2px 2px 0 0;
        opacity: .9;
    }
    .bar-v2:nth-child(1) { height: 24px; }
    .bar-v2:nth-child(2) { height: 37px; }
    .bar-v2:nth-child(3) { height: 31px; }
    .bar-v2:nth-child(4) { height: 52px; }
    .donut-v2 {
        position: absolute;
        right: 31px;
        top: 42px;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        border: 12px solid #334A91;
        border-top-color: #7569F5;
        border-right-color: #22C8EE;
        box-sizing: border-box;
        transform: rotate(25deg);
    }
    .panel-lines-v2 {
        position: absolute;
        right: 25px;
        bottom: 27px;
        width: 65px;
    }
    .panel-lines-v2 div {
        height: 6px;
        margin-top: 7px;
        border-radius: 5px;
        background: #29467D;
    }
    .floating-tag-v2 {
        position: absolute;
        padding: 7px 11px;
        border-radius: 7px;
        background: rgba(8,32,70,.95);
        border: 1px solid rgba(25,205,234,.32);
        color: #18D9E7;
        font-size: 9px;
        font-weight: 800;
        box-shadow: 0 7px 18px rgba(0,0,0,.20);
    }
    .tag-risk-v2 {
        left: 0;
        top: 28px;
    }
    .tag-smart-v2 {
        right: -2px;
        top: 76px;
    }
    .tag-warning-v2 {
        left: 12px;
        bottom: 21px;
        color: #E7D34C;
        border-color: rgba(231,211,76,.35);
    }
    .shield-large-v2 {
        position: absolute;
        right: 25px;
        bottom: 1px;
        width: 58px;
        height: 67px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: linear-gradient(145deg,#1CD7DF,#12A9C5);
        clip-path: polygon(50% 0%,92% 15%,85% 70%,50% 100%,15% 70%,8% 15%);
        color: white;
        font-size: 27px;
        font-weight: 900;
        filter: drop-shadow(0 0 14px rgba(26,218,225,.25));
    }
    /* ========================================================
       HERO FEATURE ROW
       ======================================================== */
    .hero-features-v2 {
        position: absolute;
        left: 42px;
        bottom: 18px;
        display: grid;
        grid-template-columns: repeat(4, auto);
        z-index: 5;
    }
    .hero-feature-v2 {
        display: flex;
        align-items: center;
        gap: 9px;
        min-width: 165px;
        padding: 0 19px;
        border-right: 1px solid rgba(255,255,255,.14);
    }
    .hero-feature-v2:first-child {
        padding-left: 0;
    }
    .hero-feature-v2:last-child {
        border-right: 0;
    }
    .feature-icon-v2 {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        background: rgba(41,91,172,.35);
        color: #4CCBFF;
        font-size: 17px;
    }
    .feature-title-v2 {
        color: #FFFFFF;
        font-size: 10px;
        font-weight: 800;
        margin-bottom: 3px;
    }
    .feature-desc-v2 {
        color: #7F96B9;
        font-size: 8px;
        white-space: nowrap;
    }
    /* ========================================================
       UPLOAD SECTION
       ======================================================== */
    .upload-shell-v2 {
        margin: 0 2px;
        padding: 14px;
        background: #FFFFFF;
        border: 1px solid #E0E7F1;
        border-radius: 13px;
        box-shadow: 0 7px 25px rgba(18,42,76,.07);
    }
    .upload-inner-v2 {
        min-height: 104px;
        display: grid;
        grid-template-columns: 1.35fr 1fr .72fr;
        align-items: center;
        gap: 18px;
        padding: 15px;
        border: 2px dashed #78A9FF;
        border-radius: 10px;
        box-sizing: border-box;
    }
    .upload-left-v2 {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .upload-icon-v2 {
        width: 57px;
        height: 57px;
        flex: 0 0 57px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        background: #EEF4FF;
        color: #2563EB;
        font-size: 28px;
    }
    .upload-title-v2 {
        color: #0D1B35;
        font-size: 15px;
        font-weight: 850;
        margin-bottom: 8px;
    }
    .upload-text-v2 {
        color: #70809A;
        font-size: 10px;
        line-height: 17px;
    }
    .upload-safe-v2 {
        height: 74px;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        border-radius: 8px;
        background: linear-gradient(135deg,#EDFCFB,#E9F9F8);
        box-sizing: border-box;
    }
    .safe-icon-v2 {
        color: #0CA6A6;
        font-size: 25px;
    }
    .safe-title-v2 {
        color: #087C7D;
        font-size: 10px;
        font-weight: 850;
        margin-bottom: 4px;
    }
    .safe-text-v2 {
        color: #6E9294;
        font-size: 8px;
        line-height: 12px;
    }
    /* ========================================================
       TIP
       ======================================================== */
    .tip-v2 {
        margin: 12px 2px 18px 2px;
        padding: 10px 15px;
        border-radius: 6px;
        background: #EAF3FF;
        border: 1px solid #D2E5FF;
        color: #2665B8;
        font-size: 9px;
    }
    /* ========================================================
       WORKFLOW
       ======================================================== */
    .workflow-v2 {
        margin: 0 2px 14px 2px;
        padding: 24px 28px 26px 28px;
        border: 1px solid #DCE5F0;
        border-radius: 16px;
        background: #FFFFFF;
        box-shadow: 0 8px 24px rgba(16,42,86,.055);
        box-sizing: border-box;
    }
    .workflow-heading-v2 {
        color: #102A56;
        font-size: 16px;
        font-weight: 800;
        margin-bottom: 22px;
        letter-spacing: -0.2px;
    }
    .workflow-grid-v2 {
        display: grid;
        grid-template-columns: 1fr 55px 1fr 55px 1fr;
        align-items: center;
        width: 100%;
    }
    .workflow-step-v2 {
        display: flex;
        align-items: center;
        gap: 15px;
        min-width: 0;
    }
    .workflow-icon-v2 {
        width: 66px;
        height: 66px;
        flex: 0 0 66px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 15px;
        font-size: 30px;
        box-sizing: border-box;
    }
    .workflow-upload-v2 {
        background: #F0EDFF;
        color: #6657D9;
    }
    .workflow-risk-v2 {
        background: #FFF0F2;
        color: #E34A62;
    }
    .workflow-investigate-v2 {
        background: #E9F8F7;
        color: #16979B;
    }
    .step-number-v2 {
        position: relative;
        top: -27px;
        left: -7px;
        width: 23px;
        height: 23px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: -23px;
        border-radius: 50%;
        background: #FFFFFF;
        color: #6254D8;
        font-size: 10px;
        font-weight: 800;
        box-shadow: 0 2px 7px rgba(16,42,86,.12);
        z-index: 2;
    }
    .workflow-title-v2 {
        color: #172B4D;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 6px;
        white-space: nowrap;
    }
    .workflow-desc-v2 {
        color: #71809A;
        font-size: 10px;
        line-height: 15px;
    }
    .workflow-tag-v2 {
        display: inline-block;
        margin-top: 8px;
        padding: 5px 9px;
        border-radius: 8px;
        background: #F0EDFF;
        color: #6254D8;
        font-size: 8px;
        font-weight: 800;
    }
    .workflow-tag-risk-v2 {
        background: #FFECEF;
        color: #D83D59;
    }
    .workflow-tag-investigate-v2 {
        background: #E5F6F4;
        color: #138C91;
    }
    .workflow-arrow-v2 {
        text-align: center;
        color: #9AA9BC;
        font-size: 25px;
        font-weight: 400;
    }
    .bottom-strip-v2 {
        margin: 0 2px;
        padding: 14px 16px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        border: 1px solid #DCE5F0;
        border-radius: 13px;
        background: #FFFFFF;
        box-shadow: 0 6px 20px rgba(16,42,86,.045);
        box-sizing: border-box;
    }    .bottom-item-v2 {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 16px;
        border-right: 1px solid #E6EBF2;
    }
    .bottom-item-v2:first-child {
        padding-left: 4px;
    }
    .bottom-item-v2:last-child {
        border-right: 0;
    }
    .bottom-icon-v2 {
        font-size: 14px;
    }
    .bottom-title-v2 {
        color: #27344C;
        font-size: 9px;
        font-weight: 850;
        margin-bottom: 3px;
    }
    .bottom-desc-v2 {
        color: #7A879C;
        font-size: 7px;
        white-space: nowrap;
    }
    /* ========================================================
       RESPONSIVE
       ======================================================== */
    @media (max-width: 1100px) {
        .hero-v2 {
            min-height: 390px;
        }
        .analytics-scene-v2 {
            right: 15px;
            opacity: .65;
        }
        .hero-content-v2 {
            width: 62%;
        }
        .hero-features-v2 {
            left: 30px;
        }
        .hero-feature-v2 {
            min-width: 145px;
        }
        .upload-inner-v2 {
            grid-template-columns: 1fr;
        }
        .workflow-grid-v2 {
            grid-template-columns: 1fr;
            gap: 15px;
        }
        .workflow-arrow-v2 {
            display: none;
        }
    }
</style>
    """, unsafe_allow_html=True)
    # ========================================================
    # HERO
    # ========================================================
    st.markdown("""
    <div class="hero-v2">
        <div class="brand-row-v2">
            <div class="brand-shield-v2">🛡️</div>
            <div class="brand-name-v2">AI Financial Risk Intelligence</div>
            <div class="enterprise-badge-v2">ENTERPRISE V2.0</div>
        </div>
        <div class="hero-actions-v2">
            <div class="hero-action-v2">
                🔒 &nbsp; Enterprise Security
                <span>Your data is private & secure</span>
            </div>
            <div class="hero-action-v2">
                ▶ &nbsp; How It Works
            </div>
        </div>
        <div class="hero-content-v2">
            <h1 class="hero-heading-v2">
                Turn Financial Data into<br>
                <span class="hero-gradient-v2">Actionable Risk Intelligence</span>
            </h1>
            <div class="hero-sub-v2">
                Upload your financial statements and our AI will identify risks,
                highlight what matters, and guide you on what to investigate.
            </div>
        </div>
        <div class="analytics-scene-v2">
            <div class="floating-tag-v2 tag-risk-v2">
                Risk Detection
            </div>
            <div class="dashboard-panel-v2">
                <div class="chart-line-v2"></div>
                <div class="bars-v2">
                    <div class="bar-v2"></div>
                    <div class="bar-v2"></div>
                    <div class="bar-v2"></div>
                    <div class="bar-v2"></div>
                </div>
                <div class="donut-v2"></div>
                <div class="panel-lines-v2">
                    <div></div>
                    <div></div>
                    <div></div>
                </div>
            </div>
            <div class="floating-tag-v2 tag-smart-v2">
                Smart Analysis
            </div>
            <div class="floating-tag-v2 tag-warning-v2">
                Early Warnings
            </div>
            <div class="shield-large-v2">✓</div>
        </div>
        <div class="hero-features-v2">
            <div class="hero-feature-v2">
                <div class="feature-icon-v2">📄</div>
                <div>
                    <div class="feature-title-v2">Multi-Year Analysis</div>
                    <div class="feature-desc-v2">5+ years of financial data</div>
                </div>
            </div>
            <div class="hero-feature-v2">
                <div class="feature-icon-v2">🛡️</div>
                <div>
                    <div class="feature-title-v2">Risk Identification</div>
                    <div class="feature-desc-v2">AI-powered risk detection</div>
                </div>
            </div>
            <div class="hero-feature-v2">
                <div class="feature-icon-v2">📄</div>
                <div>
                    <div class="feature-title-v2">Smart Investigation</div>
                    <div class="feature-desc-v2">Guided audit checkpoints</div>
                </div>
            </div>
            <div class="hero-feature-v2">
                <div class="feature-icon-v2">⬇</div>
                <div>
                    <div class="feature-title-v2">Executive Reports</div>
                    <div class="feature-desc-v2">PDF & insights ready</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # ========================================================
    # UPLOAD CARD — LARGE COLORFUL CENTERED VERSION
    # ========================================================
    st.markdown("""
    <style>
    .upload-card-final {
        margin: 22px auto 20px auto;
        padding: 34px 40px;
        max-width: 1050px;
        min-height: 245px;
        border-radius: 20px;
        background:
            linear-gradient(135deg, #EEF5FF 0%, #F8FBFF 48%, #EAF3FF 100%);
        border: 1px solid #BFD5FF;
        box-shadow:
            0 12px 32px rgba(30, 88, 170, 0.12),
            inset 0 1px 0 rgba(255,255,255,0.9);
        text-align: center;
        box-sizing: border-box;
    }
    .upload-icon-final {
        width: 64px;
        height: 64px;
        margin: 0 auto 14px auto;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #2563EB, #4F8CFF);
        color: white;
        font-size: 34px;
        font-weight: 700;
        box-shadow: 0 8px 20px rgba(37,99,235,0.25);
    }
    .upload-title-final {
        color: #102A56;
        font-size: 23px;
        font-weight: 850;
        margin-bottom: 7px;
    }
    .upload-subtitle-final {
        color: #60789F;
        font-size: 13px;
        line-height: 20px;
        margin-bottom: 18px;
    }
    /* ========================================================
       CLEAN STREAMLIT UPLOADER
       ======================================================== */
    [data-testid="stFileUploader"] {
        width: 100% !important;
        max-width: 1050px !important;
        margin: 10px auto 20px auto !important;
        padding: 0 !important;
        box-sizing: border-box !important;
        position: relative !important;
        z-index: 30 !important;
    }
    [data-testid="stFileUploader"] section {
        width: 100% !important;
        min-height: 58px !important;
        border: 0 !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 auto !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stFileUploader"] section > div {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        width: 100% !important;
        min-height: 58px !important;
        height: 58px !important;
        border: 0 !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stFileUploaderDropzone"] > div {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
    }
    [data-testid="stFileUploader"] button {
        display: block !important;
        width: 230px !important;
        height: 52px !important;
        margin: 0 auto !important;
        border-radius: 12px !important;
        border: 1px solid #2563EB !important;
        background: linear-gradient(135deg,#2563EB,#3B82F6) !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 750 !important;
        box-shadow: 0 7px 18px rgba(37,99,235,.25) !important;
    }
    [data-testid="stFileUploader"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 22px rgba(37,99,235,.32) !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploader"] label {
        display: none !important;
    }
    [data-testid="stFileUploader"] small {
        text-align: center !important;
        width: 100% !important;
    }
    <div class="upload-card-final">
        <div class="upload-icon-final">⇧</div>
        <div class="upload-title-final">
            Upload Financial Statements
        </div>
        <div class="upload-subtitle-final">
            Upload Balance Sheet, Profit & Loss, Cash Flow Statement
            <br>
            or any financial workbook

        </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload Financial Statements",
        type=["xlsx", "xls", "csv"],
        key="initial_uploader",
        label_visibility="collapsed"
    )    # ========================================================
    # TIP
    # ========================================================
    st.markdown("""
    <div class="tip-v2">
        ℹ️ &nbsp; <b>Tip:</b> For best results, upload complete financial statements with 3-5 years of data.
    </div>
    """, unsafe_allow_html=True)
    # ========================================================
    # WORKFLOW
    # ========================================================
    st.markdown("""
    <div class="workflow-v2">
        <div class="workflow-heading-v2">
            Simple, Powerful, Risk-Focused Workflow
        </div>
        <div class="workflow-grid-v2">
            <div class="workflow-step-v2">
                <div class="workflow-icon-v2 workflow-upload-v2">☑️</div>
                <div>
                    <div class="workflow-title-v2">
                        <span class="step-number-v2">1</span>
                        Upload
                    </div>
                    <div class="workflow-desc-v2">
                        Upload your financial statements<br>
                        and supporting documents.
                    </div>
                    <span class="workflow-tag-v2">Secure & Encrypted</span>
                </div>
            </div>
            <div class="workflow-arrow-v2">→</div>
            <div class="workflow-step-v2">
                <div class="workflow-icon-v2 workflow-risk-v2">◉</div>
                <div>
                    <div class="workflow-title-v2">
                        <span class="step-number-v2">2</span>
                        Identify Risk
                    </div>
                    <div class="workflow-desc-v2">
                        AI analyzes your data and identifies<br>
                        key financial risks and anomalies.
                    </div>
                    <span class="workflow-tag-v2 workflow-tag-risk-v2">AI-Powered Analysis</span>
                </div>
            </div>
            <div class="workflow-arrow-v2">→</div>
            <div class="workflow-step-v2">
                <div class="workflow-icon-v2 workflow-investigate-v2">⌕</div>
                <div>
                    <div class="workflow-title-v2">
                        <span class="step-number-v2">3</span>
                        Investigate
                    </div>
                    <div class="workflow-desc-v2">
                        Understand why each risk matters<br>
                        and what you should check next.
                    </div>
                    <span class="workflow-tag-v2 workflow-tag-investigate-v2">Actionable Insights</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # ========================================================
    # BOTTOM FEATURE STRIP
    # ========================================================
    st.markdown("""
    <div class="bottom-strip-v2">
        <div class="bottom-item-v2">
            <div class="bottom-icon-v2">⚡</div>
            <div>
                <div class="bottom-title-v2">Early Warning System</div>
                <div class="bottom-desc-v2">Detect risks before they impact</div>
            </div>
        </div>
        <div class="bottom-item-v2">
            <div class="bottom-icon-v2">🎯</div>
            <div>
                <div class="bottom-title-v2">Focus on What Matters</div>
                <div class="bottom-desc-v2">Prioritized risks, not data overload</div>
            </div>
        </div>
        <div class="bottom-item-v2">
            <div class="bottom-icon-v2">[AI]</div>
            <div>
                <div class="bottom-title-v2">AI + Expert Logic</div>
                <div class="bottom-desc-v2">Powered by financial intelligence</div>
            </div>
        </div>
        <div class="bottom-item-v2">
            <div class="bottom-icon-v2">📊</div>
            <div>
                <div class="bottom-title-v2">Board-Ready Reports</div>
                <div class="bottom-desc-v2">Download detailed PDF reports</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # ========================================================
    # REAL UPLOAD HANDLING — VISIBLE HOMEPAGE LOADING STATE
    # ========================================================
    if uploaded_file is not None:
        # ----------------------------------------------------
        # FIRST RUN:
        # Store file and request a visible loading screen.
        # ----------------------------------------------------
        if not st.session_state.analysis_in_progress:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.analysis_in_progress = True
            st.session_state.analysis_complete = False
            st.rerun()
        # ----------------------------------------------------
        # SECOND RUN:
        # The complete designed homepage is already rendered
        # above this point. Show the loading panel and give
        # Streamlit a separate run before starting analysis.
        # ----------------------------------------------------
        if (
            st.session_state.analysis_in_progress
            and not st.session_state.analysis_complete
        ):
            st.markdown("""
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: min(560px, calc(100vw - 40px));
                padding: 32px 28px;
                border-radius: 16px;
                background: #FFFFFF;
                border: 1px solid #DCE5F0;
                box-shadow: 0 15px 45px rgba(18,42,76,.18);
                text-align: center;
                z-index: 9999;
            ">
                <div style="
                    font-size: 34px;
                    margin-bottom: 14px;
                    display: inline-block;
                    animation: financialSpin 1.2s linear infinite;
                ">
                    🔄
                </div>
                <div style="
                    color:#10203C;
                    font-size:18px;
                    font-weight:850;
                    margin-bottom:7px;
                ">
                    Analyzing Your Financial Statements
                </div>
                <div style="
                    color:#71809A;
                    font-size:10px;
                    line-height:16px;
                ">
                    Extracting financial data, identifying risks,
                    and preparing your financial intelligence...
                </div>
            </div>
            <style>
            @keyframes financialSpin {
                from {
                    transform: rotate(0deg);
                }
                to {
                    transform: rotate(360deg);
                }
            }
            </style>
            """, unsafe_allow_html=True)
            # Allow the browser to visibly render the homepage
            # and loading state before analysis begins.
            import time
            time.sleep(1.5)
            # ------------------------------------------------
            # ACTUAL EXISTING ANALYSIS ENGINE
            # ------------------------------------------------
            try:
                with st.spinner("Analyzing financial statements..."):
                    uploaded_file = st.session_state.uploaded_file
                    uploaded_file.seek(0)
                    if uploaded_file.name.lower().endswith(".csv"):
                        df = pd.read_csv(
                            uploaded_file,
                            header=None
                        )
                        workbook_data = {
                            "Sheet1": df
                        }
                    else:
                        excel = pd.ExcelFile(uploaded_file)
                        workbook_data = {
                            sheet: pd.read_excel(
                                uploaded_file,
                                sheet_name=sheet,
                                header=None
                            )
                            for sheet in excel.sheet_names
                        }
                    company_name = detect_company_name(
                        workbook_data,
                        uploaded_file.name
                    )
                    financial_data, validation_report = (
                        extract_financial_data(workbook_data)
                    )
                    intelligence = generate_financial_intelligence(
                        financial_data
                    )
                    # Save existing analysis results.
                    st.session_state.company_name = company_name
                    st.session_state.financial_data = financial_data
                    st.session_state.validation_report = validation_report
                    st.session_state.intelligence = intelligence
                    st.session_state.analysis_complete = True
                    st.session_state.analysis_in_progress = False
            except Exception as e:
                st.session_state.analysis_in_progress = False
                st.session_state.analysis_complete = False
                st.error(f"Analysis engine error: {e}")
                st.stop()
            # Only now move to the existing dashboard.
            st.rerun()
    st.stop()
# ============================================================
# INTERFACE 2: ANALYSIS DASHBOARD (ORIGINAL SINGLE-PAGE LAYOUT)
# ============================================================# ============================================================
# INTERFACE 2: ANALYSIS DASHBOARD (ORIGINAL SINGLE-PAGE LAYOUT)
# ============================================================

col_top_left, col_top_right = st.columns([1, 2])

with col_top_left:
    st.caption("📁 Currently Selected File:")
    re_uploaded_file = st.file_uploader(
        "Replace File", 
        type=["xlsx", "xls", "csv"], 
        key="top_left_uploader",
        label_visibility="collapsed"
    )
    if re_uploaded_file is not None:
        st.session_state.uploaded_file = re_uploaded_file

with col_top_right:
    st.markdown("""
    <div class="hero-container" style="padding: 12px 20px; margin-bottom:0px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size: 1.2rem; font-weight:800; color:#FFF;">AI Financial Risk Intelligence</div>
                <div style="font-size: 0.8rem; color:#94A3B8;">Analysis Interface Active</div>
            </div>
            <span style="background:rgba(255,255,255,0.1); padding:4px 10px; border-radius:12px; color:#38BDF8; font-size:0.75rem; font-weight:700;">
                ENTERPRISE V2.0
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 12px 0;'/>", unsafe_allow_html=True)

uploaded_file = st.session_state.uploaded_file

# ============================================================
# USE ANALYSIS RESULTS ALREADY GENERATED ON HOMEPAGE
# ============================================================
uploaded_file = st.session_state.uploaded_file
company_name = st.session_state.company_name
financial_data = st.session_state.financial_data
validation_report = st.session_state.validation_report
intelligence = st.session_state.intelligence
if financial_data is None or intelligence is None:
    st.error("Analysis results are not available.")
    st.stop()

revenue = get_value(financial_data, "revenue")
previous_revenue = get_value(financial_data, "previous_revenue")
net_profit = get_value(financial_data, "net_profit")
previous_net_profit = get_value(financial_data, "previous_net_profit")
receivables = get_value(financial_data, "trade_receivables")
previous_receivables = get_value(financial_data, "previous_trade_receivables")
inventory = get_value(financial_data, "inventory")
previous_inventory = get_value(financial_data, "previous_inventory")
current_assets = get_value(financial_data, "current_assets")
current_liabilities = get_value(financial_data, "current_liabilities")
debt = get_value(financial_data, "total_debt")
equity = get_value(financial_data, "total_equity")
ocf = get_value(financial_data, "operating_cash_flow")

revenue_growth = yoy(revenue, previous_revenue)
current_ratio = safe_ratio(current_assets, current_liabilities)
profit_margin = safe_ratio(net_profit, revenue)
debt_equity = safe_ratio(debt, equity)
health_score = 68


# ------------------------------------------------------------
# STEP 3: ANALYSIS WORKSPACE
# ------------------------------------------------------------
# ============================================================
# DISPLAY HELPERS — UI ONLY
# ============================================================
def fmt_inr(value):
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    sign = "-" if value < 0 else ""
    value = abs(value)
    # Indian numbering format
    formatted = f"{value:,.0f}"
    return f"{sign}₹{formatted}"
def movement_color(change):
    if change is None:
        return "#64748B"
    try:
        change = float(change)
    except (TypeError, ValueError):
        return "#64748B"
    return "#16A34A" if change >= 0 else "#DC2626"
def risk_color(level):
    level = str(level).upper()
    if "HIGH" in level or "CRITICAL" in level:
        return "#DC2626"
    if "MEDIUM" in level or "MODERATE" in level:
        return "#D97706"
    if "LOW" in level or "HEALTHY" in level:
        return "#16A34A"
    return "#2563EB"
# ============================================================
# ANALYSIS NAVIGATION
# ============================================================
st.markdown("""
<style>
/* ============================================================
/* ============================================================
   DASHBOARD — POLISHED UI
   ============================================================

/* LOCKED MAIN NAVIGATION */

div[data-baseweb="tab-list"] {
    width: 100% !important;
    display: flex !important;
    gap: 14px !important;
    padding: 0 !important;
    margin: 18px 0 34px 0 !important;
    background: transparent !important;
}

div[data-baseweb="tab-list"] > button[data-baseweb="tab"] {
    flex: 1 1 0 !important;
    width: 33.333% !important;
    min-width: 0 !important;
    min-height: 82px !important;
    height: 82px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 24px !important;
    margin: 0 !important;
    background: #FFFFFF !important;
    color: #172B4D !important;
    border: 1px solid #D7E0EA !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 14px rgba(15,23,42,.07) !important;
    font-size: 20px !important;
    font-weight: 800 !important;
}

div[data-baseweb="tab-list"] > button[data-baseweb="tab"] p {
    margin: 0 !important;
    padding: 0 !important;
    color: #172B4D !important;
    font-size: 20px !important;
    font-weight: 800 !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
}

div[data-baseweb="tab-list"] > button[aria-selected="true"] {
    background: #EFF6FF !important;
    border: 2px solid #2563EB !important;
    color: #1D4ED8 !important;
    box-shadow: 0 6px 18px rgba(37,99,235,.14) !important;
}

div[data-baseweb="tab-list"] > button[aria-selected="true"] p {
    color: #1D4ED8 !important;
    font-weight: 900 !important;
}

div[data-baseweb="tab-highlight"] {
    display: none !important;
}

@media (max-width: 900px) {
    div[data-baseweb="tab-list"] {
        gap: 8px !important;
    }

    div[data-baseweb="tab-list"] > button[data-baseweb="tab"] {
        min-height: 64px !important;
        height: 64px !important;
        padding: 0 10px !important;
    }

    div[data-baseweb="tab-list"] > button[data-baseweb="tab"] p {
        font-size: 14px !important;
    }
}

/* SECTION HEADINGS */
.dashboard-section-title {
    font-size: 24px !important;
    font-weight: 850 !important;
    color: #102A56 !important;
    margin: 30px 0 6px 0 !important;
    letter-spacing: -.3px !important;
}

.dashboard-section-subtitle {
    font-size: 14px !important;
    color: #64748B !important;
    margin-bottom: 20px !important;
    line-height: 21px !important;
}

/* EXECUTIVE DASHBOARD */
.executive-card {
    padding: 26px 28px !important;
    border-radius: 18px !important;
    background: linear-gradient(135deg,#F8FBFF,#EEF5FF) !important;
    border: 1px solid #D6E4F5 !important;
    box-shadow: 0 8px 24px rgba(30,70,120,.07) !important;
    min-height: 155px !important;
}

.executive-label {
    font-size: 12px !important;
    font-weight: 800 !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    letter-spacing: .6px !important;
    margin-bottom: 10px !important;
}

.executive-value {
    font-size: 35px !important;
    font-weight: 900 !important;
    color: #102A56 !important;
    line-height: 1.15 !important;
}

.executive-description {
    margin-top: 10px !important;
    font-size: 13px !important;
    line-height: 20px !important;
    color: #607089 !important;
}

/* FINANCIAL HEALTH COMPONENTS */
.health-detail-grid {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 20px !important;
    margin-top: 10px !important;
}
.health-detail-card {
    position: relative !important;
    padding: 25px 26px 24px 26px !important;
    border-radius: 19px !important;
    background: #FFFFFF !important;
    border: 1px solid #DFE7F1 !important;
    box-shadow: 0 7px 20px rgba(17,37,67,.06) !important;
    min-height: 215px !important;
    overflow: hidden !important;
    cursor: pointer !important;
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease !important;
}
.health-detail-card::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 5px !important;
    transition: height .22s ease !important;
}
.health-detail-card:hover {
    transform: translateY(-8px) scale(1.025) !important;
    box-shadow: 0 20px 42px rgba(15,23,42,.16) !important;
    z-index: 5 !important;
}
.health-detail-card:hover::before {
    height: 7px !important;
}
/* LIQUIDITY — BLUE */
.health-detail-card:nth-child(1) {
    background: linear-gradient(145deg,#F8FBFF,#EEF6FF) !important;
    border-color: #CFE1FA !important;
}
.health-detail-card:nth-child(1)::before {
    background: #2563EB !important;
}
.health-detail-card:nth-child(1):hover {
    border-color: #60A5FA !important;
    box-shadow: 0 20px 42px rgba(37,99,235,.20) !important;
}
/* PROFITABILITY — RED */
.health-detail-card:nth-child(2) {
    background: linear-gradient(145deg,#FFF9F9,#FFF0F2) !important;
    border-color: #F3D0D7 !important;
}
.health-detail-card:nth-child(2)::before {
    background: #DC2626 !important;
}
.health-detail-card:nth-child(2):hover {
    border-color: #F87171 !important;
    box-shadow: 0 20px 42px rgba(220,38,38,.20) !important;
}
/* SOLVENCY — GREEN */
.health-detail-card:nth-child(3) {
    background: linear-gradient(145deg,#F8FFFB,#ECFDF3) !important;
    border-color: #CBEBD7 !important;
}
.health-detail-card:nth-child(3)::before {
    background: #16A34A !important;
}
.health-detail-card:nth-child(3):hover {
    border-color: #4ADE80 !important;
    box-shadow: 0 20px 42px rgba(22,163,74,.20) !important;
}
/* WORKING CAPITAL — ORANGE */
.health-detail-card:nth-child(4) {
    background: linear-gradient(145deg,#FFFCF7,#FFF7E8) !important;
    border-color: #F2DFC0 !important;
}
.health-detail-card:nth-child(4)::before {
    background: #D97706 !important;
}
.health-detail-card:nth-child(4):hover {
    border-color: #F59E0B !important;
    box-shadow: 0 20px 42px rgba(217,119,6,.20) !important;
}
/* OPERATING CASH FLOW — PURPLE */
.health-detail-card:nth-child(5) {
    background: linear-gradient(145deg,#FBF9FF,#F3EEFF) !important;
    border-color: #DED3F7 !important;
}
.health-detail-card:nth-child(5)::before {
    background: #7C3AED !important;
}
.health-detail-card:nth-child(5):hover {
    border-color: #A78BFA !important;
    box-shadow: 0 20px 42px rgba(124,58,237,.20) !important;
}
/* REVENUE — CYAN */
.health-detail-card:nth-child(6) {
    background: linear-gradient(145deg,#F7FEFF,#EAFBFC) !important;
    border-color: #C9EAED !important;
}
.health-detail-card:nth-child(6)::before {
    background: #0891B2 !important;
}
.health-detail-card:nth-child(6):hover {
    border-color: #22D3EE !important;
    box-shadow: 0 20px 42px rgba(8,145,178,.20) !important;
}
.health-detail-title {
    font-size: 15px !important;
    font-weight: 850 !important;
    color: #334155 !important;
    margin-bottom: 10px !important;
}
.health-detail-value {
    font-size: 34px !important;
    font-weight: 950 !important;
    line-height: 1.15 !important;
    margin: 7px 0 11px 0 !important;
    letter-spacing: -.6px !important;
    transition: transform .22s ease !important;
}
.health-detail-card:hover .health-detail-value {
    transform: scale(1.05) !important;
}
.health-detail-status {
    display: inline-block !important;
    padding: 6px 12px !important;
    border-radius: 999px !important;
    font-size: 10px !important;
    font-weight: 850 !important;
    margin-bottom: 13px !important;
}
.health-detail-description {
    font-size: 12px !important;
    line-height: 19px !important;
    color: #64748B !important;
}
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 16px !important;
}

.movement-grid {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 18px !important;
}
.movement-card { background: linear-gradient(145deg,#F8FBFF,#EEF5FF) !important; border-color:#D6E4F5 !important; } .movement-card {
    position: relative !important;
    overflow: hidden !important;
    padding: 24px 26px !important;
    border-radius: 18px !important;
    background: #FFFFFF !important;
    border: 1px solid #DFE7F1 !important;
    box-shadow: 0 7px 22px rgba(17,37,67,.055) !important;
    min-height: 185px !important;
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease !important;
}
.movement-card::before {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    bottom: 0 !important;
    width: 5px !important;
    background: #2563EB !important;
}
/* REVENUE — BLUE */
.movement-colored:nth-child(1) {
    background: linear-gradient(145deg,#F8FBFF,#EEF5FF) !important;
    border-color: #D6E4F5 !important;
}
.movement-card:nth-child(1)::before {
    background: #2563EB !important;
}
/* NET PROFIT — RED */
.movement-colored:nth-child(2) {
    background: linear-gradient(145deg,#FFF9FA,#FFF0F2) !important;
    border-color: #F3D4DA !important;
}
.movement-card:nth-child(2)::before {
    background: #DC2626 !important;
}
/* TRADE RECEIVABLES — CYAN */
.movement-colored:nth-child(3) {
    background: linear-gradient(145deg,#F7FEFF,#EAFBFC) !important;
    border-color: #C9EAED !important;
}
.movement-card:nth-child(3)::before {
    background: #0891B2 !important;
}
/* INVENTORY — ORANGE */
.movement-colored:nth-child(4) {
    background: linear-gradient(145deg,#FFFCF7,#FFF7E8) !important;
    border-color: #F2DFC0 !important;
}
.movement-card:nth-child(4)::before {
    background: #D97706 !important;
}
/* TOTAL DEBT — PURPLE */
.movement-colored:nth-child(5) {
    background: linear-gradient(145deg,#FBF9FF,#F3EEFF) !important;
    border-color: #DED3F7 !important;
}
.movement-card:nth-child(5)::before {
    background: #7C3AED !important;
}
/* TOTAL EQUITY — GREEN */
.movement-colored:nth-child(6) {
    background: linear-gradient(145deg,#F8FFFB,#ECFDF3) !important;
    border-color: #CBEBD7 !important;
}
.movement-card:nth-child(6)::before {
    background: #16A34A !important;
}
/* OPERATING CASH FLOW — PINK */
.movement-colored:nth-child(7) {
    background: linear-gradient(145deg,#FFF8FB,#FFF0F6) !important;
    border-color: #F3D4E1 !important;
}
.movement-card:nth-child(7)::before {
    background: #E11D48 !important;
}
/* HOVER / POP */
.movement-card:hover {
    transform: translateY(-7px) scale(1.012) !important;
    box-shadow: 0 20px 42px rgba(17,37,67,.14) !important;
    border-color: #B8C7D9 !important;
}
.movement-name {
    font-size: 15px !important;
    font-weight: 850 !important;
    color: #334155 !important;
    margin-bottom: 15px !important;
}
.movement-values {
    display: flex !important;
    gap: 42px !important;
    align-items: flex-end !important;
}
.movement-current {
    font-size: 31px !important;
    font-weight: 950 !important;
    line-height: 1.12 !important;
    letter-spacing: -.7px !important;
    transition: transform .22s ease !important;
}
.movement-card:hover .movement-current {
    transform: scale(1.045) !important;
}
.movement-card:nth-child(1) .movement-current {
    color: #2563EB !important;
}
.movement-card:nth-child(2) .movement-current {
    color: #DC2626 !important;
}
.movement-card:nth-child(3) .movement-current {
    color: #0891B2 !important;
}
.movement-card:nth-child(4) .movement-current {
    color: #D97706 !important;
}
.movement-card:nth-child(5) .movement-current {
    color: #7C3AED !important;
}
.movement-card:nth-child(6) .movement-current {
    color: #16A34A !important;
}
.movement-card:nth-child(7) .movement-current {
    color: #E11D48 !important;
}
.movement-previous {
    font-size: 17px !important;
    font-weight: 750 !important;
    color: #64748B !important;
    line-height: 1.2 !important;
}
.movement-change {
    margin-top: 15px !important;
    font-size: 16px !important;
    font-weight: 950 !important;
    line-height: 1.2 !important;
}
.movement-signal {
    margin-top: 6px !important;
    font-size: 12px !important;
    line-height: 17px !important;
    color: #64748B !important;
}/* ============================================================
   KEY FINANCIAL MOVEMENTS — INDIVIDUAL CARD COLORS
   ============================================================ */
.movement-colored.revenue {
    background: linear-gradient(145deg,#F8FBFF,#EEF5FF) !important;
    border-color:#C9DBF5 !important;
}
.movement-colored.net-profit {
    background: linear-gradient(145deg,#FFF8F8,#FFECEE) !important;
    border-color:#F3C9D0 !important;
}
.movement-colored.trade-receivables {
    background: linear-gradient(145deg,#F4FEFF,#E6FAFC) !important;
    border-color:#BFE7EC !important;
}
.movement-colored.inventory {
    background: linear-gradient(145deg,#FFFCF5,#FFF3D9) !important;
    border-color:#F0D8A8 !important;
}
.movement-colored.total-debt {
    background: linear-gradient(145deg,#FBF8FF,#F1EAFE) !important;
    border-color:#DCCEF3 !important;
}
.movement-colored.total-equity {
    background: linear-gradient(145deg,#F6FFF9,#E8F8EE) !important;
    border-color:#C6E5D0 !important;
}
.movement-colored.operating-cash-flow {
    background: linear-gradient(145deg,#FFF8FB,#FFEAF2) !important;
    border-color:#F1C9D8 !important;
}
/* Individual accent borders */
.movement-colored.revenue { border-left:5px solid #2563EB !important; }
.movement-colored.net-profit { border-left:5px solid #DC2626 !important; }
.movement-colored.trade-receivables { border-left:5px solid #0891B2 !important; }
.movement-colored.inventory { border-left:5px solid #D97706 !important; }
.movement-colored.total-debt { border-left:5px solid #7C3AED !important; }
.movement-colored.total-equity { border-left:5px solid #16A34A !important; }
.movement-colored.operating-cash-flow { border-left:5px solid #E11D48 !important; }
/* Pop / hover */
.movement-colored {
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease !important;
}
.movement-colored:hover {
    transform: translateY(-7px) scale(1.012) !important;
}
.movement-colored.revenue:hover {
    box-shadow:0 20px 42px rgba(37,99,235,.20) !important;
}
.movement-colored.net-profit:hover {
    box-shadow:0 20px 42px rgba(220,38,38,.20) !important;
}
.movement-colored.trade-receivables:hover {
    box-shadow:0 20px 42px rgba(8,145,178,.20) !important;
}
.movement-colored.inventory:hover {
    box-shadow:0 20px 42px rgba(217,119,6,.20) !important;
}
.movement-colored.total-debt:hover {
    box-shadow:0 20px 42px rgba(124,58,237,.20) !important;
}
.movement-colored.total-equity:hover {
    box-shadow:0 20px 42px rgba(22,163,74,.20) !important;
}
.movement-colored.operating-cash-flow:hover {
    box-shadow:0 20px 42px rgba(225,29,72,.20) !important;
}
/* RATIO CARDS */
.ratio-grid {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 18px !important;
}

.ratio-card {
    padding: 25px !important;
    border-radius: 18px !important;
    background: #FFFFFF !important;
    border: 1px solid #DDE6F1 !important;
    box-shadow: 0 8px 24px rgba(17,37,67,.055) !important;
}

.ratio-name {
    font-size: 15px !important;
    font-weight: 800 !important;
    color: #64748B !important;
}

.ratio-value {
    font-size: 34px !important;
    font-weight: 900 !important;
    color: #2563EB !important;
    margin: 10px 0 !important;
}

.ratio-target {
    font-size: 12px !important;
    color: #64748B !important;
}

/* ============================================================
   RATIO CARD COLORS + HOVER / POP
   ============================================================ */
.ratio-card {
    position: relative !important;
    overflow: hidden !important;
    padding: 24px !important;
    border-radius: 17px !important;
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease !important;
}
.ratio-card::before {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    width: 5px !important;
    height: 100% !important;
    border-radius: 17px 0 0 17px !important;
}
.ratio-current-ratio {
    background: linear-gradient(145deg,#F8FBFF,#EEF5FF) !important;
    border-color: #D6E4F5 !important;
}
.ratio-current-ratio::before {
    background: #2563EB !important;
}
.ratio-current-ratio:hover {
    transform: translateY(-7px) scale(1.012) !important;
    border-color: #60A5FA !important;
    box-shadow: 0 20px 42px rgba(37,99,235,.20) !important;
}
.ratio-debt-to-equity {
    background: linear-gradient(145deg,#FBF9FF,#F3EEFF) !important;
    border-color: #DED3F7 !important;
}
.ratio-debt-to-equity::before {
    background: #7C3AED !important;
}
.ratio-debt-to-equity:hover {
    transform: translateY(-7px) scale(1.012) !important;
    border-color: #A78BFA !important;
    box-shadow: 0 20px 42px rgba(124,58,237,.20) !important;
}
.ratio-profit-margin {
    background: linear-gradient(145deg,#F7FEFF,#EAFBFC) !important;
    border-color: #C9EAED !important;
}
.ratio-profit-margin::before {
    background: #0891B2 !important;
}
.ratio-profit-margin:hover {
    transform: translateY(-7px) scale(1.012) !important;
    border-color: #22D3EE !important;
    box-shadow: 0 20px 42px rgba(8,145,178,.20) !important;
}
.ratio-card:hover .ratio-value {
    transform: scale(1.06) !important;
}
.ratio-value {
    transition: transform .22s ease !important;
}
.ratio-target {
    display: inline-block !important;
    margin-top: 5px !important;
    padding: 6px 10px !important;
    border-radius: 999px !important;
    background: rgba(255,255,255,.72) !important;
    border: 1px solid rgba(148,163,184,.22) !important;
}
/* DETAILED RATIO TABLE */
div[data-testid="stDataFrame"] {
    border: 1px solid #D8E2EF !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 10px 28px rgba(17,37,67,.07) !important;
    background: #FFFFFF !important;
    margin-top: 10px !important;
}
/* PREMIUM DETAILED RATIO TABLE */
div[data-testid="stDataFrame"] {
    border: 1px solid #D8E2EF !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 10px 28px rgba(17,37,67,.07) !important;
    background: #FFFFFF !important;
    margin-top: 12px !important;
}
div[data-testid="stDataFrame"] > div {
    border-radius: 16px !important;
}
/* DETAILED RATIO TABLE — PREMIUM */
.ratio-table-wrap {
    margin-top: 18px !important;
    border: 1px solid #DCE5F0 !important;
    border-radius: 18px !important;
    overflow: hidden !important;
    background: #FFFFFF !important;
    box-shadow: 0 10px 30px rgba(17,37,67,.07) !important;
}
.ratio-table {
    width: 100% !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
.ratio-table th {
    background: linear-gradient(135deg,#F1F5FB,#E8EEF7) !important;
    color: #183153 !important;
    font-size: 12px !important;
    font-weight: 850 !important;
    text-transform: uppercase !important;
    letter-spacing: .7px !important;
    padding: 16px 18px !important;
    text-align: left !important;
    border-bottom: 1px solid #D8E2EE !important;
}
.ratio-table td {
    padding: 17px 18px !important;
    font-size: 14px !important;
    font-weight: 650 !important;
    color: #475569 !important;
    border-bottom: 1px solid #EDF1F6 !important;
    background: #FFFFFF !important;
    transition: all .18s ease !important;
}
.ratio-table tr:last-child td {
    border-bottom: none !important;
}
.ratio-table tbody tr:hover td {
    background: #F8FAFD !important;
    transform: translateX(2px) !important;
}
.ratio-table .ratio-label {
    color: #243B5A !important;
    font-weight: 800 !important;
}
.ratio-table .ratio-value {
    font-size: 15px !important;
    font-weight: 900 !important;
}
.ratio-table .ratio-target {
    color: #64748B !important;
    font-weight: 700 !important;
}
.ratio-table .ratio-indicator {
    display: inline-block !important;
    width: 8px !important;
    height: 8px !important;
    border-radius: 50% !important;
    margin-right: 9px !important;
    vertical-align: middle !important;
}
/* ============================================================
   RISK & INVESTIGATION — PREMIUM USP DESIGN
   ============================================================ */
.risk-card {
    position: relative !important;
    min-height: 158px !important;
    padding: 18px 18px 14px 18px !important;
    border-radius: 15px !important;
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 7px 20px rgba(15,23,42,.07) !important;
    overflow: hidden !important;
    transition: all .22s ease !important;
}
.risk-card::before {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    width: 100% !important;
    height: 4px !important;
    background: #EF4444 !important;
}
.risk-card:hover {
    transform: translateY(-6px) !important;
    box-shadow: 0 18px 35px rgba(15,23,42,.13) !important;
    border-color: #CBD5E1 !important;
}
.risk-card-header {
    display: flex !important;
    align-items: center !important;
    gap: 9px !important;
    margin-bottom: 13px !important;
}
.risk-card-header span:first-child {
    width: 34px !important;
    height: 34px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 50% !important;
    background: #FEF2F2 !important;
    font-size: 17px !important;
}
.risk-card-header span:last-child {
    padding: 4px 9px !important;
    border-radius: 999px !important;
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    letter-spacing: .3px !important;
}
.risk-card-title {
    font-size: 15px !important;
    font-weight: 900 !important;
    color: #172B4D !important;
    margin-bottom: 6px !important;
    line-height: 20px !important;
}
.risk-card-desc {
    font-size: 11px !important;
    line-height: 17px !important;
    color: #64748B !important;
    min-height: 34px !important;
}
/* RISK COLOR VARIANTS */
.risk-high::before {
    background: #EF4444 !important;
}
.risk-high .risk-card-header span:first-child {
    background: #FEE2E2 !important;
}
.risk-medium::before {
    background: #F59E0B !important;
}
.risk-medium .risk-card-header span:first-child {
    background: #FEF3C7 !important;
}
.risk-low::before {
    background: #0EA5E9 !important;
}
.risk-low .risk-card-header span:first-child {
    background: #E0F2FE !important;
}
/* INVESTIGATION SECTION */
.risk-investigation-shell {
    margin-top: 22px !important;
    border-radius: 18px !important;
}
.investigation-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-bottom: 15px !important;
}
.investigation-title {
    font-size: 21px !important;
    font-weight: 900 !important;
    color: #172B4D !important;
}
.investigation-subtitle {
    font-size: 12px !important;
    color: #64748B !important;
    margin-top: 4px !important;
}
/* STREAMLIT EXPANDER = INVESTIGATION PANEL */
div[data-testid="stExpander"] {
    border: 1px solid #DCE5F0 !important;
    border-radius: 14px !important;
    margin-bottom: 12px !important;
    background: #FFFFFF !important;
    box-shadow: 0 5px 18px rgba(15,23,42,.045) !important;
    overflow: hidden !important;
    transition: all .2s ease !important;
}
div[data-testid="stExpander"]:hover {
    border-color: #CBD5E1 !important;
    box-shadow: 0 10px 25px rgba(15,23,42,.08) !important;
}
div[data-testid="stExpander"] summary {
    padding: 15px 18px !important;
    font-weight: 800 !important;
    color: #243B5A !important;
}
div[data-testid="stExpander"] summary:hover {
    background: #F8FAFC !important;
}
/* EXPANDED INVESTIGATION CONTENT */
div[data-testid="stExpander"] [data-testid="stVerticalBlock"] {
    gap: 10px !important;
}
.investigation-panel {
    padding: 4px !important;
}
.investigation-risk-summary {
    padding: 16px !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg,#FFF7F7,#FFFDFD) !important;
    border: 1px solid #FECACA !important;
    margin-bottom: 12px !important;
}
.investigation-risk-summary-title {
    font-size: 12px !important;
    font-weight: 900 !important;
    color: #DC2626 !important;
    text-transform: uppercase !important;
    letter-spacing: .5px !important;
    margin-bottom: 7px !important;
}
.investigation-evidence {
    padding: 14px 16px !important;
    border-radius: 12px !important;
    background: #F8FAFC !important;
    border: 1px solid #E2E8F0 !important;
}
.investigation-evidence-title {
    font-size: 12px !important;
    font-weight: 850 !important;
    color: #334155 !important;
    margin-bottom: 6px !important;
}
.investigation-check {
    padding: 12px 14px !important;
    border-radius: 10px !important;
    background: #F0FDF4 !important;
    border: 1px solid #BBF7D0 !important;
    color: #166534 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    margin-top: 8px !important;
}
/* MOBILE */
@media (max-width: 1100px) {
    .risk-card {
        min-height: 145px !important;
    }
}
/* ============================================================
   FINAL RISK CARD OVERRIDE — USP
   ============================================================ */
.risk-card {
    position: relative !important;
    padding: 20px !important;
    min-height: 175px !important;
    border-radius: 18px !important;
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,.08) !important;
    overflow: hidden !important;
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease !important;
}
.risk-card::before {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    width: 100% !important;
    height: 5px !important;
}
.risk-card:hover {
    transform: translateY(-8px) scale(1.015) !important;
    box-shadow: 0 20px 40px rgba(15,23,42,.15) !important;
}
/* HIGH */
.risk-high {
    background: linear-gradient(145deg,#FFF8F8,#FFFFFF) !important;
    border-color: #FECACA !important;
}
.risk-high::before {
    background: #DC2626 !important;
}
.risk-high:hover {
    border-color: #F87171 !important;
    box-shadow: 0 22px 42px rgba(220,38,38,.18) !important;
}
/* MEDIUM */
.risk-medium {
    background: linear-gradient(145deg,#FFFCF5,#FFFFFF) !important;
    border-color: #FDE68A !important;
}
.risk-medium::before {
    background: #D97706 !important;
}
.risk-medium:hover {
    border-color: #F59E0B !important;
    box-shadow: 0 22px 42px rgba(217,119,6,.18) !important;
}
/* LOW */
.risk-low {
    background: linear-gradient(145deg,#F7FCFF,#FFFFFF) !important;
    border-color: #BAE6FD !important;
}
.risk-low::before {
    background: #0284C7 !important;
}
.risk-low:hover {
    border-color: #38BDF8 !important;
    box-shadow: 0 22px 42px rgba(2,132,199,.18) !important;
}
/* HEADER */
.risk-card-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-bottom: 15px !important;
}
.risk-card-header span:first-child {
    width: 38px !important;
    height: 38px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 11px !important;
    font-size: 19px !important;
}
.risk-high .risk-card-header span:first-child {
    background: #FEE2E2 !important;
}
.risk-medium .risk-card-header span:first-child {
    background: #FEF3C7 !important;
}
.risk-low .risk-card-header span:first-child {
    background: #E0F2FE !important;
}
/* LEVEL BADGE */
.risk-card-header span:last-child {
    padding: 5px 10px !important;
    border-radius: 999px !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    letter-spacing: .35px !important;
    text-transform: uppercase !important;
}
.risk-high .risk-card-header span:last-child {
    color: #B91C1C !important;
    background: #FEE2E2 !important;
}
.risk-medium .risk-card-header span:last-child {
    color: #B45309 !important;
    background: #FEF3C7 !important;
}
.risk-low .risk-card-header span:last-child {
    color: #0369A1 !important;
    background: #E0F2FE !important;
}
/* TITLE */
.risk-card-title {
    font-size: 16px !important;
    font-weight: 900 !important;
    color: #172B4D !important;
    line-height: 21px !important;
    margin-bottom: 8px !important;
}
/* DESCRIPTION */
.risk-card-desc {
    font-size: 11.5px !important;
    line-height: 18px !important;
    color: #64748B !important;
}
/* REAL INVESTIGATE BUTTON */
div.stButton > button {
    width: 100% !important;
    min-height: 38px !important;
    margin-top: 14px !important;
    border-radius: 10px !important;
    border: 1px solid #D8E1EC !important;
    background: #F8FAFC !important;
    color: #2563EB !important;
    font-size: 12px !important;
    font-weight: 850 !important;
    transition: all .2s ease !important;
}
div.stButton > button:hover {
    background: #EFF6FF !important;
    border-color: #93C5FD !important;
    color: #1D4ED8 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 18px rgba(37,99,235,.12) !important;
}
/* PDF BUTTON */
div.stDownloadButton > button {
    min-height: 52px !important;
    border-radius: 11px !important;
    font-size: 15px !important;
    font-weight: 800 !important;
    border: 1px solid #CBD5E1 !important;
}

@media (max-width: 900px) {
    .health-detail-grid,
    .ratio-grid {
        grid-template-columns: 1fr !important;
    }

    .movement-grid {
        grid-template-columns: 1fr !important;
    }

    button[data-baseweb="tab"],
    button[data-baseweb="tab"] p {
        font-size: 14px !important;
    }
}
</style>
""", unsafe_allow_html=True)
# ============================================================
# BUILD DATA
# ============================================================
summary_text = "Analysis completed."
if isinstance(intelligence, dict):
    summary_text = intelligence.get(
        "management_summary",
        "Analysis completed."
    )
overall = intelligence.get("overall_risk", {}) if isinstance(intelligence, dict) else {}
overall_level = overall.get("level", "NOT AVAILABLE")
trend_metrics = {
    "Revenue": "revenue",
    "Net Profit": "net_profit",
    "Trade Receivables": "trade_receivables",
    "Inventory": "inventory",
    "Total Debt": "total_debt",
    "Total Equity": "total_equity",
    "Operating Cash Flow": "operating_cash_flow",
}
trend_rows = []
for display_name, key in trend_metrics.items():
    cur = get_value(financial_data, key)
    prev = get_value(financial_data, f"previous_{key}")
    chg = yoy(cur, prev)
    trend_rows.append({
        "Metric": display_name,
        "Current Year": fmt_num(cur),
        "Previous Year": fmt_num(prev),
        "Change": fmt_pct(chg),
        "Signal": calculate_change_label(chg),
        "_current": cur,
        "_previous": prev,
        "_change": chg,
    })
ratio_rows = [
    {
        "Ratio": "Current Ratio",
        "Value": fmt_ratio(current_ratio),
        "Target": "> 1.5x"
    },
    {
        "Ratio": "Debt to Equity",
        "Value": fmt_ratio(debt_equity),
        "Target": "< 1.0x"
    },
    {
        "Ratio": "Profit Margin",
        "Value": fmt_pct(
            profit_margin * 100
            if profit_margin is not None
            else None
        ),
        "Target": "> 10%"
    },
]
raw_risks = (
    intelligence.get("risks", {})
    if isinstance(intelligence, dict)
    else {}
)
risks_list = []
if isinstance(raw_risks, dict):
    for risk_name, risk_data in raw_risks.items():
        if not isinstance(risk_data, dict):
            continue
        level = str(
            risk_data.get(
                "level",
                "NOT AVAILABLE"
            )
        ).upper()
        if level == "HIGH":
            badge = "🔴"
            color_class = "risk-high"
        elif level == "MEDIUM":
            badge = "🟡"
            color_class = "risk-medium"
        elif level == "LOW":
            badge = "🟢"
            color_class = "risk-low"
        else:
            badge = "⚪"
            color_class = "risk-unavailable"
        evidence = risk_data.get(
            "evidence",
            "Insufficient financial data to reliably assess this area."
        )
        financial_impact = risk_data.get(
            "financial_impact",
            "Cannot determine financial impact from the available information."
        )
        recommended_action = risk_data.get(
            "recommended_action",
            "Provide the missing financial information for a reliable assessment."
        )
        risks_list.append(
            {
                "title": risk_name,
                "badge": badge,
                "level": level,
                "color_class": color_class,
                "flagged_reason": evidence,
                "evidence": evidence,
                "what_changed": evidence,
                "why_it_matters": financial_impact,
                "implications": financial_impact,
                "what_to_check": recommended_action,
                "documents_required": {
    "Liquidity Risk": [
        "Bank Statements",
        "Cash Flow Statement",
        "Short-Term Borrowing Schedule"
    ],
    "Collection Risk": [
        "Aged Receivables Ledger",
        "Customer Credit Policy",
        "Top Customer Invoices"
    ],
    "Inventory Risk": [
        "Inventory Ageing Report",
        "Inventory Valuation Working",
        "Physical Stock Count Report"
    ],
    "Leverage Risk": [
        "Loan Schedules",
        "Debt Repayment Schedule",
        "Loan / Debt Covenant Agreements"
    ],
    "Profitability Risk": [
        "Detailed Profit & Loss",
        "Cost / Expense Break-up",
        "Gross Margin Analysis"
    ],
    "Cash-Flow Risk": [
        "Cash Flow Statement",
        "Bank Statements",
        "Working Capital Movement Schedule"
    ],
    "Earnings Quality Risk": [
        "Cash Flow Statement",
        "Aged Receivables Ledger",
        "Working Capital Movement Schedule"
    ]
}.get(risk_name, [])
            }
        )# ============================================================
# PDF — CREATED ONCE, AVAILABLE INSIDE DASHBOARD
# ============================================================
pdf_bytes = create_pdf_report(
    company_name=company_name,
    financial_data=financial_data,
    intelligence=intelligence,
    health_score=health_score,
    trend_rows=trend_rows,
    ratio_rows=ratio_rows,
    risks=risks_list
)
# ============================================================
# HORIZONTAL TABS
# ============================================================
# ============================================================
# CUSTOM MAIN NAVIGATION
# ============================================================

if "active_analysis_tab" not in st.session_state:
    st.session_state.active_analysis_tab = "dashboard"

st.markdown("""
<style>
.custom-nav-title {
    font-size: 12px;
    font-weight: 800;
    color: #64748B;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin: 6px 0 10px 2px;
}

div[data-testid="stHorizontalBlock"]:has(.custom-nav-marker) {
    gap: 14px !important;
}

.custom-nav-marker {
    display: none;
}

.custom-nav-card {
    width: 100%;
    min-height: 82px;
    border: 1px solid #D7E0EA;
    border-radius: 14px;
    background: #FFFFFF;
    box-shadow: 0 4px 14px rgba(15,23,42,.07);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 800;
    color: #172B4D;
}

.custom-nav-active {
    background: #EFF6FF;
    border: 2px solid #2563EB;
    color: #1D4ED8;
    box-shadow: 0 6px 18px rgba(37,99,235,.14);
}

.custom-nav-subtitle {
    text-align: center;
    font-size: 11px;
    color: #64748B;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="custom-nav-title">Financial Analysis</div>',
    unsafe_allow_html=True
)

nav1, nav2, nav3 = st.columns(3, gap="medium")

with nav1:
    if st.button(
        "📊  Dashboard",
        key="custom_nav_dashboard",
        use_container_width=True
    ):
        st.session_state.active_analysis_tab = "dashboard"
        st.rerun()

with nav2:
    if st.button(
        "📈  Ratio Analysis",
        key="custom_nav_ratio",
        use_container_width=True
    ):
        st.session_state.active_analysis_tab = "ratio"
        st.rerun()

with nav3:
    if st.button(
        "🚨  Risk & Investigation",
        key="custom_nav_risk",
        use_container_width=True
    ):
        st.session_state.active_analysis_tab = "risk"
        st.rerun()

# Active-state styling
st.markdown(
    f"""
    <style>
    button[kind="secondary"] {{
        min-height: 82px !important;
        border-radius: 14px !important;
        border: 1px solid #D7E0EA !important;
        background: #FFFFFF !important;
        color: #172B4D !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 14px rgba(15,23,42,.07) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ============================================================
# ACTIVE SECTION
# ============================================================
# ============================================================
# TAB 1 — DASHBOARD
# ============================================================
if st.session_state.active_analysis_tab == "dashboard":
    # --------------------------------------------------------
    # EXECUTIVE DASHBOARD HEADER
    # --------------------------------------------------------
    dash_head_left, dash_head_right = st.columns([4.5, 1])
    with dash_head_left:
        st.markdown(
            f"""
            <div class="dashboard-section-title">
                🎯 Executive Dashboard: {company_name}
            </div>
            <div class="dashboard-section-subtitle">
                High-level financial health and management decision view.
            </div>
            """,
            unsafe_allow_html=True
        )
    with dash_head_right:
        st.download_button(
            label="📄 Download PDF",
            data=pdf_bytes,
            file_name=f"{company_name.replace(' ', '_')}_Risk_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    # --------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------
    revenue_change = yoy(
        revenue,
        previous_revenue
    )
    ocf_previous = get_value(
        financial_data,
        "previous_operating_cash_flow"
    )
    ocf_change = yoy(
        ocf,
        ocf_previous
    )
    overall_color = risk_color(overall_level)
    exec_c1, exec_c2 = st.columns(2)
    with exec_c1:
        st.markdown(
            f"""
            <div class="executive-card">
                <div class="executive-label">
                    OVERALL ASSESSMENT
                </div>
                <div class="executive-value"
                     style="color:{overall_color};">
                    {overall_level}
                </div>
                <div class="executive-description">
                    {summary_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with exec_c2:
        revenue_signal_color = movement_color(revenue_change)
        ocf_signal_color = movement_color(ocf_change)
        st.markdown(
            f"""
            <div class="executive-card">
                <div class="executive-label">
                    KEY FINANCIAL SIGNALS
                </div>
                <div class="signal-row">
                    <span>📉 Revenue movement</span>
                    <strong style="color:{revenue_signal_color};">
                        {fmt_pct(revenue_change)}
                    </strong>
                </div>
                <div class="signal-row">
                    <span>💵 Operating cash flow</span>
                    <strong style="color:{ocf_signal_color};">
                        {fmt_pct(ocf_change)}
                    </strong>
                </div>
                <div class="executive-description">
                    🔎 Receivables, liquidity and cash conversion
                    require attention.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    # --------------------------------------------------------
    # FINANCIAL HEALTH COMPONENTS
    # --------------------------------------------------------
    st.markdown(
        """
        <div class="dashboard-section-title">
            🏥 Financial Health Components
        </div>
        <div class="dashboard-section-subtitle">
            Detailed assessment of liquidity, profitability, solvency,
            working capital, cash generation and revenue strength.
        </div>
        """,
        unsafe_allow_html=True
    )
    working_capital = (
        current_assets - current_liabilities
        if current_assets is not None
        and current_liabilities is not None
        else None
    )
    health_cards = [
        (
            "💧",
            "Liquidity",
            fmt_ratio(current_ratio),
            "#2563EB",
            "Moderate Risk",
            "Measures the company's ability to meet short-term obligations using current assets."
        ),
        (
            "💰",
            "Profitability",
            fmt_pct(
                profit_margin * 100
                if profit_margin is not None
                else None
            ),
            "#DC2626",
            "Margin Compression",
            "Shows the profit generated from revenue. Negative or declining margins require attention."
        ),
        (
            "🛡️",
            "Solvency",
            fmt_ratio(debt_equity),
            "#16A34A",
            "Leverage Position",
            "Compares total debt with shareholder equity and indicates financial leverage."
        ),
        (
            "🔄",
            "Working Capital",
            fmt_inr(working_capital),
            "#D97706",
            "Working Capital Position",
            "Current assets less current liabilities, indicating the company's operating liquidity buffer."
        ),
        (
            "💵",
            "Operating Cash Flow",
            fmt_inr(ocf),
            "#7C3AED",
            "Cash Conversion",
            "Cash generated from core operations. Divergence from accounting profit can be an important risk signal."
        ),
        (
            "📈",
            "Revenue",
            fmt_inr(revenue),
            "#0891B2",
            "Current Revenue",
            "Current-period revenue used as the base for assessing growth, margins and working-capital movements."
        ),
    ]
    # FIRST ROW
    h1, h2, h3 = st.columns(3)
    for col, card in zip(
        [h1, h2, h3],
        health_cards[:3]
    ):
        icon, title, value, color, status, description = card
        with col:
            st.markdown(
                f"""
                <div class="health-detail-card health-{title.lower().replace(" ", "-")}">
                    <div class="health-detail-title">
                        <span class="health-icon">{icon}</span>
                        {title}
                    </div>
                    <div class="health-detail-value"
                         style="color:{color};">
                        {value}
                    </div>
                    <div class="health-detail-status"
                         style="
                            color:{color};
                            background:{color}18;
                         ">
                        {status}
                    </div>
                    <div class="health-detail-description">
                        {description}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    st.markdown("<div style='height:14px;'></div>",
                unsafe_allow_html=True)
    # SECOND ROW
    h4, h5, h6 = st.columns(3)
    for col, card in zip(
        [h4, h5, h6],
        health_cards[3:]
    ):
        icon, title, value, color, status, description = card
        with col:
            st.markdown(
                f"""
                <div class="health-detail-card health-{title.lower().replace(" ", "-")}">
                    <div class="health-detail-title">
                        <span class="health-icon">{icon}</span>
                        {title}
                    </div>
                    <div class="health-detail-value"
                         style="color:{color};">
                        {value}
                    </div>
                    <div class="health-detail-status"
                         style="
                            color:{color};
                            background:{color}18;
                         ">
                        {status}
                    </div>
                    <div class="health-detail-description">
                        {description}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    # --------------------------------------------------------
    # KEY FINANCIAL MOVEMENTS
    # --------------------------------------------------------
    st.markdown(
        """
        <div class="dashboard-section-title">
            📊 Key Financial Movements
        </div>
        <div class="dashboard-section-subtitle">
            Current-year performance compared with the previous year.
            Monetary values are presented in Indian Rupees.
        </div>
        """,
        unsafe_allow_html=True
    )
    movement_columns = [
        st.columns(3),
        st.columns(3),
        st.columns(3)
    ]
    for index, row in enumerate(trend_rows):
        current = row["_current"]
        previous = row["_previous"]
        change = row["_change"]
        change_col = movement_color(change)
        metric_class = row["Metric"].lower().replace(" ", "-")
        if change is None:
            change_text = "N/A"
        else:
            change_text = f"{change:+.1f}%"
        col = movement_columns[index // 3][index % 3]
        with col:
            st.markdown(
                f"""
                <div class="movement-card movement-colored {metric_class}">
                    <div class="movement-name">
                        {row["Metric"]}
                    </div>
                    <div class="movement-current"
                         style="color:#2563EB;">
                        {fmt_inr(current)}
                    </div>
                    <div class="movement-previous">
                        Previous Year:
                        <span style="color:#475569;">
                            {fmt_inr(previous)}
                        </span>
                    </div>
                    <div class="movement-change"
                         style="color:{change_col};">
                        {change_text}
                        <span style="
                            font-size:12px;
                            font-weight:700;
                            color:#64748B;
                        ">
                            YoY
                        </span>
                    </div>
                    <div class="movement-signal">
                        {row["Signal"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )# TAB 2 — RATIO ANALYSIS
# ============================================================
if st.session_state.active_analysis_tab == "ratio":
    st.markdown(
        """
        <div class="dashboard-section-title">
            📈 Ratio Analysis
        </div>
        <div class="dashboard-section-subtitle">
            Core financial ratios with current values and benchmark targets.
        </div>
        """,
        unsafe_allow_html=True
    )
    ratio_values = [
        (
            "Current Ratio",
            fmt_ratio(current_ratio),
            "> 1.5x",
            "#2563EB"
        ),
        (
            "Debt to Equity",
            fmt_ratio(debt_equity),
            "< 1.0x",
            "#7C3AED"
        ),
        (
            "Profit Margin",
            fmt_pct(
                profit_margin * 100
                if profit_margin is not None
                else None
            ),
            "> 10%",
            "#0891B2"
        ),
    ]
    st.markdown(
        '<div class="ratio-grid">',
        unsafe_allow_html=True
    )
    for name, value, target, color in ratio_values:
        st.markdown(
            f"""
            <div class="ratio-card ratio-{name.lower().replace(" ", "-")}">
                <div class="ratio-name">
                    {name}
                </div>
                <div class="ratio-value"
                     style="color:{color};">
                    {value}
                </div>
                <div class="ratio-target">
                    Benchmark target: <b>{target}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown("## 📋 Detailed Ratio Analysis")
    st.markdown('<div class="ratio-table-wrap"><table class="ratio-table"><thead><tr><th>Ratio</th><th>Current Value</th><th>Benchmark</th></tr></thead><tbody>' + ''.join('<tr><td class="ratio-label"><span class="ratio-indicator" style="background:' + {"Current Ratio":"#2563EB","Debt to Equity":"#7C3AED","Profit Margin":"#0891B2"}.get(r["Ratio"],"#2563EB") + ';"></span>' + str(r["Ratio"]) + '</td><td class="ratio-value" style="color:' + {"Current Ratio":"#2563EB","Debt to Equity":"#7C3AED","Profit Margin":"#0891B2"}.get(r["Ratio"],"#2563EB") + ';">' + str(r["Value"]) + '</td><td class="ratio-target">' + str(r["Target"]) + '</td></tr>' for r in ratio_rows) + '</tbody></table></div>', unsafe_allow_html=True)
# ============================================================
# TAB 3 — RISK & INVESTIGATION
# ============================================================
if st.session_state.active_analysis_tab == "risk":
    st.markdown(
        """
        <div class="risk-heading">
            🚨 Risk & Investigation
        </div>
        <div class="dashboard-section-subtitle">
            Prioritized financial risks first. Detailed investigation
            appears only when the user opens a risk.
        </div>
        """,
        unsafe_allow_html=True
    )
    if risks_list:
        cols = st.columns(len(risks_list))
        for idx, r in enumerate(risks_list):
            with cols[idx]:
                if isinstance(r, dict):
                    badge = r.get("badge", "🔴")
                    level = r.get("level", "High")
                    title = r.get("title", "Risk Item")
                    reason = r.get(
                        "flagged_reason",
                        "Flagged by analysis engine."
                    )
                    normalized_level = str(
                        r.get(
                            "level",
                            "NOT AVAILABLE"
                        )
                    ).upper().strip()
                    if normalized_level == "HIGH":
                        badge = "🔴"
                        color_class = "risk-high"
                    elif normalized_level == "MEDIUM":
                        badge = "🟡"
                        color_class = "risk-medium"
                    elif normalized_level == "LOW":
                        badge = "🟢"
                        color_class = "risk-low"
                    else:
                        badge = "⚪"
                        color_class = "risk-unavailable"
                        level = "NOT AVAILABLE"
                else:
                    badge = "🔴"
                    level = "Attention Required"
                    title = str(r)
                    reason = "Financial variance flagged."
                    color_class = "risk-high"
                st.markdown(
                    f"""
                    <div class="risk-card {color_class}">
                        <div class="risk-card-header">
                            <span style="font-size:1.1rem;">
                                {badge}
                            </span>
                            <span style="
                                font-size:.75rem;
                                font-weight:700;
                                color:#64748B;">
                                {level}
                            </span>
                        </div>
                        <div class="risk-card-title">
                            {title}
                        </div>
                        <div class="risk-card-desc">
                            {reason}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(
                    "🔎 Investigate →",
                    key=f"investigate_risk_{idx}",
                    use_container_width=True
                ):
                    st.session_state.selected_risk = r
                    st.rerun()

    else:
        st.success(
            "No structured financial risks were identified."
        )
    st.markdown(
        """
        <div class="dashboard-section-title">
            🔬 Investigation
        </div>
        <div class="dashboard-section-subtitle">
            Open a risk below to see the financial evidence,
            implications and documents/data that should be checked.
        </div>
        """,
        unsafe_allow_html=True
    )
    selected_risk = st.session_state.get("selected_risk", None)
    if selected_risk is not None:
        r = selected_risk
        if isinstance(r, dict):
            title = r.get("title", "Risk Item")
            badge = r.get("badge", "🔴")
            level = r.get("level", "High")
            reason = r.get(
                "flagged_reason",
                "Flagged by analysis engine."
            )
            st.markdown(
                f"""
                <div class="investigation-panel">
                    <div class="investigation-panel-header">
                        <div>
                            <div class="investigation-kicker">
                                🔬 RISK INVESTIGATION
                            </div>
                            <div class="investigation-title">
                                {badge} {title}
                            </div>
                        </div>
                        <div class="investigation-level">
                            {level}
                        </div>
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class="investigation-detail-card">
                    <div class="investigation-detail-title">
                        Financial Assessment
                    </div>
                    <div class="investigation-detail-text">
                        {r.get("flagged_reason", "Not available")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c1, c2 = st.columns(2)

            with c1:
                st.markdown(
                    f"""
                    <div class="investigation-detail-card">
                        <div class="investigation-detail-title">
                            Financial Evidence
                        </div>
                        <div class="investigation-evidence">
                            {r.get("evidence", "Not available")}
                        </div>
                    </div>

                    <div class="investigation-detail-card">
                        <div class="investigation-detail-title">
                            Financial Impact
                        </div>
                        <div class="investigation-detail-text">
                            {r.get(
                                "why_it_matters",
                                "Cannot determine from available data."
                            )}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c2:
                st.markdown(
                    f"""
                    <div class="investigation-detail-card">
                        <div class="investigation-detail-title">
                            Assessment Implication
                        </div>
                        <div class="investigation-detail-text">
                            {r.get(
                                "implications",
                                "No additional implication available."
                            )}
                        </div>
                    </div>

                    <div class="investigation-detail-card">
                        <div class="investigation-detail-title">
                            Recommended Review
                        </div>
                        <div class="investigation-detail-text">
                            {r.get(
                                "what_to_check",
                                "Additional review required."
                            )}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            documents = r.get("documents_required", [])

            if isinstance(documents, list) and documents:
                documents_html = "".join(
                    f"<div class='investigation-evidence-item'>• {doc}</div>"
                    for doc in documents
                )
            else:
                documents_html = (
                    "<div class='investigation-muted'>"
                    "No additional documents were identified as required "
                    "from the available financial statement data."
                    "</div>"
                )

            st.markdown(
                f"""
                <div class="investigation-detail-card">
                    <div class="investigation-detail-title">
                        Supporting Documents / Data
                    </div>
                    <div class="investigation-detail-text">
                        {documents_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                "← Back to All Risks",
                key="back_to_all_risks",
                use_container_width=False
            ):
                st.session_state.selected_risk = None
                st.rerun()
    else:
        st.info(
            "Select **🔎 Investigate →** on a risk above to open "
            "its detailed investigation."
        )





































