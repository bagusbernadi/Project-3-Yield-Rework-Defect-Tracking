"""Hitungan KPI versi pandas, ditulis terpisah dari SQL agar bisa dipakai sebagai cek silang dan uji sensitivitas."""
import numpy as np
import pandas as pd


def kpis(prod, dlog, rlog, stations):
    """Ringkasan KPI dari tiga tabel (data bersih atau varian). Mengembalikan dict metrik -> nilai."""
    st = prod.groupby("station")[["input_qty", "ok_first_pass", "ng_qty"]].sum().reindex(stations)
    st["fpy"] = st.ok_first_pass / st.input_qty
    rw = rlog.groupby(["station_origin", "result"]).size().unstack(fill_value=0).reindex(stations, fill_value=0)
    st["final_yield"] = (st.ok_first_pass + rw["OK"]) / st.input_qty
    started = st.input_qty.iloc[0]
    out = {f"fpy | {s}": v for s, v in st.fpy.items()}
    out.update({
        "rty": float(np.prod(st.fpy)),
        "final_yield": float(np.prod(st.final_yield)),
        "rework_rate": st.ng_qty.sum() / started,
        "scrap_rate": rw["Scrap"].sum() / started,
        "recovery_rate": rw["OK"].sum() / (rw["OK"].sum() + rw["Scrap"].sum()),
        "worst_station": st.fpy.idxmin(),
    })
    par = dlog.groupby("defect_code").qty.sum().sort_values(ascending=False)
    out["top_defect"] = par.index[0]
    out["top_defect_share"] = par.iloc[0] / par.sum()
    out["defects_in_80pct"] = int((par.cumsum().shift(fill_value=0) / par.sum() < 0.8).sum())
    sh = prod.groupby(["station", "shift"])[["ng_qty", "input_qty"]].sum()
    rate = (sh.ng_qty / sh.input_qty).unstack()
    gap = rate.get("Shift 2") - rate.get("Shift 1")
    out["max_shift_gap_station"] = gap.idxmax()
    out["max_shift_gap"] = gap.max()
    rec = rlog.dropna(subset=["result"]).groupby("defect_code").result.apply(lambda s: (s == "OK").mean())
    out["lowest_recovery_defect"] = rec.idxmin()
    out["lowest_recovery_rate"] = rec.min()
    return out


def backlog(rlog, dates):
    a = rlog.groupby("date_in").size().reindex(dates, fill_value=0)
    b = rlog.dropna(subset=["date_out"]).groupby("date_out").size().reindex(dates, fill_value=0)
    return (a - b).cumsum()


def spike_days(prod, threshold=3.5):
    x = prod.groupby(["date", "station"])[["ng_qty", "input_qty"]].sum()
    x["r"] = x.ng_qty / x.input_qty
    g = x.groupby("station").r
    med = g.transform("median")
    mad = (x.r - med).abs().groupby("station").transform("median") * 1.4826
    x["z"] = (x.r - med) / mad
    return x[x.z > threshold].reset_index()[["date", "station", "z"]]
