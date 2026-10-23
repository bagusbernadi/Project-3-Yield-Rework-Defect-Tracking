[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 3: Yield, Rework & Defect Tracking System

**Status: Design (rancangan).**

Halaman rancangan: https://bagusbernadi.github.io/Project-3-Yield-Rework-Defect-Tracking/

## Tujuan

Membangun sistem pemantauan harian yang menunjukkan stasiun, shift, dan jenis defect yang paling menurunkan yield dan menambah beban rework, sehingga perbaikan dapat difokuskan pada sumber masalah terbesar dan dampaknya dapat dipantau dari hari ke hari.

| | |
|---|---|
| Kategori | Manufaktur (lini perakitan smartphone) |
| Tingkat | Mudah |
| Data | Data simulasi buatan sendiri (10 stasiun, 3 model, 2 shift, ±3 bulan) |
| Tools | Python (pandas, NumPy), DuckDB + SQL, Excel (cek silang), Streamlit + Plotly, GitHub |

## 1. Problem

Pertanyaan utama: stasiun, shift, dan jenis defect mana yang paling menurunkan yield dan menambah rework, dan bagaimana trennya dari hari ke hari?

Pertanyaan ini dipecah menjadi 14 pertanyaan (9 prioritas utama) dalam 6 tema: yield, defect, rework, tren, dampak, dan validitas data. Daftar lengkap ada di halaman rancangan.

## 2. Data

- Sumber data: data simulasi buatan sendiri, dibuat oleh skrip `scripts/generate_data.py` (Versi: v1, rancangan; dibuat saat Tahap B dikerjakan). Tidak memakai dataset publik atau data perusahaan.
- 4 tabel: `production_daily`, `defect_log`, `rework_log`, `dim_defect`.
- Ukuran perkiraan: ±4.500 baris produksi harian, ±6.000 baris defect, 1 baris per unit rework. Jumlah pasti diketahui setelah data dibuat.
- Fakta yang sengaja ditanam (ground truth) dan 2–3% data kotor dipakai untuk menguji apakah analisis berhasil menemukannya.

Belum dikerjakan.

## 3. Analysis

KPI yang dihitung: FPY, RTY, final yield, rework rate, dan scrap rate, ditambah Pareto defect, perbandingan shift dan model, keberhasilan rework, dan tren harian.

Belum dikerjakan.

## 4. Recommendation

Belum dikerjakan.

## 5. Impact

Estimasi unit terselamatkan = (rate lama − rate baru) × volume. Semua angka dampak akan diberi label `estimated` / `simulated`.

Belum dikerjakan.

## Batasan yang sudah diketahui

- Data simulasi: hasil akhir membuktikan metode, bukan kondisi pabrik sebenarnya.
- Pola belum tentu penyebab. Perbedaan antar shift atau stasiun perlu dicek di lapangan.
- Persentase dari hari dengan input sedikit mudah melonjak, sehingga tren memakai rata-rata 7 hari.

## Struktur repository

```
index.html   Halaman rancangan project (GitHub Pages)
README.md    Dokumen ini
```

Struktur lengkap yang direncanakan (docs/, scripts/, sql/, notebooks/, dashboard/, outputs/) ada di bagian "Project Outputs" pada halaman rancangan.
