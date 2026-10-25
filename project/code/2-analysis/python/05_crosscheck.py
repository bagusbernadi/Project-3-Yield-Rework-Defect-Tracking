"""Langkah 7 (bagian 1): cek silang hasil SQL dengan hitungan pandas yang ditulis terpisah.

Hasil: results/2-analysis/crosscheck.csv (semua baris harus PASS).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CLEAN_DIR, RES_ANALYSIS, STATIONS, result
from kpi_pandas import backlog, kpis, spike_days

prod = pd.read_csv(CLEAN_DIR / "production_daily.csv")
dlog = pd.read_csv(CLEAN_DIR / "defect_log.csv")
rlog = pd.read_csv(CLEAN_DIR / "rework_log.csv")
pd_k = kpis(prod, dlog, rlog, STATIONS)

st = pd.read_csv(result("station.csv")).set_index("station")
line = pd.read_csv(result("line_kpi.csv")).iloc[0]
par = pd.read_csv(result("pareto_line.csv"))
sh = pd.read_csv(result("shift_station.csv")).set_index("station")
rd = pd.read_csv(result("rework_defect.csv"))
bl = pd.read_csv(result("backlog_daily.csv"))
sp = pd.read_csv(result("spike_days.csv"))

sql_k = {f"fpy | {s}": st.fpy[s] for s in STATIONS}
sql_k.update({
    "rty": line.rty, "final_yield": line.final_yield, "rework_rate": line.rework_rate,
    "scrap_rate": line.scrap_rate, "recovery_rate": line.recovery_rate,
    "worst_station": st.fpy.idxmin(), "top_defect": par.defect_code[0], "top_defect_share": par.share[0],
    "defects_in_80pct": int(par.vital_few.sum()), "max_shift_gap_station": sh.gap.idxmax(),
    "max_shift_gap": sh.gap.max(), "lowest_recovery_defect": rd.defect_code[0],
    "lowest_recovery_rate": rd.recovery_rate[0],
})
dates = sorted(prod.date.unique())
pd_k["max_backlog"] = int(backlog(rlog, dates).max())
sql_k["max_backlog"] = int(bl.backlog.max())
pd_k["spike_days"] = ", ".join(sorted(spike_days(prod).date.unique()))
sql_k["spike_days"] = ", ".join(sp.loc[sp.is_spike, "date"].astype(str))

rows = []
for k in sql_k:
    a, b = sql_k[k], pd_k[k]
    ok = abs(float(a) - float(b)) < 1e-8 if isinstance(a, (int, float)) and not isinstance(a, bool) else str(a) == str(b)
    rows.append((k, a, b, "PASS" if ok else "FAIL"))
out = pd.DataFrame(rows, columns=["metric", "sql", "pandas", "status"])
out.to_csv(RES_ANALYSIS / "crosscheck.csv", index=False, float_format="%.10g")
print(out.status.value_counts().to_string())
assert (out.status == "PASS").all(), out[out.status != "PASS"]
