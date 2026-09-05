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
    st.markdown("### :material/tune: Control panel")
    st.caption("Configure AI providers, models, OCR engines, and API keys.")
    st.space("small")

    # Developer Mode Authentication Toggle
    is_developer = st.session_state.get("dev_authenticated", False)
    dev_toggle = st.toggle("🔐 Developer mode", value=is_developer, help="Unlock raw database inspector, audit logs, and domain tables.")
    if dev_toggle != is_developer:
        if dev_toggle:
            dev_pass = st.text_input("Developer password", type="password", key="dev_pass_input", placeholder="Ketik sandi developer (cth: admin)...")
            if dev_pass in ["admin", "developer", "ocrme"]:
                st.session_state["dev_authenticated"] = True
                st.toast("Developer mode unlocked!", icon="🔓")
                st.rerun()
            elif dev_pass:
                st.error("Sandi developer salah.", icon=":material/lock:")
        else:
            st.session_state["dev_authenticated"] = False
            st.toast("Developer mode locked", icon="🔒")
            st.rerun()

    st.space("small")

    # AI Provider Selection Dropdown
    st.markdown("**AI provider selection**")
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
            placeholder="Masukkan OpenAI API Key Anda",
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
            placeholder="Masukkan Anthropic API Key Anda",
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
            placeholder="Masukkan Gemini API Key Anda"
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        model_name_input = st.text_input("Gemini model", value="gemini-3.6-flash", placeholder="gemini-3.6-flash")

    st.space("small")

    # OCR Engine Selector
    st.markdown("**OCR engine selection**")
    engine_choice = st.segmented_control(
        "OCR engine",
        options=["easyocr", "tesseract"],
        format_func=lambda x: "EasyOCR (Layout preserving)" if x == "easyocr" else "Tesseract OCR (Fast)",
        default="easyocr",
        label_visibility="collapsed"
    )

    st.space("small")

    # Parsing Method Selector
    st.markdown("**Parsing & AI mode**")
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

    # System Status Card
    with st.container(border=True):
        st.markdown("##### :material/monitor_heart: System status")
        has_key = bool(api_key_input) or ai_provider == "ollama"
        if has_key:
            st.caption(":material/check_circle: **AI Provider**: Active")
        else:
            st.caption(":material/offline_bolt: **AI Provider**: Regex mode")
        
        st.caption(f":material/document_scanner: **OCR Engine**: {engine_choice.upper()}")
        st.caption(f":material/schema: **Parsing Mode**: {parsing_mode.upper()}")

    st.space("medium")
    st.markdown("""
    <div style="font-size: 12px; color: #64748b; line-height: 1.5; text-align: center;">
        OCRMe v2.5 General Document Engine<br/>
        Supported formats: PDF, Image, Word, Excel, PPT, Text, JSON
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# Main Content Area
# ==============================================================================

# Top Header Hero Banner
st.markdown("""
<div class="main-header-card">
    <div class="badge-pill">✨ Universal Document Intelligence System</div>
    <div class="main-title">🔍 OCRMe — Intelligent Document Processing</div>
    <div class="main-subtitle">
        Automated text extraction, multi-category document classification, and AI-powered structured data parsing for any document type—invoices, receipts, tax forms, identity cards, bank statements, spreadsheets, and Office files.
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_playground, tab_database, tab_eval, tab_etl, tab_guide = st.tabs([
    "📑 Document processor",
    "📊 Database & analytics",
    "🎯 Accuracy evaluator",
    "⚙️ Batch ETL pipeline",
    "📘 Panduan pengguna"
])

# ==============================================================================
# TAB 1: Live Document Processor & Playground
# ==============================================================================
with tab_playground:
    st.markdown("#### :material/file_present: Process Single Document")
    st.caption("Upload any file format or enter a local file path to run instant extraction & multi-modal AI parsing.")

    input_method = st.segmented_control(
        "Input method",
        options=["upload", "local_path"],
        format_func=lambda x: "☁️ Upload file (drag & drop)" if x == "upload" else "💻 Local file path",
        default="upload",
        label_visibility="collapsed"
    )

    tmp_path = None
    file_name = None
    file_ext = None

    if input_method == "upload":
        st.markdown("""
        <div>
            <span class="format-badge fmt-pdf">PDF</span>
            <span class="format-badge fmt-img">PNG / JPG / WEBP</span>
            <span class="format-badge fmt-doc">DOCX / PPTX</span>
            <span class="format-badge fmt-xls">XLSX / CSV</span>
            <span class="format-badge fmt-doc">TXT / JSON</span>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose a document file",
            type=None,
            help="Drag and drop any document format (PDF, PNG, JPG, DOCX, XLSX, TXT, JSON, etc.)",
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
                "Enter local file path on your computer",
                placeholder="/home/user/Documents/invoice.pdf or C:\\Scans\\document.docx",
                help="Enter any absolute or relative path to a file on your filesystem."
            )
            if local_path and os.path.exists(local_path):
                tmp_path = os.path.abspath(os.path.expanduser(local_path))
                file_name = os.path.basename(tmp_path)
                file_ext = os.path.splitext(file_name.lower())[1]
                st.caption(f":material/check_circle: File found: `{tmp_path}`")
            elif local_path:
                st.caption(f":material/error: File not found: `{local_path}`")

    # Quick sample test helper (if files exist in data/input)
    if tmp_path is None and os.path.exists(DEFAULT_INPUT_DIR):
        all_in_folder = [os.path.join(DEFAULT_INPUT_DIR, f) for f in os.listdir(DEFAULT_INPUT_DIR) if not f.startswith(".")]
        if all_in_folder:
            st.space("small")
            with st.expander("💡 Or test quickly with a sample document from data/input", icon=":material/lightbulb:"):
                sample_selected = st.selectbox("Select sample file", options=["Select sample file..."] + [os.path.basename(f) for f in all_in_folder])
                if sample_selected != "Select sample file...":
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
            st.info("Inspeksi raw database, audit log, dan tabel spesifik ini diproteksi khusus untuk Developer. Aktifkan **Developer mode** pada sidebar sebelah kiri (masukkan password `admin`) untuk membuka akses.", icon=":material/lock:")

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
# TAB 3: Accuracy Evaluator Suite
# ==============================================================================
with tab_eval:
    st.markdown("#### :material/target: Accuracy Evaluator Suite")
    st.caption("Evaluate OCR character accuracy (CER/WER) or JSON field extraction accuracy against ground truth benchmarks.")

    eval_mode = st.segmented_control(
        "Evaluation mode",
        options=["ocr", "json"],
        format_func=lambda x: "🔤 OCR Accuracy (CER/WER)" if x == "ocr" else "📦 JSON Parsing Field Accuracy",
        default="ocr",
        label_visibility="collapsed"
    )

    st.space("small")

    if eval_mode == "ocr":
        col_gt, col_ocr = st.columns(2, gap="medium")
        with col_gt:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/description: Ground Truth Document</div>", unsafe_allow_html=True)
                gt_file = st.file_uploader("Upload ground truth file (PDF, TXT, JPG)", type=["pdf", "txt", "jpg", "png"], key="gt_eval")
        with col_ocr:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/output: OCR Output Text File</div>", unsafe_allow_html=True)
                ocr_file = st.file_uploader("Upload OCR output file (.txt)", type=["txt"], key="ocr_eval")

        if gt_file and ocr_file:
            if st.button("Calculate OCR accuracy", icon=":material/analytics:", type="primary"):
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(gt_file.name)[1], delete=False) as f_gt:
                    f_gt.write(gt_file.getvalue())
                    gt_tmp = f_gt.name

                gt_pages = load_ground_truth(gt_tmp)
                ocr_text = ocr_file.getvalue().decode("utf-8")

                if gt_pages:
                    stats = evaluate_ocr_accuracy(gt_pages, ocr_text)

                    st.markdown("##### Accuracy summary")
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("CER (Character error)", f"{stats['overall_cer']*100:.2f}%", help="Character Error Rate: lower is better")
                    with m2:
                        st.metric("WER (Word error)", f"{stats['overall_wer']*100:.2f}%", help="Word Error Rate: lower is better")
                    with m3:
                        st.metric("Page mean CER", f"{stats['mean_cer']*100:.2f}%")
                    with m4:
                        st.metric("Overall accuracy", f"{stats['overall_accuracy']:.2f}%")

                    st.markdown("##### Page-by-page breakdown")
                    df_pages = pd.DataFrame(stats["page_metrics"])
                    st.dataframe(df_pages, width="stretch")
                else:
                    st.error("Could not read text from Ground Truth file.", icon=":material/error:")

    else:
        col_gt_j, col_res_j = st.columns(2, gap="medium")
        with col_gt_j:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/data_object: Ground Truth JSON</div>", unsafe_allow_html=True)
                gt_json_file = st.file_uploader("Upload ground truth JSON", type=["json"], key="gt_json")
        with col_res_j:
            with st.container(border=True):
                st.markdown("<div class='section-card-title'>:material/fact_check: Result JSON</div>", unsafe_allow_html=True)
                res_json_file = st.file_uploader("Upload result JSON", type=["json"], key="res_json")

        if gt_json_file and res_json_file:
            if st.button("Calculate JSON field accuracy", icon=":material/analytics:", type="primary"):
                with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_gt:
                    f_gt.write(gt_json_file.getvalue())
                    gt_j_tmp = f_gt.name
                with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_res:
                    f_res.write(res_json_file.getvalue())
                    res_j_tmp = f_res.name

                report = evaluate_parsing_accuracy(gt_j_tmp, res_j_tmp)

                if report:
                    st.markdown("##### Parsing accuracy summary")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Field accuracy", f"{report['accuracy']:.2f}%")
                    with c2:
                        st.metric("Matched fields", report['matched_fields'])
                    with c3:
                        st.metric("Mismatched fields", len(report['mismatched_fields']))
                    with c4:
                        st.metric("Missing fields", len(report['missing_fields']))

                    if report["mismatched_fields"]:
                        st.markdown("##### Mismatched fields detail")
                        df_mismatch = pd.DataFrame(report["mismatched_fields"])
                        st.dataframe(df_mismatch, width="stretch")

# ==============================================================================
# TAB 4: Batch ETL Pipeline (Custom Directory Support)
# ==============================================================================
with tab_etl:
    st.markdown("#### :material/rocket_launch: Batch ETL Pipeline Runner")
    st.caption("Scan and process all documents in any target directory automatically.")

    with st.container(border=True):
        st.markdown("<div class='section-card-title'>:material/folder: Directory Configuration</div>", unsafe_allow_html=True)
        custom_input_dir = st.text_input(
            "Target input folder path",
            value=DEFAULT_INPUT_DIR,
            help="Enter any local folder path on your machine (e.g. /home/user/Documents/Scans)"
        )

    unprocessed_files = get_unprocessed_files(input_dir=custom_input_dir)

    if not os.path.exists(custom_input_dir):
        st.error(f"Folder '{custom_input_dir}' not found on file system.", icon=":material/error:")
    elif not unprocessed_files:
        st.success(f"All files in `{custom_input_dir}` are processed and up-to-date!", icon=":material/check_circle:")
    else:
        st.info(f"Found **{len(unprocessed_files)}** unprocessed document(s) in `{custom_input_dir}`:", icon=":material/folder_open:")
        for f in unprocessed_files:
            st.caption(f":material/description: `{f}`")

        if st.button("Run batch ETL pipeline", icon=":material/rocket_launch:", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            use_llm_flag = parsing_mode != "regex"
            success_count = 0

            for idx, f in enumerate(unprocessed_files):
                status_text.text(f"Processing ({idx+1}/{len(unprocessed_files)}): {f}")
                success = process_file(f, engine=engine_choice, use_llm=use_llm_flag)
                if success:
                    success_count += 1
                progress_bar.progress((idx + 1) / len(unprocessed_files))

            status_text.text("Batch ETL completed!")
            st.toast(f"Successfully processed {success_count} of {len(unprocessed_files)} files!", icon="🚀")

# ==============================================================================
# TAB 5: Panduan Pengguna (User Guide & Safety Documentation)
# ==============================================================================
with tab_guide:
    st.markdown("#### :material/menu_book: Panduan Penggunaan Aplikasi OCRMe")
    st.caption("Panduan lengkap penggunaan fitur, pilihan AI provider, dan jaminan keamanan data.")

    guide_path = os.path.join(os.path.dirname(__file__), "PANDUAN_PENGGUNA.md")
    if os.path.exists(guide_path):
        with open(guide_path, "r", encoding="utf-8") as gf:
            guide_md = gf.read()
        with st.container(border=True):
            st.markdown(guide_md)
    else:
        st.info("File `PANDUAN_PENGGUNA.md` tidak ditemukan.")
