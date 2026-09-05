# 📘 Panduan Penggunaan Aplikasi OCRMe (Untuk Pengguna Awam)

Selamat datang di **OCRMe — Intelligent Document Processing (IDP)**! 🚀
Aplikasi ini dirancang untuk membaca, mengekstrak, dan mengubah berbagai jenis dokumen fisik/digital (seperti KTP, Nota, Faktur/Invoice, Rekening Koran, Surat, File Word, Excel, PDF, dll.) menjadi data terstruktur secara otomatis menggunakan kecerdasan buatan (AI).

---

## 📌 Apa yang Bisa Dilakukan OCRMe?

- **Membaca Berbagai Jenis Dokumen**: Faktur (Invoice), Nota Pembelian, KTP, Rekening Koran Bank, Sertifikat, File Word (`.docx`), File Excel (`.xlsx`), PowerPoint (`.pptx`), PDF, dan Foto/Gambar (`.jpg`, `.png`, `.webp`).
- **Mengekstrak Data Otomatis**: Mengenali nama, tanggal, nomor KTP, daftar transaksi, total harga, dan rincian item tanpa perlu diketik manual.
- **Menyimpan Data**: Semua hasil pembacaan langsung tersimpan rapi di dalam database lokal dan bisa diunduh ke bentuk **Excel (CSV)**, **JSON**, atau **Teks (TXT)**.

---

## 🚀 Langkah Cepat Membuka Aplikasi

### Cara 1: Akses Langsung Online (Public Web App)
- 🚀 **Streamlit Cloud App (Fitur Lengkap AI & Python Deep Learning)**: [https://ocrme-idp.streamlit.app/](https://ocrme-idp.streamlit.app/)
- ⚡ **Vercel Web Studio (Versi Web Cepat Client-Side)**: [https://ocrme-idp.vercel.app/](https://ocrme-idp.vercel.app/)

### Cara 2: Menjalankan Langsung di Komputer (Python Local)
1. Buka terminal atau command prompt pada komputer Anda.
2. Jalankan perintah berikut:
   ```bash
   streamlit run app.py
   ```

### Cara 2: Menjalankan Menggunakan Docker (Rekomendasi Kontainer)
Jika komputer Anda sudah terpasang **Docker**, Anda bisa menjalankannya dengan 1 perintah tanpa perlu menginstall library di komputer:
```bash
docker-compose up -d --build
```
3. Browser internet Anda (Chrome/Edge/Firefox) dapat diakses pada alamat `http://localhost:8501`.

### Cara 3: Publish & Akses Vercel Web Studio (Web App Modern)
Aplikasi ini sudah dilengkapi dengan web frontend modern yang siap di-deploy ke **Vercel**:
1. Pastikan Vercel CLI terinstall (`npm install -g vercel`).
2. Jalankan perintah deployment dari direktori ini:
   ```bash
   vercel --prod
   ```
3. Website OCRMe Web Studio Anda langsung aktif di Vercel dengan domain gratis HTTPS!


---

## 🎛️ Panduan Penggunaan Fitur Utama

Aplikasi OCRMe memiliki **4 Menu/Tab Utama** di bagian atas layar:

```
[ 📑 Document Processor ]  [ 📊 Database & Analytics ]  [ 🎯 Accuracy Evaluator ]  [ ⚙️ Batch ETL Pipeline ]
```

---

### Menu 1: 📑 Document Processor (Memproses Dokumen Tunggal)

Gunakan menu ini jika Anda ingin membaca **satu file dokumen** secara langsung.

#### Langkah-langkah:
1. **Pilih Cara Memasukkan Dokumen**:
   - ☁️ **Upload file**: Klik kotak unggah atau tarik *(drag & drop)* file dari komputer Anda (PDF, Foto, Word, Excel, dll.).
   - 💻 **Local file path**: Ketik alamat lokasi file yang ada di komputer Anda (misal: `/home/user/Dokumen/nota.pdf`).
2. **Pengaturan Opsional (Sidebar Kiri)**:
   - **AI Provider Selection**: Anda dapat memilih provider AI yang ingin digunakan:
     - 🔵 **Google Gemini AI** (`gemini-3.6-flash`, `gemini-1.5-flash`)
     - 🟢 **OpenAI ChatGPT** (`gpt-4o-mini`, `gpt-4o`)
     - 🟠 **Anthropic Claude** (`claude-3-5-haiku`, `claude-3-5-sonnet`)
     - 🦙 **Ollama (Local LLM)** (`llama3.1`, `qwen2.5`) — *100% Offline tanpa internet!*
   - **API Key / Host URL**: Masukkan Kunci API dari penyedia AI yang Anda pilih (atau alamat host Ollama jika menggunakan AI lokal).
   - **OCR Engine**: Pilih `EasyOCR` (direkomendasikan untuk dokumen bertabel) atau `Tesseract` (untuk teks biasa).
3. **Klik Tombol "Process & extract document"** 🚀.
4. **Lihat Hasil Extraction**:
   - **Kartu Ringkasan**: Menampilkan kategori dokumen yang terdeteksi (Invoice, KTP, Bank Statement, dll.), tingkat keyakinan (Confidence), dan metode parsing.
   - **Tab Hasil**:
     - 📦 **Structured data (JSON)**: Data hasil ekstraksi dalam bentuk struktur rapi.
     - 📊 **Line items & tables**: Tabel rincian transaksi atau barang (bisa diunduh dalam format **CSV/Excel**).
     - 📝 **Raw extracted text**: Seluruh teks mentah yang dibaca dari dokumen (bisa diunduh dalam format **TXT**).

---

### Menu 2: 📊 Database & Analytics (Melihat & Mencari Data)

Gunakan menu ini untuk melihat seluruh riwayat dokumen yang pernah diproses.

#### Fitur Utama:
1. **Kartu Ringkasan (KPI)**:
   - Memantau total file yang berhasil diproses, jumlah kategori dokumen, rata-rata akurasi, dan persentase penggunaan AI.
2. **Pencarian & Filter Dokumen**:
   - Anda dapat memilih kategori dokumen tertentu (misal: hanya ingin melihat `invoice` atau `identity_card`).
   - Gunakan **Kolom Pencarian** untuk menemukan dokumen berdasarkan nama file atau lokasi folder.
3. **Inspeksi Rincian JSON**:
   - Buka opsi **"Inspect structured JSON payload for a document"** untuk memilih salah satu dokumen dan melihat rincian datanya secara detail.
4. **Grafik Analytics**:
   - Lihat visualisasi grafik batang tentang distribusi jenis dokumen dan tingkat akurasi rata-rata per kategori.

---

### Menu 3: 🎯 Accuracy Evaluator (Pengujian Akurasi)

Menu ini khusus digunakan jika Anda ingin **menguji seberapa akurat** hasil pembacaan teks aplikasi dibandingkan dengan teks asli (Ground Truth).

#### Langkah-langkah:
1. Pilih Mode Pengujian:
   - 🔤 **OCR Accuracy (CER/WER)**: Mengukur persentase kesalahan karakter/kata.
   - 📦 **JSON Parsing Field Accuracy**: Mengukur kecocokan field data JSON.
2. Unggah file dokumen referensi (Ground Truth) dan file hasil pembacaan OCR.
3. Klik tombol **"Calculate OCR accuracy"** untuk melihat laporan skor akurasi.

---

### Menu 4: ⚙️ Batch ETL Pipeline (Memproses Banyak Dokumen Sekaligus)

Gunakan menu ini jika Anda memiliki **satu folder berisi puluhan atau ratusan dokumen** dan ingin memproses Semuanya sekaligus secara otomatis.

#### Langkah-langkah:
1. Ketik jalur/lokasi folder input pada kolom **"Target input folder path"** (misal: `data/input`).
2. Sistem akan menampilkan daftar semua dokumen yang belum pernah diproses.
3. Klik tombol **"Run batch ETL pipeline"** 🚀.
4. Perhatikan bilah kemajuan *(progress bar)* hingga selesai. Semua hasil dokumen akan langsung tersimpan di database dan folder output.

---

## ❓ Pertanyaan Umum (FAQ)

### 1. Apakah saya harus memiliki API Key Gemini untuk menggunakan website ini?
**Tidak wajib.** Jika Anda tidak memasukkan Gemini API Key, aplikasi akan secara otomatis beralih ke **Mode Offline (Regex Fallback Engine)**. Aplikasi tetap bisa membaca dokumen seperti KTP, Rekening Koran, dan Nota secara gratis tanpa koneksi API.

### 2. Format file apa saja yang bisa dibaca oleh OCRMe?
- **PDF**: PDF digital maupun PDF hasil scan.
- **Gambar**: PNG, JPG, JPEG, WEBP, BMP, TIFF, GIF.
- **Dokumen Office**: Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`, `.csv`).
- **Teks & Data**: TXT, JSON, HTML, XML, RTF.

### 3. Di mana hasil pembacaan dokumen disimpan?
- Data disimpan secara otomatis di database lokal bernama `data/ocr_database.db`.
- File unduhan hasil ekstraksi (JSON, CSV, TXT) juga dapat diunduh langsung dari tombol **Download** di halaman aplikasi atau ditemukan di folder `data/output/`.

---

## 🔒 Keamanan & Privasi Data: Apakah Ada Risiko Kebocoran Data?

Jawabannya: **Secara umum Sangat Aman**, karena aplikasi ini berjalan secara **Lokal di Komputer Anda**. Namun, ada beberapa aspek penting yang perlu Anda ketahui:

### 1. Mode Offline / Tanpa API Key (100% Aman & Tanpa Risiko Kebocoran)
- Jika Anda **tidak mengisi Gemini API Key** atau memilih **Parsing Mode: Regex Fallback Only**:
- **0 byte data** yang keluar ke internet. Seluruh proses pembacaan teks (OCR), pemrosesan gambar, dan penyimpanan database SQLite (`data/ocr_database.db`) dilakukan **100% secara lokal di dalam laptop/komputer Anda sendiri**.
- Data Anda tidak pernah dikirim ke server pihak ketiga mana pun.

### 2. Mode AI Gemini (Saat Menggunakan Gemini API Key)
- Jika Anda memasukkan Gemini API Key untuk menggunakan fitur analisis AI:
- Teks hasil pembacaan dokumen akan dikirimkan melalui **koneksi terenkripsi (HTTPS/SSL)** langsung ke server resmi Google Gemini API.
- Kebijakan privasi resmi Google API menyatakan bahwa data yang dikirim melalui Developer API **tidak digunakan oleh Google untuk melatih model publik** mereka dan dijaga kerahasiaannya.
- Namun, karena data teks dikirimkan melalui internet ke server Google, jika Anda memproses **dokumen rahasia negara / rahasia bisnis tingkat tinggi**, disarankan untuk menggunakan **Mode Offline (Regex Only)** agar data tidak pernah menyentuh jaringan internet.

### 3. Ringkasan Rekomendasi Keamanan:
| Jenis Dokumen | Mode yang Disarankan | Tingkat Keamanan Data |
| :--- | :--- | :--- |
| **Dokumen Publik / Umum** (Invoice biasa, Form, Nota toko) | Mode Auto / AI Gemini | 🛡️ Sangat Aman (Terenkripsi HTTPS) |
| **Dokumen Sangat Rahasia / Sensitif** (KTP, Dokumen Hukum, Laporan Keuangan Rahasia) | Mode Offline (Regex Fallback Only) | 🔒 100% Isolation (Tidak terhubung ke Internet) |

---

**Pengembang**: Dinar Wahyu Rahman ([dinarrahman30@gmail.com](mailto:dinarrahman30@gmail.com))
