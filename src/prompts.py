"""
Prompt templates for Gemini LLM integration in OCRMe pipeline.
Three-stage prompts: OCR Correction → Document Classification → Adaptive Parsing.
"""

# ==============================================================================
# PROMPT 1: OCR Text Correction
# ==============================================================================
PROMPT_OCR_CORRECTION = """Kamu adalah ahli koreksi teks OCR untuk dokumen Indonesia.

TUGAS:
Perbaiki teks OCR mentah berikut. Teks ini diekstrak dari gambar/PDF dokumen menggunakan OCR dan mungkin mengandung kesalahan.

ATURAN KETAT:
1. Perbaiki HANYA kesalahan OCR yang jelas (huruf salah baca, spasi rusak, karakter aneh).
2. JANGAN menambah, mengarang, atau mengubah data asli.
3. JANGAN mengubah angka kecuali jelas salah baca (misal: 'O' yang harusnya '0', 'l' yang harusnya '1').
4. Pertahankan format dan struktur teks asli (baris baru, spasi antar kolom).
5. Untuk istilah Indonesia yang umum, perbaiki ejaan (misal: 'KELAMIN' bukan 'KELAMlN').

TEKS OCR MENTAH:
---
{raw_text}
---

Berikan HANYA teks yang sudah diperbaiki tanpa penjelasan tambahan."""


# ==============================================================================
# PROMPT 2: Document Classification
# ==============================================================================
PROMPT_CLASSIFY_DOCUMENT = """Kamu adalah sistem klasifikasi dokumen Indonesia.

TUGAS:
Analisis teks dokumen berikut dan identifikasi jenis dokumen serta field data yang ada.

TEKS DOKUMEN:
---
{text}
---

Berikan respons dalam format JSON SAJA (tanpa markdown code block, tanpa penjelasan) dengan struktur:
{{
    "doc_type": "<kategori utama: identity_card | bank_statement | invoice | tax_document | receipt | letter | other>",
    "doc_subtype": "<deskripsi spesifik, contoh: KTP, Mutasi BCA, Faktur Pajak, dll>",
    "confidence": <float 0.0-1.0>,
    "detected_fields": ["<daftar nama field data yang terdeteksi dalam dokumen>"],
    "language": "id",
    "notes": "<catatan singkat tentang dokumen jika ada>"
}}

ATURAN:
- doc_type HARUS salah satu dari: identity_card, bank_statement, invoice, tax_document, receipt, letter, other
- detected_fields berisi nama-nama field yang bisa diekstrak dari dokumen
- confidence menunjukkan seberapa yakin klasifikasi ini (0.0 = tidak yakin, 1.0 = sangat yakin)"""


# ==============================================================================
# PROMPT 3: Adaptive Document Parsing
# ==============================================================================
PROMPT_PARSE_DOCUMENT = """Kamu adalah sistem ekstraksi data terstruktur dari dokumen Indonesia.

TUGAS:
Ekstrak SEMUA data terstruktur dari teks dokumen berikut ke format JSON.

INFORMASI DOKUMEN:
- Jenis: {doc_type}
- Sub-jenis: {doc_subtype}
- Field yang terdeteksi: {detected_fields}

TEKS DOKUMEN:
---
{text}
---

ATURAN KETAT:
1. Ekstrak HANYA data yang benar-benar ada di dokumen. JANGAN mengarang data.
2. Jika suatu field tidak ditemukan, isi dengan null.
3. Untuk angka/nominal uang, gunakan format angka biasa tanpa pemisah ribuan (contoh: 1500000.00 bukan 1,500,000.00).
4. Untuk tanggal, pertahankan format asli dari dokumen.
5. Berikan JSON SAJA tanpa markdown code block dan tanpa penjelasan.

FORMAT OUTPUT berdasarkan jenis dokumen:

Jika bank_statement, output berupa object:
{{
    "header": {{
        "bank_name": "<nama bank>",
        "account_number": "<nomor rekening>",
        "account_holder": "<nama pemilik>",
        "period": "<periode mutasi>",
        "currency": "<mata uang>"
    }},
    "transactions": [
        {{
            "date": "<tanggal transaksi>",
            "description": "<keterangan>",
            "type": "<DB atau CR>",
            "amount": <nominal float>,
            "balance": <saldo float atau null>
        }}
    ]
}}

Jika identity_card (KTP), output berupa object:
{{
    "provinsi": "<provinsi>",
    "kabupaten_kota": "<kabupaten/kota>",
    "nik": "<NIK 16 digit>",
    "nama": "<nama lengkap>",
    "tempat_tgl_lahir": "<tempat, tanggal lahir>",
    "jenis_kelamin": "<LAKI-LAKI atau PEREMPUAN>",
    "gol_darah": "<golongan darah>",
    "alamat": "<alamat>",
    "rt_rw": "<RT/RW>",
    "kel_desa": "<kelurahan/desa>",
    "kecamatan": "<kecamatan>",
    "agama": "<agama>",
    "status_perkawinan": "<status>",
    "pekerjaan": "<pekerjaan>",
    "kewarganegaraan": "<WNI/WNA>",
    "berlaku_hingga": "<masa berlaku>"
}}

Jika invoice / receipt / kuitansi / faktur, output berupa object:
{{
    "header": {{
        "invoice_number": "<nomor invoice/faktur>",
        "invoice_date": "<tanggal>",
        "due_date": "<tanggal jatuh tempo>",
        "vendor_name": "<nama penjual/toko>",
        "customer_name": "<nama pembeli/klien>",
        "payment_terms": "<syarat pembayaran>"
    }},
    "line_items": [
        {{
            "item_name": "<nama barang/jasa>",
            "quantity": <jumlah float/int>,
            "unit_price": <harga satuan float>,
            "total_price": <total harga float>
        }}
    ],
    "summary": {{
        "subtotal": <subtotal float>,
        "tax_amount": <pajak/ppn float>,
        "discount": <diskon float>,
        "total_amount": <total bayar float>
    }}
}}

Untuk jenis dokumen lainnya, buat struktur JSON yang paling sesuai berdasarkan field yang terdeteksi."""


# ==============================================================================
# PROMPT GABUNGAN: Single-Call Full Pipeline
# ==============================================================================
PROMPT_FULL_PIPELINE = """Kamu adalah sistem Intelligent Document Processing (IDP) untuk dokumen Indonesia.

TUGAS:
Lakukan 3 langkah sekaligus terhadap teks OCR mentah berikut:
1. KOREKSI: Perbaiki kesalahan OCR (typo, karakter salah baca, spasi rusak)
2. KLASIFIKASI: Identifikasi jenis dokumen
3. EKSTRAKSI: Ekstrak semua data terstruktur ke JSON

TEKS OCR MENTAH:
---
{raw_text}
---

ATURAN KETAT:
1. Ekstrak HANYA data yang benar-benar ada. JANGAN mengarang.
2. Nominal uang: format angka biasa (contoh: 1500000.00).
3. Tanggal: pertahankan format asli dokumen.
4. Berikan JSON SAJA tanpa markdown code block dan tanpa penjelasan.

OUTPUT FORMAT:
{{
    "correction_applied": true,
    "classification": {{
        "doc_type": "<identity_card | bank_statement | invoice | tax_document | receipt | letter | other>",
        "doc_subtype": "<deskripsi spesifik>",
        "confidence": <float 0.0-1.0>
    }},
    "extracted_data": <object atau array sesuai jenis dokumen>
}}

Untuk bank_statement, extracted_data berisi:
{{
    "header": {{"bank_name": "...", "account_number": "...", "account_holder": "...", "period": "...", "currency": "..."}},
    "transactions": [{{"date": "...", "description": "...", "type": "DB/CR", "amount": <float>, "balance": <float|null>}}]
}}

Untuk identity_card (KTP), extracted_data berisi:
{{
    "provinsi": "...", "kabupaten_kota": "...", "nik": "...", "nama": "...",
    "tempat_tgl_lahir": "...", "jenis_kelamin": "...", "gol_darah": "...",
    "alamat": "...", "rt_rw": "...", "kel_desa": "...", "kecamatan": "...",
    "agama": "...", "status_perkawinan": "...", "pekerjaan": "...",
    "kewarganegaraan": "...", "berlaku_hingga": "..."
}}

Untuk invoice / receipt / faktur, extracted_data berisi:
{{
    "header": {{"invoice_number": "...", "invoice_date": "...", "due_date": "...", "vendor_name": "...", "customer_name": "..."}},
    "line_items": [{{"item_name": "...", "quantity": <number>, "unit_price": <number>, "total_price": <number>}}],
    "summary": {{"subtotal": <number>, "tax_amount": <number>, "discount": <number>, "total_amount": <number>}}
}}

Untuk dokumen lain, buat struktur JSON yang paling sesuai."""
