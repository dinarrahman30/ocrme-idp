import os
import json
import sqlite3
import argparse
import logging
from dotenv import load_dotenv
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf, process_any_file
from src.parser import smart_parse, save_to_json, save_to_csv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/etl_pipeline.log", encoding="utf-8")
    ]
)

DEFAULT_DB_PATH = "data/ocr_database.db"
DEFAULT_INPUT_DIR = "data/input"
DEFAULT_OUTPUT_DIR = "data/output"
EXCLUDED_EXTENSIONS = {'.db', '.sqlite', '.log', '.pyc', '.py', '.git', '.ds_store'}

def init_db(db_path=DEFAULT_DB_PATH):
    """Initializes the SQLite database schema at any target location."""
    db_path = os.path.abspath(os.path.expanduser(db_path))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Process log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            file_path TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            error_message TEXT
        )
    """)
    
    # KTP records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ktp_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            nik TEXT,
            nama TEXT,
            tempat_tgl_lahir TEXT,
            jenis_kelamin TEXT,
            alamat TEXT,
            rt_rw TEXT,
            kel_desa TEXT,
            kecamatan TEXT,
            agama TEXT,
            status_perkawinan TEXT,
            pekerjaan TEXT,
            kewarganegaraan TEXT,
            berlaku_hingga TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Bank statements transaction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            date TEXT,
            description TEXT,
            amount REAL,
            type TEXT,
            balance REAL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Generic document records table (for LLM-parsed documents of any type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            doc_type TEXT,
            doc_subtype TEXT,
            parsed_data TEXT,
            parsing_method TEXT,
            confidence REAL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logging.info(f"SQLite database initialized at: {db_path}")

def get_unprocessed_files(input_dir=DEFAULT_INPUT_DIR, db_path=DEFAULT_DB_PATH):
    """Returns list of files in input_dir (any path) that have not been processed successfully."""
    input_dir = os.path.abspath(os.path.expanduser(input_dir))
    if not os.path.exists(input_dir):
        logging.warning(f"Input directory '{input_dir}' does not exist.")
        return []
        
    all_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.startswith('.'):
                continue
            _, ext = os.path.splitext(file.lower())
            if ext not in EXCLUDED_EXTENSIONS:
                all_files.append(os.path.join(root, file))
                
    db_path = os.path.abspath(os.path.expanduser(db_path))
    if not os.path.exists(db_path):
        return all_files

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_path FROM processed_files WHERE status = 'SUCCESS'")
        processed = {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        processed = set()
    conn.close()
    
    unprocessed = [f for f in all_files if f not in processed and os.path.abspath(f) not in processed]
    return unprocessed

def load_ktp_to_db(file_path, data, db_path=DEFAULT_DB_PATH):
    """Loads a single parsed KTP record into SQLite."""
    conn = sqlite3.connect(os.path.abspath(os.path.expanduser(db_path)))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ktp_records (
            file_path, nik, nama, tempat_tgl_lahir, jenis_kelamin, alamat, 
            rt_rw, kel_desa, kecamatan, agama, status_perkawinan, 
            pekerjaan, kewarganegaraan, berlaku_hingga
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_path,
        data.get("nik"),
        data.get("nama"),
        data.get("tempat_tgl_lahir"),
        data.get("jenis_kelamin"),
        data.get("alamat"),
        data.get("rt_rw"),
        data.get("kel_desa"),
        data.get("kecamatan"),
        data.get("agama"),
        data.get("status_perkawinan"),
        data.get("pekerjaan"),
        data.get("kewarganegaraan"),
        data.get("berlaku_hingga")
    ))
    conn.commit()
    conn.close()

def load_transactions_to_db(file_path, transactions, db_path=DEFAULT_DB_PATH):
    """Loads parsed bank statement transactions into SQLite."""
    conn = sqlite3.connect(os.path.abspath(os.path.expanduser(db_path)))
    cursor = conn.cursor()
    for tx in transactions:
        cursor.execute("""
            INSERT INTO bank_transactions (
                file_path, date, description, amount, type, balance
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            file_path,
            tx.get("date"),
            tx.get("description"),
            tx.get("amount"),
            tx.get("type"),
            tx.get("balance")
        ))
    conn.commit()
    conn.close()

def load_generic_to_db(file_path, doc_type, doc_subtype, parsed_data, parsing_method, confidence, db_path=DEFAULT_DB_PATH):
    """Loads a generic LLM-parsed document record into SQLite."""
    conn = sqlite3.connect(os.path.abspath(os.path.expanduser(db_path)))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO document_records (
            file_path, doc_type, doc_subtype, parsed_data, parsing_method, confidence
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        file_path,
        doc_type,
        doc_subtype,
        json.dumps(parsed_data, ensure_ascii=False) if not isinstance(parsed_data, str) else parsed_data,
        parsing_method,
        confidence,
    ))
    conn.commit()
    conn.close()

def update_file_status(file_path, status, error_message=None, db_path=DEFAULT_DB_PATH):
    """Updates the processing status of a file in the database."""
    conn = sqlite3.connect(os.path.abspath(os.path.expanduser(db_path)))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO processed_files (file_path, status, error_message, processed_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (file_path, status, error_message))
    conn.commit()
    conn.close()

def process_file(file_path, engine="easyocr", use_llm=True, output_dir=DEFAULT_OUTPUT_DIR, db_path=DEFAULT_DB_PATH):
    """Runs OCR/text extraction, parses text with LLM or regex, and writes structured outputs to disk and database."""
    file_path = os.path.abspath(os.path.expanduser(file_path))
    logging.info(f"Starting processing for file: {file_path}")
    base_name, file_ext = os.path.splitext(os.path.basename(file_path))
    file_ext = file_ext.lower()
    
    # 1. Text Extraction (OCR for images/PDFs, native parser for Office/text files)
    try:
        extracted_text = process_any_file(file_path, engine=engine)
    except Exception as e:
        error_msg = f"Text extraction failed: {str(e)}"
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg, db_path=db_path)
        return False

    if not extracted_text.strip():
        error_msg = "Extracted text is empty."
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg, db_path=db_path)
        return False

    # Save raw extracted text
    os.makedirs(output_dir, exist_ok=True)
    raw_text_path = os.path.join(output_dir, f"hasil_{base_name}.txt")
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    logging.info(f"Raw text output saved to {raw_text_path}")

    # 2. Smart Parsing (LLM with regex fallback)
    try:
        result = smart_parse(extracted_text, use_llm=use_llm)
        
        doc_type = result["doc_type"]
        doc_subtype = result["doc_subtype"]
        confidence = result["confidence"]
        parsed_data = result["data"]
        method = result["method"]

        logging.info(f"Parsed as {doc_type}/{doc_subtype} via {method} (confidence: {confidence})")

        # Save JSON output with metadata
        json_path = os.path.join(output_dir, f"hasil_{base_name}.json")
        output_data = {
            "metadata": {
                "source_file": file_path,
                "ocr_engine": engine,
                "parsing_method": method,
                "doc_type": doc_type,
                "doc_subtype": doc_subtype,
                "confidence": confidence,
            },
            "data": parsed_data,
        }
        save_to_json(output_data, json_path)

        # 3. Load to appropriate database table
        if doc_type == "identity_card":
            ktp_data = parsed_data if isinstance(parsed_data, dict) else {}
            load_ktp_to_db(file_path, ktp_data, db_path=db_path)
            logging.info("Parsed KTP data loaded into SQLite ktp_records.")

        elif doc_type == "bank_statement":
            # Extract transactions list
            transactions = None
            if isinstance(parsed_data, list):
                transactions = parsed_data
            elif isinstance(parsed_data, dict) and "transactions" in parsed_data:
                transactions = parsed_data["transactions"]

            if transactions:
                load_transactions_to_db(file_path, transactions, db_path=db_path)
                logging.info(f"Parsed {len(transactions)} transactions loaded into SQLite bank_transactions.")

                # Also save CSV
                csv_path = os.path.join(output_dir, f"hasil_{base_name}.csv")
                save_to_csv(transactions, csv_path)

        # Always save to generic document_records table for full traceability
        load_generic_to_db(file_path, doc_type, doc_subtype, parsed_data, method, confidence, db_path=db_path)

        update_file_status(file_path, "SUCCESS", db_path=db_path)
        return True
        
    except Exception as e:
        error_msg = f"Parsing or Database loading failed: {str(e)}"
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg, db_path=db_path)
        return False

def main():
    parser = argparse.ArgumentParser(description="OCRMe — Batch ETL Pipeline Runner untuk Folder Apapun")
    parser.add_argument("-d", "--input-dir", default=DEFAULT_INPUT_DIR, help="Folder berisi dokumen-dokumen yang ingin diproses (default: data/input)")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR, help="Folder tujuan hasil ekstraksi (default: data/output)")
    parser.add_argument("-db", "--db-path", default=DEFAULT_DB_PATH, help="Path ke database SQLite (default: data/ocr_database.db)")
    parser.add_argument("-e", "--engine", choices=["easyocr", "tesseract"], default="easyocr", help="OCR Engine (default: easyocr)")
    parser.add_argument("-m", "--mode", choices=["auto", "llm", "regex"], default="auto", help="Metode Parsing (default: auto)")

    args = parser.parse_args()

    print("====================================================")
    print("          OCRMe — ETL PIPELINE RUNNER (LLM)         ")
    print("====================================================\n")
    
    init_db(db_path=args.db_path)
    
    unprocessed = get_unprocessed_files(input_dir=args.input_dir, db_path=args.db_path)
    if not unprocessed:
        logging.info(f"Tidak ada berkas baru yang perlu diproses di folder: '{args.input_dir}'.")
        print("\nPipeline finished: Everything is up-to-date.")
        return
        
    print(f"Ditemukan {len(unprocessed)} berkas di '{args.input_dir}' untuk diproses:")
    for f in unprocessed:
        print(f"  - {f}")
        
    engine = args.engine
    use_llm = args.mode != "regex"
    
    print(f"\nStarting pipeline execution with {engine} engine and {args.mode.upper()} parsing...\n")
    
    success_count = 0
    for f in unprocessed:
        success = process_file(f, engine=engine, use_llm=use_llm, output_dir=args.output_dir, db_path=args.db_path)
        if success:
            success_count += 1
            
    print("\n====================================================")
    print("                  PIPELINE SUMMARY                  ")
    print("====================================================")
    print(f"Input Directory      : {os.path.abspath(args.input_dir)}")
    print(f"Total files detected : {len(unprocessed)}")
    print(f"Successfully loaded  : {success_count}")
    print(f"Failed               : {len(unprocessed) - success_count}")
    print(f"Database location    : {os.path.abspath(args.db_path)}")
    print("====================================================")

if __name__ == "__main__":
    main()
