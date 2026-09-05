# fungsi eksekusi LSTM Tesseract & EasyOCR (Optimized)

import os
import easyocr
import numpy as np
import pytesseract
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor
from src.prepocessing import clean_image

try:
    import torch
    num_cpus = os.cpu_count() or 4
    torch.set_num_threads(max(1, num_cpus))
    HAS_GPU = torch.cuda.is_available()
except ImportError:
    HAS_GPU = False

_easyocr_reader = None

def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['id', 'en'], gpu=HAS_GPU)
    return _easyocr_reader

def image_to_text_easyocr(processed_image):
    reader = get_easyocr_reader()
    results = reader.readtext(processed_image)
    
    if not results:
        return ""
        
    boxes = []
    for bbox, text, conf in results:
        y_center = sum([p[1] for p in bbox]) / 4.0
        x_min = min([p[0] for p in bbox])
        y_min = min([p[1] for p in bbox])
        y_max = max([p[1] for p in bbox])
        height = y_max - y_min
        boxes.append({
            'bbox': bbox,
            'text': text,
            'conf': conf,
            'y_center': y_center,
            'x_min': x_min,
            'height': height
        })
        
    lines = []
    boxes_sorted_y = sorted(boxes, key=lambda b: b['y_center'])
    
    for box in boxes_sorted_y:
        placed = False
        for line in lines:
            line_y_avg = sum([b['y_center'] for b in line]) / len(line)
            line_h_avg = sum([b['height'] for b in line]) / len(line)
            if abs(box['y_center'] - line_y_avg) < (line_h_avg * 0.6):
                line.append(box)
                placed = True
                break
        if not placed:
            lines.append([box])
            
    reconstructed_lines = []
    lines_sorted_y = sorted(lines, key=lambda l: sum([b['y_center'] for b in l]) / len(l))
    
    for line in lines_sorted_y:
        line_sorted_x = sorted(line, key=lambda b: b['x_min'])
        line_text = "   ".join([b['text'] for b in line_sorted_x])
        reconstructed_lines.append(line_text)
        
    return "\n".join(reconstructed_lines)

def image_to_text(processed_image, lang='ind+eng', engine='tesseract'):
    if engine == 'easyocr':
        return image_to_text_easyocr(processed_image)
    else:
        try:
            pil_image = Image.fromarray(processed_image)
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(pil_image, config=custom_config, lang=lang)
            return text.strip()
        except Exception:
            # Fallback to easyocr if tesseract binary is not installed on system
            return image_to_text_easyocr(processed_image)

def _process_single_page(args):
    page_num, page_image, lang, engine = args
    cleaned_img = clean_image(page_image)
    extracted_text = image_to_text(cleaned_img, lang=lang, engine=engine)
    return page_num, f"\n--- Halaman {page_num + 1} ---\n{extracted_text}"

def process_pdf(pdf_path, dpi=150, engine='tesseract', force_ocr=False):
    """
    Super-fast PDF processing:
    1. First attempts instant native digital text extraction (<0.05 seconds).
    2. If PDF is a scanned image without text, falls back to multi-threaded OCR.
    """
    if not os.path.exists(pdf_path):
        return f"PDF file '{pdf_path}' tidak ditemukan."
    
    # 1. Native Digital PDF Text Extraction Attempt
    native_text_pages = []
    has_native_text = False
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            total_char_count = 0
            
            for i, page in enumerate(reader.pages):
                page_str = page.extract_text() or ""
                total_char_count += len(page_str.strip())
                native_text_pages.append(f"\n--- Halaman {i + 1} ---\n{page_str}")
                
            # If native text exists (more than 50 chars per file), use instant native text
            if total_char_count > 50 and not force_ocr:
                print(f"  [*] Instant Native Digital PDF text extracted ({total_char_count} chars in {num_pages} pages).")
                return "\n".join(native_text_pages)
    except Exception:
        pass

    # 2. Scanned PDF Image Fallback: Multi-threaded OCR Execution
    print(f"  [*] Scanned PDF detected, running multi-threaded OCR ({num_pages} pages)...")
    thread_count = min(4, os.cpu_count() or 4)
    images = convert_from_path(pdf_path, dpi=dpi, thread_count=thread_count)

    tasks = [(i, img, 'ind+eng', engine) for i, img in enumerate(images)]
    max_workers = 2 if engine == 'easyocr' else min(4, os.cpu_count() or 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = list(executor.map(_process_single_page, tasks))
        futures.sort(key=lambda x: x[0])
        results = [text for _, text in futures]

    return "\n".join(results)


# ==============================================================================
# Universal File Text Extractor (Supports All File Formats)
# ==============================================================================
import json
import re
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif', '.svg'}
OFFICE_DOCX_EXTENSIONS = {'.docx'}
OFFICE_PPTX_EXTENSIONS = {'.pptx'}
SPREADSHEET_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.tsv'}

def process_any_file(file_path, dpi=150, engine='tesseract'):
    """
    Universal text extractor for any file format:
    - PDFs (.pdf) -> process_pdf
    - Images (.png, .jpg, .bmp, .tiff, .webp, .gif, .svg) -> OCR
    - Word (.docx) -> Zip XML extraction
    - PowerPoint (.pptx) -> Zip XML extraction
    - Excel / CSV (.xlsx, .xls, .csv, .tsv) -> Pandas dataframe formatting
    - Text / Code / Markup (.txt, .json, .md, .html, .xml, .rtf, .log) -> UTF-8 decoding
    - Binary / Unknown -> Fallback printable string extraction
    """
    file_path = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' not found.")

    _, ext = os.path.splitext(file_path.lower())

    # 1. PDF
    if ext == '.pdf':
        return process_pdf(file_path, dpi=dpi, engine=engine)

    # 2. Image formats
    if ext in IMAGE_EXTENSIONS:
        clean_img = clean_image(file_path)
        return image_to_text(clean_img, lang='ind+eng', engine=engine)

    # 3. Word Document (.docx)
    if ext in OFFICE_DOCX_EXTENSIONS:
        try:
            with zipfile.ZipFile(file_path) as z:
                xml_content = z.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iter() if node.tag.endswith('}t') and node.text]
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass

    # 4. PowerPoint (.pptx)
    if ext in OFFICE_PPTX_EXTENSIONS:
        try:
            with zipfile.ZipFile(file_path) as z:
                texts = []
                slide_names = sorted([n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')])
                for i, s_name in enumerate(slide_names):
                    xml_content = z.read(s_name)
                    tree = ET.fromstring(xml_content)
                    slide_texts = [node.text for node in tree.iter() if node.tag.endswith('}t') and node.text]
                    if slide_texts:
                        texts.append(f"--- Slide {i + 1} ---\n" + "\n".join(slide_texts))
                if texts:
                    return "\n\n".join(texts)
        except Exception:
            pass

    # 5. Spreadsheet / Tabular (.xlsx, .xls, .csv, .tsv)
    if ext in SPREADSHEET_EXTENSIONS:
        try:
            if ext in ('.csv', '.tsv'):
                sep = '\t' if ext == '.tsv' else ','
                df = pd.read_csv(file_path, sep=sep)
                return df.to_string(index=False)
            else:
                xls = pd.ExcelFile(file_path)
                sheets_text = []
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    sheets_text.append(f"--- Sheet: {sheet_name} ---\n" + df.to_string(index=False))
                return "\n\n".join(sheets_text)
        except Exception:
            pass

    # 6. JSON Formatting
    if ext == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 7. Plain text / Code / Markup (txt, md, html, xml, rtf, log, etc.)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            if text.strip():
                return text.strip()
    except Exception:
        pass

    # 8. Binary fallback: Extract printable ASCII strings
    try:
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()
            strings = re.findall(rb'[\x20-\x7E\s]{4,}', raw_bytes)
            decoded = [s.decode('ascii', errors='ignore').strip() for s in strings if len(s.strip()) > 3]
            if decoded:
                return "\n".join(decoded[:500])
    except Exception as e:
        return f"Error reading file content: {str(e)}"

    return f"[File {os.path.basename(file_path)} could not be decoded as text or image]"