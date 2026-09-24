import os
import re
from typing import Any

import streamlit as st
from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


st.set_page_config(
    page_title="VitalScope | Blood report review",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blood_report.txt")

TEST_RULES: dict[str, dict[str, Any]] = {
    "Hemoglobin": {"pattern": r"Hemoglobin", "unit": "g/dL", "low": 13.5, "high": 17.5},
    "Hematocrit": {"pattern": r"Hematocrit", "unit": "%", "low": 41, "high": 53},
    "WBC": {"pattern": r"WBC", "unit": "x10^3/uL", "low": 4.5, "high": 11},
    "Platelets": {"pattern": r"Platelets", "unit": "x10^3/uL", "low": 150, "high": 400},
    "Total Cholesterol": {"pattern": r"Total Cholesterol", "unit": "mg/dL", "low": 0, "high": 200},
    "LDL Cholesterol": {"pattern": r"LDL Cholesterol", "unit": "mg/dL", "low": 0, "high": 100},
    "HDL Cholesterol": {"pattern": r"HDL Cholesterol", "unit": "mg/dL", "low": 40, "high": 1000},
    "Triglycerides": {"pattern": r"Triglycerides", "unit": "mg/dL", "low": 0, "high": 150},
    "Glucose (Fasting)": {"pattern": r"Glucose \(Fasting\)", "unit": "mg/dL", "low": 70, "high": 99},
    "HbA1c": {"pattern": r"HbA1c", "unit": "%", "low": 0, "high": 5.7},
    "Creatinine": {"pattern": r"Creatinine", "unit": "mg/dL", "low": 0.7, "high": 1.3},
    "eGFR": {"pattern": r"eGFR", "unit": "mL/min", "low": 60, "high": 1000},
    "ALT": {"pattern": r"ALT", "unit": "U/L", "low": 7, "high": 40},
    "AST": {"pattern": r"AST", "unit": "U/L", "low": 10, "high": 40},
    "Bilirubin Total": {"pattern": r"Bilirubin Total", "unit": "mg/dL", "low": 0.2, "high": 1.2},
}


def normalize_report(text: str) -> str:
    return text.replace("–", "-").replace("—", "-").replace("×", "x")


def parse_report(text: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    text = normalize_report(text)
    patient: dict[str, str] = {}
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    match = re.search(r"Patient:\s*(.*?),\s*Age\s*(\d+),\s*(\w+)", first_line, re.I)
    if match:
        patient = {"name": match.group(1), "age": match.group(2), "sex": match.group(3)}
    date_match = re.search(r"Date:\s*(.+)", text, re.I)
    patient["date"] = date_match.group(1).strip() if date_match else "Not provided"

    results: list[dict[str, Any]] = []
    for name, rule in TEST_RULES.items():
        line = next((line for line in text.splitlines() if re.search(rule["pattern"], line, re.I)), "")
        value_match = re.search(r":\s*([0-9]+(?:\.[0-9]+)?)", line)
        if not value_match:
            continue
        value = float(value_match.group(1))
        if value < rule["low"]:
            status = "LOW"
        elif value > rule["high"]:
            status = "HIGH"
        else:
            status = "NORMAL"
        results.append({"name": name, "value": value, "unit": rule["unit"], "status": status, "reference": f"{rule['low']} - {rule['high']}"})
    return patient, results


def generate_guidance(results: list[dict[str, Any]]) -> str:
    abnormal = [item for item in results if item["status"] != "NORMAL"]
    if not abnormal:
        return "Your listed results are within the supplied reference ranges. Keep regular checkups, balanced meals, movement, and any plan from your clinician."
    concerns = ", ".join(item["name"] for item in abnormal)
    return f"The main pattern to discuss with your clinician is {concerns}. Your glucose, kidney, liver, and blood-count markers are otherwise broadly reassuring based on the supplied ranges."


def ask_gemini(report: str, extracted: str) -> str | None:
    if not os.getenv("GOOGLE_API_KEY"):
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.2)
        prompt = f"""You are a clinical nutritionist. Review this blood report carefully.
Give a short, cautious health summary in 3 plain-language lines, then exactly two diet sections:
Foods to avoid and Foods to eat more of. Use practical Indian food examples. Do not diagnose.

Extracted results:
{extracted}

Original report:
{report}"""
        return llm.invoke(prompt).text
    except Exception as error:
        st.session_state["llm_error"] = str(error)
        return None


def render_metric(item: dict[str, Any]) -> None:
    status_class = item["status"].lower()
    st.markdown(
        f"<div class='metric-card {status_class}'><div class='metric-top'><span>{item['name']}</span><span class='status {status_class}'>{item['status']}</span></div><div class='metric-value'>{item['value']:g} <small>{item['unit']}</small></div><div class='reference'>Reference {item['reference']}</div></div>",
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#17231f; --muted:#6b7871; --mint:#d9f2df; --green:#196b4a; --coral:#e6785c; --line:#dce7df; }
    .stApp { background: #f6f8f4; color: var(--ink); font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
    h1 { font-size: 3rem !important; letter-spacing: -1px; margin-bottom: 0 !important; }
    .hero { padding: 22px 0 28px; border-bottom: 1px solid var(--line); margin-bottom: 24px; }
    .eyebrow { color: var(--green); font-weight: 700; font-size: .76rem; letter-spacing: 1.8px; text-transform: uppercase; }
    .lede { color: var(--muted); font-size: 1.05rem; margin-top: 8px; }
    .patient-card, .metric-card, .insight { background: white; border: 1px solid var(--line); border-radius: 8px; padding: 18px; }
    .patient-card { border-left: 5px solid var(--green); }
    .patient-name { font: 700 1.25rem 'Space Grotesk'; }
    .patient-meta { color: var(--muted); margin-top: 5px; font-size: .9rem; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .metric-top { display:flex; justify-content:space-between; align-items:center; color:var(--muted); font-size:.85rem; gap: 8px; }
    .metric-value { font: 700 1.7rem 'Space Grotesk'; margin: 14px 0 3px; }
    .metric-value small { color:var(--muted); font: 400 .78rem 'DM Sans'; }
    .reference { color:var(--muted); font-size:.75rem; }
    .status { border-radius: 20px; padding: 3px 8px; font-size:.67rem; font-weight:700; letter-spacing:.5px; }
    .status.normal { color:#196b4a; background:#d9f2df; } .status.high { color:#9a422b; background:#ffe2d8; } .status.low { color:#876516; background:#fff0c8; }
    .metric-card.high { border-top: 3px solid var(--coral); } .metric-card.low { border-top: 3px solid #d6ac43; } .metric-card.normal { border-top: 3px solid #64b783; }
    .insight { background: #eaf6ed; border-color: #c8e6d0; line-height: 1.6; }
    .section-label { color:var(--green); font:700 .78rem 'DM Sans'; letter-spacing:1.4px; text-transform:uppercase; margin:22px 0 10px; }
    [data-testid='stSidebar'] { background: #edf5ee; border-right: 1px solid var(--line); }
    .disclaimer { color:var(--muted); font-size:.76rem; border-top:1px solid var(--line); padding-top:14px; margin-top:28px; }
    @media (max-width: 800px) { h1 { font-size: 2.25rem !important; } .metric-grid { grid-template-columns: repeat(2, 1fr); } }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### VitalScope")
    st.caption("A clearer first look at your blood report")
    uploaded = st.file_uploader("Upload a report", type=["txt"])
    if st.button("Load demo report", use_container_width=True):
        with open(REPORT_PATH, encoding="utf-8") as report_file:
            st.session_state["report"] = report_file.read()
    st.markdown("---")
    st.caption("Your report is analyzed in this session. This tool is not a diagnosis or a replacement for medical advice.")


if uploaded is not None:
    report_text = uploaded.getvalue().decode("utf-8")
elif "report" in st.session_state:
    report_text = st.session_state["report"]
else:
    with open(REPORT_PATH, encoding="utf-8") as report_file:
        report_text = report_file.read()

patient, results = parse_report(report_text)
abnormal = [item for item in results if item["status"] != "NORMAL"]

st.markdown("<div class='hero'><div class='eyebrow'>Personal health workspace</div><h1>Blood report, made legible.</h1><div class='lede'>A calm, structured view of the numbers that deserve your attention.</div></div>", unsafe_allow_html=True)

left, right = st.columns([1.5, 1], gap="large")
with left:
    st.markdown("<div class='section-label'>Patient profile</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='patient-card'><div class='patient-name'>{patient.get('name', 'Patient')}</div><div class='patient-meta'>Age {patient.get('age', '—')} · {patient.get('sex', '—')} · Report date {patient.get('date', 'Not provided')}</div></div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='section-label'>At a glance</div>", unsafe_allow_html=True)
    st.metric("Markers outside range", len(abnormal), delta="Review with clinician" if abnormal else "All within range", delta_color="inverse" if abnormal else "normal")

st.markdown("<div class='section-label'>Lab markers</div>", unsafe_allow_html=True)
st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
for item in results:
    render_metric(item)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section-label'>Interpretation</div>", unsafe_allow_html=True)
st.markdown(f"<div class='insight'>{generate_guidance(results)}</div>", unsafe_allow_html=True)

if st.button("Generate personalized guidance", type="primary"):
    extracted = "\n".join(f"- {item['name']}: {item['value']:g} {item['unit']} | {item['status']}" for item in results)
    with st.spinner("Preparing guidance..."):
        guidance = ask_gemini(report_text, extracted)
    if guidance:
        st.session_state["guidance"] = guidance
    else:
        st.session_state["guidance"] = "No API key is configured, so the local interpretation above is shown. Add GOOGLE_API_KEY to enable personalized Gemini guidance."

if "guidance" in st.session_state:
    st.markdown("<div class='section-label'>Nutrition notes</div>", unsafe_allow_html=True)
    st.markdown(st.session_state["guidance"])

with st.expander("View source report"):
    st.code(report_text, language="text")

st.markdown("<div class='disclaimer'>For educational use only. Reference ranges can vary by laboratory, age, history, and clinical context. Discuss abnormal or concerning results with a qualified healthcare professional.</div>", unsafe_allow_html=True)