import re
import json
import csv

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

def save_to_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_to_csv(data, output_path):
    if not data:
        return
    headers = data[0].keys()
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
