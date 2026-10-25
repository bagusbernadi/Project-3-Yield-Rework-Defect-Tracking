"""Langkah 8-9 (presentasi): membuat results/3-presentation/analysis.ipynb (Q1-Q14).

Notebook hanya membaca CSV hasil; semua angka di teks dicetak dari data, tidak diketik tangan.
Jalankan setelah ini:  jupyter nbconvert --to notebook --execute --inplace results/3-presentation/analysis.ipynb
"""
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import RES_PRESENT

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip("\n")))

md("""# Analisis Yield, Rework & Defect (Q1-Q14)

Data simulasi buatan sendiri (10 stasiun, 3 model, 2 shift, 75 hari kerja). Notebook ini membaca CSV di `results/` dan menjawab pertanyaan di halaman rancangan. Semua angka dicetak dari data. Hasil membuktikan metode, bukan kondisi pabrik sebenarnya.""")
code("""
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "code" / "common.py").exists() or (p / "project" / "code" / "common.py").exists())
ROOT = ROOT / "project" if (ROOT / "project" / "code").exists() else ROOT
sys.path.insert(0, str(ROOT / "code"))
from common import result
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#8a8984"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#ebeae6", "figure.dpi": 100})
pct = lambda v, d=1: f"{v*100:.{d}f}%"
read = lambda n: pd.read_csv(result(n))
""")

md("## Q13. Kualitas data (validitas)\nBerapa persen data tidak valid, dan apakah hasil berubah jika dibuang atau dikoreksi?")
code("""
rows, dq, sens, cons = read("table_rows.csv"), read("data_quality_summary.csv"), read("sensitivity.csv"), read("consistency_checks.csv")
display(rows); display(dq); display(cons)
print(f"Baris produksi bermasalah: {rows.flagged_rows[0]} dari {rows.raw_rows[0]} ({rows.flagged_pct[0]}%).")
key = sens[sens.metric.isin(["rty", "final_yield", "rework_rate", "scrap_rate", "top_defect_share", "max_shift_gap"])]
display(key)
same = sens.same_conclusion.dropna().astype(bool).all()
print("Kesimpulan kategorikal (stasiun terburuk, defect teratas, stasiun selisih shift, defect tersulit) sama di tiga varian:", same)
""")

md("## Q1-Q3. Yield: stasiun, final yield, model")
code("""
st, line, mod = read("station.csv"), read("line_kpi.csv").iloc[0], read("model.csv")
w = st.loc[st.fpy.idxmin()]
print(f"Stasiun FPY terendah: {w.station} ({pct(w.fpy,2)}), menyumbang {pct(w.rty_loss_share)} dari seluruh kehilangan RTY.")
print(f"Rata-rata FPY stasiun {pct(line.avg_station_fpy,2)}, tetapi RTY lini {pct(line.rty,2)}.")
print(f"Final yield lini {pct(line.final_yield,2)} vs RTY {pct(line.rty,2)}: rework menyelamatkan {(line.final_yield-line.rty)*100:.1f} poin.")
fig, ax = plt.subplots(figsize=(9, 3.6))
ng = st.ng_qty / st.input_qty
ax.bar(st.station, ng, color=[ORANGE if v == ng.max() else BLUE for v in ng])
ax.set_ylabel("NG rate percobaan pertama"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.set_ylim(0)
plt.xticks(rotation=35, ha="right"); plt.tight_layout(); plt.show()
display(st[["seq", "station", "input_qty", "ng_qty", "fpy", "final_yield", "rty_loss_share"]].round(4))
display(mod.round(4))
ms = read("model_station.csv").pivot(index="model", columns="seq", values="fpy")
display((1 - ms).round(4).rename_axis("NG rate", axis=1))
""")

md("## Q4-Q5. Defect: Pareto dan shift")
code("""
par, ds, ss = read("pareto_line.csv"), read("defect_shift.csv"), read("shift_station.csv")
n80 = int(par.vital_few.sum())
print(f"{n80} dari {len(par)} jenis defect menyumbang sekitar 80% dari {par.qty.sum():,} NG. Teratas: {par.defect_name[0]} ({pct(par.share[0])}).")
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.bar(par.defect_code, par.share, color=[BLUE if v else "#9ec5f4" for v in par.vital_few])
ax2 = ax.twinx(); ax2.plot(par.defect_code, par.cum_share, color="#52514e"); ax2.set_ylim(0, 1); ax2.grid(False)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
plt.setp(ax.get_xticklabels(), rotation=45, ha="right"); plt.tight_layout(); plt.show()
g = ss.loc[ss.gap.idxmax()]
print(f"Selisih shift terbesar: {g.station}, NG rate Shift 2 {pct(g.ng_rate_s2,2)} vs Shift 1 {pct(g.ng_rate_s1,2)} (rasio {g.ratio:.2f}).")
print("Stasiun lain: rasio Shift2/Shift1 antara", f"{ss[ss.station != g.station].ratio.min():.2f} dan {ss[ss.station != g.station].ratio.max():.2f}.")
display(ds.head(4).round(4))
""")

md("## Q6-Q8. Rework: recovery, defect tersulit, lead time dan antrean")
code("""
rd, lead, bl = read("rework_defect.csv"), read("rework_lead.csv"), read("backlog_daily.csv")
print(f"Dari {line.ng_events:,.0f} unit NG: {pct(line.recovery_rate)} berhasil diselamatkan, {line.scrap:,.0f} scrap, {line.rework_open:.0f} masih menunggu di akhir periode.")
h = rd.iloc[0]
print(f"Defect tersulit: {h.defect_name} ({h.defect_code}), recovery {pct(h.recovery_rate)}, {h.scrap:,.0f} scrap; defect berikutnya {rd.defect_name[1]} {pct(rd.recovery_rate[1])}.")
display(lead)
print(f"Antrean puncak {bl.backlog.max():.0f} unit pada {bl.date[bl.backlog.idxmax()]}; antrean > 0 pada {(bl.backlog>0).sum()} dari {len(bl)} hari; akhir periode {bl.backlog.iloc[-1]:.0f}.")
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
axs[0].barh(rd.defect_code[::-1], rd.recovery_rate[::-1], color=[BLUE] * (len(rd) - 1) + [ORANGE]); axs[0].set_xlim(0, 1)
axs[0].xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
axs[1].plot(pd.to_datetime(bl.date), bl.backlog, color=BLUE); axs[1].set_ylim(0); axs[1].set_ylabel("unit menunggu")
plt.tight_layout(); plt.show()
""")

md("## Q9-Q10. Tren harian dan lonjakan")
code("""
dly, spk, drl, wk = read("daily.csv"), read("spike_days.csv"), read("spike_drill.csv"), read("weekly.csv")
days = spk[spk.is_spike]
print(f"Hari lonjakan: {len(days)} ({days.date.iloc[0]} sampai {days.date.iloc[-1]}), stasiun: {', '.join(days.stations.unique())}.")
w6 = wk.loc[wk.ng_per_unit.idxmax()]
print(f"Minggu dengan NG per unit tertinggi: minggu {w6.week} ({w6.week_start}), {w6.ng_per_unit:.3f} vs median mingguan {wk.ng_per_unit.median():.3f}.")
fig, ax = plt.subplots(figsize=(9, 3.4))
d = pd.to_datetime(dly.date)
ax.plot(d, dly.rty, color=GREY, lw=1); ax.plot(d, dly.rty_ma7, color=BLUE, lw=2.5)
for t in pd.to_datetime(days.date): ax.axvspan(t - pd.Timedelta(hours=12), t + pd.Timedelta(hours=12), color="#eda100", alpha=.25)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); plt.tight_layout(); plt.show()
for dim in ("station", "defect"):
    t = drl[drl.dim == dim].iloc[0]
    print(f"Kelebihan NG per hari lonjakan, {dim}: {t.value} menyumbang {pct(t.share_of_excess,0)} dari seluruh kelebihan positif ({t.excess_per_day:.1f} unit per hari).")
for dim in ("model", "shift"):
    t = drl[drl.dim == dim]
    print(f"{dim}: kelebihan positif tersebar " + ", ".join(f"{r.value} {pct(r.share_of_excess,0)}" for r in t.itertuples()) + " (semua positif, tidak ada yang melebihi 60%, jadi tidak terpusat).")
    assert t.share_of_excess.max() < 0.6 and (t.share_of_excess > 0).all()
""")

md("## Q11-Q12. Dampak (estimated)")
code("""
imp = read("impact.csv")
imp["scenario"] = imp.target + " -" + (imp.reduction * 100).round().astype(int).astype(str) + "%"
display(imp[["scenario", "rate_old", "rate_new", "units_saved_month", "scrap_avoided_month", "rework_hours_saved_month", "rty_old", "rty_new"]].round(4))
b = imp[(imp.target_type == "station") & (imp.reduction == .3)].iloc[0]
print(f"[estimated, simulated] NG {b.target} turun 30%: sekitar {b.units_saved_month:,.0f} unit per bulan tidak perlu rework, {b.rework_hours_saved_month:,.0f} jam rework, RTY {pct(b.rty_old,2)} menjadi {pct(b.rty_new,2)}.")
""")

md("## Q14. Cek silang")
code("""
cx, ce = read("crosscheck.csv"), read("crosscheck_excel.csv")
print(f"SQL vs pandas: {(cx.status == 'PASS').sum()}/{len(cx)} PASS. SQL vs Excel: {(ce.status == 'PASS').sum()}/{len(ce)} PASS.")
gt = read("ground_truth_check.csv"); display(gt[["id", "fact", "planted", "found", "match"]])
""")
nb["cells"] = C
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
(RES_PRESENT / "analysis.ipynb").write_text(nbf.writes(nb), encoding="utf-8")
print("analysis.ipynb dibuat,", len(C), "sel")
