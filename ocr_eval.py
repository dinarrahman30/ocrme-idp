# evaluate_pdf_vs_txt.py
import os
import re
import json
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


def evaluate_ocr_accuracy(gt_pages, ocr_text):
    """
    Evaluates OCR accuracy against ground truth pages.
    Returns a dict with page_metrics, overall stats, and summary.
    """
    ocr_pages = split_ocr_text_into_pages(ocr_text)
    
    num_eval_pages = min(len(gt_pages), len(ocr_pages))
    page_metrics = []
    page_cers = []
    page_wers = []
    
    for i in range(num_eval_pages):
        gt_p_clean = " ".join(gt_pages[i].lower().split())
        ocr_p_clean = " ".join(ocr_pages[i].lower().split())
        
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

    gt_text = " ".join(gt_pages)
    gt_clean = " ".join(gt_text.lower().split())
    ocr_clean = " ".join(ocr_text.lower().split())
    
    overall_cer = cer(gt_clean, ocr_clean)
    overall_wer = wer(gt_clean, ocr_clean)
    overall_accuracy = max(0.0, (1 - overall_cer) * 100)

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

    return {
        "page_metrics": page_metrics,
        "overall_cer": overall_cer,
        "overall_wer": overall_wer,
        "overall_accuracy": overall_accuracy,
        "mean_cer": mean_cer,
        "std_cer": std_cer,
        "mean_wer": mean_wer,
        "std_wer": std_wer,
        "gt_page_count": len(gt_pages),
        "ocr_page_count": len(ocr_pages),
    }


def evaluate_parsing_accuracy(gt_json_path, result_json_path):
    """
    Evaluates parsing accuracy by comparing LLM/Regex JSON output against ground truth JSON.
    
    Compares field-by-field and computes:
    - Field-level accuracy (% fields correctly extracted)
    - Missing fields, extra fields, and mismatched values
    """
    try:
        with open(gt_json_path, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)
        with open(result_json_path, 'r', encoding='utf-8') as f:
            result_raw = json.load(f)
    except Exception as e:
        print(f"[Error] Gagal membaca file JSON: {str(e)}")
        return None

    # If result has metadata wrapper, extract data
    result_data = result_raw.get("data", result_raw)
    
    report = {
        "total_fields": 0,
        "matched_fields": 0,
        "mismatched_fields": [],
        "missing_fields": [],
        "extra_fields": [],
        "parsing_method": result_raw.get("metadata", {}).get("parsing_method", "unknown"),
    }

    def compare_dicts(gt, result, prefix=""):
        """Recursively compare two dicts."""
        if isinstance(gt, dict) and isinstance(result, dict):
            all_keys = set(gt.keys()) | set(result.keys())
            for key in all_keys:
                full_key = f"{prefix}.{key}" if prefix else key
                if key not in gt:
                    report["extra_fields"].append(full_key)
                elif key not in result:
                    report["missing_fields"].append(full_key)
                    report["total_fields"] += 1
                else:
                    compare_dicts(gt[key], result[key], full_key)
        elif isinstance(gt, list) and isinstance(result, list):
            count = min(len(gt), len(result))
            for i in range(count):
                compare_dicts(gt[i], result[i], f"{prefix}[{i}]")
            if len(result) < len(gt):
                for i in range(len(result), len(gt)):
                    report["missing_fields"].append(f"{prefix}[{i}]")
                    report["total_fields"] += 1
        else:
            report["total_fields"] += 1
            # Normalize for comparison
            gt_str = str(gt).strip().lower() if gt is not None else ""
            res_str = str(result).strip().lower() if result is not None else ""
            if gt_str == res_str:
                report["matched_fields"] += 1
            else:
                report["mismatched_fields"].append({
                    "field": prefix,
                    "expected": gt,
                    "actual": result,
                })

    compare_dicts(gt_data, result_data)
    
    if report["total_fields"] > 0:
        report["accuracy"] = (report["matched_fields"] / report["total_fields"]) * 100
    else:
        report["accuracy"] = 0.0

    return report


def print_parsing_report(report):
    """Prints a parsing accuracy evaluation report."""
    if not report:
        return
        
    print("\n====================================================")
    print("       EVALUASI AKURASI PARSING (JSON vs GT)        ")
    print("====================================================")
    print(f"Metode Parsing       : {report['parsing_method'].upper()}")
    print(f"Total Field Dievaluasi : {report['total_fields']}")
    print(f"Field Cocok            : {report['matched_fields']}")
    print(f"Field Tidak Cocok      : {len(report['mismatched_fields'])}")
    print(f"Field Hilang           : {len(report['missing_fields'])}")
    print(f"Field Tambahan         : {len(report['extra_fields'])}")
    print("----------------------------------------------------")
    print(f"🎯 AKURASI PARSING     : {report['accuracy']:.2f}%")
    print("====================================================")
    
    if report["mismatched_fields"]:
        print("\n[Detail Mismatch]:")
        for m in report["mismatched_fields"][:20]:  # Limit to 20
            print(f"  ❌ {m['field']}")
            print(f"     Expected: {m['expected']}")
            print(f"     Actual  : {m['actual']}")
    
    if report["missing_fields"]:
        print(f"\n[Missing Fields]: {', '.join(report['missing_fields'][:20])}")

    if report["extra_fields"]:
        print(f"\n[Extra Fields]: {', '.join(report['extra_fields'][:20])}")


import sys
import time

def run_auto_eval(output_dir="data/output", scorecard_path="data/output/scorecard.json"):
    """
    Automated evaluation harness execution for Docker / CI / non-interactive CLI.
    Evaluates available GT vs OCR/JSON results and writes scorecard.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    scorecard = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluations": [],
        "overall_summary": {}
    }

    # Evaluate KTP
    ktp_gt = "data/input/KTP.txt"
    ktp_ocr = "data/output/hasil_KTP.txt"
    if os.path.exists(ktp_gt) and os.path.exists(ktp_ocr):
        gt_pages = load_ground_truth(ktp_gt)
        with open(ktp_ocr, 'r', encoding='utf-8') as f:
            ocr_text = f.read()
        stats = evaluate_ocr_accuracy(gt_pages, ocr_text)
        scorecard["evaluations"].append({
            "document": "KTP.jpg",
            "type": "identity_card",
            "cer": round(stats["overall_cer"], 4),
            "wer": round(stats["overall_wer"], 4),
            "accuracy": round(stats["overall_accuracy"], 2),
            "status": "PASS" if stats["overall_accuracy"] >= 95.0 else ("WARNING" if stats["overall_accuracy"] >= 85.0 else "FAIL")
        })

    # Evaluate PDF documents (BCA, BNI, BRI)
    for pdf_name in ["BCA.pdf", "BNI.pdf", "BRI GSJA Kaltim.pdf"]:
        pdf_path = os.path.join("data/input", pdf_name)
        txt_path = os.path.join("data/output", f"hasil_{os.path.splitext(pdf_name)[0]}.txt")
        if os.path.exists(pdf_path) and os.path.exists(txt_path):
            gt_pages = load_ground_truth(pdf_path)
            with open(txt_path, 'r', encoding='utf-8') as f:
                ocr_text = f.read()
            if gt_pages:
                stats = evaluate_ocr_accuracy(gt_pages, ocr_text)
                scorecard["evaluations"].append({
                    "document": pdf_name,
                    "type": "pdf_document",
                    "cer": round(stats["overall_cer"], 4),
                    "wer": round(stats["overall_wer"], 4),
                    "accuracy": round(stats["overall_accuracy"], 2),
                    "status": "PASS" if stats["overall_accuracy"] >= 95.0 else ("WARNING" if stats["overall_accuracy"] >= 85.0 else "FAIL")
                })

    # Calculate overall scorecard stats
    if scorecard["evaluations"]:
        accuracies = [e["accuracy"] for e in scorecard["evaluations"]]
        scorecard["overall_summary"] = {
            "total_documents_evaluated": len(scorecard["evaluations"]),
            "mean_accuracy": round(statistics.mean(accuracies), 2),
            "pass_count": sum(1 for e in scorecard["evaluations"] if e["status"] == "PASS"),
            "warning_count": sum(1 for e in scorecard["evaluations"] if e["status"] == "WARNING"),
            "fail_count": sum(1 for e in scorecard["evaluations"] if e["status"] == "FAIL"),
        }

    # Write scorecard.json artifact
    with open(scorecard_path, 'w', encoding='utf-8') as f:
        json.dump(scorecard, f, indent=4, ensure_ascii=False)

    print("\n====================================================")
    print("      OCRMe SCORECARD REPORT (EVAL HARNESS)         ")
    print("====================================================")
    print(f"Timestamp           : {scorecard['timestamp']}")
    print(f"Total Evaluated     : {scorecard['overall_summary'].get('total_documents_evaluated', 0)}")
    print(f"Mean Accuracy       : {scorecard['overall_summary'].get('mean_accuracy', 0)}%")
    print(f"PASS Count          : {scorecard['overall_summary'].get('pass_count', 0)}")
    print("----------------------------------------------------")
    for item in scorecard["evaluations"]:
        print(f"📄 {item['document']:<22} | Acc: {item['accuracy']:>6.2f}% | CER: {item['cer']:>6.4f} | [{item['status']}]")
    print("====================================================")
    print(f"✅ Scorecard report written to: {scorecard_path}\n")

    return scorecard


import sys
import time

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["--auto", "auto", "--batch"]:
        run_auto_eval()
        return

    print("====================================================")
    print("    EVALUASI AKURASI OCRMe (OCR + PARSING)          ")
    print("====================================================\n")
    
    print("Pilih mode evaluasi:")
    print("1. Evaluasi Akurasi OCR (CER/WER — teks vs Ground Truth)")
    print("2. Evaluasi Akurasi Parsing (JSON output vs Ground Truth JSON)")
    print("3. Auto Scorecard Batch Evaluator (Semua Dokumen & Export JSON)")
    mode = input("Pilihan (1/2/3) [Default: 3]: ").strip()

    if mode == "3" or mode == "":
        run_auto_eval()
        return

    # ==================================================================
    # MODE 1: OCR Accuracy (CER/WER)
    # ==================================================================
    if mode == "1":
        print("\n--- EVALUASI AKURASI OCR ---")
        
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
            
        print("[2/3] Membaca berkas teks hasil OCR...")
        with open(txt_input, 'r', encoding='utf-8') as f:
            ocr_text = f.read()

        print("[3/3] Menghitung jarak sunting (Levenshtein Distance)...")

        stats = evaluate_ocr_accuracy(gt_pages, ocr_text)

        # Print Page-by-Page Table
        print("\n====================================================")
        print("           DETAIL EVALUASI PER HALAMAN              ")
        print("====================================================")
        print(f"{'Halaman':<10} | {'CER (%)':<10} | {'WER (%)':<10} | {'Akurasi':<10} | Status")
        print("----------------------------------------------------")
        for pm in stats["page_metrics"]:
            print(f"Halaman {pm['page']:<2} | {pm['cer']*100:>7.2f}% | {pm['wer']*100:>7.2f}% | {pm['accuracy']:>7.2f}% | {pm['status']}")
        if stats["gt_page_count"] != stats["ocr_page_count"]:
            print("----------------------------------------------------")
            print(f"[Info] Jumlah halaman tidak cocok! GT: {stats['gt_page_count']}, OCR: {stats['ocr_page_count']}")
        print("====================================================")

        # Quality Report
        print("\n====================================================")
        print("           LAPORAN EVALUASI PERFORMA OCR            ")
        print("====================================================")
        print(f"📄 Ground Truth    : {pdf_input}")
        print(f"📝 TXT Hasil OCR   : {txt_input}")
        print("----------------------------------------------------")
        print(f"Rata-rata CER (Page Mean)    : {stats['mean_cer']*100:.2f}%")
        print(f"Standar Deviasi CER (SD)     : {stats['std_cer']*100:.2f}%")
        print(f"Rata-rata WER (Page Mean)    : {stats['mean_wer']*100:.2f}%")
        print(f"Standar Deviasi WER (SD)     : {stats['std_wer']*100:.2f}%")
        print("----------------------------------------------------")
        print(f"Character Error Rate (CER)   : {stats['overall_cer']:.4f} ({stats['overall_cer']*100:.2f}%)")
        print(f"Word Error Rate (WER)        : {stats['overall_wer']:.4f} ({stats['overall_wer']*100:.2f}%)")
        print("----------------------------------------------------")
        print(f"🎯 AKURASI AKHIR PIPELINE    : {stats['overall_accuracy']:.2f}%")
        print("====================================================")
        
        if stats["overall_accuracy"] >= 95.0:
            print("[STATUS: PASS] Sangat Baik. Data aman untuk Data Warehouse.")
        elif stats["overall_accuracy"] >= 85.0:
            print("[STATUS: WARNING] Cukup Baik. Perlu sedikit optimasi Regex Parser.")
        else:
            print("[STATUS: FAIL] Buruk. Evaluasi kembali tahap prapemrosesan gambar Anda.")

    # ==================================================================
    # MODE 2: Parsing Accuracy (JSON comparison)
    # ==================================================================
    if mode == "2":
        print("\n--- EVALUASI AKURASI PARSING ---")
        
        gt_json = input("Masukkan path file Ground Truth JSON (cth: JSON EXAMPLE.json): ").strip()
        if not os.path.exists(gt_json):
            candidate_paths = [
                os.path.join("data", gt_json),
                os.path.join("data/output", gt_json),
                gt_json
            ]
            found = False
            for path in candidate_paths:
                if os.path.exists(path):
                    gt_json = path
                    found = True
                    break
            if not found:
                print(f"[Error] File GT JSON '{gt_json}' tidak ditemukan.")
                return

        result_json = input("Masukkan path file Hasil Parsing JSON (cth: data/output/hasil_BCA.json): ").strip()
        if not os.path.exists(result_json):
            candidate_paths = [
                os.path.join("data/output", result_json),
                os.path.join("data", result_json),
            ]
            found = False
            for path in candidate_paths:
                if os.path.exists(path):
                    result_json = path
                    found = True
                    break
            if not found:
                print(f"[Error] File hasil JSON '{result_json}' tidak ditemukan.")
                return

        report = evaluate_parsing_accuracy(gt_json, result_json)
        print_parsing_report(report)

if __name__ == "__main__":
    main()