"""Langkah 6 dan 8-9: membuat view KPI (SQL 03) lalu menyimpan hasil tiap view ke results/2-analysis/*.csv."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_ANALYSIS, SQL_ANALYSIS, chdir_root

VIEWS = ["v_station", "v_line_kpi", "v_model_station", "v_model", "v_pareto_line", "v_pareto_station",
         "v_shift_station", "v_defect_shift", "v_rework_defect", "v_rework_lead", "v_backlog_daily",
         "v_daily", "v_weekly", "v_station_daily", "v_spike_days", "v_spike_drill", "v_impact"]

chdir_root()
RES_ANALYSIS.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB_PATH))
con.execute((SQL_ANALYSIS / "03_kpi_views.sql").read_text(encoding="utf-8"))
for v in VIEWS:
    df = con.execute(f"SELECT * FROM {v}").df()
    df.to_csv(RES_ANALYSIS / f"{v[2:]}.csv", index=False, float_format="%.10g")
    print(f"{v:18s} {len(df):4d} baris")
con.close()
