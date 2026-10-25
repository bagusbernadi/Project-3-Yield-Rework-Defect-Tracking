"""Langkah 4: memeriksa dan membersihkan data (Q13).

Setiap baris bermasalah dicatat di results/1-data-preparation/cleaning_log.csv beserta keputusannya
(diperbaiki / dibuang). Data bersih ditulis ke data/clean/ dan ringkasannya ke docs/cleaning_log.md.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import CLEAN_DIR, DIM_DEFECT_CSV, DOCS_DIR, GROUND_TRUTH, RAW_DIR, RES_PREP

KEY = ["date", "shift", "station", "model"]
prod = pd.read_csv(RAW_DIR / "production_daily.csv")
dlog = pd.read_csv(RAW_DIR / "defect_log.csv")
rlog = pd.read_csv(RAW_DIR / "rework_log.csv")
dim = pd.read_csv(DIM_DEFECT_CSV)
valid = set(dim.defect_code)
log = []


def note(table, rows, issue, action, before, after):
    for r, b, a in zip(rows, before, after):
        log.append([table, int(r) + 2, issue, action, b, a])   # +2 = nomor baris di file CSV (header = 1)


# 1. baris ganda: simpan kemunculan pertama
d = prod.duplicated(keep="first")
note("production_daily", prod.index[d], "duplicate", "dibuang", ["baris ganda"] * d.sum(), [""] * d.sum())
prod = prod[~d]

# 2. jumlah negatif: diperbaiki jika |ng| membuat OK + NG = input, selain itu dibuang
neg = prod.ng_qty < 0
fix = neg & (prod.ok_first_pass - prod.ng_qty == prod.input_qty)
note("production_daily", prod.index[fix], "negative_qty", "diperbaiki",
     prod.ng_qty[fix].map(lambda v: f"ng_qty={v}"), prod.ng_qty[fix].map(lambda v: f"ng_qty={-v}"))
prod.loc[fix, "ng_qty"] = -prod.loc[fix, "ng_qty"]
drop = (prod[["input_qty", "ok_first_pass", "ng_qty"]] < 0).any(axis=1)
note("production_daily", prod.index[drop], "negative_qty", "dibuang", ["tidak bisa dipulihkan"] * drop.sum(), [""] * drop.sum())
prod = prod[~drop]

# 3. OK + NG lebih dari input: NG dicek ke defect_log; jika cocok, OK = input - NG
dsum = dlog.assign(defect_code=dlog.defect_code).groupby(KEY, dropna=False).qty.sum()
over = prod.ok_first_pass + prod.ng_qty > prod.input_qty
for i in prod.index[over]:
    r = prod.loc[i]
    k = (r.date, r["shift"], r.station, r.model)
    if dsum.get(k, 0) == r.ng_qty:
        note("production_daily", [i], "ok_ng_over_input", "diperbaiki", [f"ok_first_pass={r.ok_first_pass}"],
             [f"ok_first_pass={r.input_qty - r.ng_qty}"])
        prod.at[i, "ok_first_pass"] = r.input_qty - r.ng_qty
    else:
        note("production_daily", [i], "ok_ng_over_input", "dibuang", ["NG tidak cocok dengan defect_log"], [""])
        prod = prod.drop(i)
under = prod.ok_first_pass + prod.ng_qty < prod.input_qty
note("production_daily", prod.index[under], "ok_ng_under_input", "dibuang", ["unit hilang"] * under.sum(), [""] * under.sum())
prod = prod[~under]

# 4. shift kosong: diisi dari operator_id (setiap operator selalu di stasiun dan shift yang sama)
op_shift = prod.dropna(subset=["shift"]).groupby("operator_id")["shift"].agg(lambda s: s.unique())
assert op_shift.map(len).eq(1).all(), "operator bekerja di lebih dari satu shift"
op_shift = op_shift.map(lambda a: a[0])
blank = prod["shift"].isna()
note("production_daily", prod.index[blank], "blank_shift", "diperbaiki", ["shift kosong"] * blank.sum(),
     prod.operator_id[blank].map(lambda o: f"shift={op_shift[o]} (dari {o})"))
prod.loc[blank, "shift"] = prod.loc[blank, "operator_id"].map(op_shift)


# 5. kode defect salah ketik: huruf besar, hapus spasi, O -> 0 pada bagian angka, sisipkan tanda hubung
def normalize(c):
    c = c.strip().upper()
    m = re.fullmatch(r"([A-Z]{3})-?([0-9O]{2})", c)
    return f"{m.group(1)}-{m.group(2).replace('O', '0')}" if m else c


for name, df, col in (("defect_log", dlog, "defect_code"), ("rework_log", rlog, "defect_code")):
    bad = ~df[col].isin(valid)
    fixed = df.loc[bad, col].map(normalize)
    ok = fixed.isin(valid)
    note(name, fixed.index[ok], "defect_code_typo", "diperbaiki", df.loc[fixed.index[ok], col].map(repr), fixed[ok])
    note(name, fixed.index[~ok], "defect_code_unknown", "dibuang", df.loc[fixed.index[~ok], col].map(repr), [""] * (~ok).sum())
    df.loc[fixed.index[ok], col] = fixed[ok]
    df.drop(index=fixed.index[~ok], inplace=True)
dd = dlog.duplicated(keep="first")
note("defect_log", dlog.index[dd], "duplicate", "dibuang", ["baris ganda"] * dd.sum(), [""] * dd.sum())
dlog = dlog[~dd]

# 6. pemeriksaan konsistensi (harus 0 setelah cleaning)
chk = prod.set_index(KEY).ng_qty.sub(dlog.groupby(KEY).qty.sum(), fill_value=0)
rw = rlog.groupby(["date_in", "station_origin", "model", "defect_code"]).size()
dl = dlog.groupby(["date", "station", "model", "defect_code"]).qty.sum()
dl.index.names = rw.index.names
rw_out = rlog.dropna(subset=["date_out"])
checks = {
    "ng_qty = jumlah defect_log per kunci": int((chk != 0).sum()),
    "baris rework_log = qty defect_log per tanggal/stasiun/model/kode": int((rw.sub(dl, fill_value=0) != 0).sum()),
    "rework date_out >= date_in": int((rw_out.date_out < rw_out.date_in).sum()),
    "result kosong hanya jika date_out kosong": int((rlog.result.isna() != rlog.date_out.isna()).sum()),
    "kunci production_daily unik": int(prod.duplicated(KEY).sum()),
    "OK + NG = input": int((prod.ok_first_pass + prod.ng_qty != prod.input_qty).sum()),
}

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
RES_PREP.mkdir(parents=True, exist_ok=True)
prod.to_csv(CLEAN_DIR / "production_daily.csv", index=False)
dlog.to_csv(CLEAN_DIR / "defect_log.csv", index=False)
rlog.to_csv(CLEAN_DIR / "rework_log.csv", index=False)
log = pd.DataFrame(log, columns=["table", "csv_row", "issue", "action", "before", "after"])
log.to_csv(RES_PREP / "cleaning_log.csv", index=False)

# ringkasan per masalah, dibandingkan dengan jumlah yang ditanam generator
inj = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["facts"][4]["injected"]
raw_rows = {"production_daily": len(pd.read_csv(RAW_DIR / "production_daily.csv")),
            "defect_log": len(pd.read_csv(RAW_DIR / "defect_log.csv")), "rework_log": len(pd.read_csv(RAW_DIR / "rework_log.csv"))}
summ = log.groupby(["table", "issue", "action"]).size().rename("rows").reset_index()
summ["injected"] = summ.apply(lambda r: inj.get(r.issue) if r.table != "rework_log" else None, axis=1)
summ["pct_of_table"] = (summ.rows / summ.table.map(raw_rows) * 100).round(2)
summ.to_csv(RES_PREP / "data_quality_summary.csv", index=False)
rows = pd.DataFrame([{"table": t, "raw_rows": raw_rows[t], "clean_rows": len(x),
                      "flagged_rows": int((log.table == t).sum())}
                     for t, x in (("production_daily", prod), ("defect_log", dlog), ("rework_log", rlog))])
rows["flagged_pct"] = (rows.flagged_rows / rows.raw_rows * 100).round(2)
rows.to_csv(RES_PREP / "table_rows.csv", index=False)
pd.DataFrame(list(checks.items()), columns=["check", "violations"]).to_csv(RES_PREP / "consistency_checks.csv", index=False)

md = ["# Cleaning log", "",
      "Dibuat otomatis oleh `code/1-data-preparation/python/02_clean_data.py`. Rincian per baris: "
      "`results/1-data-preparation/cleaning_log.csv`.", "",
      "| Tabel | Masalah | Keputusan | Baris | Ditanam generator |", "|---|---|---|---:|---:|"]
md += [f"| {r.table} | {r.issue} | {r.action} | {r.rows} | {'' if pd.isna(r.injected) else int(r.injected)} |"
       for r in summ.itertuples()]
md += ["", "Aturan keputusan:", "",
       "- Baris ganda persis: dibuang, kemunculan pertama disimpan.",
       "- Jumlah negatif: diperbaiki (tanda dibalik) jika OK + |NG| = input; selain itu dibuang.",
       "- OK + NG > input: NG dicocokkan ke defect_log; jika sama, OK = input - NG; selain itu dibuang.",
       "- Shift kosong: diisi dari operator_id karena setiap operator selalu bekerja di stasiun dan shift yang sama.",
       "- Kode defect salah ketik: dinormalisasi (huruf besar, tanpa spasi, O menjadi 0, tanda hubung); kode yang tetap tidak dikenal dibuang.",
       "", "Pemeriksaan konsistensi setelah cleaning (jumlah pelanggaran):", "",
       "| Pemeriksaan | Pelanggaran |", "|---|---:|"]
md += [f"| {k} | {v} |" for k, v in checks.items()]
(DOCS_DIR / "cleaning_log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(summ.to_string(index=False))
print(checks)
assert not any(checks.values()), "data bersih belum konsisten"
