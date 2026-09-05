import os
import json
import sqlite3
import tempfile
import pandas as pd
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# Import project modules
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf, process_any_file
from src.parser import smart_parse
from run_etl import (
    init_db,
    get_unprocessed_files,
    process_file,
    load_ktp_to_db,
    load_transactions_to_db,
    load_generic_to_db,
    update_file_status,
    DEFAULT_DB_PATH,
    DEFAULT_INPUT_DIR,
)
from ocr_eval import load_ground_truth, evaluate_ocr_accuracy, evaluate_parsing_accuracy

# Load environment variables
load_dotenv()

# ==============================================================================
# Page Configuration & Premium Styling System
# ==============================================================================
st.set_page_config(
    page_title="OCRMe — Intelligent Document Processing",
    page_icon=":material/find_in_page:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Modern UI/UX CSS Injection
st.markdown("""
<style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Typography & Font Setup */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }

    code, pre, div[data-baseweb="textarea"] textarea {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
    }

    /* Header Hero Banner */
    .main-header-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 28px 36px;
        margin-bottom: 24px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .main-header-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
        pointer-events: none;
    }
    
    .main-title {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.8px;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .main-subtitle {
        font-size: 15px;
        color: #94a3b8;
        font-weight: 400;
        line-height: 1.6;
        max-width: 900px;
    }

    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 12px;
    }

    /* Metric Cards Custom Styling */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    div[data-testid="stMetric"]:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-3px);
        box-shadow: 0 12px 24px rgba(99, 102, 241, 0.15);
    }

    div[data-testid="stMetricValue"] {
        font-size: 20px !important;
        font-weight: 800 !important;
        word-break: break-word !important;
        white-space: normal !important;
        line-height: 1.3 !important;
        color: #38bdf8 !important;
        letter-spacing: -0.5px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #94a3b8 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Container Border Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 16px !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        background: rgba(15, 23, 42, 0.4) !important;
        backdrop-filter: blur(10px);
    }

    /* Section Card Header */
    .section-card-title {
        font-size: 16px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
        letter-spacing: -0.2px;
    }

    /* Form & Input Enhancements */
    div[data-baseweb="input"] {
        border-radius: 12px !important;
    }

    /* Tab bar customization */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
        border-radius: 10px !important;
    }

    /* Feature Badge Tags */
    .format-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        margin-right: 4px;
        margin-bottom: 4px;
    }
    .fmt-pdf { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .fmt-img { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .fmt-doc { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .fmt-xls { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
</style>
""", unsafe_allow_html=True)

# Ensure SQLite DB is initialized
init_db()

# ==============================================================================
# Sidebar Control & Configuration Panel
# ==============================================================================
with st.sidebar:
    st.markdown("### 🌐 Bahasa / Language")
    lang_choice = st.radio(
        "Pilih Bahasa / Select Language",
        options=["Bahasa Indonesia 🇮🇩", "English 🇬🇧"],
        index=0,
        horizontal=True,
        key="app_lang_radio",
        label_visibility="collapsed"
    )
    is_en = "English" in lang_choice

    st.divider()

    st.markdown(f"### :material/tune: {'Control panel' if is_en else 'Panel kontrol'}")
    st.caption("Configure AI providers, models, OCR engines, and API keys." if is_en else "Atur penyedia AI, model, mesin OCR, dan kunci API.")
    st.space("small")

    # Developer Mode Authentication Toggle
    is_developer = st.session_state.get("dev_authenticated", False)
    dev_toggle_label = "🔐 Developer mode" if is_en else "🔐 Mode developer"
    dev_toggle_help = "Unlock raw database inspector, audit logs, and domain tables." if is_en else "Buka kunci inspektur basis data mentah, log audit, dan tabel domain."
    dev_toggle = st.toggle(dev_toggle_label, value=is_developer, help=dev_toggle_help)
    if dev_toggle != is_developer:
        if dev_toggle:
            pass_placeholder = "Enter developer password..." if is_en else "Ketik sandi developer..."
            dev_pass = st.text_input("Developer password" if is_en else "Sandi developer", type="password", key="dev_pass_input", placeholder=pass_placeholder)
            valid_dev_pass = os.getenv("DEV_PASSWORD", r'u8"V&U$Z94gU,v?')
            if dev_pass == valid_dev_pass:
                st.session_state["dev_authenticated"] = True
                st.toast("Developer mode unlocked!", icon="🔓")
                st.rerun()
            elif dev_pass:
                st.error("Invalid developer password." if is_en else "Sandi developer salah.", icon=":material/lock:")
        else:
            st.session_state["dev_authenticated"] = False
            st.toast("Developer mode locked", icon="🔒")
            st.rerun()

    st.space("small")

    # AI Provider Selection Dropdown
    st.markdown(f"**{'AI provider selection' if is_en else 'Pilihan penyedia AI'}**")
    ai_provider = st.selectbox(
        "AI provider",
        options=["gemini", "openai", "claude", "ollama"],
        format_func=lambda x: {
            "gemini": "Google Gemini AI",
            "openai": "OpenAI ChatGPT",
            "claude": "Anthropic Claude",
            "ollama": "Ollama (Local LLM)"
        }[x],
        index=0,
        label_visibility="collapsed"
    )

    # API Key or Host Input based on Provider
    if ai_provider == "openai":
        api_key_input = st.text_input(
            "OpenAI API key",
            value="",
            type="password",
            placeholder="Enter your OpenAI API key" if is_en else "Masukkan OpenAI API Key Anda",
            help="Enter your OpenAI API Key."
        )
        if api_key_input:
            os.environ["OPENAI_API_KEY"] = api_key_input
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        model_name_input = st.text_input("OpenAI model", value="gpt-4o-mini", placeholder="gpt-4o-mini")

    elif ai_provider == "claude":
        api_key_input = st.text_input(
            "Anthropic API key",
            value="",
            type="password",
            placeholder="Enter your Anthropic API key" if is_en else "Masukkan Anthropic API Key Anda",
            help="Enter your Anthropic Claude API Key."
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input
        else:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        model_name_input = st.text_input("Claude model", value="claude-3-5-haiku-20241022", placeholder="claude-3-5-haiku-20241022")

    elif ai_provider == "ollama":
        api_key_input = st.text_input("Ollama host URL", value=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
        model_name_input = st.text_input("Ollama model", value="llama3.1", placeholder="llama3.1")

    else:
        api_key_input = st.text_input(
            "Gemini API key",
            value="",
            type="password",
            help="Paste your Google Gemini API key to enable AI multi-category adaptive extraction.",
            placeholder="Enter your Gemini API key" if is_en else "Masukkan Gemini API Key Anda"
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        model_name_input = st.text_input("Gemini model", value="gemini-3.6-flash", placeholder="gemini-3.6-flash")

    st.space("small")

    # OCR Engine Selector
    st.markdown(f"**{'OCR engine selection' if is_en else 'Pilihan mesin OCR'}**")
    engine_choice = st.segmented_control(
        "OCR engine",
        options=["easyocr", "tesseract"],
        format_func=lambda x: "EasyOCR (Layout preserving)" if x == "easyocr" else "Tesseract OCR (Fast)",
        default="easyocr",
        label_visibility="collapsed"
    )

    st.space("small")

    # Parsing Method Selector
    st.markdown(f"**{'Parsing & AI mode' if is_en else 'Mode ekstraksi & AI'}**")
    parsing_mode = st.segmented_control(
        "Parsing mode",
        options=["auto", "llm", "regex"],
        format_func=lambda x: {
            "auto": f"Auto ({ai_provider.title()} AI → Regex)",
            "llm": f"{ai_provider.title()} AI only",
            "regex": "Regex fallback only"
        }[x],
        default="auto",
        label_visibility="collapsed"
    )

    st.space("medium")

    # System Status Card (High-Tech Glassmorphism Redesign)
    has_key = bool(api_key_input) or ai_provider == "ollama"
    status_title = "System status" if is_en else "Status sistem"
    
    provider_names = {
        "gemini": "Gemini AI",
        "openai": "OpenAI",
        "claude": "Claude AI",
        "ollama": "Ollama Local"
    }
    current_provider_name = provider_names.get(ai_provider, ai_provider.title())

    ai_badge_html = (
        f'''<span class="status-pill status-pill-active">
            <span class="status-dot green-dot"></span>Active
        </span>'''
        if has_key else
        f'''<span class="status-pill status-pill-amber">
            <span class="status-dot amber-dot"></span>Regex Mode
        </span>'''
    )

    st.markdown(f"""
    <style>
        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6); }}
            70% {{ box-shadow: 0 0 0 7px rgba(52, 211, 153, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }}
        }}
        @keyframes amberPulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }}
            70% {{ box-shadow: 0 0 0 7px rgba(245, 158, 11, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }}
        }}
        .status-card-container {{
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.75) 100%);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            padding: 1.15rem;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            transition: all 0.25s ease-in-out;
        }}
        .status-card-container:hover {{
            border-color: rgba(59, 130, 246, 0.35);
            box-shadow: 0 14px 35px -5px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        }}
        .status-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.9rem;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .status-card-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 700;
            font-size: 0.95rem;
            color: #f8fafc;
            letter-spacing: 0.2px;
        }}
        .online-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.68rem;
            padding: 0.18rem 0.6rem;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
            font-weight: 700;
            letter-spacing: 0.6px;
        }}
        .status-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }}
        .green-dot {{
            background-color: #10b981;
            animation: pulseGlow 2s infinite;
        }}
        .amber-dot {{
            background-color: #f59e0b;
            animation: amberPulse 2s infinite;
        }}
        .status-row-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        .status-row-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.83rem;
        }}
        .status-label {{
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-weight: 500;
        }}
        .status-label strong {{
            color: #e2e8f0;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.76rem;
        }}
        .status-pill-active {{
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .status-pill-amber {{
            background: rgba(245, 158, 11, 0.16);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        .status-pill-blue {{
            background: rgba(59, 130, 246, 0.16);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .status-pill-purple {{
            background: rgba(168, 85, 247, 0.16);
            color: #c084fc;
            border: 1px solid rgba(168, 85, 247, 0.3);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .status-subtext {{
            margin-top: 0.6rem;
            padding-top: 0.5rem;
            border-top: 1px dashed rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #64748b;
        }}
    </style>

    <div class="status-card-container">
        <div class="status-card-header">
            <div class="status-card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                <span>{status_title}</span>
            </div>
            <span class="online-badge">
                <span class="status-dot green-dot"></span>ONLINE
            </span>
        </div>
        <div class="status-row-list">
            <div class="status-row-item">
                <span class="status-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#a7f3d0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                        <circle cx="12" cy="5" r="2"></circle>
                        <path d="M12 7v4"></path>
                        <line x1="8" y1="16" x2="8.01" y2="16"></line>
                        <line x1="16" y1="16" x2="16.01" y2="16"></line>
                    </svg>
                    <strong>AI Provider</strong>
                </span>
                {ai_badge_html}
            </div>
            <div class="status-row-item">
                <span class="status-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#93c5fd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                        <circle cx="12" cy="13" r="4"></circle>
                    </svg>
                    <strong>OCR Engine</strong>
                </span>
                <span class="status-pill status-pill-blue">{engine_choice.upper()}</span>
            </div>
            <div class="status-row-item">
                <span class="status-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#d8b4fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="18" cy="18" r="3"></circle>
                        <circle cx="6" cy="6" r="3"></circle>
                        <path d="M6 9v12"></path>
                        <path d="M18 9v3a3 3 0 0 1-3 3H6"></path>
                    </svg>
                    <strong>Parsing Mode</strong>
                </span>
                <span class="status-pill status-pill-purple">{parsing_mode.upper()}</span>
            </div>
        </div>
        <div class="status-subtext">
            <span>Model: <strong style="color: #cbd5e1;">{model_name_input}</strong></span>
            <span>Provider: <strong style="color: #cbd5e1;">{current_provider_name}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.space("medium")
    st.markdown(f"""
    <div style="font-size: 12px; color: #64748b; line-height: 1.5; text-align: center;">
        OCRMe v2.5 General Document Engine<br/>
        {'Supported formats' if is_en else 'Format didukung'}: PDF, Image, Word, Excel, PPT, Text, JSON
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# Main Content Area
# ==============================================================================

# Top Header Hero Banner
hero_badge = "✨ OCRMe — Intelligent Document Processing Engine" if is_en else "✨ OCRMe — Pembaca & Ekstraktor Dokumen Otomatis"
hero_title = "📄 Automatic Document Data Extraction" if is_en else "📄 Ekstraksi Data Dokumen Otomatis"
hero_subtitle = (
    "Upload photos or documents (ID Cards, Receipts, Invoices, Bank Statements, Letters, Word, PDF, Excel) to automatically extract structured data without manual typing."
    if is_en else
    "Unggah foto atau dokumen (KTP, Nota, Faktur/Invoice, Rekening Koran, Surat, Word, PDF, Excel) untuk membaca dan mengekstrak data secara otomatis tanpa perlu diketik manual."
)

st.markdown(f"""
<div class="main-header-card">
    <div class="badge-pill">{hero_badge}</div>
    <div class="main-title">{hero_title}</div>
    <div class="main-subtitle">{hero_subtitle}</div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs (Bilingual)
tab_playground, tab_database, tab_guide, tab_advanced = st.tabs([
    "📄 Document extraction" if is_en else "📄 Ekstraksi dokumen",
    "📊 Summary & analytics" if is_en else "📊 Ringkasan & statistik",
    "📘 User guide" if is_en else "📘 Panduan pengguna",
    "⚙️ Advanced & batch features" if is_en else "⚙️ Fitur lanjutan & batch"
])

# ==============================================================================
# TAB 1: Live Document Processor & Playground (Sederhana & Mudah)
# ==============================================================================
with tab_playground:
    st.markdown("#### :material/file_present: Unggah & Proses Dokumen Tunggal")
    st.caption("Pilih file dari komputer Anda atau ketik jalur berkas lokal untuk membaca dan mengekstrak data secara otomatis.")

    input_method = st.segmented_control(
        "Metode input",
        options=["upload", "local_path"],
        format_func=lambda x: "☁️ Upload file (seret & lepas)" if x == "upload" else "💻 Alamat file lokal",
        default="upload",
        label_visibility="collapsed"
    )

    tmp_path = None
    file_name = None
    file_ext = None

    if input_method == "upload":
        st.markdown(":red-badge[PDF] :blue-badge[Foto / Gambar] :green-badge[Word / PPT] :orange-badge[Excel / CSV] :purple-badge[Teks / JSON]")
        
        uploaded_file = st.file_uploader(
            "Pilih berkas dokumen",
            type=None,
            help="Tarik dan lepas berkas dokumen apa saja (PDF, PNG, JPG, DOCX, XLSX, TXT, JSON, dll.)",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_ext = os.path.splitext(file_name.lower())[1]
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

    else:
        with st.container(border=True):
            local_path = st.text_input(
                "Masukkan alamat file di komputer Anda",
                placeholder="/home/user/Dokumen/nota.pdf atau C:\\Scans\\faktur.docx",
                help="Ketik alamat lokasi berkas pada komputer Anda."
            )
            if local_path and os.path.exists(local_path):
                tmp_path = os.path.abspath(os.path.expanduser(local_path))
                file_name = os.path.basename(tmp_path)
                file_ext = os.path.splitext(file_name.lower())[1]
                st.caption(f":material/check_circle: Berkas ditemukan: `{tmp_path}`")
            elif local_path:
                st.caption(f":material/error: Berkas tidak ditemukan: `{local_path}`")

    # Quick sample test helper (if files exist in data/input)
    if tmp_path is None and os.path.exists(DEFAULT_INPUT_DIR):
        all_in_folder = [os.path.join(DEFAULT_INPUT_DIR, f) for f in os.listdir(DEFAULT_INPUT_DIR) if not f.startswith(".")]
        if all_in_folder:
            st.space("small")
            with st.expander("💡 Atau coba langsung dengan contoh dokumen dari sampel data/input", icon=":material/lightbulb:"):
                sample_selected = st.selectbox("Pilih berkas contoh", options=["Pilih berkas contoh..."] + [os.path.basename(f) for f in all_in_folder])
                if sample_selected != "Pilih berkas contoh...":
                    tmp_path = os.path.join(DEFAULT_INPUT_DIR, sample_selected)
                    file_name = sample_selected
                    file_ext = os.path.splitext(file_name.lower())[1]

    # Processing Workspace Area
    if tmp_path is not None and file_name is not None:
        st.space("small")
        col_preview, col_action = st.columns([1, 2], gap="medium")

        with col_preview:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/visibility: Document Preview</div>", unsafe_allow_html=True)
                if file_ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif", ".svg"]:
                    try:
                        image = Image.open(tmp_path)
                        st.image(image, caption=file_name, width="stretch")
                    except Exception:
                        st.info(f"🖼️ Image file: **{file_name}**")
                elif file_ext == ".pdf":
                    st.info(f":material/picture_as_pdf: PDF Document: **{file_name}**")
                elif file_ext in [".docx", ".doc", ".pptx", ".ppt"]:
                    st.info(f":material/description: Office Document: **{file_name}**")
                elif file_ext in [".xlsx", ".xls", ".csv", ".tsv"]:
                    st.info(f":material/table_chart: Spreadsheet: **{file_name}**")
                else:
                    st.info(f":material/draft: Document File: **{file_name}** ({file_ext.upper()})")

        with col_action:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/rocket_launch: Extraction & Parsing Action</div>", unsafe_allow_html=True)
                st.caption(f"Configured Engine: **{engine_choice.upper()}** | Mode: **{parsing_mode.upper()}**")
                
                if st.button("Process & extract document", icon=":material/play_arrow:", type="primary", width="stretch"):
                    with st.spinner("Extracting text content and parsing structured fields..."):
                        try:
                            # 1. Universal Text / Content Extraction
                            raw_text = process_any_file(tmp_path, engine=engine_choice)

                            # 2. Smart Parsing
                            use_llm_flag = parsing_mode != "regex"
                            parse_result = smart_parse(
                                raw_text,
                                use_llm=use_llm_flag,
                                provider=ai_provider,
                                api_key=api_key_input,
                                model_name=model_name_input
                            )

                            # Extract metadata
                            doc_type = parse_result.get("doc_type", "unknown")
                            doc_subtype = parse_result.get("doc_subtype", "Unknown")
                            confidence = parse_result.get("confidence", 0.0)
                            method = parse_result.get("method", "regex")
                            parsed_data = parse_result.get("data", {})

                            # 3. Automatically persist to SQLite DB for real-time Database Analytics
                            try:
                                db_path_file = tmp_path if (input_method == "local_path" and local_path) else file_name
                                if doc_type == "identity_card":
                                    ktp_data = parsed_data if isinstance(parsed_data, dict) else {}
                                    load_ktp_to_db(db_path_file, ktp_data, db_path=DEFAULT_DB_PATH)
                                elif doc_type == "bank_statement":
                                    tx_list_save = parsed_data if isinstance(parsed_data, list) else (parsed_data.get("transactions") if isinstance(parsed_data, dict) else None)
                                    if tx_list_save:
                                        load_transactions_to_db(db_path_file, tx_list_save, db_path=DEFAULT_DB_PATH)
                                
                                load_generic_to_db(db_path_file, doc_type, doc_subtype, parsed_data, method, confidence, db_path=DEFAULT_DB_PATH)
                                update_file_status(db_path_file, "SUCCESS", db_path=DEFAULT_DB_PATH)
                            except Exception as db_sync_err:
                                st.caption(f"Database sync note: {db_sync_err}")

                            # Clean up temp file if uploaded
                            if input_method == "upload" and os.path.exists(tmp_path):
                                os.remove(tmp_path)

                            st.toast("Processing completed & saved to database!", icon="✅")

                            # Results Display Container
                            st.markdown("##### Classification & metadata")
                            
                            m1, m2, m3, m4 = st.columns(4)
                            with m1:
                                st.metric("Document category", doc_type.upper())
                            with m2:
                                st.metric("Subtype", doc_subtype)
                            with m3:
                                st.metric("Confidence", f"{confidence:.0%}")
                            with m4:
                                method_badge = "AI (GEMINI)" if method == "llm" else "REGEX"
                                st.metric("Parsing engine", method_badge)

                            st.space("medium")

                            # Output Tabs
                            out_tab1, out_tab2, out_tab3 = st.tabs([
                                "📦 Structured data (JSON)",
                                "📊 Line items & tables",
                                "📝 Raw extracted text"
                            ])

                            with out_tab1:
                                full_output = {
                                    "metadata": {
                                        "filename": file_name,
                                        "ocr_engine": engine_choice,
                                        "parsing_method": method,
                                        "doc_type": doc_type,
                                        "doc_subtype": doc_subtype,
                                        "confidence": confidence
                                    },
                                    "data": parsed_data
                                }
                                st.json(full_output)
                                st.download_button(
                                    "Download JSON result",
                                    data=json.dumps(full_output, indent=4, ensure_ascii=False),
                                    file_name=f"result_{os.path.splitext(file_name)[0]}.json",
                                    mime="application/json",
                                    icon=":material/download:"
                                )

                            with out_tab2:
                                tx_list = None
                                if isinstance(parsed_data, list):
                                    tx_list = parsed_data
                                elif isinstance(parsed_data, dict) and "transactions" in parsed_data:
                                    tx_list = parsed_data["transactions"]
                                elif isinstance(parsed_data, dict) and "line_items" in parsed_data:
                                    tx_list = parsed_data["line_items"]

                                if tx_list and isinstance(tx_list, list) and len(tx_list) > 0:
                                    df_tx = pd.DataFrame(tx_list)
                                    st.dataframe(df_tx, width="stretch")
                                    st.download_button(
                                        "Download line items / tables (CSV)",
                                        data=df_tx.to_csv(index=False),
                                        file_name=f"result_{os.path.splitext(file_name)[0]}.csv",
                                        mime="text/csv",
                                        icon=":material/download:"
                                    )
                                else:
                                    st.info("No tabular transactions or line items detected in this document.", icon=":material/info:")

                            with out_tab3:
                                st.text_area("Raw extracted text", value=raw_text, height=320, label_visibility="collapsed")
                                st.download_button(
                                    "Download raw text (TXT)",
                                    data=raw_text,
                                    file_name=f"result_{os.path.splitext(file_name)[0]}.txt",
                                    mime="text/plain",
                                    icon=":material/download:"
                                )

                        except Exception as e:
                            st.error(f"Processing failed: {str(e)}", icon=":material/error:")

# ==============================================================================
# TAB 2: Database Analytics & Inspector (General Document Analytics)
# ==============================================================================
with tab_database:
    col_hdr, col_ref = st.columns([3, 1])
    with col_hdr:
        st.markdown("#### :material/analytics: Database Inspector & General Analytics")
        st.caption("Explore system analytics, document distribution insights, and database records.")
    with col_ref:
        if st.button("Refresh database", icon=":material/refresh:", width="stretch"):
            st.rerun()

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    is_dev = st.session_state.get("dev_authenticated", False)

    # Database Sub-Tabs (Visual Analytics is PUBLIC, others are DEVELOPER ONLY)
    db_tab_visual, db_tab_records, db_tab_audit, db_tab_tables = st.tabs([
        "📊 Visual analytics",
        "📑 All parsed documents (Private)",
        "📋 Audit log (Private)",
        "🗃️ Specialized tables (Private)"
    ])

    # Load full document_records dataframe for analytics and inspection
    try:
        df_docs_all = pd.read_sql_query("SELECT * FROM document_records ORDER BY processed_at DESC", conn)
    except Exception as e:
        df_docs_all = pd.DataFrame()

    # --------------------------------------------------------------------------
    # Sub-tab 1: PUBLIC — Visual Analytics Dashboard (Beautified)
    # --------------------------------------------------------------------------
    with db_tab_visual:
        # Top-level KPI Metrics Summary Grid
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM processed_files WHERE status = 'SUCCESS'")
            total_files = cur.fetchone()[0] or 0

            cur.execute("SELECT COUNT(DISTINCT doc_type) FROM document_records")
            total_categories = cur.fetchone()[0] or 0

            cur.execute("SELECT COUNT(*) FROM document_records")
            total_docs = cur.fetchone()[0] or 0

            cur.execute("SELECT AVG(confidence) FROM document_records WHERE confidence IS NOT NULL")
            avg_confidence = float(cur.fetchone()[0] or 0.0)

            cur.execute("SELECT COUNT(*) FROM document_records WHERE parsing_method = 'llm'")
            llm_count = cur.fetchone()[0] or 0
            ai_share = (llm_count / total_docs * 100) if total_docs > 0 else 0.0

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Total processed files", total_files)
            with c2:
                st.metric("Document categories", total_categories)
            with c3:
                st.metric("Total parsed records", total_docs)
            with c4:
                st.metric("Average confidence", f"{avg_confidence:.1%}")
            with c5:
                st.metric("AI extraction share", f"{ai_share:.0f}%")

        except Exception as e:
            st.caption(f"Could not load database metrics summary: {e}")

        st.space("medium")

        if df_docs_all.empty:
            st.info("Belum ada data analitik. Silakan proses dokumen terlebih dahulu pada tab Document processor.", icon=":material/info:")
        else:
            st.markdown("##### 📈 Distribution & performance insights")
            
            c_chart1, c_chart2 = st.columns(2, gap="medium")
            
            with c_chart1:
                with st.container(border=True):
                    st.markdown("**:material/folder: Document breakdown by category**")
                    cat_counts = df_docs_all["doc_type"].value_counts().reset_index()
                    cat_counts.columns = ["Category", "Count"]
                    st.bar_chart(cat_counts, x="Category", y="Count", color="#38bdf8")

            with c_chart2:
                with st.container(border=True):
                    st.markdown("**:material/auto_awesome: Parsing engine breakdown**")
                    method_counts = df_docs_all["parsing_method"].value_counts().reset_index()
                    method_counts.columns = ["Method", "Count"]
                    st.bar_chart(method_counts, x="Method", y="Count", color="#818cf8")

            st.space("small")

            c_chart3, c_chart4 = st.columns(2, gap="medium")
            
            with c_chart3:
                with st.container(border=True):
                    st.markdown("**:material/verified: Average confidence score per category**")
                    if "confidence" in df_docs_all.columns:
                        conf_avg = df_docs_all.groupby("doc_type")["confidence"].mean().reset_index()
                        conf_avg.columns = ["Category", "Confidence (%)"]
                        conf_avg["Confidence (%)"] = (conf_avg["Confidence (%)"] * 100).round(1)
                        st.bar_chart(conf_avg, x="Category", y="Confidence (%)", color="#34d399")

            with c_chart4:
                with st.container(border=True):
                    st.markdown("**:material/schedule: Processing timeline activity**")
                    if "processed_at" in df_docs_all.columns:
                        df_time = df_docs_all.copy()
                        df_time["date"] = pd.to_datetime(df_time["processed_at"]).dt.date
                        time_counts = df_time.groupby("date").size().reset_index(name="Volume")
                        st.line_chart(time_counts, x="date", y="Volume", color="#f43f5e")

    # Helper function for developer-only tabs
    def render_dev_lock_notice():
        with st.container(border=True):
            st.markdown("##### :material/shield_lock: Developer Private Access Required")
            st.info("Inspeksi raw database, audit log, dan tabel spesifik ini diproteksi khusus untuk Developer. Aktifkan **Developer mode** pada sidebar sebelah kiri untuk membuka akses.", icon=":material/lock:")

    # --------------------------------------------------------------------------
    # Sub-tab 2: PRIVATE — All parsed documents with filter & JSON viewer
    # --------------------------------------------------------------------------
    with db_tab_records:
        if not is_dev:
            render_dev_lock_notice()
        elif df_docs_all.empty:
            st.info("No document records found in database.", icon=":material/info:")
        else:
            # Filter bar
            f_col1, f_col2, f_col3 = st.columns([1, 1, 2], gap="small")
            
            categories = ["All categories"] + sorted(df_docs_all["doc_type"].dropna().unique().tolist())
            with f_col1:
                selected_cat = st.selectbox("Filter category", options=categories, label_visibility="collapsed")
            
            methods = ["All methods"] + sorted(df_docs_all["parsing_method"].dropna().unique().tolist())
            with f_col2:
                selected_method = st.selectbox("Filter method", options=methods, label_visibility="collapsed")

            with f_col3:
                search_query = st.text_input("Search filename / path", placeholder="Search document by path or filename...", label_visibility="collapsed")

            # Apply filters
            df_filtered = df_docs_all.copy()
            if selected_cat != "All categories":
                df_filtered = df_filtered[df_filtered["doc_type"] == selected_cat]
            if selected_method != "All methods":
                df_filtered = df_filtered[df_filtered["parsing_method"] == selected_method]
            if search_query.strip():
                df_filtered = df_filtered[df_filtered["file_path"].str.contains(search_query.strip(), case=False, na=False)]

            st.caption(f"Showing **{len(df_filtered)}** of **{len(df_docs_all)}** document record(s)")

            # Table view
            df_display_table = df_filtered.drop(columns=["parsed_data"]) if "parsed_data" in df_filtered.columns else df_filtered

            st.dataframe(df_display_table, width="stretch")

            # Download CSV option for filtered metadata
            st.download_button(
                "Download filtered list (CSV)",
                data=df_display_table.to_csv(index=False),
                file_name="document_records_export.csv",
                mime="text/csv",
                icon=":material/download:"
            )

            st.space("small")

            # Interactive Detail Viewer for single document record
            with st.expander("🔍 Inspect structured JSON payload for a document", icon=":material/data_object:"):
                doc_options = df_filtered["id"].astype(str) + " — " + df_filtered["doc_type"].astype(str) + " (" + df_filtered["file_path"].apply(lambda p: os.path.basename(str(p))) + ")"
                if not doc_options.empty:
                    selected_doc_label = st.selectbox("Select document record to inspect", options=doc_options.tolist())
                    selected_id = int(selected_doc_label.split(" — ")[0])
                    doc_row = df_filtered[df_filtered["id"] == selected_id].iloc[0]

                    col_d1, col_d2 = st.columns([1, 2], gap="medium")
                    with col_d1:
                        st.markdown(f"**ID:** `{doc_row['id']}`")
                        st.markdown(f"**File:** `{doc_row['file_path']}`")
                        st.markdown(f"**Category:** `{doc_row['doc_type']}`")
                        st.markdown(f"**Subtype:** `{doc_row['doc_subtype']}`")
                        conf_disp = 0.0
                        try:
                            if pd.notnull(doc_row.get("confidence")):
                                conf_disp = float(doc_row["confidence"])
                        except Exception:
                            conf_disp = 0.0
                        st.markdown(f"**Confidence:** `{conf_disp:.0%}`")
                        st.markdown(f"**Method:** `{doc_row['parsing_method']}`")
                        st.markdown(f"**Processed at:** `{doc_row['processed_at']}`")
                    with col_d2:
                        raw_json = doc_row['parsed_data']
                        try:
                            json_obj = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                            st.json(json_obj)
                        except Exception:
                            st.text(raw_json)
                else:
                    st.caption("No document matching current filters.")

    # --------------------------------------------------------------------------
    # Sub-tab 3: PRIVATE — Processed files audit log
    # --------------------------------------------------------------------------
    with db_tab_audit:
        if not is_dev:
            render_dev_lock_notice()
        else:
            try:
                df_log = pd.read_sql_query("SELECT * FROM processed_files ORDER BY processed_at DESC", conn)
                
                succ_count = len(df_log[df_log["status"] == "SUCCESS"])
                fail_count = len(df_log[df_log["status"] == "FAILED"])
                
                l1, l2 = st.columns(2)
                with l1:
                    st.metric("Successfully processed files", f"{succ_count}")
                with l2:
                    st.metric("Failed processing attempts", f"{fail_count}")

                st.space("small")
                st.dataframe(df_log, width="stretch")
            except Exception as e:
                st.caption(f"Could not load processed files log: {e}")

    # --------------------------------------------------------------------------
    # Sub-tab 4: PRIVATE — Specialized tables (KTP & Bank Transactions)
    # --------------------------------------------------------------------------
    with db_tab_tables:
        if not is_dev:
            render_dev_lock_notice()
        else:
            st.markdown("##### Specialized structured tables inspector")
            st.caption("Inspect domain-specific tables for structured bank transactions or identity cards.")

            with st.expander("💳 Bank transactions table (`bank_transactions`)", icon=":material/credit_card:"):
                try:
                    df_tx_all = pd.read_sql_query("SELECT * FROM bank_transactions ORDER BY id DESC", conn)
                    if df_tx_all.empty:
                        st.caption("No bank statement transaction records found.")
                    else:
                        st.dataframe(df_tx_all, width="stretch")
                        if "type" in df_tx_all.columns:
                            st.markdown("###### Debit vs credit summary by file")
                            chart_data = df_tx_all.groupby(["file_path", "type"])["amount"].sum().unstack(fill_value=0)
                            st.bar_chart(chart_data)
                except Exception as e:
                    st.caption(f"Error loading bank transactions: {e}")

            with st.expander("🪪 KTP records table (`ktp_records`)", icon=":material/badge:"):
                try:
                    df_ktp = pd.read_sql_query("SELECT * FROM ktp_records ORDER BY id DESC", conn)
                    if df_ktp.empty:
                        st.caption("No KTP records found.")
                    else:
                        st.dataframe(df_ktp, width="stretch")
                except Exception as e:
                    st.caption(f"Error loading KTP records: {e}")

    conn.close()

# ==============================================================================
# TAB 4: Fitur Lanjutan & Batch (Advanced ETL & Evaluator)
# ==============================================================================
with tab_advanced:
    st.markdown("#### :material/settings: Fitur Lanjutan & Pemrosesan Batch")
    st.caption("Gunakan menu ini untuk memproses banyak berkas sekaligus dalam satu folder atau menguji tingkat akurasi ekstraksi.")

    adv_tab1, adv_tab2 = st.tabs([
        "⚙️ Pemrosesan batch (Banyak berkas)",
        "🎯 Pengujian akurasi (CER / WER)"
    ])

    with adv_tab1:
        st.markdown("##### Pemrosesan otomatis folder berkas")
        st.caption("Pindai dan proses seluruh dokumen di dalam direktori folder sekaligus.")

        with st.container(border=True):
            st.markdown("<div class='section-card-title'>:material/folder: Lokasi Folder Input</div>", unsafe_allow_html=True)
            custom_input_dir = st.text_input(
                "Jalur folder lokal",
                value=DEFAULT_INPUT_DIR,
                help="Ketik alamat folder di komputer Anda (misal: data/input)"
            )

        unprocessed_files = get_unprocessed_files(input_dir=custom_input_dir)

        if not os.path.exists(custom_input_dir):
            st.error(f"Folder '{custom_input_dir}' tidak ditemukan pada sistem.", icon=":material/error:")
        elif not unprocessed_files:
            st.success(f"Semua berkas di dalam `{custom_input_dir}` sudah selesai diproses!", icon=":material/check_circle:")
        else:
            st.info(f"Ditemukan **{len(unprocessed_files)}** dokumen yang belum diproses di `{custom_input_dir}`:", icon=":material/folder_open:")
            for f in unprocessed_files:
                st.caption(f":material/description: `{f}`")

            if st.button("Jalankan pemrosesan batch", icon=":material/rocket_launch:", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                use_llm_flag = parsing_mode != "regex"
                success_count = 0

                for idx, f in enumerate(unprocessed_files):
                    status_text.text(f"Memproses ({idx+1}/{len(unprocessed_files)}): {f}")
                    success = process_file(f, engine=engine_choice, use_llm=use_llm_flag)
                    if success:
                        success_count += 1
                    progress_bar.progress((idx + 1) / len(unprocessed_files))

                status_text.text("Pemrosesan batch selesai!")
                st.toast(f"Berhasil memproses {success_count} dari {len(unprocessed_files)} berkas!", icon="🚀")

    with adv_tab2:
        st.markdown("##### Pengujian akurasi ekstraksi")
        st.caption("Bandingkan hasil pembacaan teks/JSON dengan dokumen acuan asli (Ground Truth).")

        eval_mode = st.segmented_control(
            "Mode evaluasi",
            options=["ocr", "json"],
            format_func=lambda x: "🔤 Akurasi karakter (CER/WER)" if x == "ocr" else "📦 Akurasi field JSON",
            default="ocr",
            label_visibility="collapsed"
        )

        st.space("small")

        if eval_mode == "ocr":
            col_gt, col_ocr = st.columns(2, gap="medium")
            with col_gt:
                with st.container(border=True):
                    st.markdown("<div class='section-card-title'>:material/description: Dokumen Asli (Ground Truth)</div>", unsafe_allow_html=True)
                    gt_file = st.file_uploader("Unggah berkas dokumen acuan", type=["pdf", "txt", "jpg", "png"], key="gt_eval")
            with col_ocr:
                with st.container(border=True):
                    st.markdown("<div class='section-card-title'>:material/output: Berkas Teks OCR</div>", unsafe_allow_html=True)
                    ocr_file = st.file_uploader("Unggah berkas teks hasil OCR (.txt)", type=["txt"], key="ocr_eval")

            if gt_file and ocr_file:
                if st.button("Hitung skor akurasi OCR", icon=":material/analytics:", type="primary"):
                    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(gt_file.name)[1], delete=False) as f_gt:
                        f_gt.write(gt_file.getvalue())
                        gt_tmp = f_gt.name

                    gt_pages = load_ground_truth(gt_tmp)
                    ocr_text = ocr_file.getvalue().decode("utf-8")

                    if gt_pages:
                        stats = evaluate_ocr_accuracy(gt_pages, ocr_text)

                        st.markdown("##### Ringkasan akurasi")
                        m1, m2, m3, m4 = st.columns(4)
                        with m1:
                            st.metric("CER (Character Error)", f"{stats['overall_cer']*100:.2f}%")
                        with m2:
                            st.metric("WER (Word Error)", f"{stats['overall_wer']*100:.2f}%")
                        with m3:
                            st.metric("Rata-rata CER halaman", f"{stats['mean_cer']*100:.2f}%")
                        with m4:
                            st.metric("Akurasi keseluruhan", f"{stats['overall_accuracy']:.2f}%")

                        st.markdown("##### Rincian akurasi per halaman")
                        df_pages = pd.DataFrame(stats["page_metrics"])
                        st.dataframe(df_pages, width="stretch")
                    else:
                        st.error("Gagal membaca teks dari berkas acuan Ground Truth.", icon=":material/error:")

        else:
            col_gt_j, col_res_j = st.columns(2, gap="medium")
            with col_gt_j:
                with st.container(border=True):
                    st.markdown("<div class='section-card-title'>:material/data_object: JSON Acuan (Ground Truth)</div>", unsafe_allow_html=True)
                    gt_json_file = st.file_uploader("Unggah JSON acuan", type=["json"], key="gt_json")
            with col_res_j:
                with st.container(border=True):
                    st.markdown("<div class='section-card-title'>:material/fact_check: JSON Hasil Extraction</div>", unsafe_allow_html=True)
                    res_json_file = st.file_uploader("Unggah JSON hasil", type=["json"], key="res_json")

            if gt_json_file and res_json_file:
                if st.button("Hitung kecocokan field JSON", icon=":material/analytics:", type="primary"):
                    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_gt:
                        f_gt.write(gt_json_file.getvalue())
                        gt_j_tmp = f_gt.name
                    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_res:
                        f_res.write(res_json_file.getvalue())
                        res_j_tmp = f_res.name

                    report = evaluate_parsing_accuracy(gt_j_tmp, res_j_tmp)

                    if report:
                        st.markdown("##### Ringkasan akurasi JSON")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("Akurasi field", f"{report['accuracy']:.2f}%")
                        with c2:
                            st.metric("Field cocok", report['matched_fields'])
                        with c3:
                            st.metric("Field tidak cocok", len(report['mismatched_fields']))
                        with c4:
                            st.metric("Field hilang", len(report['missing_fields']))

                        if report["mismatched_fields"]:
                            st.markdown("##### Rincian field tidak cocok")
                            df_mismatch = pd.DataFrame(report["mismatched_fields"])
                            st.dataframe(df_mismatch, width="stretch")
