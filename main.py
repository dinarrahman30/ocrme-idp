import os
import argparse
from dotenv import load_dotenv
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf, process_any_file
from src.parser import smart_parse, save_to_json, save_to_csv

# Load environment variables from .env file
load_dotenv()

EXCLUDED_EXTENSIONS = {'.db', '.sqlite', '.log', '.pyc', '.py', '.git', '.ds_store'}

def process_single_file(input_file, output_dir="data/output", engine="easyocr", parsing_mode="auto"):
    """
    Processes any document file from any path on the system.
    
    Args:
        input_file: Path to input document (absolute or relative)
        output_dir: Target directory to save outputs
        engine: 'easyocr' or 'tesseract'
        parsing_mode: 'auto', 'llm', or 'regex'
    """
    input_file = os.path.abspath(os.path.expanduser(input_file))
    
    if not os.path.exists(input_file):
        print(f"[ERROR] Path file tidak ditemukan: {input_file}")
        return False
        
    _, file_ext = os.path.splitext(input_file.lower())
    if file_ext in EXCLUDED_EXTENSIONS:
        print(f"[ERROR] Ekstensi file {file_ext} dikecualikan dari pemrosesan.")
        return False

    os.makedirs(output_dir, exist_ok=True)
    use_llm = parsing_mode != "regex"

    print(f"\n[INFO] Memproses berkas: {input_file}")
    print(f"[INFO] Engine / Parser  : {engine}")
    print(f"[INFO] Metode Parsing : {parsing_mode.upper()}")

    # 1. Universal Text / Content Extraction
    try:
        extracted_text = process_any_file(input_file, engine=engine)
    except Exception as e:
        print(f"[ERROR] Ekstraksi isi berkas gagal: {str(e)}")
        return False

    if not extracted_text.strip():
        print(f"[WARNING] Hasil ekstraksi teks kosong dari file: {input_file}")
        return False

    # 2. Save Raw Text Output
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    txt_filename = f"hasil_{base_name}.txt"
    txt_path = os.path.join(output_dir, txt_filename)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    print(f"[DONE] Teks mentah OCR tersimpan di: {txt_path}")

    # 3. Smart Parsing (LLM dengan Fallback Regex)
    print(f"[INFO] Memulai parsing data terstruktur...")
    result = smart_parse(extracted_text, use_llm=use_llm)
    
    doc_type = result["doc_type"]
    doc_subtype = result["doc_subtype"]
    confidence = result["confidence"]
    parsed_data = result["data"]
    method = result["method"]

    print(f"[INFO] Hasil Klasifikasi: {doc_subtype} ({doc_type}) | Confidence: {confidence:.0%} | Method: {method.upper()}")

    # 4. Save JSON Output
    json_path = os.path.join(output_dir, f"hasil_{base_name}.json")
    output_data = {
        "metadata": {
            "source_file": input_file,
            "ocr_engine": engine,
            "parsing_method": method,
            "doc_type": doc_type,
            "doc_subtype": doc_subtype,
            "confidence": confidence,
        },
        "data": parsed_data,
    }
    save_to_json(output_data, json_path)
    print(f"[DONE] Hasil parsing JSON tersimpan di: {json_path}")

    # 5. Save CSV Output (if transactions present)
    transactions = None
    if isinstance(parsed_data, list):
        transactions = parsed_data
    elif isinstance(parsed_data, dict) and "transactions" in parsed_data:
        transactions = parsed_data["transactions"]

    if transactions and isinstance(transactions, list) and len(transactions) > 0:
        csv_path = os.path.join(output_dir, f"hasil_{base_name}.csv")
        save_to_csv(transactions, csv_path)
        print(f"[DONE] Data transaksi CSV tersimpan di: {csv_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description="OCRMe — Intelligent Document Processing untuk Semua Jenis Dokumen & Path")
    parser.add_argument("-i", "--input", help="Path ke berkas dokumen (contoh: /path/to/invoice.pdf, D:/ktp.jpg, dll.)")
    parser.add_argument("-o", "--output", default="data/output", help="Folder tujuan untuk menyimpan hasil (default: data/output)")
    parser.add_argument("-e", "--engine", choices=["easyocr", "tesseract"], default="easyocr", help="OCR Engine (default: easyocr)")
    parser.add_argument("-m", "--mode", choices=["auto", "llm", "regex"], default="auto", help="Metode Parsing (default: auto)")
    
    args = parser.parse_args()

    print("=" * 52)
    print("          OCRMe — Intelligent Document Processing")
    print("=" * 52)

    # Interactive mode if --input CLI argument is not provided
    if not args.input:
        input_file = input("\nMasukkan path file apapun (Gambar/PDF): ").strip()

        if not os.path.exists(input_file):
            # Check in data/input as fallback shortcut
            input_in_folder = os.path.join("data/input", input_file)
            if os.path.exists(input_in_folder):
                input_file = input_in_folder
            else:
                print(f"[ERROR] Path file '{input_file}' tidak ditemukan.")
                return
        
        output_dir = input("Folder Output [Default: data/output]: ").strip() or "data/output"

        print("\nPilih OCR Engine:")
        print("1. EasyOCR (Layout Preserving — Rekomendasi)")
        print("2. Tesseract OCR (Fast)")
        choice = input("Pilihan (1/2) [Default: 1]: ").strip()
        engine = 'tesseract' if choice == '2' else 'easyocr'

        print("\nPilih Metode Parsing:")
        print("1. 🧠 LLM (Gemini) — Adaptif untuk dokumen apapun [Rekomendasi]")
        print("2. 📐 Regex (Legacy) — Hanya KTP & Mutasi BCA")
        print("3. 🔄 Auto (LLM → Regex fallback)")
        parse_choice = input("Pilihan (1/2/3) [Default: 3]: ").strip()
        parsing_mode = "regex" if parse_choice == "2" else ("llm" if parse_choice == "1" else "auto")

        process_single_file(input_file, output_dir=output_dir, engine=engine, parsing_mode=parsing_mode)
    else:
        process_single_file(args.input, output_dir=args.output, engine=args.engine, parsing_mode=args.mode)

if __name__ == "__main__":
    main()
