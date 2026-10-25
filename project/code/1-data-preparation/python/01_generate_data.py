"""Langkah 3: membuat data simulasi lini perakitan smartphone (seed tetap).

Hasil: data/raw/{production_daily,defect_log,rework_log}.csv, data/reference/dim_defect.csv,
data/ground_truth.json. Fakta yang ditanam dan data kotor dicatat di ground_truth.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import (DIM_DEFECT_CSV, GROUND_TRUTH, MODELS, N_DAYS, RAW_DIR, REF_DIR, SEED,
                    SHIFTS, START_DATE, STATIONS)

rng = np.random.default_rng(SEED)

# kode defect: (kode, nama, stasiun, kategori, bobot di stasiun, peluang berhasil rework, menit rework)
DEFECTS = [
    ("SPP-01", "Pasta solder kurang", 0, "Solder", 1.00, 0.97, 10),
    ("CPL-01", "Missing component", 1, "Komponen", 0.60, 0.95, 12),
    ("CPL-02", "Komponen terbalik", 1, "Komponen", 0.40, 0.96, 12),
    ("RFL-01", "Solder bridge", 2, "Solder", 0.68, 0.90, 18),
    ("RFL-02", "Cold solder", 2, "Solder", 0.32, 0.88, 15),
    ("AOI-01", "Komponen bergeser", 3, "Komponen", 1.00, 0.97, 8),
    ("ICT-01", "Short circuit", 4, "Elektrikal", 0.55, 0.85, 25),
    ("ICT-02", "Open circuit", 4, "Elektrikal", 0.45, 0.87, 25),
    ("SCR-01", "Layar retak", 5, "Layar", 0.50, 0.90, 20),
    ("SCR-02", "Dead pixel", 5, "Layar", 0.50, 0.30, 20),
    ("HSG-01", "Gores casing", 6, "Casing", 0.60, 0.93, 15),
    ("HSG-02", "Celah casing", 6, "Casing", 0.40, 0.90, 15),
    ("FIN-01", "Cacat kosmetik", 7, "Kosmetik", 1.00, 0.96, 8),
    ("FCT-01", "Kamera gagal tes", 8, "Fungsi", 0.40, 0.80, 30),
    ("FCT-02", "Sensor gagal tes", 8, "Fungsi", 0.35, 0.82, 30),
    ("FCT-03", "Baterai gagal tes", 8, "Fungsi", 0.25, 0.85, 30),
    ("PKG-01", "Label salah", 9, "Label", 1.00, 0.99, 5),
]
BASE_NG = [0.012, 0.011, 0.040, 0.008, 0.013, 0.010, 0.015, 0.012, 0.020, 0.003]
MODEL_FACTOR = {"Basic": 0.85, "Plus": 1.00, "Pro": 1.25}
START_QTY = {"Basic": 460, "Plus": 420, "Pro": 360}
SHIFT2_STATION, SHIFT2_FACTOR = 1, 1.9           # fakta 2: Shift 2 di Component Placement
SPIKE_STATION, SPIKE_CODE, SPIKE_DAYS, SPIKE_EXTRA = 5, "SCR-01", range(25, 30), 0.025   # fakta 3
REWORK_CAPACITY = 410                             # unit per hari, FIFO

dates = pd.bdate_range(START_DATE, periods=N_DAYS)
codes_by_station = {s: [d for d in DEFECTS if d[2] == s] for s in range(len(STATIONS))}
recovery = {d[0]: d[5] for d in DEFECTS}
operator = {(s, sh): f"OP{2 * s + j + 1:02d}" for s in range(len(STATIONS)) for j, sh in enumerate(SHIFTS)}

prod, dlog, rlog = [], [], []
queue = []                                       # item rework menunggu: [id, hari masuk, stasiun, model, shift, kode]
returns = {}                                     # unit hasil rework OK yang masuk stasiun berikutnya besok
rid = 0
for t, day in enumerate(dates):
    noise = np.exp(rng.normal(0, 0.15, len(STATIONS)))            # variasi harian per stasiun
    next_returns = {}
    for m in MODELS:
        for sh in SHIFTS:
            qty = int(round(START_QTY[m] * rng.normal(1, 0.05)))
            for s, st in enumerate(STATIONS):
                inp = qty + returns.get((s, m, sh), 0)
                p = BASE_NG[s] * MODEL_FACTOR[m] * noise[s]
                if s == SHIFT2_STATION and sh == "Shift 2":
                    p *= SHIFT2_FACTOR
                cds = codes_by_station[s]
                w = np.array([c[4] * p for c in cds])
                if s == SPIKE_STATION and t in SPIKE_DAYS:
                    w[[c[0] for c in cds].index(SPIKE_CODE)] += SPIKE_EXTRA
                ng = int(rng.binomial(inp, min(w.sum(), 0.5)))
                split = rng.multinomial(ng, w / w.sum())
                ok = inp - ng
                prod.append([day.date(), sh, st, m, operator[(s, sh)], inp, ok, ng])
                for c, q in zip(cds, split):
                    if q:
                        dlog.append([day.date(), sh, st, m, c[0], int(q)])
                        for _ in range(q):
                            rid += 1
                            queue.append([rid, t, s, m, sh, c[0]])
                qty = ok
    # stasiun rework memproses antrean FIFO sesuai kapasitas
    done, queue = queue[:REWORK_CAPACITY], queue[REWORK_CAPACITY:]
    for r_id, t_in, s, m, sh, code in done:
        res = "OK" if rng.random() < recovery[code] else "Scrap"
        rlog.append([f"RW{r_id:06d}", dates[t_in].date(), day.date(), STATIONS[s], m, code, res])
        if res == "OK" and s + 1 < len(STATIONS):
            k = (s + 1, m, sh)
            next_returns[k] = next_returns.get(k, 0) + 1
    returns = next_returns
for r_id, t_in, s, m, sh, code in queue:          # masih di antrean saat periode berakhir
    rlog.append([f"RW{r_id:06d}", dates[t_in].date(), None, STATIONS[s], m, code, None])

prod = pd.DataFrame(prod, columns=["date", "shift", "station", "model", "operator_id",
                                   "input_qty", "ok_first_pass", "ng_qty"])
dlog = pd.DataFrame(dlog, columns=["date", "shift", "station", "model", "defect_code", "qty"])
rlog = pd.DataFrame(rlog, columns=["rework_id", "date_in", "date_out", "station_origin", "model",
                                   "defect_code", "result"]).sort_values("rework_id")

# ---- fakta 5: data kotor (sekitar 2,5% baris produksi, 2% baris defect) ----
n = len(prod)
pick = rng.permutation(np.flatnonzero(prod.ng_qty > 0))
dup_i, neg_i, over_i, blank_i = pick[:35], pick[35:57], pick[57:85], pick[85:112]
prod.loc[neg_i, "ng_qty"] = -prod.loc[neg_i, "ng_qty"]
prod.loc[over_i, "ok_first_pass"] += rng.integers(5, 31, len(over_i))
prod.loc[blank_i, "shift"] = None
prod["_ord"] = np.arange(n, dtype=float)
dups = prod.loc[dup_i].copy()
dups["_ord"] += 0.5
prod = pd.concat([prod, dups]).sort_values("_ord").drop(columns="_ord").reset_index(drop=True)

typo_i = rng.choice(len(dlog), int(round(len(dlog) * 0.02)), replace=False)
styles = ["lower", "nohyphen", "space", "letterO"]
typo_style = {}
for k, i in enumerate(sorted(typo_i)):
    c, sty = dlog.at[i, "defect_code"], styles[k % 4]
    dlog.at[i, "defect_code"] = {"lower": c.lower(), "nohyphen": c.replace("-", ""),
                                 "space": c + " ", "letterO": c.replace("-0", "-O")}[sty]
    typo_style[sty] = typo_style.get(sty, 0) + 1

RAW_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)
prod.to_csv(RAW_DIR / "production_daily.csv", index=False)
dlog.to_csv(RAW_DIR / "defect_log.csv", index=False)
rlog.to_csv(RAW_DIR / "rework_log.csv", index=False)
pd.DataFrame([(d[0], d[1], STATIONS[d[2]], d[3], d[6]) for d in DEFECTS],
             columns=["defect_code", "defect_name", "station", "category", "rework_min"]
             ).to_csv(DIM_DEFECT_CSV, index=False)
pd.DataFrame({"station": STATIONS, "seq": range(1, len(STATIONS) + 1)}).to_csv(REF_DIR / "dim_station.csv", index=False)

gt = {
    "seed": SEED, "start_date": START_DATE, "n_days": N_DAYS,
    "facts": [
        {"id": 1, "fact": "Stasiun paling sering NG", "station": STATIONS[2], "dominant_defect": "RFL-01",
         "param": f"base NG {BASE_NG[2]:.3f}, solder bridge 68% dari NG stasiun"},
        {"id": 2, "fact": "Shift 2 lebih tinggi NG di satu stasiun", "station": STATIONS[SHIFT2_STATION],
         "shift": "Shift 2", "param": f"faktor {SHIFT2_FACTOR}"},
        {"id": 3, "fact": "Lonjakan defect selama satu minggu", "station": STATIONS[SPIKE_STATION],
         "defect_code": SPIKE_CODE, "start": str(dates[SPIKE_DAYS[0]].date()),
         "end": str(dates[SPIKE_DAYS[-1]].date()), "param": f"tambahan peluang {SPIKE_EXTRA}"},
        {"id": 4, "fact": "Defect sulit di-rework", "defect_code": "SCR-02",
         "param": f"peluang berhasil {recovery['SCR-02']}"},
        {"id": 5, "fact": "Data kotor", "production_rows_clean": int(n),
         "injected": {"duplicate": len(dup_i), "negative_qty": len(neg_i), "ok_ng_over_input": len(over_i),
                      "blank_shift": len(blank_i), "defect_code_typo": len(typo_i)},
         "typo_styles": typo_style},
    ],
    "rework_capacity_per_day": REWORK_CAPACITY,
}
GROUND_TRUTH.write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"production_daily {len(prod)} baris, defect_log {len(dlog)}, rework_log {len(rlog)}")
