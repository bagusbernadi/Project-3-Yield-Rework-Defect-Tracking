"""Langkah 10: mencocokkan temuan analisis dengan fakta yang sengaja ditanam (data/ground_truth.json).

Hasil: results/2-analysis/ground_truth_check.csv.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import GROUND_TRUTH, RES_ANALYSIS, result

gt = {f["id"]: f for f in json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["facts"]}
st = pd.read_csv(result("station.csv"))
pst = pd.read_csv(result("pareto_station.csv"))
sh = pd.read_csv(result("shift_station.csv"))
sp = pd.read_csv(result("spike_days.csv"))
drill = pd.read_csv(result("spike_drill.csv"))
rd = pd.read_csv(result("rework_defect.csv"))
dq = pd.read_csv(result("data_quality_summary.csv"))

rows = []
# 1. stasiun paling sering NG dan defect dominannya
worst = st.loc[st.fpy.idxmin(), "station"]
top = pst[(pst.station == worst) & (pst.rank_in_station == 1)].iloc[0]
rows.append((1, gt[1]["fact"], f"{gt[1]['station']} / {gt[1]['dominant_defect']}",
             f"{worst} (FPY terendah) / {top.defect_code} {top.share_in_station:.1%} dari NG stasiun",
             worst == gt[1]["station"] and top.defect_code == gt[1]["dominant_defect"]))
# 2. selisih shift terbesar
g = sh.loc[sh.gap.idxmax()]
rows.append((2, gt[2]["fact"], f"{gt[2]['station']} / {gt[2]['shift']}",
             f"{g.station}: NG rate Shift 2 {g.ng_rate_s2:.2%} vs Shift 1 {g.ng_rate_s1:.2%}",
             g.station == gt[2]["station"] and g.gap > 0))
# 3. lonjakan: tanggal, stasiun, dan defect penyumbang kelebihan NG terbesar
days = sp.loc[sp.is_spike, "date"].astype(str).tolist()
planted = pd.bdate_range(gt[3]["start"], gt[3]["end"]).strftime("%Y-%m-%d").tolist()
ds = drill[drill.dim == "station"].iloc[0].value
dd = drill[drill.dim == "defect"].iloc[0].value
rows.append((3, gt[3]["fact"], f"{gt[3]['start']} s.d. {gt[3]['end']} / {gt[3]['station']} / {gt[3]['defect_code']}",
             f"{len(days)} hari terdeteksi ({days[0]} s.d. {days[-1]}) / {ds} / {dd}" if days else "tidak terdeteksi",
             days == planted and ds == gt[3]["station"] and dd == gt[3]["defect_code"]))
# 4. defect paling sulit di-rework
low = rd.iloc[0]
rows.append((4, gt[4]["fact"], gt[4]["defect_code"], f"{low.defect_code} recovery {low.recovery_rate:.1%}",
             low.defect_code == gt[4]["defect_code"]))
# 5. data kotor: setiap jenis yang ditanam ditemukan dengan jumlah yang sama
found = dq[dq.table != "rework_log"].groupby("issue").rows.sum()
inj = gt[5]["injected"]
rows.append((5, gt[5]["fact"], ", ".join(f"{k} {v}" for k, v in inj.items()),
             ", ".join(f"{k} {found.get(k, 0)}" for k in inj), all(found.get(k, 0) == v for k, v in inj.items())))

out = pd.DataFrame(rows, columns=["id", "fact", "planted", "found", "match"])
out.to_csv(RES_ANALYSIS / "ground_truth_check.csv", index=False)
print(out.to_string(index=False))
assert out.match.all(), "ada fakta yang tidak ditemukan"
