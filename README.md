[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 3: Yield, Rework & Defect Tracking System

**Status: Selesai, kecuali deploy dashboard (laporan versi 2).** Rancangan dan laporan (7 bagian evaluasi) ada di [`design-and-report/index.html`](design-and-report/index.html), tab *Design Project* dan *Report Project*. Dashboard HTML: [`project/results/3-presentation/dashboard.html`](project/results/3-presentation/dashboard.html). Dashboard Streamlit: `project/code/3-presentation/python/streamlit_app.py` (diuji lokal, belum di-deploy).

**Tujuan:** membangun sistem pemantauan harian yang menunjukkan stasiun, shift, dan jenis defect yang paling menurunkan yield dan menambah beban rework, sehingga perbaikan dapat difokuskan pada sumber masalah terbesar dan dampaknya dapat dipantau dari hari ke hari.

| | |
|---|---|
| Kategori | Manufaktur (lini perakitan smartphone) |
| Tingkat | Mudah |
| Data | Data simulasi buatan sendiri (10 stasiun, 3 model, 2 shift, 75 hari kerja) |
| Tools | Python (pandas, NumPy), DuckDB + SQL, Excel (cek silang), Streamlit + Plotly, dashboard HTML, GitHub |

## 1. Problem
Stasiun, shift, dan jenis defect mana yang paling menurunkan yield dan menambah rework, dan bagaimana trennya dari hari ke hari? Dipecah menjadi 14 pertanyaan (9 Utama) dalam 6 tema; daftar lengkap di halaman rancangan.

## 2. Data
Data simulasi buatan sendiri, dibuat oleh `project/code/1-data-preparation/python/01_generate_data.py` dengan seed tetap (hasil identik setiap dijalankan). Tidak memakai dataset publik atau data perusahaan, jadi tidak ada masalah lisensi. 4.500 baris production_daily (mentah 4.535), 7.100 baris defect_log, 28.566 unit rework_log. Fakta yang sengaja ditanam dan data kotor (254 baris) dicatat di `project/data/ground_truth.json`. Rincian: `project/data/README.md`, `project/docs/data_dictionary.md`.

## 3. Analysis
Pipeline: SQL (DuckDB, constraint + 16 view KPI) menghitung KPI, pandas menghitung ulang secara independen, Excel menghitung ulang sampel dengan rumus, dashboard menghitung ulang sesuai filter. Cek silang: SQL vs pandas 25/25 PASS, SQL vs Excel 49/49 PASS.

Temuan utama (angka dari `project/results/`):
- **Yield**: RTY lini 85,53% meski rata-rata FPY stasiun 98,45%; final yield setelah rework 98,27%. Stasiun FPY terendah: Reflow Soldering (95,99%), 26,2% dari kehilangan RTY.
- **Model**: RTY Basic 87,76%, Plus 85,90%, Pro 82,33%.
- **Defect**: 12 dari 17 jenis membentuk sekitar 80% NG; teratas Solder bridge (17,8%).
- **Shift**: Component Placement, NG rate Shift 2 2,15% vs Shift 1 1,06%; stasiun lain berselisih kecil. Ini pola, bukan penyebab.
- **Rework**: recovery 88,8%, 3.199 scrap. Paling sulit: Dead pixel (recovery 29,1%).
- **Antrean**: puncak 78 unit pada 2026-04-10, pulih setelahnya.
- **Lonjakan**: 5 hari (2026-04-06 sampai 2026-04-10), semuanya di Screen Assembly, terpusat di SCR-01.
- **Fakta yang ditanam**: 5 dari 5 ditemukan.

## 4. Recommendation
- Prioritaskan Reflow Soldering dan defect Solder bridge.
- Periksa di lapangan mengapa Component Placement lebih buruk di Shift 2 sebelum menyimpulkan penyebab.
- Dead pixel sulit di-rework: cegah di hulu daripada diperbaiki.
- Pasang peringatan lonjakan per stasiun (bukan per lini) di dashboard harian; pakai satu definisi KPI (`project/docs/kpi_definitions.md`).

## 5. Impact
[estimated, simulated] Menurunkan NG Reflow Soldering sebesar 30% menyelamatkan sekitar 646 unit per bulan dari rework, menghemat sekitar 184 jam rework, dan menaikkan RTY dari 85,53% ke 86,60%. Dampak nyata belum diukur karena datanya simulasi.

## Batasan
- Data simulasi: hasil membuktikan metode, bukan kondisi pabrik. Fakta yang ditemukan adalah fakta yang ditanam sendiri.
- Kapasitas rework, peluang berhasil rework, dan menit rework per unit adalah parameter buatan sendiri.
- `rework_log` tidak punya kolom shift: saat filter Shift aktif di dashboard, Final yield dan Scrap rate tidak dihitung.
- Perbedaan antar shift belum diuji secara statistik; persentase dari hari sepi mudah melonjak (tren memakai rata-rata 7 hari).

## Item terbuka
- Dashboard Streamlit belum di-deploy ke Streamlit Community Cloud (success criteria "dashboard ter-deploy" belum terpenuhi).
- One-sheet infografik (Utama) dan slide presentasi (Opsional) tidak dibuat.
- Kriteria "orang awam menyebut stasiun dan defect terburuk dalam < 1 menit" belum diuji ke pembaca sebenarnya.

## Menjalankan
Semua perintah dari folder `project/`. Skrip memakai jalur relatif, jadi bisa dijalankan dari mana saja. Langkah Excel (06) membutuhkan Windows + Microsoft Excel.
```
cd project
pip install -r requirements.txt
python code/1-data-preparation/python/01_generate_data.py   # data/raw, reference, ground_truth.json
python code/1-data-preparation/python/02_clean_data.py      # data/clean, cleaning_log
python code/1-data-preparation/python/03_build_db.py        # yield.duckdb + uji constraint
python code/2-analysis/python/04_run_queries.py             # view KPI -> results/2-analysis/*.csv
python code/2-analysis/python/05_crosscheck.py              # SQL vs pandas (semua PASS)
python code/2-analysis/python/06_excel_crosscheck.py        # SQL vs Excel (Windows + Excel)
python code/2-analysis/python/07_sensitivity.py             # tiga perlakuan data kotor
python code/2-analysis/python/08_ground_truth.py            # fakta ditanam vs temuan
python code/3-presentation/python/09_build_dashboard.py     # dashboard.html + dash_*.csv
python code/3-presentation/python/10_build_notebook.py
jupyter nbconvert --to notebook --execute --inplace results/3-presentation/analysis.ipynb
python code/3-presentation/python/11_build_readme.py        # README.md
python ../design-and-report/src/build_report.py             # design-and-report/index.html
streamlit run code/3-presentation/python/streamlit_app.py          # dashboard Streamlit
```

## Struktur repository
Kode dan hasil dipisah, keduanya mengikuti tahap yang sama (1 data-preparation, 2 analysis, 3 presentation). Di dalam `code/` dipisah lagi per tool.
```
README.md                      ringkasan project (file ini)
index.html                     pengalihan ke design-and-report/ (URL GitHub Pages tetap)
design-and-report/
  index.html                   halaman Design Project dan Report Project
  src/                         page_v1.html (sumber Design), build_report.py, report_lib.py, report.css
project/
  code/                        PROGRAM
    common.py                  jalur dan konstanta bersama
    1-data-preparation/        python/ (01-03)   sql/ (01_schema, 02_load)
    2-analysis/                python/ (04-08, kpi_pandas)   sql/ (03_kpi_views)
    3-presentation/            python/ (09-11, streamlit_app)   html/ (dashboard_template)
  results/                     HASIL ANALISIS
    1-data-preparation/        cleaning_log, data_quality_summary, constraint_tests, ...
    2-analysis/                csv hasil query, crosscheck(.xlsx), sensitivity, ground_truth_check
    3-presentation/            dashboard.html, analysis.ipynb, dash_*.csv
  data/                        raw/ clean/ (tidak di-commit), reference/, ground_truth.json, README.md
  docs/                        kpi_definitions, data_dictionary, cleaning_log
  requirements.txt
```
