import streamlit as st
import pdfplumber
import json
import os
import re
import tempfile
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# ─────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Payment Advice Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

/* ── ROOT THEME ── */
:root {
    --bg:        #0a0e17;
    --surface:   #111827;
    --surface2:  #1a2235;
    --border:    #1f2d45;
    --accent:    #00d4aa;
    --accent2:   #0ea5e9;
    --warn:      #f59e0b;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --radius:    12px;
}

/* ── GLOBAL ── */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background: var(--bg) !important;
    color: var(--text);
}

.stApp { background: var(--bg); }

/* hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1300px; }

/* ── HERO HEADER ── */
.hero {
    display: flex;
    align-items: center;
    gap: 1.4rem;
    padding: 2.5rem 0 2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2.5rem;
}
.hero-icon {
    width: 56px; height: 56px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px;
    flex-shrink: 0;
    box-shadow: 0 0 28px rgba(0,212,170,.25);
}
.hero-text h1 {
    font-size: 1.9rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin: 0 0 .25rem;
    background: linear-gradient(90deg, #fff 30%, var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-text p { color: var(--muted); font-size: .92rem; margin: 0; }

/* ── UPLOAD ZONE ── */
.upload-wrapper {
    background: var(--surface);
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 2.5rem 2rem;
    text-align: center;
    transition: border-color .3s;
    margin-bottom: 1.8rem;
}
.upload-wrapper:hover { border-color: var(--accent); }

/* override streamlit file uploader */
[data-testid="stFileUploader"] {
    background: transparent !important;
}
[data-testid="stFileUploader"] > div {
    border: none !important;
    background: transparent !important;
}
[data-testid="stFileUploadDropzone"] {
    background: var(--surface) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--muted) !important;
    transition: border-color .3s, background .3s;
}
[data-testid="stFileUploadDropzone"]:hover {
    border-color: var(--accent) !important;
    background: var(--surface2) !important;
}
[data-testid="stFileUploadDropzone"] span { color: var(--muted) !important; }

/* ── BUTTON ── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%) !important;
    color: #0a0e17 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: .95rem !important;
    padding: .65rem 2.2rem !important;
    letter-spacing: .3px;
    cursor: pointer;
    transition: opacity .2s, transform .15s;
    box-shadow: 0 0 20px rgba(0,212,170,.2);
}
.stButton > button:hover {
    opacity: .88 !important;
    transform: translateY(-1px);
}
.stButton > button:disabled {
    background: var(--surface2) !important;
    color: var(--muted) !important;
    box-shadow: none !important;
}

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--accent) !important;
    border: 1.5px solid var(--accent) !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: .9rem !important;
    padding: .55rem 1.8rem !important;
    transition: background .2s, color .2s;
}
.stDownloadButton > button:hover {
    background: var(--accent) !important;
    color: #0a0e17 !important;
}

/* ── CARDS ── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.4rem;
}
.card-title {
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 1.1rem;
}

/* ── KV GRID ── */
.kv-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: .9rem;
}
.kv-item {
    background: var(--surface2);
    border-radius: 8px;
    padding: .75rem 1rem;
    border-left: 3px solid var(--accent2);
}
.kv-label {
    font-size: .7rem;
    color: var(--muted);
    letter-spacing: .8px;
    text-transform: uppercase;
    margin-bottom: .3rem;
    font-family: 'DM Mono', monospace;
}
.kv-value {
    font-size: .95rem;
    font-weight: 600;
    color: var(--text);
    word-break: break-all;
}
.kv-value.amount {
    color: var(--accent);
    font-family: 'DM Mono', monospace;
    font-size: 1.05rem;
}

/* ── TRANSACTION TABLE ── */
.tx-table {
    width: 100%;
    border-collapse: collapse;
    font-size: .85rem;
    font-family: 'DM Mono', monospace;
}
.tx-table th {
    background: var(--surface2);
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .9px;
    font-size: .68rem;
    padding: .75rem 1rem;
    text-align: left;
    border-bottom: 2px solid var(--border);
}
.tx-table td {
    padding: .7rem 1rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: top;
}
.tx-table tr:hover td { background: var(--surface2); }
.badge {
    display: inline-block;
    padding: .2rem .6rem;
    border-radius: 4px;
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .5px;
}
.badge-inv { background: rgba(0,212,170,.15); color: var(--accent); }
.badge-tds { background: rgba(245,158,11,.15); color: var(--warn); }

/* ── JSON PREVIEW BOX ── */
.json-box {
    background: #060b12;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem;
    overflow-x: auto;
    font-family: 'DM Mono', monospace;
    font-size: .82rem;
    line-height: 1.7;
    color: #a8c0d6;
    max-height: 450px;
    overflow-y: auto;
}
.json-box::-webkit-scrollbar { width: 6px; height: 6px; }
.json-box::-webkit-scrollbar-track { background: transparent; }
.json-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── STATUS / INFO ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: .7rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: .8rem 1.2rem;
    font-size: .88rem;
    color: var(--muted);
    margin-bottom: 1.5rem;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-idle  { background: var(--muted); }
.dot-ready { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
.dot-error { background: #ef4444; box-shadow: 0 0 6px #ef4444; }

/* ── DIVIDER ── */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}

/* ── SECTION LABEL ── */
.section-label {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent2);
    margin-bottom: 1rem;
}

/* ── STREAMLIT SPINNER ── */
[data-testid="stSpinner"] { color: var(--accent) !important; }

/* ── SUCCESS / ERROR MESSAGES ── */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  GROQ CLIENT  (same as original)
# ─────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

MODEL = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────
#  ORIGINAL LOGIC (untouched)
# ─────────────────────────────────────────
def extract_pdf_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

def clean_json(text):
    text = re.sub(r"json", "", text)
    text = re.sub(r"", "", text)
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text.strip()

def validate_pa_utr(data):
    pa  = data.get("PA_Number", "").strip()
    utr = data.get("PA_UTR",    "").strip()
    if pa and utr:
        data["PA_Number"] = pa
        data["PA_UTR"]    = utr
    elif pa and not utr:
        data["PA_Number"] = pa
        data["PA_UTR"]    = ""
    elif utr and not pa:
        data["PA_Number"] = utr
        data["PA_UTR"]    = utr
    else:
        data["PA_Number"] = ""
        data["PA_UTR"]    = ""
    return data

def extract_with_llm(pdf_text):
    client = get_client()
    prompt = f"""
You are an expert financial document parser.

Extract payment advice data from the document text.

Return STRICT JSON.

Schema:

{{
 "PA_Company":"",
 "PA_Total":"",
 "PA_Date":"",
 "PA_Number":"",
 "PA_MMD_Bank_Account_NAME":"",
 "PA_MMD_Bank_Account_NO":"",
 "PA_UTR":"",
 "pa_trans_line_details":[
  {{
   "pa_invoice_number":"",
   "pa_client_ref_number":"",
   "pa_client_ref_date":"",
   "pa_amount":"",
   "pa_trans_type":"",
   "pa_trans_des":"",
   "pa_account_site":""
  }}
 ]
}}

Rules:

1. PA_Company = payment sender (FROM company)
2. Never choose the company after "To" or "M/s"
3. PA_Number = payment reference such as:
   - NEFT No
   - Payment Advice No
   - Transaction Reference
4. PA_UTR = UTR reference if present
5. Invoice rows → pa_trans_type = "INV"
6. Less / TDS / negative rows → pa_trans_type = "TDS"
7. Dates → YYYY-MM-DD
8. Remove commas from amounts
9. Return ONLY JSON

Document Text:

{pdf_text}
"""
    response = client.responses.create(model=MODEL, input=prompt, temperature=0)
    return response.output_text

def process_pdf(pdf_path):
    pdf_text = extract_pdf_text(pdf_path)
    raw      = extract_with_llm(pdf_text)
    cleaned  = clean_json(raw)
    try:
        data = json.loads(cleaned)
        data = validate_pa_utr(data)
        return data, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────
#  RENDER HELPERS
# ─────────────────────────────────────────
def render_kv(label, value, is_amount=False):
    cls = "kv-value amount" if is_amount else "kv-value"
    return f"""
<div class="kv-item">
  <div class="kv-label">{label}</div>
  <div class="{cls}">{value if value else '<span style="color:#475569">—</span>'}</div>
</div>"""

def render_result(data):
    # ── Summary card ──────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📋 Payment Summary</div>', unsafe_allow_html=True)

    kv_html = '<div class="kv-grid">'
    kv_html += render_kv("Company",      data.get("PA_Company",""))
    kv_html += render_kv("Date",         data.get("PA_Date",""))
    kv_html += render_kv("PA Number",    data.get("PA_Number",""))
    kv_html += render_kv("UTR",          data.get("PA_UTR",""))
    kv_html += render_kv("Total Amount", data.get("PA_Total",""), is_amount=True)
    kv_html += render_kv("Bank Name",    data.get("PA_MMD_Bank_Account_NAME",""))
    kv_html += render_kv("Account No",   data.get("PA_MMD_Bank_Account_NO",""))
    kv_html += '</div>'
    st.markdown(kv_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Transaction lines ──────────────────────
    lines = data.get("pa_trans_line_details", [])
    if lines:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📑 Transaction Line Details</div>', unsafe_allow_html=True)

        table  = '<div style="overflow-x:auto"><table class="tx-table"><thead><tr>'
        headers = ["Invoice No", "Client Ref", "Ref Date", "Amount", "Type", "Description", "Account Site"]
        for h in headers:
            table += f"<th>{h}</th>"
        table += "</tr></thead><tbody>"

        for row in lines:
            t = row.get("pa_trans_type","").upper()
            badge_cls = "badge-tds" if t == "TDS" else "badge-inv"
            badge_lbl = t if t else "—"
            table += "<tr>"
            table += f"<td>{row.get('pa_invoice_number','') or '—'}</td>"
            table += f"<td>{row.get('pa_client_ref_number','') or '—'}</td>"
            table += f"<td>{row.get('pa_client_ref_date','') or '—'}</td>"
            amount_val = row.get('pa_amount','') or '—'
            table += f"<td style='font-family:DM Mono,monospace;color:var(--accent)'>{amount_val}</td>"
            table += f"<td><span class='badge {badge_cls}'>{badge_lbl}</span></td>"
            table += f"<td>{row.get('pa_trans_des','') or '—'}</td>"
            table += f"<td>{row.get('pa_account_site','') or '—'}</td>"
            table += "</tr>"

        table += "</tbody></table></div>"
        st.markdown(table, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── JSON Preview ───────────────────────────
    st.markdown('<div class="section-label">⬡ Raw JSON Preview</div>', unsafe_allow_html=True)
    json_str = json.dumps(data, indent=4)
    st.markdown(
        f'<div class="json-box"><pre style="margin:0;background:transparent">{json_str}</pre></div>',
        unsafe_allow_html=True
    )

    # ── Download ───────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇  Download JSON",
        data=json_str,
        file_name="payment_advice.json",
        mime="application/json",
        use_container_width=False,
    )

# ─────────────────────────────────────────
#  APP LAYOUT
# ─────────────────────────────────────────

# Hero
st.markdown("""
<div class="hero">
  <div class="hero-icon">📄</div>
  <div class="hero-text">
    <h1>Payment Advice Extractor</h1>
    <p>Upload a PDF payment advice — get structured JSON in seconds, powered by LLaMA 3.3 via Groq</p>
  </div>
</div>
""", unsafe_allow_html=True)

# Two-column layout
col_left, col_right = st.columns([1.1, 1.9], gap="large")

with col_left:
    st.markdown('<div class="section-label">Upload Document</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        label="",
        type=["pdf"],
        help="Only PDF files are accepted",
        label_visibility="collapsed",
    )

    file_ready = uploaded is not None

    if file_ready:
        size_kb = round(uploaded.size / 1024, 1)
        st.markdown(f"""
        <div class="status-bar">
          <div class="status-dot dot-ready"></div>
          <span><strong>{uploaded.name}</strong> &nbsp;·&nbsp; {size_kb} KB</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-bar">
          <div class="status-dot dot-idle"></div>
          <span>Waiting for PDF upload…</span>
        </div>""", unsafe_allow_html=True)

    extract_btn = st.button(
        "Extract Data →",
        disabled=not file_ready,
        use_container_width=True,
    )

    # tips
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#475569;font-size:.8rem;line-height:1.8">
    <strong style="color:#64748b;letter-spacing:.5px">SUPPORTED FORMATS</strong><br>
    NEFT / RTGS Advice &nbsp;·&nbsp; Bank Remittance<br>
    Payment Voucher &nbsp;·&nbsp; TDS Deduction Slips<br><br>
    <strong style="color:#64748b;letter-spacing:.5px">OUTPUT FIELDS</strong><br>
    Company · Date · PA/UTR Number<br>
    Bank Account · Transaction Lines
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-label">Extracted Output</div>', unsafe_allow_html=True)

    result_placeholder = st.empty()

    if not file_ready and not extract_btn:
        result_placeholder.markdown("""
        <div style="
            background:var(--surface);
            border:1px dashed var(--border);
            border-radius:12px;
            padding:4rem 2rem;
            text-align:center;
            color:var(--muted);
            font-size:.92rem;
        ">
            <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.4">📂</div>
            Upload a PDF and click <strong>Extract Data</strong><br>to see the structured output here.
        </div>
        """, unsafe_allow_html=True)

    if extract_btn and uploaded:
        with result_placeholder.container():
            with st.spinner("Extracting text & running LLM inference…"):
                # save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name

                result, err = process_pdf(tmp_path)
                os.unlink(tmp_path)

            if result:
                st.success("Extraction complete!", icon="✅")
                render_result(result)
            else:
                st.error(f"JSON parsing failed. Raw model output logged below.", icon="🚫")
                st.code(err or "Unknown error", language="text")