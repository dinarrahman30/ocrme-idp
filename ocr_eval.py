# evaluate_pdf_vs_txt.py
import os
import re
import statistics
import PyPDF2
from jiwer import cer, wer

def extract_text_from_pdf_pages(pdf_path):
    """Mengekstrak teks per halaman dari PDF master (Ground Truth)."""
    pages = []
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                pages.append(page.extract_text() or "")
        return pages
    except Exception as e:
        print(f"[-] Gagal membaca PDF: {str(e)}")
        return []

def split_ocr_text_into_pages(ocr_text):
    """Membagi teks OCR berdasarkan penanda Halaman."""
    # Pattern to match page separator: --- Halaman X ---
    pattern = r'---\s*Halaman\s*\d+\s*---'
    parts = re.split(pattern, ocr_text)
    
    # If the pattern is not found, parts will just be [ocr_text]
    if len(parts) <= 1:
        return [ocr_text.strip()]
        
    pages = []
    # If the first part has content (before the first separator), keep it
    if parts[0].strip():
        pages.append(parts[0].strip())
        
    for part in parts[1:]:
        p_stripped = part.strip()
        if p_stripped:
            pages.append(p_stripped)
            
    return pages

def load_ground_truth(file_path):
    """
    Memuat teks Ground Truth dari path yang diberikan.
    - PDF: Mengekstrak teks per halaman.
    - TXT: Membaca konten teks langsung.
    - Gambar: Mencari berkas .txt pendukung dengan nama yang sama.
    """
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == ".pdf":
        return extract_text_from_pdf_pages(file_path)
        
    elif ext == ".txt":
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return split_ocr_text_into_pages(content)
        except Exception as e:
            print(f"[-] Gagal membaca file Ground Truth: {str(e)}")
            return []
            
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
        # Cari file .txt dengan nama yang sama di direktori yang sama
        txt_path = os.path.splitext(file_path)[0] + ".txt"
        if os.path.exists(txt_path):
            print(f"[Info] Ditemukan berkas teks Ground Truth pendukung: {txt_path}")
            return load_ground_truth(txt_path)
        else:
            # Juga cari di data/input/ atau data/
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            candidate_paths = [
                os.path.join(os.path.dirname(file_path), base_name + ".txt"),
                os.path.join("data/input", base_name + ".txt"),
                os.path.join("data", base_name + ".txt"),
            ]
            for path in candidate_paths:
                if os.path.exists(path):
                    print(f"[Info] Ditemukan berkas teks Ground Truth pendukung: {path}")
                    return load_ground_truth(path)
            
            print(f"\n[Error] Gagal! Berkas Ground Truth berupa gambar '{file_path}' memerlukan berkas teks pendukung (cth: {base_name}.txt) untuk evaluasi.")
            return []
    else:
        print(f"\n[Error] Format berkas Ground Truth '{ext}' tidak didukung.")
        return []

def main():
    print("====================================================")
    print("    EVALUASI AKURASI OTOMATIS: PDF VS TXT OUTPUT    ")
    print("====================================================\n")
    
    # 1. Input path file Ground Truth
    pdf_input = input("Masukkan path/nama file Ground Truth (cth: BCA.pdf, KTP.txt, atau KTP.jpg): ").strip()
    if not os.path.exists(pdf_input):
        candidate_paths = [
            os.path.join("data/input", pdf_input),
            os.path.join("data", pdf_input),
            os.path.join("data/input", os.path.basename(pdf_input))
        ]
        found = False
        for path in candidate_paths:
            if os.path.exists(path):
                pdf_input = path
                found = True
                break
        if not found:
            print(f"[Error] Berkas Ground Truth di '{pdf_input}' tidak ditemukan.")
            return

    # 2. Input path file TXT Hasil OCR
    txt_input = input("Masukkan path/nama file TXT Hasil OCR    (cth: data/output/hasil_BCA.txt atau hasil_BCA.txt): ").strip()
    if not os.path.exists(txt_input):
        candidate_paths = [
            os.path.join("data/output", txt_input),
            os.path.join("data", txt_input),
            os.path.join("data/output", os.path.basename(txt_input))
        ]
        found = False
        for path in candidate_paths:
            if os.path.exists(path):
                txt_input = path
                found = True
                break
        if not found:
            print(f"[Error] Berkas TXT di '{txt_input}' tidak ditemukan.")
            return

    print("\n[1/3] Mengekstrak teks dari Ground Truth...")
    gt_pages = load_ground_truth(pdf_input)
    
    if not gt_pages or not any(page.strip() for page in gt_pages):
        print("\n[Error] Gagal! Ground Truth tidak memiliki data teks.")
        return
        
    gt_text = " ".join(gt_pages)

    print("[2/3] Membaca berkas teks hasil OCR...")
    with open(txt_input, 'r', encoding='utf-8') as f:
        ocr_text = f.read()

    print("[3/3] Menghitung jarak sunting (Levenshtein Distance)...")
    
    # Split OCR text into pages
    ocr_pages = split_ocr_text_into_pages(ocr_text)
    
    # Calculate page-by-page metrics
    num_eval_pages = min(len(gt_pages), len(ocr_pages))
    page_metrics = []
    page_cers = []
    page_wers = []
    
    for i in range(num_eval_pages):
        gt_p_clean = " ".join(gt_pages[i].lower().split())
        ocr_p_clean = " ".join(ocr_pages[i].lower().split())
        
        # Avoid division by zero if both are empty
        if not gt_p_clean and not ocr_p_clean:
            p_cer = 0.0
            p_wer = 0.0
        elif not gt_p_clean:
            p_cer = 1.0
            p_wer = 1.0
        else:
            p_cer = cer(gt_p_clean, ocr_p_clean)
            p_wer = wer(gt_p_clean, ocr_p_clean)
            
        p_acc = max(0.0, (1 - p_cer) * 100)
        page_cers.append(p_cer)
        page_wers.append(p_wer)
        
        # Page status
        if p_acc >= 95.0:
            p_status = "PASS"
        elif p_acc >= 85.0:
            p_status = "WARNING"
        else:
            p_status = "FAIL"
            
        page_metrics.append({
            "page": i + 1,
            "cer": p_cer,
            "wer": p_wer,
            "accuracy": p_acc,
            "status": p_status
        })

    # Overall full text normalization and calculation
    gt_clean = " ".join(gt_text.lower().split())
    ocr_clean = " ".join(ocr_text.lower().split())
    
    overall_cer = cer(gt_clean, ocr_clean)
    overall_wer = wer(gt_clean, ocr_clean)
    overall_accuracy = max(0.0, (1 - overall_cer) * 100)

    # Standard Deviation and Mean Calculations
    if len(page_cers) > 1:
        mean_cer = statistics.mean(page_cers)
        std_cer = statistics.stdev(page_cers)
        mean_wer = statistics.mean(page_wers)
        std_wer = statistics.stdev(page_wers)
    else:
        mean_cer = page_cers[0] if page_cers else overall_cer
        std_cer = 0.0
        mean_wer = page_wers[0] if page_wers else overall_wer
        std_wer = 0.0

    # Print Page-by-Page Table
    print("\n====================================================")
    print("           DETAIL EVALUASI PER HALAMAN              ")
    print("====================================================")
    print(f"{'Halaman':<10} | {'CER (%)':<10} | {'WER (%)':<10} | {'Akurasi':<10} | Status")
    print("----------------------------------------------------")
    for pm in page_metrics:
        print(f"Halaman {pm['page']:<2} | {pm['cer']*100:>7.2f}% | {pm['wer']*100:>7.2f}% | {pm['accuracy']:>7.2f}% | {pm['status']}")
    if len(gt_pages) != len(ocr_pages):
        print("----------------------------------------------------")
        print(f"[Info] Jumlah halaman tidak cocok! GT: {len(gt_pages)}, OCR: {len(ocr_pages)}")
    print("====================================================")

    # 3. Cetak Laporan Kualitas Data Finansial
    print("\n====================================================")
    print("           LAPORAN EVALUASI PERFORMA OCR            ")
    print("====================================================")
    print(f"📄 Ground Truth    : {pdf_input}")
    print(f"📝 TXT Hasil OCR   : {txt_input}")
    print("----------------------------------------------------")
    print(f"Rata-rata CER (Page Mean)    : {mean_cer*100:.2f}%")
    print(f"Standar Deviasi CER (SD)     : {std_cer*100:.2f}%")
    print(f"Rata-rata WER (Page Mean)    : {mean_wer*100:.2f}%")
    print(f"Standar Deviasi WER (SD)     : {std_wer*100:.2f}%")
    print("----------------------------------------------------")
    print(f"Character Error Rate (CER)   : {overall_cer:.4f} ({overall_cer*100:.2f}%)")
    print(f"Word Error Rate (WER)        : {overall_wer:.4f} ({overall_wer*100:.2f}%)")
    print("----------------------------------------------------")
    print(f"🎯 AKURASI AKHIR PIPELINE    : {overall_accuracy:.2f}%")
    print("====================================================")
    
    if overall_accuracy >= 95.0:
        print("[STATUS: PASS] Sangat Baik. Data aman untuk Data Warehouse.")
    elif overall_accuracy >= 85.0:
        print("[STATUS: WARNING] Cukup Baik. Perlu sedikit optimasi Regex Parser.")
    else:
        print("[STATUS: FAIL] Buruk. Evaluasi kembali tahap prapemrosesan gambar Anda.")

if __name__ == "__main__":
    main()