"""Q13: apakah hasil berubah jika baris bermasalah dibuang, diperbaiki, atau dibiarkan?

Tiga varian dihitung dengan fungsi pandas yang sama: diperbaiki (data utama), baris bermasalah dibuang,
dan tanpa cleaning. Hasil: results/2-analysis/sensitivity.csv.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CLEAN_DIR, RAW_DIR, RES_ANALYSIS, STATIONS, result
from kpi_pandas import kpis

raw = {t: pd.read_csv(RAW_DIR / f"{t}.csv") for t in ("production_daily", "defect_log", "rework_log")}
clean = {t: pd.read_csv(CLEAN_DIR / f"{t}.csv") for t in raw}
log = pd.read_csv(result("cleaning_log.csv"))
dropped = {}
for t, df in raw.items():
    bad = log.loc[log.table == t, "csv_row"] - 2           # nomor baris CSV -> indeks data mentah
    dropped[t] = df.drop(index=bad)

variants = {"diperbaiki": clean, "dibuang": dropped, "tanpa_cleaning": raw}
res = {v: kpis(d["production_daily"], d["defect_log"], d["rework_log"], STATIONS) for v, d in variants.items()}
keys = ["rty", "final_yield", "rework_rate", "scrap_rate", "recovery_rate", "worst_station", "top_defect",
        "top_defect_share", "defects_in_80pct", "max_shift_gap_station", "max_shift_gap",
        "lowest_recovery_defect", "lowest_recovery_rate"]
rows = []
for k in keys:
    a, b, c = (res[v][k] for v in variants)
    if isinstance(a, str):
        rows.append((k, a, b, c, None, None, a == b == c))
    else:
        rows.append((k, a, b, c, b - a, c - a, None))
out = pd.DataFrame(rows, columns=["metric", "diperbaiki", "dibuang", "tanpa_cleaning",
                                  "diff_dibuang", "diff_tanpa_cleaning", "same_conclusion"])
out.loc[len(out)] = ["rows_production", len(clean["production_daily"]), len(dropped["production_daily"]),
                     len(raw["production_daily"]), None, None, None]
out.to_csv(RES_ANALYSIS / "sensitivity.csv", index=False, float_format="%.10g")
print(out.to_string(index=False))
