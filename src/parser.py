import re
import json
import csv
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# Utility Functions
# ==============================================================================

def is_numeric(s):
    # Remove spaces, commas, periods
    cleaned = s.replace(' ', '').replace(',', '').replace('.', '').strip('-')
    return cleaned.isdigit()

def parse_numeric(s):
    # Clean up spaces
    cleaned = s.replace(' ', '')
    if not cleaned:
        return 0.0
    # Strip trailing periods or commas
    cleaned = cleaned.strip(',.')
    # Replace last comma/dot with dot, and others empty
    if len(cleaned) > 3 and cleaned[-3] in [',', '.']:
        dec = cleaned[-2:]
        int_part = cleaned[:-3].replace(',', '').replace('.', '')
        cleaned = int_part + '.' + dec
    else:
        cleaned = cleaned.replace(',', '').replace('.', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

# Keywords to skip when parsing transactions from statements
BOILERPLATE_KEYWORDS = [
    "halaman", "bca", "kcp", "rekening", "periode", "mata uang", "catatan",
    "apabila nasabah", "dengan akhir bulan", "tercantum pada", "mutasi saldo",
    "berhak setiap saat", "bersambung", "saldo awal", "saldo akhir", "keterangan",
    "ari widi", "tanah sareal", "cibadak", "bkt cimanggu", "vila blok", "tanggal keterangan"
]

def is_boilerplate(line):
    l = line.lower()
    if not l.strip():
        return True
    for kw in BOILERPLATE_KEYWORDS:
        if kw in l:
            return True
    return False

# ==============================================================================
# Legacy Regex Parsers (Fallback)
# ==============================================================================

def parse_bca_statement(text):
    """
    Parses layout-preserved OCR text of a BCA Statement into structured transaction dicts.
    """
    lines = text.split('\n')
    transactions = []
    current_tx = None
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Check if line starts with a date pattern DD/MM (optionally DD/MM/YY)
        date_match = re.match(r'^(\d{2}/\d{2}(?:/\d{2,4})?)', line_stripped)
        
        if date_match:
            # It's a new transaction row
            # Split fields by double or more spaces
            tokens = re.split(r'\s{2,}', line_stripped)
            if len(tokens) < 2:
                continue
                
            date = tokens[0]
            right_tokens = [t.strip() for t in tokens[1:] if t.strip()]
            
            amount = 0.0
            mut_type = "CR"
            balance = None
            desc_end_idx = len(right_tokens)
            
            if len(right_tokens) >= 1:
                # Check from right to left
                if is_numeric(right_tokens[-1]):
                    # Last token is a number (balance or amount)
                    if len(right_tokens) >= 2 and right_tokens[-2] in ['DB', 'CR', '00 DB', '60 DB', '90 DB']:
                        balance = parse_numeric(right_tokens[-1])
                        t = right_tokens[-2]
                        mut_type = "DB" if "DB" in t else "CR"
                        desc_end_idx = -2
                        if len(right_tokens) >= 3 and is_numeric(right_tokens[-3]):
                            amount = parse_numeric(right_tokens[-3])
                            desc_end_idx = -3
                    elif len(right_tokens) >= 2 and is_numeric(right_tokens[-2]):
                        balance = parse_numeric(right_tokens[-1])
                        amount = parse_numeric(right_tokens[-2])
                        mut_type = "CR"
                        desc_end_idx = -2
                    else:
                        amount = parse_numeric(right_tokens[-1])
                        mut_type = "CR"
                        desc_end_idx = -1
                elif right_tokens[-1] in ['DB', 'CR', '00 DB', '60 DB', '90 DB']:
                    mut_type = "DB" if "DB" in right_tokens[-1] else "CR"
                    desc_end_idx = -1
                    if len(right_tokens) >= 2 and is_numeric(right_tokens[-2]):
                        amount = parse_numeric(right_tokens[-2])
                        desc_end_idx = -2
            
            description = " ".join(right_tokens[:desc_end_idx])
            
            if current_tx:
                transactions.append(current_tx)
                
            current_tx = {
                "date": date,
                "description": description,
                "amount": amount,
                "type": mut_type,
                "balance": balance
            }
        else:
            # Continuation line or boilerplate
            if is_boilerplate(line_stripped):
                continue
            if current_tx:
                current_tx["description"] += " " + line_stripped
                
    if current_tx:
        transactions.append(current_tx)
        
    return transactions

def parse_ktp(text):
    """
    Parses raw KTP text using regex to extract standard KTP fields.
    """
    data = {}
    
    nik_match = re.search(r'NIK\s*:?\s*(\d{16})', text, re.IGNORECASE)
    if not nik_match:
        nik_match = re.search(r'\b(\d{16})\b', text)
    if nik_match:
        data["nik"] = nik_match.group(1)
        
    def extract_field(label, text):
        pattern = re.escape(label) + r'\s*[:;]?\s*([^\n]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
        
    data["nama"] = extract_field("Nama", text)
    data["tempat_tgl_lahir"] = extract_field("Tempat/Tgl Lahir", text)
    data["jenis_kelamin"] = extract_field("Jenis Kelamin", text)
    data["alamat"] = extract_field("Alamat", text)
    data["rt_rw"] = extract_field("RT/RW", text)
    data["kel_desa"] = extract_field("Kel/Desa", text)
    data["kecamatan"] = extract_field("Kecamatan", text)
    data["agama"] = extract_field("Agama", text)
    data["status_perkawinan"] = extract_field("Status Perkawinan", text)
    data["pekerjaan"] = extract_field("Pekerjaan", text)
    data["kewarganegaraan"] = extract_field("Kewarganegaraan", text)
    data["berlaku_hingga"] = extract_field("Berlaku Hingga", text)
    
    return data

def parse_invoice(text):
    """
    Parses invoice/receipt text using regex key-value and line item extraction.
    """
    header = {}
    summary = {}
    
    inv_no_match = re.search(r'(?:invoice|faktur|kwitansi|receipt|inv|no\.?)\s*#?\s*[:;]?\s*([A-Za-z0-9\-\/]+)', text, re.IGNORECASE)
    if inv_no_match:
        header["invoice_number"] = inv_no_match.group(1).strip()
        
    date_match = re.search(r'(?:date|tanggal|tgl)\s*[:;]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})', text, re.IGNORECASE)
    if date_match:
        header["invoice_date"] = date_match.group(1).strip()

    due_match = re.search(r'(?:due date|jatuh tempo)\s*[:;]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text, re.IGNORECASE)
    if due_match:
        header["due_date"] = due_match.group(1).strip()

    total_match = re.search(r'(?:total|grand total|jumlah total|total bayar)\s*[:;]?\s*(?:rp\.?|idr)?\s*([\d\.,\s]+)', text, re.IGNORECASE)
    if total_match:
        summary["total_amount"] = parse_numeric(total_match.group(1))

    subtotal_match = re.search(r'(?:subtotal|sub total)\s*[:;]?\s*(?:rp\.?|idr)?\s*([\d\.,\s]+)', text, re.IGNORECASE)
    if subtotal_match:
        summary["subtotal"] = parse_numeric(subtotal_match.group(1))

    tax_match = re.search(r'(?:tax|vat|ppn|pajak)\s*[:;]?\s*(?:rp\.?|idr)?\s*([\d\.,\s]+)', text, re.IGNORECASE)
    if tax_match:
        summary["tax_amount"] = parse_numeric(tax_match.group(1))

    # Line item regex extraction (lines with item text followed by numeric values)
    line_items = []
    lines = text.split('\n')
    for line in lines:
        line_s = line.strip()
        match = re.search(r'^([A-Za-z0-9\s\-\._\/]+?)\s{2,}(\d+)\s{2,}(?:rp\.?|idr)?\s*([\d\.,]+)\s{2,}(?:rp\.?|idr)?\s*([\d\.,]+)$', line_s, re.IGNORECASE)
        if match:
            line_items.append({
                "item_name": match.group(1).strip(),
                "quantity": int(match.group(2)),
                "unit_price": parse_numeric(match.group(3)),
                "total_price": parse_numeric(match.group(4))
            })

    return {
        "header": header,
        "line_items": line_items,
        "summary": summary
    }

# ==============================================================================
# LLM-Powered Parsing
# ==============================================================================

def parse_with_llm(raw_text, use_three_step=False, provider="gemini", api_key=None, model_name=None):
    """
    Parses document text using MultiProviderLLMClient.
    
    Args:
        raw_text: Raw OCR-extracted text
        use_three_step: If True, uses 3 separate API calls.
        provider: 'gemini', 'openai', 'claude', or 'ollama'
        api_key: API Key string
        model_name: Model name string
    
    Returns:
        dict with keys: doc_type, doc_subtype, confidence, data, method
    """
    from src.llm_client import MultiProviderLLMClient

    client = MultiProviderLLMClient(provider=provider, api_key=api_key, model_name=model_name)

    if use_three_step:
        result = client.process_three_step(raw_text)
    else:
        result = client.process_full(raw_text)

    classification = result.get("classification", {})
    
    return {
        "doc_type": classification.get("doc_type", "other"),
        "doc_subtype": classification.get("doc_subtype", "Unknown"),
        "confidence": classification.get("confidence", 0.0),
        "data": result.get("extracted_data", {}),
        "method": f"llm ({provider})",
    }


def smart_parse(raw_text, use_llm=True, provider="gemini", api_key=None, model_name=None):
    """
    Intelligent parsing entry point with automatic fallback.
    
    Strategy:
    1. If use_llm=True and LLM is available → use MultiProvider LLM (Gemini, OpenAI, Claude, Ollama)
    2. If LLM fails or unavailable → fallback to regex parser
    3. If regex doesn't match → return raw text result
    
    Args:
        raw_text: Raw OCR-extracted text
        use_llm: Whether to attempt LLM parsing first (default True)
        provider: 'gemini', 'openai', 'claude', or 'ollama'
        api_key: API Key string
        model_name: Model name string
    
    Returns:
        dict with keys: doc_type, doc_subtype, confidence, data, method
    """
    # Attempt LLM parsing
    if use_llm:
        from src.llm_client import is_llm_available
        if is_llm_available(provider=provider):
            try:
                logger.info(f"Attempting LLM-based parsing with provider: {provider}...")
                result = parse_with_llm(raw_text, provider=provider, api_key=api_key, model_name=model_name)
                logger.info(
                    f"LLM parsing successful: {result['doc_type']}/{result['doc_subtype']} "
                    f"(confidence: {result['confidence']})"
                )
                return result
            except Exception as e:
                logger.warning(f"LLM parsing failed, falling back to regex: {str(e)}")
        else:
            logger.info(f"LLM not available for provider {provider} (missing API key). Using regex parser.")

    # Fallback to regex parser
    return _regex_fallback(raw_text)


def _regex_fallback(raw_text):
    """
    Applies legacy regex parsers based on keyword detection.
    """
    text_lower = raw_text.lower()
    
    # Detect KTP
    if "nik" in text_lower or "ktp" in text_lower:
        logger.info("Regex fallback: detected KTP document")
        parsed_data = parse_ktp(raw_text)
        return {
            "doc_type": "identity_card",
            "doc_subtype": "KTP",
            "confidence": 0.7,
            "data": parsed_data,
            "method": "regex",
        }

    # Detect Invoice / Receipt / Faktur
    if any(kw in text_lower for kw in ["invoice", "faktur", "receipt", "kwitansi", "subtotal", "total bayar", "bill to", "due date"]):
        logger.info("Regex fallback: detected invoice / receipt document")
        parsed_data = parse_invoice(raw_text)
        return {
            "doc_type": "invoice",
            "doc_subtype": "Invoice / Receipt",
            "confidence": 0.7,
            "data": parsed_data,
            "method": "regex",
        }

    # Detect BCA Statement
    if "bca" in text_lower or "mutasi" in text_lower or "saldo" in text_lower:
        logger.info("Regex fallback: detected BCA statement")
        parsed_data = parse_bca_statement(raw_text)
        return {
            "doc_type": "bank_statement",
            "doc_subtype": "Mutasi BCA",
            "confidence": 0.7,
            "data": parsed_data,
            "method": "regex",
        }

    # Unknown document
    logger.warning("Regex fallback: unknown document type")
    return {
        "doc_type": "other",
        "doc_subtype": "Unknown",
        "confidence": 0.0,
        "data": {"raw_text": raw_text},
        "method": "regex",
    }


# ==============================================================================
# File Output Helpers
# ==============================================================================

def save_to_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_to_csv(data, output_path):
    if not data:
        return
    if isinstance(data, dict):
        data = [data]
    headers = data[0].keys()
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
