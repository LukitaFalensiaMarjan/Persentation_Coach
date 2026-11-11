# PRD — Persentation Coach

| | |
|---|---|
| **Nama produk** | Persentation Coach |
| **Jenis** | Proyek mata kuliah (prototipe) |
| **Versi dokumen** | 1.1 — 11 November 2026 |
| **Status** | Pengembangan — deteksi 7 gestur real-time sudah berjalan (pendekatan hibrida keypoint) |

---

## 1. Deskripsi singkat

**Persentation Coach** adalah aplikasi pelatih presentasi berbasis kamera untuk mahasiswa. Cukup dengan webcam, sistem membaca 17 titik tubuh presenter dengan **YOLO11-pose**, lalu mengenali 7 kondisi bahasa tubuh (netral, gestur aktif, menunjuk slide, menunduk, membelakangi, tangan terlipat, tangan tersembunyi) melalui **pendekatan hibrida**: aturan geometri tubuh, pengukuran gerak tangan, dan classifier Random Forest berbasis keypoint. Karena hanya memakai posisi tubuh, bukan piksel gambar, deteksinya tidak terpengaruh latar belakang, pakaian, atau ruangan. Setelah latihan, mahasiswa menerima **laporan PDF** melalui **bot Telegram** dan dapat **berkonsultasi dengan chatbot** yang menjawab berdasarkan data latihannya sendiri dan dibatasi pada topik presentasi. Tanpa perangkat IoT atau sensor tambahan.

---

## 2. Latar belakang & masalah

- Keterampilan komunikasi termasuk kompetensi utama yang dicari pemberi kerja dari lulusan baru (NACE Job Outlook 2025).
- Banyak mahasiswa mengalami kecemasan berbicara di depan umum; salah satu penyebabnya adalah kurangnya pengalaman dan latihan.
- Umpan balik dari dosen terbatas: satu dosen menangani banyak mahasiswa, dan latihan sebelum hari presentasi umumnya dilakukan sendiri tanpa penilai.
- Sistem umpan balik presentasi otomatis yang ada sebagian besar hanya diuji di laboratorium, memakai perangkat khusus, dan berhenti pada skor tanpa ruang untuk bertanya "bagaimana memperbaikinya".

Detail data dan sumber ada di dokumen *Latar Belakang — Pelatih Presentasi Berbasis YOLO-Pose*.

---

## 3. Tujuan & non-tujuan

### Tujuan
1. Memberi umpan balik bahasa tubuh yang **terukur dan otomatis** hanya dengan kamera.
2. Membuat hasil latihan **mudah diakses dan dipantau** perkembangannya melalui Telegram.
3. Menyediakan **konsultasi** yang dipersonalisasi dari data sesi pengguna, dengan topik terbatas.
4. Membuktikan keandalan sistem dengan **validasi terhadap penilaian manusia**.

### Non-tujuan (di luar cakupan versi ini)
- Analisis suara, intonasi, kata pengisi ("eee", "anu"), atau isi materi presentasi.
- Analisis ekspresi wajah dan kontak mata yang presisi.
- Mendukung lebih dari satu presenter dalam satu frame.
- Aplikasi mobile; target adalah laptop Windows.

---

## 4. Pengguna

| Persona | Kebutuhan |
|---|---|
| **Mahasiswa** yang akan presentasi tugas, seminar, atau sidang | Latihan mandiri dengan umpan balik objektif, tahu apa yang harus diperbaiki |
| **Dosen / asisten** (pengguna sekunder) | Melihat ringkasan perkembangan latihan mahasiswa bila dibagikan |

---

## 5. User stories

1. Sebagai mahasiswa, saya ingin **memulai sesi latihan** cukup dengan menyalakan webcam, agar tidak perlu alat tambahan.
2. Sebagai mahasiswa, saya ingin melihat **peringatan langsung** di layar saat saya membelakangi audiens atau menunduk terlalu lama.
3. Sebagai mahasiswa, saya ingin menerima **laporan PDF** setelah sesi selesai, berisi skor per aspek dan menit-menit yang perlu diperbaiki.
4. Sebagai mahasiswa, saya ingin **menghubungkan sesi ke Telegram** cukup dengan memindai QR code.
5. Sebagai mahasiswa, saya ingin **melihat perkembangan** skor saya dari sesi ke sesi.
6. Sebagai mahasiswa, saya ingin **bertanya** "kenapa skor gestur saya rendah?" dan mendapat jawaban berdasarkan data sesi saya.
7. Sebagai pengembang, saya ingin chatbot **menolak pertanyaan di luar topik** presentasi.

---

## 6. Fitur & persyaratan fungsional

Prioritas: **P0** = wajib (MVP), **P1** = penting, **P2** = bonus.

### 6.1 Analisis presentasi real-time — P0
| ID | Persyaratan |
|---|---|
| F1 | Membaca video dari webcam bawaan atau eksternal (index kamera dapat dipilih). |
| F2 | Mendeteksi presenter dan 17 keypoint tubuh dengan YOLO11-pose. |
| F3 | Mengklasifikasikan gestur dengan **pendekatan hibrida** berurutan: (1) aturan geometri tubuh, (2) pengukuran kecepatan gerak tangan, (3) classifier Random Forest dari fitur keypoint. Lihat tabel di bawah. |
| F4 | Menghaluskan label dengan voting N frame terakhir (default 15) agar tidak berkedip. |
| F4b | Menyediakan mode debug yang menampilkan nilai ukuran geometri (wajah, arah, lipat, silang, lengan, gerak) dan ambangnya, untuk kalibrasi. |
| F5 | Menampilkan overlay: kerangka tubuh, label gestur, tingkat keyakinan, FPS. |

**Kelas gestur dan cara deteksinya (urutan keputusan dari atas ke bawah):**

| Urutan | Kelas | Cara deteksi | Kriteria |
|---|---|---|---|
| 1 | `membelakangi` | Aturan geometri | Wajah (hidung & mata) tidak terlihat padahal bahu terlihat, atau urutan bahu kiri-kanan terbalik |
| 2 | `tangan_terlipat` | Aturan geometri | Pergelangan tangan dekat siku seberang (`lipat` kecil), atau kedua tangan menyilang di dada |
| 3 | `menunjuk_slide` | Aturan geometri | Pergelangan tangan jauh ke samping dari bahu, di atas pinggul |
| 4 | `gestur_aktif` | Pengukuran gerak | Tangan di depan badan dan bergerak cepat (relatif terhadap bahu, anti-getar) |
| 5 | `netral`, `menunduk`, `tangan_tersembunyi` | Classifier keypoint (Random Forest) | 52 fitur: posisi 17 keypoint ternormalisasi, confidence, arah badan |

Ukuran geometri dinormalisasi terhadap panjang badan, sehingga tidak bergantung pada jarak orang ke kamera. Kelas `gelisah` ditunda (akan memakai pola gerak berulang).

**Ambang hasil kalibrasi awal (dapat diatur):**

| Parameter | Nilai default | Arti |
|---|---|---|
| `face-t` | 0,35 | wajah < nilai ini → membelakangi |
| `facing-t` | −0,15 | arah bahu < nilai ini → membelakangi |
| `fold-t` | 0,45 | lipat < nilai ini → tangan terlipat |
| `arm-t` | 0,8 | lengan > nilai ini → menunjuk slide |
| `move-t` | 1,0 | gerak (panjang badan/detik) > nilai ini → gestur aktif |
| `static-t` | 0,5 | model yakin tangan tersembunyi ≥ nilai ini → gerak diabaikan |

### 6.2 Metrik & skor sesi — P0
| ID | Persyaratan |
|---|---|
| F6 | Menghitung persentase waktu per kelas gestur selama sesi. |
| F7 | Menghitung metrik berbasis keypoint: aktivitas gerak tangan (kecepatan pergelangan tangan, dinormalisasi panjang badan) dan pergerakan posisi berdiri (heatmap titik tengah pinggul). |
| F8 | Menghasilkan skor per aspek (orientasi ke audiens, gestur, postur kepala, pergerakan) dan skor keseluruhan 0–100. |
| F9 | Menyimpan timeline kejadian (mis. "menit 3–4 membelakangi") ke database. |

### 6.3 Laporan PDF — P0
| ID | Persyaratan |
|---|---|
| F10 | Membuat PDF di akhir sesi: skor, grafik proporsi gestur, timeline, heatmap posisi, 3 saran perbaikan utama. |
| F11 | Wajah pada gambar di laporan di-blur. |

### 6.4 Bot Telegram — P1
| ID | Persyaratan |
|---|---|
| F12 | Di akhir sesi, aplikasi menampilkan QR code berisi deep link `t.me/<bot>?start=<id_sesi>` untuk menghubungkan sesi ke akun Telegram. |
| F13 | `/laporan` — mengirim PDF sesi terakhir. |
| F14 | `/riwayat` — daftar sesi sebelumnya. |
| F15 | `/progres` — perbandingan skor antar-sesi. |
| F16 | `/latihan` — satu fokus latihan berdasarkan skor terlemah. |

### 6.5 Chatbot konsultasi terbatas topik — P1
| ID | Persyaratan |
|---|---|
| F17 | Menjawab pertanyaan pengguna lewat Telegram dengan konteks ringkasan metrik sesinya. |
| F18 | Mengambil jawaban dari basis tips public speaking yang dikurasi (30–50 tips, RAG sederhana). |
| F19 | **Guardrail berlapis:** (1) system prompt dengan cakupan topik & template penolakan, (2) filter klasifikasi on/off-topic sebelum memanggil model utama, (3) sumber jawaban dibatasi data sesi + basis tips, (4) uji ketahanan prompt injection, (5) `max_tokens` dan rate limit per pengguna (mis. 20 pesan/hari). |
| F20 | Pertanyaan di luar topik dibalas dengan template sopan yang mengarahkan kembali ke latihan presentasi. |

### 6.6 Fitur bonus — P2
- Perbandingan dua sesi berdampingan.
- Mode "latihan terarah" dengan satu fokus per sesi.
- Ekspor riwayat ke CSV.

---

## 7. Persyaratan non-fungsional

| Aspek | Target |
|---|---|
| Performa | ≥ 15 FPS di laptop (inferensi CPU diperbolehkan) |
| Perangkat | Hanya kamera; berjalan di Windows 10/11, tanpa GPU khusus untuk inferensi |
| Privasi | Video tidak disimpan secara default; yang disimpan hanya metrik & timeline. Wajah di-blur pada laporan. Data penelitian memakai ID anonim (S01, S02, …) dan formulir persetujuan. |
| Ketersediaan | Analisis & laporan PDF tetap berfungsi offline; Telegram & chatbot butuh internet |
| Keamanan | API key LLM dan token bot disimpan di `.env`, tidak di-commit ke repo |

---

## 8. Arsitektur & teknologi

```
Webcam ─► YOLO11-pose (17 keypoint)
              │
              ├─► aturan geometri ─────────► membelakangi / tangan_terlipat / menunjuk_slide
              ├─► pengukur gerak tangan ───► gestur_aktif
              └─► fitur keypoint ─► Random Forest ─► netral / menunduk / tangan_tersembunyi
                                         │
                         voting 15 frame ─┴─► SQLite (sesi, metrik, timeline)
                                                   │
                                     Generator PDF ─┼─► Bot Telegram ◄──► Pengguna
                                                   └─► Chatbot LLM + guardrail + basis tips
```

| Komponen | Teknologi |
|---|---|
| Deteksi pose | Ultralytics YOLO11n-pose (pretrained COCO-Pose, 17 keypoint) |
| Klasifikasi gestur | Aturan geometri + pengukur gerak + scikit-learn Random Forest (fitur keypoint) |
| Model pembanding | Ultralytics YOLO11n-cls (klasifikasi gambar crop, 224×224) |
| Video & overlay | OpenCV |
| Labeling & versi dataset | Roboflow (project Classification, single-label) |
| Penyimpanan | SQLite |
| Laporan | ReportLab / img2pdf, matplotlib |
| Bot | python-telegram-bot |
| Chatbot | API LLM cloud (alternatif: model lokal via Ollama) |
| Training | Lokal (CPU atau GPU NVIDIA dengan CUDA) |

---

## 9. Data & model

### Status saat ini
- 1.902 foto mentah (1920×1080) dari satu presenter, dikelompokkan ke 7 folder kelas, diproses menjadi **1.658 gambar crop** dan diunggah ke Roboflow (`gesture_rf`).
- **Model gambar (YOLO11n-cls):** akurasi test top-1 99,4% pada split acak Roboflow, tetapi **gagal di ruangan lain**: model ikut mempelajari latar belakang (mis. membelakangi terbaca menunjuk slide). Disimpan sebagai pembanding.
- **Pendekatan hibrida keypoint (dipakai):** ke-7 gestur terdeteksi dengan baik saat demo real-time dengan webcam eksternal, setelah kalibrasi ambang.
- Belum ada pengukuran akurasi pada presenter lain (lihat bagian 10).

### Temuan penting
Klasifikasi dari piksel gambar mudah *overfitting* pada latar belakang ketika data hanya dari satu orang dan satu ruangan. Klasifikasi dari keypoint, ditambah aturan geometri untuk kelas yang jelas secara bentuk tubuh dan pengukuran gerak untuk gestur aktif, jauh lebih tahan terhadap perubahan ruangan.

### Spesifikasi dataset target
| Aspek | Target |
|---|---|
| Jumlah presenter | ≥ 10 orang berbeda (ideal 30) |
| Per kelas | ≥ 200–300 gambar |
| Variasi | Beberapa ruangan, pencahayaan, pakaian, sudut kamera ±30° |
| Rekaman | Video HP/webcam ≥ 720p, 30 fps, kamera diam setinggi dada, badan terlihat minimal sampai lutut |
| Pembagian data | **Per orang** (`split_dataset.py --mode subject`) untuk angka yang dilaporkan |
| Etika | Formulir persetujuan, ID anonim, wajah di-blur pada publikasi |

### Skrip pendukung
| Skrip | Fungsi |
|---|---|
| `prep_dataset.py` | Ambil frame, crop orang, buang frame kembar |
| `split_dataset.py` | Bagi train/val/test (per waktu atau per orang), buat persegi |
| `extract_keypoints.py` | Jalankan YOLO11-pose pada dataset, simpan fitur keypoint (`kp_data.npz`) |
| `train_kp.py` | Latih Random Forest dari fitur keypoint, laporan per kelas, confusion matrix (`models/kp_rf.joblib`) |
| `kp_features.py` | Fitur keypoint + aturan geometri (membelakangi, tangan terlipat, menunjuk slide) |
| `demo_kp.py` | **Demo utama**: hibrida aturan + gerak + model, voting, mode debug |
| `train.py` / `demo_webcam.py` | Model gambar YOLO11n-cls (pembanding) |
| `cek_kamera.py` | Mencari index webcam (termasuk eksternal) |

---|---|
| `prep_dataset.py` | Ambil frame, crop orang, buang frame kembar |
| `split_dataset.py` | Bagi train/val/test (per waktu atau per orang), buat persegi |
| `train.py` | Training YOLO11-cls, uji di data test, simpan `models/gesture_best.pt` |
| `cek_kamera.py` | Mencari index webcam (termasuk eksternal) |
| `demo_webcam.py` | Demo real-time pose + klasifikasi gestur |

---

## 10. Metrik keberhasilan & evaluasi

| Komponen | Metrik | Target |
|---|---|---|
| Klasifikasi gestur (sistem hibrida) | Akurasi & macro F1 pada rekaman presenter yang **tidak** ada di data training | ≥ 0,75 |
| Perbandingan pendekatan | Akurasi hibrida keypoint vs model gambar YOLO11n-cls pada data yang sama | Hibrida lebih tinggi di ruangan baru |
| Skor sistem vs penilaian manusia | Korelasi Spearman (2–3 penilai, rubrik 1–5) | ≥ 0,6 |
| Real-time | FPS di laptop | ≥ 15 |
| Guardrail chatbot | Akurasi jawab/tolak pada ±100 pertanyaan uji (50 sesuai topik, 30 di luar topik, 20 jebakan) | ≥ 90% |
| Kegunaan | System Usability Scale (±10 pengguna) | ≥ 70 |

---

## 11. Rencana rilis

| Minggu | Tahap | Output |
|---|---|---|
| 1 | Persiapan | Proposal, repo, environment |
| 2–4 | Pipeline pose + metrik heuristik | Demo real-time |
| 3–6 | Pengumpulan & pelabelan dataset | Dataset multi-orang |
| 6–8 | Training classifier + kalibrasi skor | `gesture_best.pt`, rumus skor |
| 8–9 | Laporan PDF + bot Telegram + QR deep link | Alur end-to-end |
| 10–11 | Chatbot + guardrail + RAG | Chatbot terbatas topik |
| 12–13 | Evaluasi & uji pengguna | Hasil evaluasi, laporan akhir |
| 14 | Demo & presentasi | — |

**Titik aman:** akhir minggu 4 (demo real-time) dan minggu 9 (laporan + Telegram) — proyek tetap utuh bila waktu mepet.

---

## 12. Risiko & mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Dataset hanya dari satu orang | Model gagal mengenali orang lain | Rekam ≥ 10 orang; split per orang |
| Foto berurutan hampir kembar | Akurasi terlihat terlalu tinggi | Dedupe frame; split per waktu/orang |
| Kelas tidak seimbang | Model bias ke kelas mayoritas | Rekaman terarah untuk kelas yang kurang |
| Tangan tertutup badan | Keypoint hilang | Abaikan keypoint confidence rendah; aturan terlipat memakai ambang lebih longgar |
| Model gambar ikut mempelajari latar belakang | Gagal di ruangan lain | **Sudah diatasi**: beralih ke fitur keypoint + aturan geometri |
| Getaran keypoint terbaca sebagai gerak | Gestur aktif muncul palsu | Penghalusan EMA, deadband, confidence minimum, kunci pose diam |
| Ambang dikalibrasi pada satu orang | Kurang cocok untuk orang lain | Kalibrasi ulang dengan beberapa presenter; laporkan nilai akhirnya |
| Tidak ada GPU NVIDIA | Training lambat | Training di CPU dengan model nano, atau di laptop rekan (RTX 2050) |
| Biaya / penyalahgunaan API LLM | Kuota habis | Filter topik sebelum model utama, rate limit, `max_tokens` |
| Privasi peserta | Masalah etika | Persetujuan tertulis, ID anonim, blur wajah, video tidak disimpan |

---

## 13. Pertanyaan terbuka

- Penyedia LLM mana yang dipakai (cloud vs lokal), dan berapa kuotanya?
- Siapa yang menjadi penilai manusia untuk validasi (dosen, asisten, rekan)?
- Bobot tiap aspek dalam skor keseluruhan — perlu dikalibrasi dengan data penilai.
- Apakah ambang aturan perlu dibuat otomatis (dipelajari dari data) setelah data multi-orang tersedia?
- Apakah dosen membutuhkan akses ke ringkasan latihan mahasiswa?
