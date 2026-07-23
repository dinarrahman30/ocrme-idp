import os
import sqlite3
import datetime
import logging
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf
from src.parser import parse_bca_statement, parse_ktp, save_to_json, save_to_csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/etl_pipeline.log", encoding="utf-8")
    ]
)

DB_PATH = "data/ocr_database.db"
INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"

def init_db():
    """Initializes the SQLite database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
    
    conn.commit()
    conn.close()
    logging.info("SQLite database initialized successfully.")

def get_unprocessed_files():
    """Returns list of files in INPUT_DIR that have not been processed successfully."""
    if not os.path.exists(INPUT_DIR):
        logging.warning(f"Input directory '{INPUT_DIR}' does not exist.")
        return []
        
    all_files = []
    for root, _, files in os.walk(INPUT_DIR):
        for file in files:
            _, ext = os.path.splitext(file.lower())
            if ext in [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
                all_files.append(os.path.join(root, file))
                
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM processed_files WHERE status = 'SUCCESS'")
    processed = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    unprocessed = [f for f in all_files if f not in processed]
    return unprocessed

def load_ktp_to_db(file_path, data):
    """Loads a single parsed KTP record into SQLite."""
    conn = sqlite3.connect(DB_PATH)
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

def load_transactions_to_db(file_path, transactions):
    """Loads parsed bank statement transactions into SQLite."""
    conn = sqlite3.connect(DB_PATH)
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

def update_file_status(file_path, status, error_message=None):
    """Updates the processing status of a file in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO processed_files (file_path, status, error_message, processed_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (file_path, status, error_message))
    conn.commit()
    conn.close()

def process_file(file_path, engine="easyocr"):
    """Runs OCR, parses text, and writes structured outputs to disk and database."""
    logging.info(f"Starting processing for file: {file_path}")
    base_name, file_ext = os.path.splitext(os.path.basename(file_path))
    file_ext = file_ext.lower()
    
    # 1. OCR Extraction
    try:
        if file_ext == ".pdf":
            extracted_text = process_pdf(file_path, dpi=200, engine=engine)
        else:
            clean_img = clean_image(file_path)
            extracted_text = image_to_text(clean_img, lang='ind+eng', engine=engine)
    except Exception as e:
        error_msg = f"OCR execution failed: {str(e)}"
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg)
        return False

    if not extracted_text.strip():
        error_msg = "Extracted text is empty."
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg)
        return False

    # Save raw extracted text
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_text_path = os.path.join(OUTPUT_DIR, f"hasil_{base_name}.txt")
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    logging.info(f"Raw text output saved to {raw_text_path}")

    # 2. Parsing & Loading
    text_lower = extracted_text.lower()
    is_ktp = "ktp" in base_name.lower() or "nik" in text_lower
    is_bca = "bca" in base_name.lower() or "mutasi" in text_lower or "saldo" in text_lower
    
    try:
        if is_ktp:
            logging.info("KTP format detected. Parsing fields...")
            parsed_data = parse_ktp(extracted_text)
            
            # Save files
            json_path = os.path.join(OUTPUT_DIR, f"hasil_{base_name}.json")
            save_to_json(parsed_data, json_path)
            
            # Load to DB
            load_ktp_to_db(file_path, parsed_data)
            logging.info(f"Parsed KTP data saved to JSON and loaded into SQLite.")
            
        elif is_bca:
            logging.info("BCA Statement format detected. Parsing transactions...")
            parsed_data = parse_bca_statement(extracted_text)
            
            # Save files
            json_path = os.path.join(OUTPUT_DIR, f"hasil_{base_name}.json")
            csv_path = os.path.join(OUTPUT_DIR, f"hasil_{base_name}.csv")
            save_to_json(parsed_data, json_path)
            save_to_csv(parsed_data, csv_path)
            
            # Load to DB
            load_transactions_to_db(file_path, parsed_data)
            logging.info(f"Parsed {len(parsed_data)} transactions to JSON/CSV and loaded into SQLite.")
            
        else:
            logging.warning("Unknown document format. Skipping parsing step.")
            update_file_status(file_path, "SUCCESS", "Parsed as generic/unknown format")
            return True
            
        update_file_status(file_path, "SUCCESS")
        return True
        
    except Exception as e:
        error_msg = f"Parsing or Database loading failed: {str(e)}"
        logging.error(error_msg)
        update_file_status(file_path, "FAILED", error_msg)
        return False

def main():
    print("====================================================")
    print("                OCR ETL PIPELINE RUNNER             ")
    print("====================================================\n")
    
    init_db()
    
    unprocessed = get_unprocessed_files()
    if not unprocessed:
        logging.info("No new unprocessed files found.")
        print("\nPipeline finished: Everything is up-to-date.")
        return
        
    print(f"Found {len(unprocessed)} new files to process:")
    for f in unprocessed:
        print(f"  - {f}")
        
    print("\nSelect OCR Engine:")
    print("1. EasyOCR (Layout Preserving - Recommended for statement tables)")
    print("2. Tesseract OCR (Fast - Recommended for plain documents)")
    choice = input("Pilihan (1/2) [Default: 1]: ").strip()
    engine = 'tesseract' if choice == '2' else 'easyocr'
    
    print(f"\nStarting pipeline execution with {engine} engine...\n")
    
    success_count = 0
    for f in unprocessed:
        success = process_file(f, engine=engine)
        if success:
            success_count += 1
            
    print("\n====================================================")
    print("                  PIPELINE SUMMARY                  ")
    print("====================================================")
    print(f"Total files detected : {len(unprocessed)}")
    print(f"Successfully loaded  : {success_count}")
    print(f"Failed               : {len(unprocessed) - success_count}")
    print(f"Database location    : {DB_PATH}")
    print("====================================================")

if __name__ == "__main__":
    main()
