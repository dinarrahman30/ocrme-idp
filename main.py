import os
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf
from src.parser import parse_bca_statement, parse_ktp, save_to_json, save_to_csv

def main():
    print("=============")
    print("OCRSample")
    print("=============")
    input_file = input("Masukkan path file (Gambar/PDF): ").strip()

    # Cari file di path input langsung atau di dalam folder data/input/
    if not os.path.exists(input_file):
        input_in_folder = os.path.join("data/input", input_file)
        if os.path.exists(input_in_folder):
            input_file = input_in_folder
        else:
            print(f"[ERROR] Path file tidak ditemukan")
            return
    
    output_dir = "data/output/"
    os.makedirs(output_dir, exist_ok=True)

    print("\nPilih OCR Engine:")
    print("1. Tesseract OCR (Default)")
    print("2. EasyOCR (Layout Preserving)")
    choice = input("Pilihan (1/2): ").strip()
    engine = 'easyocr' if choice == '2' else 'tesseract'

    parse_choice = input("Parse hasil ke structured JSON/CSV? (y/n) [Default: y]: ").strip().lower()
    should_parse = parse_choice != 'n'

    _, file_ext = os.path.splitext(input_file.lower())

    print(f"\nMemulai pemrosesan file: {input_file} ({file_ext}) dengan engine {engine}")

    if file_ext == ".pdf":
        extracted_text = process_pdf(input_file, dpi=200, engine=engine)
    elif file_ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
        clean_img = clean_image(input_file)
        extracted_text = image_to_text(clean_img, lang='ind+eng', engine=engine)
    else:
        print(f"[ERROR] Format file tidak didukung: {file_ext}")
        return
    
    # Simpan hasil ekstraksi teks mentah dengan ekstensi .txt
    base_name, _ = os.path.splitext(os.path.basename(input_file))
    output_filename = f"hasil_{base_name}.txt"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    print(f"[DONE] Hasil teks mentah tersimpan di {output_path}")

    # Lakukan parsing jika diaktifkan
    if should_parse:
        text_lower = extracted_text.lower()
        is_ktp = "ktp" in base_name.lower() or "nik" in text_lower
        is_bca = "bca" in base_name.lower() or "mutasi" in text_lower or "saldo" in text_lower

        if is_ktp:
            print("[INFO] Mendeteksi dokumen sebagai KTP. Memulai parsing...")
            parsed_data = parse_ktp(extracted_text)
            json_path = os.path.join(output_dir, f"hasil_{base_name}.json")
            save_to_json(parsed_data, json_path)
            print(f"[DONE] Hasil parsing KTP tersimpan di {json_path}")
        elif is_bca:
            print("[INFO] Mendeteksi dokumen sebagai Mutasi BCA. Memulai parsing...")
            parsed_data = parse_bca_statement(extracted_text)
            json_path = os.path.join(output_dir, f"hasil_{base_name}.json")
            csv_path = os.path.join(output_dir, f"hasil_{base_name}.csv")
            save_to_json(parsed_data, json_path)
            save_to_csv(parsed_data, csv_path)
            print(f"[DONE] Hasil parsing Mutasi tersimpan di:")
            print(f"       - JSON: {json_path}")
            print(f"       - CSV: {csv_path}")
        else:
            print("[WARNING] Jenis dokumen tidak dikenali. Parsing dilewati.")

if __name__ == "__main__":
    main()
