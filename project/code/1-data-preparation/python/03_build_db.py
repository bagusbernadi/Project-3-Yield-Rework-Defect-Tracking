"""Langkah 5: membuat yield.duckdb dari data bersih (SQL 01-02) lalu menguji aturan pengecekan.

Uji: baris kotor dari data mentah dicoba dimasukkan; setiap baris harus ditolak oleh constraint.
Hasil: results/1-data-preparation/constraint_tests.csv.
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_PREP, SQL_PREP, chdir_root

chdir_root()
DB_PATH.unlink(missing_ok=True)
con = duckdb.connect(str(DB_PATH))
for f in ("01_schema.sql", "02_load.sql"):
    con.execute((SQL_PREP / f).read_text(encoding="utf-8"))

base = "INSERT INTO production_daily VALUES ('2026-03-02', '{shift}', 'Packaging', 'Pro', 'OP20', {i}, {ok}, {ng})"
tests = [
    ("baris ganda (kunci sama)", con.execute("SELECT * FROM production_daily LIMIT 1").fetchone()),
    ("jumlah negatif", base.format(shift="Shift 1", i=100, ok=110, ng=-10)),
    ("OK + NG > input", base.format(shift="Shift 1", i=100, ok=99, ng=5)),
    ("shift kosong", base.replace("'{shift}'", "NULL").format(i=100, ok=95, ng=5)),
    ("kode defect salah ketik", "INSERT INTO defect_log VALUES ('2026-03-02', 'Shift 1', 'Reflow Soldering', 'Pro', 'rfl-01', 3)"),
    ("rework selesai sebelum masuk", "INSERT INTO rework_log VALUES ('RWX', '2026-03-05', '2026-03-04', 'Packaging', 'Pro', 'PKG-01', 'OK')"),
]
rows = []
for name, sql in tests:
    if isinstance(sql, tuple):
        sql = "INSERT INTO production_daily VALUES (" + ", ".join(repr(str(v)) for v in sql) + ")"
    try:
        con.execute(sql)
        rows.append((name, "diterima", ""))
    except duckdb.Error as e:
        rows.append((name, "ditolak", type(e).__name__))
pd.DataFrame(rows, columns=["test", "outcome", "error"]).to_csv(RES_PREP / "constraint_tests.csv", index=False)

counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
          for t in ("production_daily", "defect_log", "rework_log", "dim_defect", "dim_station", "dim_date")}
con.close()
print(counts)
print(pd.DataFrame(rows).to_string(index=False, header=False))
assert all(r[1] == "ditolak" for r in rows), "ada data salah yang lolos constraint"
