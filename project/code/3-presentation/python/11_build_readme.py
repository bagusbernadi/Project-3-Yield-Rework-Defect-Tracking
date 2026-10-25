"""Langkah 12: menulis README.md di root repo; semua angka dibaca dari results/*.csv."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, result

R = lambda n: pd.read_csv(result(n))
n = lambda v: f"{int(round(v)):,}".replace(",", ".")
d = lambda v, k=1: f"{v:.{k}f}".replace(".", ",")
p = lambda v, k=1: d(v * 100, k) + "%"

st, ln, par, shs, rd = R("station.csv"), R("line_kpi.csv").iloc[0], R("pareto_line.csv"), R("shift_station.csv"), R("rework_defect.csv")
sp, imp, cx, ce, gt, bl = R("spike_days.csv"), R("impact.csv"), R("crosscheck.csv"), R("crosscheck_excel.csv"), R("ground_truth_check.csv"), R("backlog_daily.csv")
tr, mod, drl = R("table_rows.csv"), R("model.csv").set_index("model"), R("spike_drill.csv")
w, g, days = st.loc[st.fpy.idxmin()], shs.loc[shs.gap.idxmax()], sp[sp.is_spike]
b = imp[(imp.target_type == "station") & (imp.reduction == .3)].iloc[0]
sc = rd.iloc[0]

md = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

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
Data simulasi buatan sendiri, dibuat oleh `project/code/1-data-preparation/python/01_generate_data.py` dengan seed tetap (hasil identik setiap dijalankan). Tidak memakai dataset publik atau data perusahaan, jadi tidak ada masalah lisensi. {n(tr.clean_rows[0])} baris production_daily (mentah {n(tr.raw_rows[0])}), {n(tr.clean_rows[1])} baris defect_log, {n(tr.clean_rows[2])} unit rework_log. Fakta yang sengaja ditanam dan data kotor ({n(tr.flagged_rows[0] + tr.flagged_rows[1])} baris) dicatat di `project/data/ground_truth.json`. Rincian: `project/data/README.md`, `project/docs/data_dictionary.md`.

## 3. Analysis
Pipeline: SQL (DuckDB, constraint + 16 view KPI) menghitung KPI, pandas menghitung ulang secara independen, Excel menghitung ulang sampel dengan rumus, dashboard menghitung ulang sesuai filter. Cek silang: SQL vs pandas {n((cx.status == 'PASS').sum())}/{n(len(cx))} PASS, SQL vs Excel {n((ce.status == 'PASS').sum())}/{n(len(ce))} PASS.

Temuan utama (angka dari `project/results/`):
- **Yield**: RTY lini {p(ln.rty, 2)} meski rata-rata FPY stasiun {p(ln.avg_station_fpy, 2)}; final yield setelah rework {p(ln.final_yield, 2)}. Stasiun FPY terendah: {w.station} ({p(w.fpy, 2)}), {d(w.rty_loss_share * 100)}% dari kehilangan RTY.
- **Model**: RTY Basic {p(mod.rty['Basic'], 2)}, Plus {p(mod.rty['Plus'], 2)}, Pro {p(mod.rty['Pro'], 2)}.
- **Defect**: {n(par.vital_few.sum())} dari {n(len(par))} jenis membentuk sekitar 80% NG; teratas {par.defect_name[0]} ({p(par.share[0])}).
- **Shift**: {g.station}, NG rate Shift 2 {p(g.ng_rate_s2, 2)} vs Shift 1 {p(g.ng_rate_s1, 2)}; stasiun lain berselisih kecil. Ini pola, bukan penyebab.
- **Rework**: recovery {p(ln.recovery_rate)}, {n(ln.scrap)} scrap. Paling sulit: {sc.defect_name} (recovery {p(sc.recovery_rate)}).
- **Antrean**: puncak {n(bl.backlog.max())} unit pada {bl.date[bl.backlog.idxmax()]}, pulih setelahnya.
- **Lonjakan**: {n(len(days))} hari ({days.date.iloc[0]} sampai {days.date.iloc[-1]}), semuanya di {days.stations.iloc[0]}, terpusat di {drl[drl.dim == 'defect'].value.iloc[0]}.
- **Fakta yang ditanam**: {n(gt.match.sum())} dari {n(len(gt))} ditemukan.

## 4. Recommendation
- Prioritaskan {w.station} dan defect {par.defect_name[0]}.
- Periksa di lapangan mengapa {g.station} lebih buruk di Shift 2 sebelum menyimpulkan penyebab.
- {sc.defect_name} sulit di-rework: cegah di hulu daripada diperbaiki.
- Pasang peringatan lonjakan per stasiun (bukan per lini) di dashboard harian; pakai satu definisi KPI (`project/docs/kpi_definitions.md`).

## 5. Impact
[estimated, simulated] Menurunkan NG {b.target} sebesar 30% menyelamatkan sekitar {n(b.units_saved_month)} unit per bulan dari rework, menghemat sekitar {n(b.rework_hours_saved_month)} jam rework, dan menaikkan RTY dari {p(b.rty_old, 2)} ke {p(b.rty_new, 2)}. Dampak nyata belum diukur karena datanya simulasi.

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
"""
(ROOT.parent / "README.md").write_text(md, encoding="utf-8")
print("README.md ditulis")
