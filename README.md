# OCRMe (OCR Lokal & ETL Pipeline)

Aplikasi ekstraksi, pemrosesan, dan parsing data otomatis untuk dokumen finansial (Mutasi Rekening Bank BCA) dan dokumen identitas (KTP) menggunakan teknologi OCR lokal (Tesseract & EasyOCR) serta pipeline ETL dengan basis data SQLite.

---

## Deskripsi
OCRMe adalah prototipe sistem pemrosesan dokumen otomatis (IDP - Intelligent Document Processing). Aplikasi ini melakukan pra-pemrosesan gambar, mengekstraksi teks dengan OCR, mem-parsing teks mentah menjadi entitas terstruktur (JSON/CSV), dan memuatnya ke database relasional SQLite secara otomatis melalui pipeline ETL.

## Fitur Utama
1. **OCR Engine Ganda**: Dukungan untuk Tesseract OCR (cepat) dan EasyOCR (preservasi tata letak kolom tabel).
2. **Pra-pemrosesan Gambar**: Koreksi kemiringan (deskewing) otomatis menggunakan kontur dan binarisasi Otsu Thresholding untuk meningkatkan keterbacaan OCR.
3. **Regex Parser Terstruktur**:
   - **KTP**: Ekstraksi NIK, Nama, Alamat, Agama, Status Perkawinan, Pekerjaan, dll.
   - **Mutasi BCA**: Ekstraksi tanggal, keterangan transaksi, tipe mutasi (DB/CR), jumlah dana, dan saldo.
4. **Pipeline ETL**: Otomatisasi pemrosesan file baru di folder `data/input` dan pemuatan data terstruktur langsung ke tabel SQLite.
5. **Laporan Evaluasi Performa**: Evaluasi akurasi OCR per halaman (CER, WER, Akurasi Akhir) lengkap dengan perhitungan Standar Deviasi (SD).

---

## Struktur Proyek
```
OCRSample/
├── data/
│   ├── input/              # Dokumen mentah (PDF/Gambar)
│   ├── output/             # Hasil ekstraksi teks mentah, JSON, dan CSV
│   └── ocr_database.db     # Basis data SQLite penyimpan records terstruktur
├── src/
│   ├── prepocessing.py     # Deskewing & Otsu Binarization
│   ├── ocr_engine.py       # Engine Tesseract & EasyOCR
│   └── parser.py           # Parser KTP & Mutasi BCA
├── main.py                 # Penggunaan interaktif OCR satu per satu
├── run_etl.py              # Runner pipeline ETL otomatisasi database
├── verify_db.py            # Utility query & verifikasi database SQLite
├── ocr_eval.py             # Script evaluasi akurasi OCR (PDF/TXT vs GT)
├── requirements.txt        # Dependensi Python
└── README.md               # Dokumentasi
```

---

## Algoritma & Tahapan

### 1. Preprocessing (Pra-pemrosesan)
- **Deskewing**: Koreksi rotasi otomatis dengan mendeteksi koordinat non-nol, menghitung `minAreaRect`, dan memutar gambar agar tegak lurus.
- **Binarization**: Konversi ke skala abu-abu (grayscale) diikuti oleh Otsu's Thresholding untuk menghasilkan gambar hitam-putih biner dengan kontras tinggi.

### 2. OCR Engine
- **Tesseract OCR (LSTM)**: Cepat dan efisien untuk membaca paragraf teks biasa.
- **EasyOCR (Layout Preserving)**: Pengelompokan kotak batas (bounding boxes) secara horizontal berdasarkan kedekatan koordinat y-center untuk merekonstruksi tata letak baris dan tabel.

### 3. Structured Parser
- Mengekstrak data menggunakan ekspresi reguler (Regex) untuk mengenali pola teks spesifik dokumen Indonesia (seperti pola NIK 16-digit, format tanggal `DD/MM`, tipe mutasi `DB`/`CR`, dan nominal saldo).

### 4. Evaluasi
Evaluasi membandingkan teks hasil OCR dengan dokumen master/Ground Truth (GT) asli:
- **Character Error Rate (CER)**: $\frac{Substitusi + Penghapusan + Penyisipan Karakter}{Total Karakter GT}$
- **Word Error Rate (WER)**: $\frac{Substitusi + Penghapusan + Penyisipan Kata}{Total Kata GT}$
- **Standar Deviasi (SD)**: Mengukur variabilitas akurasi antar halaman dokumen.

---

## Cara Penggunaan

### 1. Penggunaan Interaktif
Untuk memproses satu file secara interaktif dan menyimpan file JSON/CSV:
```bash
python3 main.py
```
*Masukkan nama berkas (cth: `BCA.pdf` atau `KTP.jpg`), pilih OCR engine, dan pilih opsi parsing.*

### 2. Jalankan Pipeline ETL
Untuk memindai folder `data/input`, memproses file baru, dan memuatnya ke SQLite secara otomatis:
```bash
python3 run_etl.py
```

### 3. Verifikasi Data SQLite
Untuk melihat isi basis data hasil pipeline ETL:
```bash
python3 verify_db.py
```

### 4. Jalankan Evaluasi Akurasi OCR
Untuk menguji performa akurasi OCR terhadap Ground Truth:
```bash
python3 ocr_eval.py
```
*Masukkan file Ground Truth (cth: `BCA.pdf` atau `KTP.jpg`) dan file hasil OCR (`hasil_BCA.txt` atau `hasil_KTP.txt`).*

---

## Author

- **Dinar Wahyu Rahman**
- **Email**: [dinarrahman30@gmail.com](mailto:dinarrahman30@gmail.com)
- **GitHub**: [dinarrahmann](https://github.com/dinarrahmann)

