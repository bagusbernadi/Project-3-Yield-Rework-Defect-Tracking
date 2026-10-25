# Data

Tidak ada dataset publik atau data perusahaan. Semua data dibuat oleh skrip `code/1-data-preparation/python/01_generate_data.py` dengan seed tetap (`SEED` di `code/common.py`), sehingga hasilnya sama setiap dijalankan. Tidak ada masalah lisensi.

- `raw/` : data simulasi mentah beserta data kotor (tidak di-commit, dibuat ulang)
- `clean/` : data setelah `02_clean_data.py` (tidak di-commit, dibuat ulang)
- `reference/` : `dim_defect.csv`, `dim_station.csv` (di-commit, dibuat oleh generator)
- `ground_truth.json` : fakta yang sengaja ditanam dan jumlah data kotor yang disisipkan (di-commit)

Membuat ulang: lihat bagian Menjalankan di `README.md` repo.
