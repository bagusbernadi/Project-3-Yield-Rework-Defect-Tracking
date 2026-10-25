"""Dashboard Streamlit (langkah 11): 4 halaman dengan filter tanggal, stasiun, model, dan shift.

Menjalankan (dari folder project/):  streamlit run code/3-presentation/python/streamlit_app.py
Membaca results/3-presentation/dash_*.csv (dibuat oleh 09_build_dashboard.py). Rumus sama dengan dashboard.html.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results"
PRES = RES / "3-presentation"
BLUE, ORANGE, SOFT = "#2a78d6", "#eb6834", "#9ec5f4"

st.set_page_config(page_title="Yield, Rework & Defect", layout="wide")


@st.cache_data
def load():
    r = lambda n: pd.read_csv(PRES / f"dash_{n}.csv", parse_dates=["date"])
    dim = pd.read_csv(PRES.parent.parent / "data" / "reference" / "dim_defect.csv")
    st_order = pd.read_csv(PRES.parent.parent / "data" / "reference" / "dim_station.csv").station.tolist()
    return r("production"), r("defect"), r("rework_in"), r("rework_out"), dim, st_order


prod, dlog, rin, rout, dim, ORDER = load()
names = dict(zip(dim.defect_code, dim.defect_name))
pct = lambda v, d=1: "-" if pd.isna(v) else f"{v * 100:.{d}f}%".replace(".", ",")

st.title("Dashboard Yield, Rework & Defect")
st.caption("Lini perakitan smartphone, data simulasi buatan sendiri: angka membuktikan metode, bukan kondisi pabrik sebenarnya.")
with st.sidebar:
    d0, d1 = st.date_input("Rentang tanggal", (prod.date.min(), prod.date.max()), prod.date.min(), prod.date.max())
    f_st = st.selectbox("Stasiun", ["Semua"] + ORDER)
    f_md = st.selectbox("Model", ["Semua"] + sorted(prod.model.unique()))
    f_sh = st.selectbox("Shift", ["Semua"] + sorted(prod["shift"].unique()))
    st.caption("rework_log tidak punya kolom shift: saat filter Shift aktif, Final yield dan Scrap rate tidak dihitung dan Rework memakai semua shift.")


def sel(df, shift=True, upto=False, station="station"):
    m = (df.date <= pd.Timestamp(d1)) if upto else df.date.between(pd.Timestamp(d0), pd.Timestamp(d1))
    if f_st != "Semua":
        m &= df[station] == f_st
    if f_md != "Semua":
        m &= df.model == f_md
    if shift and f_sh != "Semua":
        m &= df["shift"] == f_sh
    return df[m]


P, D = sel(prod), sel(dlog)
RI, RO = sel(rin, False), sel(rout, False)
stations = ORDER if f_st == "Semua" else [f_st]
a = P.groupby("station")[["input_qty", "ok_first_pass", "ng_qty"]].sum().reindex(ORDER)
rw = RI.groupby("station")[["ok", "scrap", "open", "lead_sum"]].sum().reindex(ORDER).fillna(0)
a = a.join(rw)
a["fpy"] = a.ok_first_pass / a.input_qty
a["final"] = (a.ok_first_pass + a.ok) / a.input_qty
if f_sh != "Semua":                      # rework_log tidak punya kolom shift: yield akhir dan scrap rate tidak bisa dihitung per shift
    a["final"] = np.nan
act = [s for s in stations if a.input_qty.get(s, 0) > 0]
if not act:
    st.warning("Tidak ada data pada filter ini.")
    st.stop()
den = a.input_qty[act[0]]
rty, fin = a.fpy[act].prod(), a.final[act].prod(min_count=1)
rework_rate = a.ng_qty[act].sum() / den
scrap_rate = a.scrap[act].sum() / den if f_sh == "Semua" else np.nan
rec = rw.ok[act].sum() / (rw.ok[act].sum() + rw.scrap[act].sum())
par = D.groupby("defect_code").qty.sum().sort_values(ascending=False)
par_df = par.rename("qty").reset_index().assign(share=lambda d: d.qty / d.qty.sum())
par_df["cum"] = par_df.share.cumsum()
par_df["vital"] = (par_df.cum - par_df.share) < 0.8


def tiles(cols):
    for c, (v, t) in zip(st.columns(len(cols)), cols):
        c.metric(t, v)


def layout(fig, h=330, **kw):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.1), **kw)
    return fig


tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan", "Yield per Stasiun", "Pareto Defect", "Rework"])

with tab1:
    worst = a.fpy[act].idxmin()
    st.info(f"Stasiun yang paling banyak meloloskan NG: **{worst}** (FPY {pct(a.fpy[worst])}). Defect terbanyak: "
            f"**{names[par.index[0]]}** ({par.index[0]}), {pct(par_df.share[0])} dari semua NG. "
            f"Rata-rata FPY stasiun {pct(a.fpy[act].mean())}, tetapi RTY hanya **{pct(rty)}**.")
    tiles([(pct(rty), "RTY"), (pct(fin), "Final yield"), (pct(rework_rate), "Rework rate"),
           (pct(scrap_rate, 2), "Scrap rate"), (pct(rec), "Recovery rate")])
    x = P.groupby(["date", "station"])[["input_qty", "ok_first_pass"]].sum()
    x = x[x.index.get_level_values("station").isin(act)]
    x["fpy"] = x.ok_first_pass / x.input_qty
    day = x.groupby("date").agg(rty=("fpy", "prod"), n=("input_qty", "first")).reset_index()
    day["ma7"] = day.rty.rolling(7, min_periods=1).mean()
    fig = go.Figure([go.Scatter(x=day.date, y=day.rty, name="RTY harian", line=dict(color="#8a8984", width=1),
                                customdata=day.n, hovertemplate="%{x|%Y-%m-%d}<br>RTY %{y:.1%}<br>input %{customdata:,}<extra></extra>"),
                     go.Scatter(x=day.date, y=day.ma7, name="Rata-rata 7 hari", line=dict(color=BLUE, width=3),
                                hovertemplate="%{x|%Y-%m-%d}<br>MA7 %{y:.1%}<extra></extra>")])
    st.plotly_chart(layout(fig, yaxis_tickformat=".0%"), width="stretch")

with tab2:
    tiles([(pct(rty), "RTY"), (pct(fin), "Final yield"), (pct(rework_rate), "Rework rate")])
    ng = (a.ng_qty / a.input_qty).fillna(0)
    colors = [ORANGE if s == ng[act].idxmax() else BLUE for s in ORDER]
    fig = go.Figure(go.Bar(x=ORDER, y=ng, marker_color=colors, hovertemplate="%{x}<br>NG rate %{y:.2%}<extra></extra>"))
    st.subheader("NG rate percobaan pertama per stasiun")
    st.plotly_chart(layout(fig, yaxis_tickformat=".1%", yaxis_rangemode="tozero"), width="stretch")
    hm = prod[prod.date.between(pd.Timestamp(d0), pd.Timestamp(d1))]
    if f_sh != "Semua":
        hm = hm[hm["shift"] == f_sh]
    h = hm.groupby(["model", "station"])[["input_qty", "ng_qty"]].sum()
    h = (h.ng_qty / h.input_qty).unstack().reindex(columns=ORDER)
    c1, c2 = st.columns(2)
    c1.subheader("NG rate: model × stasiun")
    c1.plotly_chart(layout(go.Figure(go.Heatmap(z=h.values, x=ORDER, y=h.index, colorscale="Blues", text=np.round(h.values * 100, 1),
                                               texttemplate="%{text}%", hovertemplate="%{y} | %{x}<br>%{z:.2%}<extra></extra>"))), width="stretch")
    s2 = prod[prod.date.between(pd.Timestamp(d0), pd.Timestamp(d1))]
    if f_md != "Semua":
        s2 = s2[s2.model == f_md]
    s2 = s2.groupby(["station", "shift"])[["input_qty", "ng_qty"]].sum()
    s2 = (s2.ng_qty / s2.input_qty).unstack().reindex(ORDER)
    fig = go.Figure([go.Bar(x=ORDER, y=s2[c], name=c, marker_color=col, hovertemplate="%{x}<br>%{y:.2%}<extra>" + c + "</extra>")
                     for c, col in zip(s2.columns, [BLUE, ORANGE])])
    c2.subheader("NG rate per shift")
    c2.plotly_chart(layout(fig, yaxis_tickformat=".1%", barmode="group"), width="stretch")
    with st.expander("Tabel"):
        t = a[["input_qty", "ng_qty", "fpy", "final"]].copy()
        t["fpy"], t["final"] = t.fpy.map(lambda v: pct(v, 2)), t.final.map(lambda v: pct(v, 2))
        st.dataframe(t)

with tab3:
    st.info(f"{int(par_df.vital.sum())} dari {len(par_df)} jenis defect menyumbang sekitar 80% dari {par_df.qty.sum():,} NG.")
    fig = go.Figure([go.Bar(x=par_df.defect_code, y=par_df.share, marker_color=[BLUE if v else SOFT for v in par_df.vital], name="Porsi NG",
                            customdata=np.c_[par_df.defect_code.map(names), par_df.qty, par_df.cum],
                            hovertemplate="%{x} %{customdata[0]}<br>%{customdata[1]:,} NG (%{y:.1%})<br>kumulatif %{customdata[2]:.1%}<extra></extra>"),
                     go.Scatter(x=par_df.defect_code, y=par_df.cum, name="Kumulatif", yaxis="y2", line=dict(color="#52514e", width=2))])
    st.plotly_chart(layout(fig, h=380, yaxis_tickformat=".0%", yaxis2=dict(overlaying="y", side="right", range=[0, 1], tickformat=".0%")), width="stretch")
    ist = prod[prod.date.between(pd.Timestamp(d0), pd.Timestamp(d1))]
    if f_md != "Semua":
        ist = ist[ist.model == f_md]
    ist = ist.groupby(["station", "shift"]).input_qty.sum()
    dd = dlog[dlog.date.between(pd.Timestamp(d0), pd.Timestamp(d1))]
    if f_md != "Semua":
        dd = dd[dd.model == f_md]
    dd = dd.groupby(["defect_code", "station", "shift"]).qty.sum().reset_index()
    dd["rate"] = [q / ist[(s, sh)] for q, s, sh in zip(dd.qty, dd.station, dd["shift"])]
    x = dd.pivot_table(index=["defect_code", "station"], columns="shift", values="rate").reset_index()
    x["Rasio S2/S1"] = x["Shift 2"] / x["Shift 1"]
    x.insert(1, "name", x.defect_code.map(names))
    st.subheader("Defect × shift (defect rate terhadap input stasiun asal)")
    st.dataframe(x.sort_values("Rasio S2/S1", ascending=False).style.format({"Shift 1": "{:.2%}", "Shift 2": "{:.2%}", "Rasio S2/S1": "{:.2f}"}), hide_index=True)

with tab4:
    tiles([(f"{int(a.ok[act].sum() + a.scrap[act].sum() + a.open[act].sum()):,}", "Masuk rework"), (pct(rec), "Recovery rate"),
           (f"{int(a.scrap[act].sum()):,}", "Scrap"), (f"{int(a.open[act].sum()):,}", "Masih menunggu")])
    rd = RI.groupby("defect_code")[["ok", "scrap"]].sum()
    rd = rd[(rd.ok + rd.scrap) > 0]
    rd["rec"] = rd.ok / (rd.ok + rd.scrap)
    rd = rd.sort_values("rec", ascending=False)
    fig = go.Figure(go.Bar(y=[f"{c} {names[c]}" for c in rd.index], x=rd.rec, orientation="h",
                           marker_color=[ORANGE if c == rd.rec.idxmin() else BLUE for c in rd.index],
                           hovertemplate="%{y}<br>recovery %{x:.1%}<extra></extra>"))
    st.subheader("Recovery rate per jenis defect")
    st.plotly_chart(layout(fig, h=480, xaxis=dict(range=[0, 1], tickformat=".0%")), width="stretch")
    inn = sel(rin, False, upto=True)
    inn = (inn.ok + inn.scrap + inn.open).groupby(inn.date).sum()
    out = sel(rout, False, upto=True).groupby("date").n.sum()
    days = sorted(prod.date.unique())
    bl = (inn.reindex(days, fill_value=0) - out.reindex(days, fill_value=0)).cumsum()
    bl = bl[bl.index >= pd.Timestamp(d0)]
    bl = bl[bl.index <= pd.Timestamp(d1)]
    st.subheader("Antrean rework harian")
    st.plotly_chart(layout(go.Figure(go.Scatter(x=bl.index, y=bl.values, line=dict(color=BLUE, width=3), hovertemplate="%{x|%Y-%m-%d}<br>menunggu %{y:,}<extra></extra>")),
                           yaxis_rangemode="tozero"), width="stretch")
