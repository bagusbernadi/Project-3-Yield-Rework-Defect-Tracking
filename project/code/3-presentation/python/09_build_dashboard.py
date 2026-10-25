"""Langkah 11: data dashboard dan dashboard HTML statis.

- results/3-presentation/dash_*.csv : data ringkas untuk dashboard HTML dan Streamlit (dibaca keduanya)
- results/3-presentation/dashboard.html : satu file, data tertanam, KPI dihitung ulang sesuai filter
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, HTML_DIR, MODELS, RES_PRESENT, SHIFTS, STATIONS, result

RES_PRESENT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB_PATH), read_only=True)
prod = con.execute("SELECT date, shift, station, model, input_qty, ok_first_pass, ng_qty FROM production_daily ORDER BY ALL").df()
dlog = con.execute("SELECT date, shift, station, model, defect_code, qty FROM defect_log ORDER BY ALL").df()
rw_in = con.execute("""
    SELECT r.date_in AS date, station_origin AS station, model, defect_code,
           count(*) FILTER (WHERE result = 'OK') AS ok, count(*) FILTER (WHERE result = 'Scrap') AS scrap,
           count(*) FILTER (WHERE result IS NULL) AS open, coalesce(sum(o.work_day - i.work_day), 0) AS lead_sum
    FROM rework_log r JOIN dim_date i ON i.date = r.date_in LEFT JOIN dim_date o ON o.date = r.date_out
    GROUP BY ALL ORDER BY ALL""").df()
rw_out = con.execute("""SELECT date_out AS date, station_origin AS station, model, defect_code, count(*) AS n
    FROM rework_log WHERE date_out IS NOT NULL GROUP BY ALL ORDER BY ALL""").df()
dim = con.execute("SELECT defect_code, defect_name, station FROM dim_defect ORDER BY defect_code").df()
con.close()
for df in (prod, dlog, rw_in, rw_out):
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
for name, df in (("dash_production", prod), ("dash_defect", dlog), ("dash_rework_in", rw_in), ("dash_rework_out", rw_out)):
    df.to_csv(RES_PRESENT / f"{name}.csv", index=False, date_format="%Y-%m-%d")

dates = sorted(prod.date.unique())
di = {d: i for i, d in enumerate(dates)}
ci = {c: i for i, c in enumerate(dim.defect_code)}
S, M, SH = ({v: i for i, v in enumerate(x)} for x in (STATIONS, MODELS, SHIFTS))
spike = pd.read_csv(result("spike_days.csv"))
data = {
    "dates": dates, "stations": STATIONS, "models": MODELS, "shifts": SHIFTS,
    "codes": dim.defect_code.tolist(), "names": dim.defect_name.tolist(), "codeStation": [S[s] for s in dim.station],
    "P": [[di[r.date], SH[r.shift], S[r.station], M[r.model], r.input_qty, r.ok_first_pass, r.ng_qty] for r in prod.itertuples()],
    "D": [[di[r.date], SH[r.shift], S[r.station], M[r.model], ci[r.defect_code], r.qty] for r in dlog.itertuples()],
    "RI": [[di[r.date], S[r.station], M[r.model], ci[r.defect_code], r.ok, r.scrap, r.open, int(r.lead_sum)] for r in rw_in.itertuples()],
    "RO": [[di[r.date], S[r.station], M[r.model], ci[r.defect_code], r.n] for r in rw_out.itertuples()],
    "spikes": [di[str(d)] for d in spike.loc[spike.is_spike, "date"]],
}
tpl = (HTML_DIR / "dashboard_template.html").read_text(encoding="utf-8")
assert tpl.count("/*DATA*/") == 1
html = tpl.replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
(RES_PRESENT / "dashboard.html").write_text(html, encoding="utf-8")
print(f"dashboard.html {len(html) / 1024:.0f} KB")
