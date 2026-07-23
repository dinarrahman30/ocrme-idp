# fungsi eksekusi LSTM Tesseract

import os
import easyocr
import numpy as np
from pytesseract import pytesseract
import pytesseract
from PIL import Image, UnidentifiedImageError
import PyPDF2
from pdf2image import convert_from_path
from src.prepocessing import clean_image

_easyocr_reader = None

def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        # Initialize easyocr reader for Indonesian and English
        _easyocr_reader = easyocr.Reader(['id', 'en'], gpu=False)
    return _easyocr_reader

def image_to_text_easyocr(processed_image):
    reader = get_easyocr_reader()
    # easyocr accepts numpy ndarrays directly
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
        
    # Group bounding boxes into horizontal lines based on y-coordinate proximity
    lines = []
    boxes_sorted_y = sorted(boxes, key=lambda b: b['y_center'])
    
    for box in boxes_sorted_y:
        placed = False
        for line in lines:
            line_y_avg = sum([b['y_center'] for b in line]) / len(line)
            line_h_avg = sum([b['height'] for b in line]) / len(line)
            # If the y-center of this box is close to the average y-center of the line
            if abs(box['y_center'] - line_y_avg) < (line_h_avg * 0.6):
                line.append(box)
                placed = True
                break
        if not placed:
            lines.append([box])
            
    # Sort lines from top to bottom, and text within lines from left to right
    reconstructed_lines = []
    lines_sorted_y = sorted(lines, key=lambda l: sum([b['y_center'] for b in l]) / len(l))
    
    for line in lines_sorted_y:
        line_sorted_x = sorted(line, key=lambda b: b['x_min'])
        # Join elements with triple spaces to distinguish tabular columns clearly
        line_text = "   ".join([b['text'] for b in line_sorted_x])
        reconstructed_lines.append(line_text)
        
    return "\n".join(reconstructed_lines)

def image_to_text(processed_image, lang='ind+eng', engine='tesseract'):
    if engine == 'easyocr':
        return image_to_text_easyocr(processed_image)
    else:
        pil_image = Image.fromarray(processed_image)
        custom_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(pil_image, config=custom_config, lang=lang)
        return text.strip()

def process_pdf(pdf_path, dpi=200, engine='tesseract'):
    if not os.path.exists(pdf_path):
        return (f"PDF file '{pdf_path}' tidak ditemukan.")
    
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        num_pages = len(reader.pages)

        print(f"  [*] Total halaman: {num_pages}")

        texts = []
        for page_num in range(num_pages):
            print(f"  [*] Memproses halaman {page_num + 1} dengan engine {engine}...")

            page_image = convert_from_path(pdf_path, dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
            cleaned_img = clean_image(page_image[0])
            extracted_text = image_to_text(cleaned_img, lang='ind+eng', engine=engine)
            texts.append(f"\n--- Halaman {page_num + 1} ---\n{extracted_text}")

        return "\n".join(texts)