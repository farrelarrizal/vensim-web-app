# Vensim Scenario Viewer

Aplikasi web sederhana untuk **membuka model Vensim (`.mdl`), mengubah angkanya, menjalankan simulasi, dan membandingkan hasilnya** tanpa perlu membuka Vensim.

Cocok untuk Anda yang ingin bertanya, *"Bagaimana hasilnya kalau angka ini saya ubah?"*

---

## Daftar Isi

1. [Apa yang bisa dilakukan aplikasi ini?](#1-apa-yang-bisa-dilakukan-aplikasi-ini)
2. [Istilah yang perlu diketahui](#2-istilah-yang-perlu-diketahui)
3. [Yang perlu disiapkan](#3-yang-perlu-disiapkan)
4. [Cara memasang (sekali saja)](#4-cara-memasang-sekali-saja)
5. [Cara menjalankan aplikasi](#5-cara-menjalankan-aplikasi)
6. [Cara memakai aplikasi (langkah demi langkah)](#6-cara-memakai-aplikasi-langkah-demi-langkah)
7. [Masalah yang sering muncul](#7-masalah-yang-sering-muncul)
8. [Isi folder proyek](#8-isi-folder-proyek)

---

## 1. Apa yang bisa dilakukan aplikasi ini?

| Fitur | Penjelasan singkat |
|---|---|
| **Unggah model** | Pilih file `.mdl` dari komputer Anda. Aplikasi membaca semua variabel di dalamnya. |
| **Pilih View** | Model Vensim biasanya dibagi menjadi beberapa "halaman" (View). Anda bisa memilih halaman yang ingin dikerjakan. |
| **Ubah angka / rumus** | Pada View yang dipilih, Anda bisa mengetik angka atau rumus baru. |
| **Jalankan skenario** | Satu klik untuk menjalankan simulasi dengan angka baru. Hasilnya disimpan sebagai **skenario**. |
| **Bandingkan** | Grafik dan tabel menunjukkan selisih antar skenario (misalnya skenario A dibanding model asli). |
| **Hapus skenario** | Skenario yang tidak diperlukan bisa dihapus. |
| **Ekspor ke Excel** | Simpan semua hasil ke satu file Excel. |
| **Ekspor ke `.mdl`** | Unduh model yang sudah berisi angka baru, supaya bisa dibuka di Vensim. |

---

## 2. Istilah yang perlu diketahui

| Istilah | Artinya |
|---|---|
| **Model** | File Vensim (`.mdl`) yang berisi "gambaran" sebuah sistem, misalnya pertumbuhan penduduk. |
| **Variabel** | Satu angka atau satu hitungan di dalam model, misalnya "Tingkat kelahiran". |
| **Persamaan** | Rumus atau nilai dari sebuah variabel. Bisa berupa angka biasa (`0.05`) atau rumus. |
| **Simulasi** | Komputer menghitung model langkah demi langkah dari awal sampai akhir waktu. |
| **Skenario** | Satu kali simulasi dengan angka tertentu. Contoh: "Kelahiran naik 10%". |
| **Base** | Skenario dasar, yaitu model asli **tanpa perubahan**. Dipakai sebagai pembanding. Base tidak bisa dihapus. |
| **View (SFD)** | "Halaman" di dalam model Vensim. Satu model bisa punya beberapa View. |
| **Konstanta** | Variabel yang berupa angka tetap. |
| **Stock** | Variabel yang bersifat "tampungan" yang terus bertambah/berkurang (misalnya jumlah penduduk). Di rumusnya ada kata `INTEG`. |
| **Auxiliary** | Variabel yang nilainya dihitung dari variabel lain. |

---

## 3. Yang perlu disiapkan

1. **Python** versi 3.9 atau lebih baru.
   - Unduh di <https://www.python.org/downloads/>
   - Untuk Windows: saat memasang, **centang** kotak **"Add Python to PATH"**.
2. **Git** (untuk mengunduh proyek ini). Unduh di <https://git-scm.com/downloads>
   - Kalau tidak ingin memakai Git, di halaman GitHub klik tombol hijau **Code → Download ZIP**, lalu ekstrak.
3. **File model Vensim** (`.mdl`) milik Anda.

> **Terminal** adalah jendela tempat mengetik perintah.
> - **Mac:** buka aplikasi **Terminal**.
> - **Windows:** buka **Command Prompt** atau **PowerShell**.

---

## 4. Cara memasang (sekali saja)

Ketik perintah di bawah ini satu per satu di Terminal, lalu tekan **Enter** setiap selesai satu baris.

**Langkah 1 - Unduh proyek**

```bash
git clone https://github.com/NAMA-ANDA/vensim-web-app.git
cd vensim-web-app
```

> Ganti `NAMA-ANDA` dengan nama akun GitHub pemilik proyek ini.
> Kalau Anda mengunduh lewat ZIP, cukup masuk ke folder hasil ekstrak: `cd vensim-web-app`

**Langkah 2 - Buat "ruang kerja" khusus** (agar tidak bercampur dengan program lain)

```bash
python3 -m venv .venv
```

> Di Windows, ketik `python -m venv .venv`

**Langkah 3 - Aktifkan ruang kerja tersebut**

Mac / Linux:
```bash
source .venv/bin/activate
```

Windows:
```bash
.venv\Scripts\activate
```

Jika berhasil, di awal baris terminal akan muncul tulisan `(.venv)`.

**Langkah 4 - Pasang semua kebutuhan aplikasi**

```bash
pip install -r requirements.txt
```

Tunggu sampai selesai. Proses ini bisa memakan beberapa menit.

---

## 5. Cara menjalankan aplikasi

Setiap kali ingin memakai aplikasi:

1. Buka Terminal, lalu masuk ke folder proyek:
   ```bash
   cd vensim-web-app
   ```
2. Aktifkan ruang kerja (lihat Langkah 3 di atas).
3. Jalankan aplikasi:
   ```bash
   streamlit run app.py
   ```
4. Browser akan terbuka otomatis. Jika tidak, buka alamat ini secara manual:
   **<http://localhost:8501>**

Untuk **menutup** aplikasi: kembali ke Terminal, tekan **Ctrl + C**.

---

## 6. Cara memakai aplikasi (langkah demi langkah)

### Langkah 1 - Unggah model
Di **panel kiri**, klik **Browse files**, pilih file `.mdl`, lalu klik **Parse & run base model**.
Aplikasi akan membaca model dan menjalankan simulasi awal. Hasilnya menjadi skenario **Base**.

### Langkah 2 - Pilih View
Di bagian atas, pada kotak **Active view**, pilih halaman model yang ingin Anda kerjakan.
Pilih **(All variables)** untuk melihat semua variabel sekaligus.

### Langkah 3 - Ubah angka (tab **Edit & run**)
1. Anda akan melihat tabel berisi variabel pada View tersebut.
2. Klik dua kali pada kolom **equation / value (editable)**, lalu ketik angka atau rumus baru.
   Contoh: ubah `0.05` menjadi `0.08`.
3. Gunakan kolom **Type** atau kotak **Search** untuk memudahkan pencarian variabel.
4. Bagian **Pending edits** menunjukkan semua perubahan Anda (nilai lama dan nilai baru).
   Perubahan tetap tersimpan walaupun Anda pindah View, jadi Anda bisa mengubah beberapa View sekaligus.
5. Isi **Scenario name** (misalnya `Kelahiran naik`), lalu klik **Run scenario**.
6. Jika ingin membatalkan semua perubahan yang belum dijalankan, klik **Clear edits**.

### Langkah 4 - Lihat dan bandingkan hasil (tab **Charts & compare**)
- Pilih skenario dan variabel yang ingin dilihat. Grafik menampilkan semua skenario dalam satu gambar.
- Tabel **Difference vs Base** menunjukkan selisih nilai akhir dibanding Base, dalam angka dan persen.

### Langkah 5 - Kelola skenario (tab **Scenarios**)
- Klik sebuah skenario untuk melihat perubahan apa saja yang dibuat.
- **Load edits**: menyalin perubahan skenario itu ke tabel edit, lalu Anda ubah lagi dan simpan sebagai skenario baru.
- **Delete**: menghapus skenario yang tidak diperlukan. (Base tidak bisa dihapus.)

### Langkah 6 - Simpan hasil (tab **Export**)
- **Excel:** klik **Save all scenarios to Excel**, lalu **Download Excel**.
  Isi file: ringkasan skenario, daftar perubahan, daftar variabel, dan satu lembar hasil untuk setiap skenario.
- **.mdl:** pilih skenario, lalu klik **Download .mdl**. File ini bisa dibuka di Vensim.
  Tombol **Download all ... as .zip** mengunduh semua skenario sekaligus.

---

## 7. Masalah yang sering muncul

| Masalah | Penyebab & cara mengatasi |
|---|---|
| `python: command not found` | Python belum terpasang, atau di Mac coba `python3`. |
| `streamlit: command not found` | Ruang kerja belum aktif. Ulangi **Langkah 3** di bagian pemasangan. |
| `ModuleNotFoundError: No module named 'pysd'` | Kebutuhan belum terpasang. Jalankan lagi `pip install -r requirements.txt`. |
| `SyntaxError: f-string expression part cannot include a backslash` | Versi Python terlalu lama. Pakai **Python 3.9 atau lebih baru** dan pastikan aplikasi versi terbaru. |
| **"Failed to process model"** setelah unggah | Model mungkin memakai fitur Vensim yang belum didukung PySD. Pesan di layar akan menyebutkan penyebabnya. |
| **"Simulation failed"** setelah Run scenario | Angka atau rumus yang Anda ketik tidak valid di Vensim. Periksa penulisannya (misalnya tanda kurung harus berpasangan). |
| Variabel tidak muncul di grafik | Ada variabel (misalnya tabel *lookup*) yang tidak punya hasil simulasi. Ini normal. |
| Halaman aplikasi tidak terbuka | Pastikan Terminal masih berjalan, lalu buka <http://localhost:8501> secara manual. |

Jika masalah belum teratasi, buka **Issues** di halaman GitHub ini dan sertakan **pesan error** serta langkah yang Anda lakukan.

---

## 8. Isi folder proyek

```
vensim-web-app/
├── app.py             <- program utama aplikasi
├── requirements.txt   <- daftar kebutuhan yang perlu dipasang
├── README.md          <- panduan ini
└── outputs/           <- file Excel hasil simpan (dibuat otomatis)
```

---

## Catatan

- Data Anda **diproses di komputer sendiri**. Model tidak dikirim ke internet.
- Hasil simulasi dan skenario tersimpan sementara selama halaman browser terbuka. Jika halaman ditutup atau dimuat ulang, skenario hilang. **Ekspor ke Excel atau .mdl** untuk menyimpannya.
- Aplikasi dibuat dengan [Streamlit](https://streamlit.io/) dan [PySD](https://pysd.readthedocs.io/).