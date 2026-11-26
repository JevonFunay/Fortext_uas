================================================================================
TUGAS A FORENSIC TEXT
DETEKSI DOKUMEN DUPLIKAT ATAU HAMPIR DUPLIKAT MENGGUNAKAN SIMHASH
================================================================================

1. IDENTITAS KELOMPOK
--------------------------------------------------------------------------------
Silakan isi nama dan NIM seluruh anggota kelompok di bawah ini sebelum dikumpulkan:

- Anggota 1 : [Isi Nama Lengkap] - [Isi NIM]
- Anggota 2 : [Isi Nama Lengkap] - [Isi NIM]
- Anggota 3 : [Isi Nama Lengkap] - [Isi NIM]
- Anggota 4 : [Isi Nama Lengkap] - [Isi NIM]
- Kelas     : [Isi Kelas / Mata Kuliah]


2. DESKRIPSI SINGKAT & KORPUS
--------------------------------------------------------------------------------
Program ini mengimplementasikan algoritma Simhash 64-bit dari nol (tanpa library
Simhash eksternal, tanpa machine learning, tanpa embedding, dan tanpa API berbayar)
untuk membandingkan kemiripan teks antardokumen pada korpus lima artikel web
mengenai klarifikasi klaim Sri Sultan Hamengkubuwono X menghentikan program MBG:

- D1 : dokumen1.txt — Pemprov Jateng (Tim.Padhang, 23 November 2026)
- D2 : dokumen2.txt — Tirto (Tim Riset Tirto, 20 Nov 2026 14:00 WIB)
- D3 : dokumen3.txt — InfoPublik (Putri / Redaksi, 23 November 2026)
- D4 : dokumen4.txt — Detik / detikJogja (Aditya Mardiastuti, 20 Nov 2026)
- D5 : dokumen5.txt — Komdigi (20 November 2026)

Catatan Penting:
- Dokumen asli (`dokumen1.txt` s.d. `dokumen5.txt`) TIDAK diubah.
- Hasil pemisahan metadata (judul, subjudul, penulis, redaktur, tanggal, kategori)
  dan elemen non-isi situs (`Penjelasan:`, `Penelusuran Fakta`, `Kesimpulan`,
  `Klarifikasi Hoaks • Hoaks•`) disimpan terpisah di folder `korpus_bersih/`
  beserta berkas `korpus_bersih/metadata_korpus.json`.
- Seluruh lima file .txt asli terbaca utuh (UTF-8), namun tidak mencantumkan
  URL artikel di dalam file .txt aslinya, dan `dokumen5.txt` tidak mencantumkan
  nama penulis secara eksplisit.
- Hasil program menunjukkan tingkat kemiripan teks berdasarkan Simhash, BUKAN
  vonis bahwa penerbit melakukan plagiarisme.


3. STRUKTUR PROYEK
--------------------------------------------------------------------------------
ForText_UAS/
├── .streamlit/config.toml          # Konfigurasi tema dasar Streamlit (Navy Editorial)
├── dokumen1.txt ... dokumen5.txt   # Dokumen korpus asli (tidak diubah)
├── korpus_bersih/                  # Teks isi bersih dan metadata terpisah
│   ├── dokumen1.txt ... dokumen5.txt
│   └── metadata_korpus.json
├── text_processing.py              # Pembersihan metadata, normalisasi, segmentasi, shingling
├── simhash_core.py                 # Implementasi Simhash 64-bit (SHA-256) & jarak Hamming
├── comparison.py                   # Perbandingan 2 dokumen, pencocokan 1-ke-1, & 10 pasangan
├── prepare_corpus.py               # Skrip pembuat folder korpus_bersih/ dari dokumen asli
├── ui_theme.py                     # Token desain, palet tema warna, ikon SVG & konfigurasi UI
├── app.py                          # Antarmuka web Streamlit
├── test_simhash.py                 # Pengujian otomatis (unittest)
├── requirements.txt                # Daftar pustaka Python yang diperlukan
└── ReadMe.txt                      # Dokumen panduan ini


4. CARA INSTALASI
--------------------------------------------------------------------------------
Prasyarat: Python 3.10 atau lebih baru.

1) Buka terminal / PowerShell di folder proyek `ForText_UAS`.
2) (Opsional) Buat dan aktifkan virtual environment jika diinginkan.
3) Pasang dependensi dengan perintah:

       python -m pip install -r requirements.txt


5. CARA MENJALANKAN PROGRAM & PENGUJIAN
--------------------------------------------------------------------------------
a) (Opsional) Menjalankan ulang pembersihan korpus dari file asli ke `korpus_bersih/`:

       python prepare_corpus.py

b) Menjalankan aplikasi antarmuka Streamlit:

       python -m streamlit run app.py

   Catatan: Jangan menjalankan dengan `python app.py` saja karena Streamlit
   membutuhkan runner server web. Jika tidak sengaja menjalankan `python app.py`,
   program akan menampilkan pengingat perintah yang benar.
   Setelah berjalan, buka tautan lokal yang tampil di terminal (umumnya
   http://localhost:8501) pada peramban (browser).

   Fitur utama & kemudahan kustomisasi pada antarmuka (3 tab):
   - Tab 1 (Bandingkan 2 Dokumen): pilih 2 dokumen (termasuk opsi uji kosong D0),
     kartu kesimpulan visual bahasa awam + bar progres, 4 KPI ringkas, serta
     pilihan tampilan Pasangan Kalimat Mirip / Baca Artikel Berdampingan /
     Tabel Kalimat & Fingerprint Biner-Desimal, ditambah rumus persentase.
   - Tab 2 (Semua 10 Pasangan): ringkasan kategori, tabel 10 pasangan unik
     berbaris progres, dan matriks kemiripan 5x5 berwarna.
   - Tab 3 (Korpus & Cara Kerja): daftar 5 dokumen, pembanding teks asli vs
     bersih, inspeksi langkah Simhash per kalimat, dan catatan konfirmasi dosen.
   - Kustomisasi mudah: ubah preset ketelitian (Identik/Standar/Longgar) langsung
     di sidebar, ganti Tema Warna (Navy Editorial, Cobalt Modern, Emerald Tenang,
     Monokrom Swiss) dan batas kategori dari menu "Kustomisasi Tampilan & Kategori",
     atau edit token desain secara terpusat pada `ui_theme.py` dan `.streamlit/config.toml`.

c) Menjalankan pengujian otomatis (unit test):

       python -m unittest test_simhash.py -v


6. PENJELASAN ALGORITMA SIMHASH YANG DIIMPLEMENTASIKAN
--------------------------------------------------------------------------------
Program menjalankan 13 langkah berikut secara transparan di `text_processing.py`,
`simhash_core.py`, dan `comparison.py`:

1. Normalisasi teks: seluruh huruf diubah menjadi huruf kecil (lowercase) dan
   spasi berlebih dirapikan. Tidak dilakukan stemming maupun penghapusan stopword.
2. Segmentasi kalimat: dokumen bersih dipecah menjadi kalimat utuh dengan menjaga
   keutuhan tanda kutip (mis. kutipan langsung dan kutipan multi-baris) serta
   tidak memutus titik pada domain situs (mis. `harianjogja.com`).
3. Pemberian ID kalimat: setiap kalimat diberi ID unik berformat `D1-K1`, `D1-K2`,
   dan seterusnya.
4. Pembentukan shingle: setiap kalimat dipecah menjadi shingle unigram/token
   alfanumerik `[a-z0-9]+` (baku). Tersedia pula opsi `Unigram + Bigram` di
   antarmuka untuk perbandingan.
5. Pembobotan TF: frekuensi kemunculan tiap shingle di dalam kalimat dihitung
   sebagai bobot Term Frequency (TF).
6. Hash deterministik 64-bit: setiap shingle di-hash menggunakan SHA-256 (UTF-8),
   lalu dipotong mengambil 64 bit paling signifikan (8 byte pertama). Hash ini
   konsisten antarproses (berbeda dengan fungsi `hash()` bawaan Python).
7. Representasi biner: nilai hash 64-bit diubah menjadi string biner sepanjang
   tepat 64 karakter (`0` dan `1`).
8. Vektor akumulasi: dibuat vektor berukuran 64 bernilai awal 0. Untuk setiap
   shingle dengan bobot TF, jika bit ke-i adalah `1` maka `vektor[i] += TF`,
   sedangkan jika bit ke-i adalah `0` maka `vektor[i] -= TF`.
9. Pembentukan fingerprint: setiap komponen vektor yang bernilai positif (`> 0`)
   menjadi bit `1`, sedangkan nol atau negatif (`<= 0`) menjadi bit `0`. Hasil
   disimpan dalam bentuk biner 64-bit dan nilai integer desimal.
10. Penyimpanan: fingerprint biner, fingerprint desimal, ID kalimat, teks asli,
    dan rincian perhitungan disimpan dalam objek `SentenceFingerprint`.
11. Perbandingan pasangan kalimat: setiap kalimat Dokumen A dibandingkan dengan
    setiap kalimat Dokumen B (`N_A x N_B` pasangan).
12. Jarak Hamming: dihitung dengan operasi XOR (`fp_a ^ fp_b`), lalu menghitung
    jumlah bit `1` pada hasil XOR tersebut (`bit_count()`).
13. Aturan ambang: pasangan kalimat ditandai sebagai pasangan kandidat mirip jika
    memenuhi `Jarak Hamming <= K`, dengan nilai ambang `K` (0..64, baku `3`)
    dapat diatur langsung melalui antarmuka.


7. RUMUS PERSENTASE KEMIRIPAN (BONUS) & KATEGORI
--------------------------------------------------------------------------------
Untuk menghindari penghitungan ulang satu kalimat terhadap banyak kalimat sekaligus,
program membedakan:
- Jumlah Pasangan Kandidat : semua pasangan (A_i, B_j) dengan Jarak Hamming <= K.
- Jumlah Pasangan Cocok Satu-ke-Satu (M): himpunan bagian dari pasangan kandidat
  yang dipilih secara greedy mulai dari jarak Hamming terkecil, dengan syarat
  setiap ID kalimat Dokumen A dan Dokumen B hanya digunakan paling banyak satu kali.
  Dengan demikian selalu berlaku M <= min(N_A, N_B).

Rumus Persentase Kemiripan Utama (Sørensen-Dice berbasis kalimat 1-ke-1):

    Persentase Kemiripan (%) = (2 * M) / (N_A + N_B) * 100%

Keterangan:
- M   = jumlah pasangan kalimat yang cocok satu-ke-satu
- N_A = jumlah kalimat Dokumen A
- N_B = jumlah kalimat Dokumen B
- Nilai selalu berada pada rentang 0% sampai 100% dan bersifat simetris.
- Jika N_A = 0 atau N_B = 0 (dokumen kosong), persentase ditetapkan 0.00%.

Metrik pendukung yang turut ditampilkan (tidak menggantikan rumus utama):
- Cakupan Dokumen A (%) = (M / N_A) * 100%
- Cakupan Dokumen B (%) = (M / N_B) * 100%

Kategori Kemiripan (PILIHAN IMPLEMENTASI — BUKAN KETENTUAN RESMI DOSEN):
- Duplikat         : >= 80%  (dapat diubah di sidebar)
- Hampir Duplikat  : 30% s.d. < 80% (dapat diubah di sidebar)
- Kemiripan Rendah : < 30%   (dapat diubah di sidebar)

Kategori ini hanya label bantu interpretasi dan bukan vonis plagiarisme.


8. ASUMSI IMPLEMENTASI & BAGIAN YANG PERLU DIKONFIRMASI KE DOSEN
--------------------------------------------------------------------------------
Saat proyek ini dikerjakan, file PDF panduan tugas maupun materi kuliah TIDAK
ditemukan di dalam folder proyek (hanya terdapat `dokumen1.txt` s.d. `dokumen5.txt`).
Oleh karena itu, beberapa hal berikut dicatat sebagai asumsi implementasi dan
HARUS dikonfirmasi kepada dosen sebelum menyatakan seluruh ketentuan panduan terpenuhi:

1. Variasi Shingle (Unigram vs Unigram + Bigram):
   - Mode baku menggunakan Unigram sesuai daftar langkah wajib.
   - Opsi `Unigram + Bigram` tetap disediakan di antarmuka untuk perbandingan.
   - Perlu konfirmasi dosen apakah penilaian akhir mewajibkan unigram saja atau
     gabungan unigram + bigram.

2. Notasi Shift Kanan "2 >> B" dan Pengurutan Nilai Desimal:
   - Tanpa melihat PDF panduan / slide kuliah asli, notasi "2 >> B" bersifat ambigu
     (tidak diketahui secara pasti apakah yang dimaksud adalah pergeseran bit,
     rotasi blok bit untuk pencarian tabel Simhash multi-tabel, atau salah ketik
     urutan operand).
   - Program TIDAK menebak bahwa "2 >> B" pasti berarti `fingerprint >> 2`.
   - Fingerprint 64-bit asli (biner dan desimal) beserta perhitungan jarak Hamming
     dasarnya dipertahankan utuh agar selalu dapat diverifikasi.
   - Fitur pengurutan tabel berdasarkan nilai desimal disediakan sebagai opsi
     tampilan tanpa mengubah nilai fingerprint asli.

3. Aturan Tanda Ambang (`<= K` vs `< K`):
   - Implementasi memakai `Jarak Hamming <= K` agar nilai `K = 0` tetap dapat
     mencocokkan kalimat identik (jarak 0). Jika dosen menghendaki strictly `< K`,
     perlu konfirmasi atau penyesuaian nilai ambang.

4. Pemisahan Subjudul Bagian dan Subjudul Tajuk:
   - Pada `dokumen2.txt` (Tirto), baris ringkasan di bawah judul sebelum byline
     penulis/tanggal dipisahkan sebagai `subjudul` pada metadata, dan subjudul
     bagian (`Penelusuran Fakta`, `Kesimpulan`) dipisahkan sebagai elemen non-isi
     sebagaimana label `Penjelasan:` pada `dokumen1.txt`.
   - Pada `dokumen1.txt`–`dokumen5.txt`, seluruh kalimat isi dan kutipan asli
     dipertahankan apa adanya tanpa diubah.
