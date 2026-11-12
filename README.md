# Persentation Coach
*Sistem Pelatih Presentasi Otomatis Berbasis Keypoint Pose & Pendekatan Hibrida Machine Learning*

> **Proyek Tugas Mata Kuliah Praktikum Machine Learning (M2)**  
> **Politeknik Manufaktur Negeri Bangka Belitung (POLMAN)**

---

## Ringkasan Eksekutif

**Persentation Coach** adalah aplikasi pelatih presentasi berbasis kecerdasan buatan (*Computer Vision & Machine Learning*) yang dirancang khusus untuk membantu mahasiswa melatih keterampilan berbicara di depan umum secara mandiri. Cukup bermodalkan kamera laptop atau webcam USB standar (tanpa perangkat sensor khusus atau IoT), sistem membaca 17 titik kerangka tubuh (*pose keypoints*) presenter secara *real-time* menggunakan **YOLO11-pose**.

Bahasa tubuh diklasifikasikan ke dalam **7 kondisi gestur** menggunakan **pendekatan hibrida**:
1. **Aturan Geometri Tubuh**: mendeteksi kondisi *membelakangi audiens*, *tangan terlipat*, dan *menunjuk slide*.
2. **Pengukuran Kecepatan Gerak Tangan (*Motion Meter*)**: mendeteksi *gestur aktif* berbasis kecepatan pergelangan tangan terhadap bahu dengan normalisasi panjang badan dan filter anti-getar (*EMA & deadband*).
3. **Random Forest Classifier**: mengklasifikasikan kondisi *netral*, *menunduk*, dan *tangan tersembunyi* berbasis 52 fitur koordinat keypoint ternormalisasi.

Karena evaluasi murni didasarkan pada proporsi geometri kerangka tubuh ternormalisasi (bukan piksel gambar mentah), sistem ini **kebal terhadap perubahan latar belakang, warna pakaian, dan kondisi pencahayaan ruangan**.

---

## Fitur Utama & Pembaruan Terbaru

- **Analisis Real-Time via Kamera**: Deteksi kerangka tubuh presenter secara langsung (≥ 15 FPS di CPU standar laptop).
- **Peringatan Langsung (*Real-Time Alert*)**: Peringatan visual di layar saat presenter membelakangi audiens (> 3 dtk), menunduk terlalu lama (> 5 dtk), atau melipat tangan (> 10 dtk).
- **Proteksi Batas Percobaan Login (*Brute Force Rate Limiting*) [BARU]**:
  - Batas maksimal 5 kali percobaan salah sebelum akun dikunci sementara selama 60 detik (HTTP 429).
  - Tampilan visual sisa kesempatan serta tombol dengan animasi hitung mundur (*cooldown countdown*) di form web.
  - Perlindungan ganda berbasis username dan IP address.
- **Antarmuka Responsif Mobile / Layar Kecil [BARU]**:
  - Tombol **Hamburger Menu** diposisikan rapi di kanan bawah tombol DAFTAR.
  - Seluruh navigasi disatukan ke dalam **Mobile Drawer** yang elegan.
  - Kompatibel dengan layar sentuh smartphone (iOS Safari & Android Chrome) dengan *touch targets* yang nyaman dan anti-*auto-zoom*.
- **Transisi Pop-up Hasil Tirai (*Curtain Unveil*) [BARU]**:
  - Pop-up evaluasi hasil latihan kini menggunakan transisi tirai membuka ke atas (*clip-path* dan *cubic-bezier*) yang selaras dengan pop-up chatbot.
  - Elemen skor, grafik, dan saran muncul bertahap (*staggered rise*).
- **Heatmap Pergerakan Panggung**: Menganalisis pergerakan posisi berdiri presenter di atas panggung (titik tengah pinggul).
- **Generator Laporan PDF Otomatis (A4)**: Menghasilkan lembar laporan lengkap berisi skor komposit, rincian 4 aspek, timeline kejadian, proporsi gestur, dan 3 saran perbaikan utama.
- **Konsultasi Chatbot Terbatas Topik**: Chatbot pendamping berbasis data latihan presenter dengan *guardrail* topik ketat (mendukung Google Gemini API, Ollama lokal, atau mode *rule-based* bawaan jika offline).
- **Integrasi Bot Telegram**: Hubungkan akun via pemindaian kode QR / deep-link untuk menerima laporan PDF dan berinteraksi dengan bot di ponsel.

---

## Arsitektur Sistem & Alur Klasifikasi Hibrida

```
                       Webcam Video Frame
                               │
                       YOLO11-pose (17 Keypoints)
                               │
              ┌────────────────┴────────────────┐
              │                                 │
     [1. Aturan Geometri]               [Bahu Terlihat?]
      • Hidung/mata tak terlihat       ┌────────┴────────┐
        atau bahu terbalik?            │ YA              │ TIDAK
        ──► membelakangi               │                 └──► Abaikan
      • Tangan menyilang di dada       │
        atau dekat siku seberang?      ▼
        ──► tangan_terlipat     [2. Pengukur Gerak (MotionMeter)]
      • Pergelangan tangan jauh       • Kecepatan tangan di depan dada
        ke samping di atas pinggul?     > ambang batas (move_t)?
        ──► menunjuk_slide              ──► gestur_aktif
              │                        │
              └─────────┬──────────────┘
                        │ Jika tidak memenuhi aturan di atas:
                        ▼
                [3. Random Forest (52 Fitur Keypoints)]
                  • netral
                  • menunduk
                  • tangan_tersembunyi
                        │
                        ▼
                Smoothing (Voting 15 Frame Terakhir)
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
Peringatan Layar & Web Sesi       Database SQLite & PDF
```

---

## Struktur Direktori Proyek

```text
Persentation_Coach/
│
├── web/                     # Aplikasi Web Fullstack (FastAPI + HTML5/CSS/JS)
│   ├── main.py              # Server web utama, autentikasi, rate limit, WebSocket
│   ├── engine.py            # Mesin analisis pose, scoring & kalkulasi metrik sesi
│   ├── laporan.py           # Generator laporan PDF (A4) berbasis matplotlib
│   ├── chat.py              # Chatbot konsultasi dengan guardrail berlapis
│   ├── tele.py              # Integrasi Bot Telegram (HTTP Polling)
│   ├── surel.py             # Layanan pengiriman email (SMTP/Verifikasi)
│   └── static/              # Asset antarmuka (HTML, CSS responsif, JavaScript)
│       ├── css/             # Stylesheet (app.css, latihan.css, chatpop.css, landing.css)
│       ├── js/              # Client scripts (shared.js, auth.js, latihan.js, hasil.js, riwayat.js)
│       └── img/             # Logo dan ikon aplikasi
│
├── models/                  # Bobot model & artefak machine learning
│   ├── kp_rf.joblib         # Model Random Forest untuk fitur keypoints
│   ├── gesture_best.pt      # Model YOLO11-cls (gambar crop pembanding)
│   └── kp_confusion_matrix.png
│
├── demo_kp.py               # Demo visualisasi real-time berbasis OpenCV
├── demo_webcam.py           # Demo pembanding menggunakan YOLO11-cls
├── kp_features.py           # Modul ekstraksi 52 fitur geometri keypoints
├── extract_keypoints.py     # Ekstraksi fitur keypoint dataset ke format .npz
├── train_kp.py              # Skrip melatih ulang Random Forest dari keypoints
├── train.py                 # Skrip melatih ulang model YOLO11-cls
├── cek_kamera.py            # Skrip utilitas pengecekan index kamera / webcam
│
├── yolo11n-pose.pt          # Bobot YOLO11-pose nano pretrained
├── kp_data.npz              # Data fitur keypoint yang telah diekstrak
├── requirements.txt         # Daftar pustaka & dependensi Python
├── .env.example             # Contoh konfigurasi variabel lingkungan
├── .env                     # File konfigurasi aktif lokal
├── .gitignore               # Konfigurasi ignore file git
├── PRD.md                   # Product Requirement Document lengkap
└── README.md                # Dokumentasi resmi proyek ini
```

---

## Prasyarat Sistem

1. **Sistem Operasi**: Windows 10/11, Linux (Ubuntu/Debian), atau macOS.
2. **Python**: Versi `3.10`, `3.11`, `3.12`, atau `3.14`.
3. **Perangkat Keras**:
   - Webcam internal laptop atau webcam USB eksternal (minimal 720p @ 30fps).
   - CPU modern (inferensi pose YOLO11n sangat ringan dan berjalan mulus tanpa kartu grafis khusus).
   - GPU NVIDIA dengan CUDA (opsional, hanya jika ingin melatih ulang deep learning model).

---

## Panduan Instalasi di Komputer Lain (Langkah-demi-Langkah)

Panduan ini ditujukan bagi penguji, dosen penilai, atau rekan pengembang yang ingin memasang dan menjalankan proyek ini di komputer baru dari awal:

### 1. Unduh / Salin Proyek
Pastikan seluruh folder repositori disalin ke komputer target, lalu buka terminal (PowerShell di Windows, atau Bash di Linux/macOS) pada direktori proyek:
```powershell
cd Persentation_Coach
```

### 2. Buat dan Aktifkan Virtual Environment
Sangat disarankan membuat virtual environment agar dependensi terisolasi rapi:
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Pasang Dependensi Python
Jalankan perintah instalasi dari `requirements.txt`:
```powershell
pip install -r requirements.txt
```

> **Info Tambahan**: Jika menggunakan GPU NVIDIA dan ingin memanfaatkan CUDA, ikuti instruksi spesifik kartu grafis di [pytorch.org](https://pytorch.org/). Secara default, mode CPU sudah menghasilkan performa inferensi ≥ 15 FPS.

### 4. Konfigurasi Lingkungan (`.env`)
Salin file `.env.example` menjadi `.env`:
- **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **Linux / macOS**:
  ```bash
  cp .env.example .env
  ```

> **Mode Standalone / Offline**: Aplikasi sudah dirancang untuk **langsung berfungsi secara mandiri (offline)** tanpa perlu mengisi API key apa pun. Tautan verifikasi email akan dicetak langsung di konsol terminal, database SQLite akan dibuat otomatis, dan chatbot menggunakan basis tips aturan lokal.

Jika ingin mengaktifkan integrasi opsional, isi file `.env`:
```ini
# Google OAuth (Opsional, untuk login akun Google)
GOOGLE_CLIENT_ID=

# Token Bot Telegram (Opsional, dari @BotFather)
TELEGRAM_BOT_TOKEN=

# Chatbot AI Cerdas (Opsional: Google Gemini API atau Ollama lokal)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=
OLLAMA_MODEL=llama3.2
CHAT_BATAS_HARIAN=20

# Konfigurasi SMTP Email (Opsional, jika kosong tautan dicetak di konsol)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
BASE_URL=http://localhost:8000
```

---

## Cara Menjalankan Aplikasi

### A. Menjalankan Dashboard Web Utama (Rekomendasi)
Jalankan server aplikasi melalui Uvicorn:
```powershell
python -m uvicorn web.main:app --reload --port 8000
```
Buka browser favorit Anda dan akses:
**[http://localhost:8000](http://localhost:8000)**

**Alur Pengujian:**
1. Masuk ke halaman **Daftar** untuk membuat akun baru. Tautan verifikasi email akan langsung muncul di terminal (jika SMTP kosong) atau akun bisa langsung login.
2. Buka menu **Latihan**.
3. Izinkan akses kamera pada browser laptop.
4. Pilih durasi latihan (misal: 1 menit), lalu klik **Mulai latihan**.
5. Cobalah berdiri di depan kamera dan variasikan bahasa tubuh (membelakangi, melipat tangan, menunjuk slide, atau berbicara dengan gestur tangan aktif).
6. Di akhir sesi, pop-up hasil evaluasi akan muncul dengan animasi tirai membuka ke atas, menampilkan cincin skor total, rincian per aspek, dan tombol **Unduh PDF**.

---

### B. Menjalankan Pengujian Kamera & Demo CLI

#### 1. Cek Indeks Kamera
Untuk memastikan kamera internal atau webcam USB terdeteksi oleh OpenCV:
```powershell
python cek_kamera.py
```

#### 2. Demo Deteksi OpenCV Langsung (Desktop GUI)
Menjalankan pipeline hibrida keypoint + Random Forest langsung pada jendela GUI OpenCV:
```powershell
python demo_kp.py --kp models\kp_rf.joblib --cam 0
```
- Gunakan `--cam 1` jika menggunakan kamera USB eksternal.
- Tekan `d` untuk menampilkan/menyembunyikan angka debug parameter geometri.
- Tekan `s` untuk menyimpan tangkapan layar.
- Tekan `q` untuk keluar.

#### 3. Melatih Ulang Model Keypoint (Opsional)
Jika Anda menambahkan data baru pada folder dataset `gesture_rf`:
```powershell
# 1. Ekstraksi koordinat pose menjadi array fitur (kp_data.npz)
python extract_keypoints.py --data gesture_rf --out kp_data.npz

# 2. Latih model Random Forest
python train_kp.py --data kp_data.npz
```

---

## Rubrik & Rumus Penilaian Skor

Sistem menghasilkan skor komposit **0–100** yang dihitung secara matematis berdasarkan 4 aspek bahasa tubuh:

$$\text{Skor Total} = (0.30 \times \text{Orientasi}) + (0.30 \times \text{Gestur}) + (0.25 \times \text{Postur}) + (0.15 \times \text{Pergerakan})$$

| Aspek | Bobot | Dasar Pengukuran |
|---|:---:|---|
| **Orientasi ke Audiens** | **30%** | Persentase waktu tubuh dan wajah presenter menghadap audiens (mengurangi waktu membelakangi). |
| **Gestur Tangan** | **30%** | Keberadaan gerakan tangan aktif dinamis yang mendukung penjelasan, serta meminimalkan posisi tangan terlipat atau dimasukkan ke saku. |
| **Postur Kepala** | **25%** | Ketegakan pandangan kepala (mengurangi kebiasaan menunduk membaca catatan terlalu lama). |
| **Pergerakan Posisi** | **15%** | Menganalisis stabilitas perpindahan presenter di panggung (melalui heatmap posisi pinggul). |

---

## Pengembang & Lisensi

- **Institusi**: Politeknik Manufaktur Negeri Bangka Belitung (POLMAN)
- **Mata Kuliah**: Praktikum Machine Learning (M2)
- **Tahun**: 2026
- **Lisensi**: *Academic & Educational Purpose*
