"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import DB_PATH, RES_ANALYSIS, RES_PREP, STATIONS, result  # noqa: E402
from report_lib import (BLUE, D, cs, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, esc, gbars, hbars,  # noqa: E402
                        legend, lines, pareto_svg, pill, qa, table)

R = lambda n: pd.read_csv(result(n))
SHORT = ["Solder Paste", "Placement", "Reflow", "AOI", "ICT", "Screen", "Housing", "Final Insp.", "Func. Test", "Packaging"]
PRIO = {1: "Utama", 2: "Utama", 3: "Utama", 4: "Utama", 5: "Pendukung", 6: "Utama", 7: "Pendukung", 8: "Pendukung",
        9: "Utama", 10: "Pendukung", 11: "Utama", 12: "Tambahan", 13: "Utama", 14: "Utama"}
QT = {1: "Stasiun mana yang paling banyak meloloskan produk gagal pada percobaan pertama, dan seberapa besar pengaruhnya terhadap yield seluruh lini?",
      2: "Berapa yield akhir setelah rework, dan seberapa jauh bedanya dengan yield percobaan pertama?",
      3: "Apakah yield berbeda untuk model Basic, Plus, dan Pro?",
      4: "Jenis defect apa saja yang menyumbang sekitar 80% dari semua produk NG, di seluruh lini dan di tiap stasiun?",
      5: "Apakah defect tertentu lebih sering muncul di shift tertentu?",
      6: "Dari semua produk NG, berapa persen yang berhasil diselamatkan lewat rework dan berapa persen yang menjadi scrap?",
      7: "Defect mana yang paling sulit diperbaiki (persentase berhasil diselamatkan paling rendah)?",
      8: "Berapa lama produk menunggu di stasiun rework, dan apakah antrean menumpuk?",
      9: "Bagaimana tren yield dan rework per hari dan per minggu, dan adakah hari dengan lonjakan defect?",
      10: "Saat terjadi lonjakan, apakah lonjakan itu terpusat di satu stasiun, model, atau shift?",
      11: "Jika NG di stasiun atau defect teratas turun sekian persen, berapa produk yang terselamatkan per bulan?",
      12: "Berapa jam kerja rework yang bisa dihemat dari perbaikan tersebut?",
      13: "Berapa persen data yang tidak valid, dan apakah hasil berubah jika data itu dibuang atau dikoreksi?",
      14: "Apakah angka KPI dari database sama persis dengan hitungan manual di Excel?"}
WARN = set()      # pertanyaan yang dijawab dengan catatan (dipakai chip, ringkasan, dan tabel evaluasi)


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)



mk = lambda *a: "".join(a)
fl = lambda s: re.sub(r"\s+", " ", s)

# ---------------------------------------------------------------- data
st, line, mod, ms = R("station.csv"), R("line_kpi.csv").iloc[0], R("model.csv"), R("model_station.csv")
par, pst, shs, dsh = R("pareto_line.csv"), R("pareto_station.csv"), R("shift_station.csv"), R("defect_shift.csv")
rd, lead, bl, dly, wk = R("rework_defect.csv"), R("rework_lead.csv"), R("backlog_daily.csv"), R("daily.csv"), R("weekly.csv")
spk, drl, imp = R("spike_days.csv"), R("spike_drill.csv"), R("impact.csv")
cx, ce, gt, sens = R("crosscheck.csv"), R("crosscheck_excel.csv"), R("ground_truth_check.csv"), R("sensitivity.csv")
rows, dq, cons, ctest = R("table_rows.csv"), R("data_quality_summary.csv"), R("consistency_checks.csv"), R("constraint_tests.csv")
clog = R("cleaning_log.csv")
dim = pd.read_csv(REPO / "project" / "data" / "reference" / "dim_defect.csv")
con = duckdb.connect(str(DB_PATH), read_only=True)
dbc = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
       ("production_daily", "defect_log", "rework_log", "dim_defect", "dim_station", "dim_date")}
d0, d1 = con.execute("SELECT min(date), max(date) FROM dim_date").fetchone()
sample = con.execute("""SELECT date, shift, station, model, input_qty, ok_first_pass, ng_qty FROM production_daily
                        WHERE date = '2026-04-08' AND shift = 'Shift 2' AND model = 'Plus' AND station IN
                        ('Component Placement', 'Reflow Soldering', 'Screen Assembly', 'Functional Test') ORDER BY date, station""").fetchall()
con.close()
dates = [str(x) for x in dly.date]
nbl = int((bl.backlog > 0).sum())

assert (st.fpy.idxmin() == 2) and st.station[2] == "Reflow Soldering"
assert list(mod.sort_values("rty").model) == ["Pro", "Plus", "Basic"]
assert spk.is_spike.sum() == 5 and set(spk.loc[spk.is_spike, "stations"]) == {"Screen Assembly"}
assert gt.match.all() and (cx.status == "PASS").all() and (ce.status == "PASS").all()
assert rd.defect_code[0] == "SCR-02" and par.vital_few.sum() == 12
assert drl[drl.dim.isin(["model", "shift"])].share_of_excess.max() < 0.6 and (drl[drl.dim.isin(["model", "shift"])].share_of_excess > 0).all()

# ---------------------------------------------------------------- 1. data
n_clean = rows.clean_rows[0]
dirty = int(rows.flagged_rows[0] + rows.flagged_rows[1])
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(n_clean), "baris production_daily", f"Dari {I(rows.raw_rows[0])} baris mentah; sisanya duplikat yang dibuang. Satu baris = satu stasiun, model, shift, hari."),
    kp("amber", I(rows.clean_rows[1]), "baris defect_log", f"Lebih banyak dari perkiraan rancangan (±6.000). Jumlah qty sama dengan total NG."),
    kp("teal", I(rows.clean_rows[2]), "unit masuk rework", f"{I(line.rework_ok)} OK, {I(line.scrap)} scrap, {I(line.rework_open)} masih menunggu di akhir periode."),
    kp("plum", I(dbc["dim_date"]), "hari kerja", f"{d0} sampai {d1}, Senin sampai Jumat."),
    kp("rose", I(dirty), "baris kotor ditemukan", f"{I(rows.flagged_rows[0])} di production_daily ({D(rows.flagged_pct[0], 2)}%), {I(rows.flagged_rows[1])} di defect_log ({D(rows.flagged_pct[1], 2)}%). Semua ditangani."),
    kp("sky", I(line.units_started), "unit dimulai", f"Input Solder Paste Printing. {I(line.units_packed)} unit selesai di Packaging."),
    '</div><h3>1.1 Data simulasi (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Cuplikan production_daily (8 April 2026, Shift 2, model Plus)</h4>' + table(
    ["date", "shift", "station", "model", "input_qty", "ok_first_pass", "ng_qty"],
    [[str(r[0]), r[1], r[2], r[3], I(r[4]), I(r[5]), I(r[6])] for r in sample]) + \
    '<p>Contoh baris tabel bersih. Data dibuat oleh skrip dengan seed tetap, jadi cuplikan ini sama setiap dijalankan ulang.</p></div>'
rp1 += '<div class="card"><h4>Tabel 1.1. Baris mentah, bersih, dan bermasalah per tabel (Q13)</h4>' + table(
    ["Tabel", "Mentah", "Bersih", "Bermasalah", "% bermasalah"],
    [[f"<code>{r.table}</code>", I(r.raw_rows), I(r.clean_rows), I(r.flagged_rows), D(r.flagged_pct, 2) + "%"] for r in rows.itertuples()])
label = {"duplicate": "Baris ganda", "negative_qty": "Jumlah negatif", "ok_ng_over_input": "OK + NG lebih dari input",
         "blank_shift": "Shift kosong", "defect_code_typo": "Kode defect salah ketik"}
dec = {"duplicate": "dibuang (kemunculan pertama disimpan)", "negative_qty": "diperbaiki (tanda dibalik; OK + |NG| = input)",
       "ok_ng_over_input": "diperbaiki (OK = input - NG; NG cocok dengan defect_log)", "blank_shift": "diperbaiki (diisi dari operator_id)",
       "defect_code_typo": "diperbaiki (huruf besar, tanpa spasi, O jadi 0, tanda hubung)"}
rp1 += table(["Masalah", "Tabel", "Ditemukan", "Ditanam generator", "Keputusan"],
             [[label[r.issue], f"<code>{r.table}</code>", I(r.rows), I(r.injected), dec[r.issue]] for r in dq.itertuples()])
rp1 += Q(13, f"{D(rows.flagged_pct[0], 2)}% baris production_daily dan {D(rows.flagged_pct[1], 2)}% baris defect_log tidak valid; semuanya ditemukan "
             f"({I(dirty)} baris, sama dengan jumlah yang ditanam) dan diperbaiki, kecuali {I(rows.raw_rows[0] - rows.clean_rows[0])} baris ganda yang dibuang. "
             f"Hasil tidak berubah secara berarti: kesimpulan kategorikal sama pada tiga perlakuan, angka KPI bergeser paling banyak {D(abs(sens.diff_tanpa_cleaning[:4]).max() * 100, 2)} poin (rincian di Tabel 2.9a).")
rp1 += '<p class="note">Pembahasan lengkap Q13 (perbandingan tiga perlakuan) ada di <a href="#sec29">2.9</a>.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>yield.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["production_daily", I(dbc["production_daily"]), "Hasil harian per stasiun, model, shift. Kunci utama (date, shift, station, model)."],
     ["defect_log", I(dbc["defect_log"]), "Jumlah defect per kode. Kunci asing ke production_daily dan dim_defect."],
     ["rework_log", I(dbc["rework_log"]), "Satu baris per unit NG. date_out dan result kosong jika masih menunggu."],
     ["dim_defect", I(dbc["dim_defect"]), "Kode, nama, stasiun, kategori, asumsi menit rework per unit."],
     ["dim_station", I(dbc["dim_station"]), "Urutan 10 stasiun."],
     ["dim_date", I(dbc["dim_date"]), "Hari kerja, minggu, bulan (ditambahkan, tidak ada di rancangan)."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(
    ["Baris salah yang dicoba dimasukkan", "Hasil"], [[r.test, OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Keenam jenis data salah ditolak oleh database. Setelah cleaning, {I(len(cons))} pemeriksaan konsistensi antar tabel menghasilkan 0 pelanggaran.</p></div>'
FILES = {"station": ("KPI per stasiun", "Q1, Q2"), "line_kpi": ("KPI seluruh lini (1 baris)", "Q1, Q2, Q6"), "model_station": ("FPY model × stasiun", "Q3"),
         "model": ("RTY per model", "Q3"), "pareto_line": ("Pareto defect lini", "Q4"), "pareto_station": ("Pareto defect per stasiun", "Q4"),
         "shift_station": ("NG rate per shift per stasiun", "Q5"), "defect_shift": ("Defect rate per shift", "Q5"), "rework_defect": ("Recovery dan lead time per defect", "Q6, Q7"),
         "rework_lead": ("Distribusi lead time rework", "Q8"), "backlog_daily": ("Antrean rework harian", "Q8"), "daily": ("RTY dan NG harian, MA7", "Q9"),
         "weekly": ("RTY dan NG mingguan", "Q9"), "station_daily": ("NG rate stasiun × hari, robust z", "Q9, Q10"), "spike_days": ("Hari lonjakan", "Q9, Q10"),
         "spike_drill": ("Sumber kelebihan NG saat lonjakan", "Q10"), "impact": ("Skenario dampak", "Q11, Q12"), "crosscheck": ("SQL vs pandas", "Q14"),
         "crosscheck_excel": ("SQL vs Excel", "Q14"), "sensitivity": ("Tiga perlakuan data kotor", "Q13"), "ground_truth_check": ("Fakta ditanam vs temuan", "validasi"),
         "cleaning_log": ("Log cleaning per baris", "Q13"), "data_quality_summary": ("Ringkasan data kotor", "Q13"), "table_rows": ("Baris per tabel", "Q13"),
         "consistency_checks": ("Pemeriksaan konsistensi", "Q13"), "constraint_tests": ("Uji constraint database", "Q13")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"],
    [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list((REPO / "project/results/3-presentation").glob("dash_*.csv"))))} CSV data dashboard.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Enam KPI seluruh lini (definisi di <code>project/docs/kpi_definitions.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["RTY lini", "hasil kali FPY 10 stasiun", P(line.rty, 2), f"{I(line.units_started)} unit dimulai"],
     ["Final yield lini", "hasil kali final yield 10 stasiun (setelah rework)", P(line.final_yield, 2), f"{I(line.units_started)} unit dimulai"],
     ["Rata-rata FPY stasiun", "rata-rata FPY 10 stasiun", P(line.avg_station_fpy, 2), f"{I(len(st))} stasiun"],
     ["Rework rate", "unit NG ÷ input stasiun pertama", P(line.rework_rate, 2), f"{I(line.ng_events)} unit NG"],
     ["Scrap rate", "unit scrap ÷ input stasiun pertama", P(line.scrap_rate, 2), f"{I(line.scrap)} unit scrap"],
     ["Recovery rate", "rework OK ÷ (rework OK + scrap)", P(line.recovery_rate, 2), f"{I(line.rework_ok + line.scrap)} unit selesai rework"]]) + \
    f'<p>RTY {P(line.rty, 2)} jauh di bawah rata-rata FPY {P(line.avg_station_fpy, 2)} karena kegagalan sepuluh stasiun saling menumpuk. {I(line.rework_open)} unit yang masih menunggu di akhir periode tidak masuk recovery rate.</p></div>'

# ---------------------------------------------------------------- 2. business questions
s21 = mk('<h3 id="sec21">2.1 Yield per stasiun dan RTY lini <span class="qlist">Q1, Q2</span></h3><div class="card">',
         Q(1, f"{st.station[2]} paling banyak meloloskan NG (FPY {P(st.fpy[2], 2)}, {D(st.rty_loss_share[2] * 100)}% dari seluruh kehilangan RTY), disusul "
              f"{st.station.iloc[st.fpy_rank.sub(2).abs().idxmin()]} dan {st.station[st.fpy_rank == 3].iloc[0]}. Rata-rata FPY stasiun {P(line.avg_station_fpy, 2)}, tetapi RTY lini hanya "
              f"{P(line.rty, 2)} karena kegagalan kecil di sepuluh stasiun saling menumpuk."),
         Q(2, f"Final yield lini {P(line.final_yield, 2)} vs RTY {P(line.rty, 2)}: rework menyelamatkan {D((line.final_yield - line.rty) * 100)} poin. "
              f"Tanpa pemisahan FPY dan final yield, {D((line.final_yield - line.rty) * 100)} poin biaya rework tidak terlihat."),
         '<h4>Grafik 2.1a. NG rate percobaan pertama per stasiun (1 - FPY)</h4>',
         bars([(SHORT[i], r.ng_qty / r.input_qty, HI if i == 2 else BLUE,
                f"{r.station}: NG rate {P(r.ng_qty / r.input_qty, 2)}, FPY {P(r.fpy, 2)}, {I(r.ng_qty)} NG dari {I(r.input_qty)}") for i, r in st.iterrows()],
              lambda v: P(v, 1), "NG rate per stasiun"),
         '<h4>Tabel 2.1b. KPI per stasiun</h4>',
         table(["Stasiun", "Input", "NG", "FPY", "Final yield", "Porsi kehilangan RTY"],
               [[r.station, I(r.input_qty), I(r.ng_qty), P(r.fpy, 2), P(r.final_yield, 2), P(r.rty_loss_share)] for r in st.itertuples()]),
         '<p>Porsi kehilangan RTY = ln(FPY stasiun) ÷ jumlah ln(FPY) semua stasiun, sehingga jumlahnya 100%. Batang dimulai dari nol.</p></div>')
mrty = {r.model: r for r in mod.itertuples()}
s22 = mk('<h3 id="sec22">2.2 Perbedaan antar model <span class="qlist">Q3</span></h3><div class="card">',
         Q(3, f"Ya, makin tinggi model makin rendah yield-nya: RTY Basic {P(mrty['Basic'].rty, 2)}, Plus {P(mrty['Plus'].rty, 2)}, Pro {P(mrty['Pro'].rty, 2)}. "
              f"Rework rate Pro {P(mrty['Pro'].rework_rate)} vs Basic {P(mrty['Basic'].rework_rate)}. Pola ini berasal dari faktor model yang disetel di generator (Pro 1,25×, Plus 1,00×, Basic 0,85×), "
              f"jadi di sini pengujian bahwa metode bisa menemukannya, bukan temuan tentang pabrik."),
         '<h4>Grafik 2.2a. NG rate per stasiun menurut model</h4>',
         gbars([SHORT[i] for i in range(10)], [(m, c, [1 - ms[(ms.model == m) & (ms.seq == i + 1)].fpy.iloc[0] for i in range(10)])
                                                for m, c in (("Basic", SOFT), ("Plus", BLUE), ("Pro", HI))], lambda v: P(v, 1), "NG rate per model"),
         legend([(SOFT, "Basic"), (BLUE, "Plus"), (HI, "Pro")]),
         '<h4>Tabel 2.2b. Yield dan rework per model</h4>',
         table(["Model", "Unit dimulai", "NG", "RTY", "Rework rate"], [[r.model, I(r.units_started), I(r.ng_qty), P(r.rty, 2), P(r.rework_rate)] for r in mod.itertuples()]), '</div>')
pn = pst[pst.rank_in_station == 1]
s23 = mk('<h3 id="sec23">2.3 Pareto defect <span class="qlist">Q4</span></h3><div class="card">',
         Q(4, f"{I(par.vital_few.sum())} dari {I(len(par))} jenis defect menyumbang sekitar 80% dari {I(par.qty.sum())} NG; kelompok teratas {par.defect_name[0]} ({P(par.share[0])}), "
              f"{par.defect_name[1]} ({P(par.share[1])}), dan {par.defect_name[2]} ({P(par.share[2])}). Pareto-nya landai: tidak ada kelompok kecil yang mendominasi, dan "
              f"{par.defect_name[0]} sendiri baru {P(par.share[0])} dari semua NG."),
         '<h4>Grafik 2.3a. Pareto defect seluruh lini</h4>', legend([(BLUE, "Sampai 80% kumulatif"), (SOFT, "Sisanya"), ("#3C4043", "Kumulatif")]),
         pareto_svg(list(par.defect_code), list(par.share), list(par.cum_share), list(par.vital_few),
                    [f"{r.defect_code} {r.defect_name} ({r.station}): {I(r.qty)} NG, {P(r.share)}, kumulatif {P(r.cum_share)}" for r in par.itertuples()], "Pareto defect"),
         '<p>Garis putus-putus = 80%. Sumbu kiri porsi batang, sumbu kanan kumulatif.</p>',
         '<h4>Tabel 2.3b. Defect teratas di tiap stasiun</h4>',
         table(["Stasiun", "Defect teratas", "Porsi dari NG stasiun"], [[r.station, f"{r.defect_code} {r.defect_name}", P(r.share_in_station)] for r in pn.itertuples()]), '</div>')
gap = shs.loc[shs.gap.idxmax()]
oth = shs[shs.station != gap.station]
top_ds = dsh.head(2)
s24 = mk('<h3 id="sec24">2.4 Shift <span class="qlist">Q5</span></h3><div class="card">',
         Q(5, f"Ya, di satu stasiun: {gap.station} memiliki NG rate Shift 2 {P(gap.ng_rate_s2, 2)} vs Shift 1 {P(gap.ng_rate_s1, 2)} (rasio {D(gap.ratio, 2)}), terutama "
              f"{top_ds.defect_name.iloc[0]} dan {top_ds.defect_name.iloc[1]}. Stasiun lain tidak menunjukkan pola serupa: rasio Shift 2 ÷ Shift 1 antara {D(oth.ratio.min(), 2)} dan {D(oth.ratio.max(), 2)}. "
              f"Ini pola, bukan penyebab; penyebabnya (operator, setup, material) perlu dicek di lapangan.", warn=True),
         '<h4>Grafik 2.4a. NG rate per stasiun menurut shift</h4>',
         gbars(SHORT, [("Shift 1", BLUE, list(shs.ng_rate_s1)), ("Shift 2", HI, list(shs.ng_rate_s2))], lambda v: P(v, 1), "NG rate per shift"),
         legend([(BLUE, "Shift 1"), (HI, "Shift 2")]),
         '<h4>Tabel 2.4b. Lima defect dengan selisih shift terbesar</h4>',
         table(["Defect", "Stasiun", "Rate Shift 1", "Rate Shift 2", "Rasio"],
               [[f"{r.defect_code} {r.defect_name}", r.station, P(r.rate_s1, 2), P(r.rate_s2, 2), D(r.rate_s2 / r.rate_s1, 2)] for r in dsh.head(5).itertuples()]),
         '<p>Rate = jumlah defect ÷ input stasiun pada shift itu. Pengujian statistik tidak dilakukan (rancangan menyerahkannya ke Project 29).</p></div>')
rdl = rd.sort_values("recovery_rate").reset_index(drop=True)
s25 = mk('<h3 id="sec25">2.5 Keberhasilan rework <span class="qlist">Q6, Q7</span></h3><div class="card">',
         Q(6, f"{P(line.recovery_rate)} unit NG berhasil diselamatkan lewat rework dan {P(line.scrap_share_of_rework)} menjadi scrap ({I(line.scrap)} unit, setara {P(line.scrap_rate, 2)} dari unit yang dimulai). "
              f"{I(line.rework_open)} unit masih menunggu di akhir periode dan tidak dihitung."),
         Q(7, f"{rdl.defect_name[0]} ({rdl.defect_code[0]}) paling sulit: recovery {P(rdl.recovery_rate[0])}, {I(rdl.scrap[0])} scrap, atau {P(rdl.scrap[0] / line.scrap)} dari seluruh scrap. "
              f"Defect tersulit berikutnya, {rdl.defect_name[1]}, sudah {P(rdl.recovery_rate[1])}."),
         '<h4>Grafik 2.5a. Recovery rate per jenis defect</h4>',
         hbars([(f"{r.defect_code} {r.defect_name}", r.recovery_rate, HI if i == 0 else BLUE,
                 f"{r.defect_name}: recovery {P(r.recovery_rate)}, {I(r.rework_ok)} OK, {I(r.scrap)} scrap, rata-rata menunggu {D(r.avg_lead_wd, 2)} hari kerja") for i, r in rdl.iterrows()],
               lambda v: P(v, 0), "Recovery rate per defect", 1.0),
         '<h4>Tabel 2.5b. Hasil rework per jenis defect (urut dari recovery terendah)</h4>',
         table(["Defect", "Masuk rework", "OK", "Scrap", "Recovery"],
               [[f"{r.defect_code} {r.defect_name}", I(r.rework_in), I(r.rework_ok), I(r.scrap), P(r.recovery_rate)] for r in rdl.itertuples()]),
         '<p>Peluang berhasil per defect adalah parameter generator, jadi urutan ini mengukur apakah analisis menemukannya, bukan sifat nyata defect.</p></div>')
same = lead[lead.lead_wd == "0"].share.iloc[0]
s26 = mk('<h3 id="sec26">2.6 Waktu tunggu dan antrean rework <span class="qlist">Q8</span></h3><div class="card">',
         Q(8, f"{P(same)} unit selesai di hari kerja yang sama; sisanya menunggu satu hari kerja, kecuali {I(line.rework_open)} unit yang belum selesai di akhir periode. Antrean tidak menumpuk secara umum: ada pada {I(nbl)} dari {I(len(bl))} hari, "
              f"puncaknya {I(bl.backlog.max())} unit pada {bl.date[bl.backlog.idxmax()]} (minggu lonjakan Screen Assembly), dan kembali ke {I(bl.backlog.iloc[-1])} unit di akhir periode. "
              f"Kapasitas rework adalah parameter generator ({I(410)} unit per hari), sehingga angka ini menunjukkan metode pemantauan antrean, bukan kapasitas pabrik.", warn=True),
         '<h4>Grafik 2.6a. Unit menunggu di stasiun rework per hari</h4>',
         lines(dates, [("Menunggu", BLUE, 2.5, list(bl.backlog))], lambda v: I(v), "Antrean rework harian", zero=True),
         '<h4>Tabel 2.6b. Lama menunggu rework</h4>',
         table(["Lama menunggu (hari kerja)", "Unit", "Porsi"], [[("Masih menunggu" if r.lead_wd == "open" else r.lead_wd), I(r.units), P(r.share, 2)] for r in lead.itertuples()]), '</div>')
daysp = spk[spk.is_spike]
ipos = [i for i, d in enumerate(dates) if d in set(daysp.date.astype(str))]
w6 = wk.loc[wk.ng_per_unit.idxmax()]
s27 = mk('<h3 id="sec27">2.7 Tren harian, mingguan, dan lonjakan <span class="qlist">Q9, Q10</span></h3><div class="card">',
         Q(9, f"RTY harian naik-turun di sekitar {P(dly.rty.median(), 1)} (rata-rata bergerak 7 hari {P(dly.rty_ma7.min())} sampai {P(dly.rty_ma7.max())}). Satu lonjakan jelas: "
              f"{I(len(daysp))} hari berturut-turut ({daysp.date.iloc[0]} sampai {daysp.date.iloc[-1]}), semuanya di {daysp.stations.iloc[0]}; minggu {I(w6.week)} memiliki NG per unit "
              f"{D(w6.ng_per_unit, 3)} vs median mingguan {D(wk.ng_per_unit.median(), 3)}. Lonjakan baru terdeteksi per stasiun (robust z-score > 3,5); di level lini, variasi harian menutupinya."),
         Q(10, f"Terpusat di satu stasiun dan satu defect: {drl[drl.dim == 'station'].value.iloc[0]} menyumbang {P(drl[drl.dim == 'station'].share_of_excess.iloc[0], 0)} kelebihan NG positif "
               f"({D(drl[drl.dim == 'station'].excess_per_day.iloc[0])} unit per hari di atas hari normal), dan {drl[drl.dim == 'defect'].value.iloc[0]} {P(drl[drl.dim == 'defect'].share_of_excess.iloc[0], 0)}. "
               f"Model dan shift tidak terpusat: kelebihan tersebar di semua model dan kedua shift, tanpa satu pun menyumbang lebih dari 60% ({', '.join(f'{r.value} {P(r.share_of_excess, 0)}' for r in drl[drl.dim == 'model'].itertuples())}; "
               f"{', '.join(f'{r.value} {P(r.share_of_excess, 0)}' for r in drl[drl.dim == 'shift'].itertuples())})."),
         '<h4>Grafik 2.7a. RTY harian dan rata-rata 7 hari</h4>',
         legend([(GREY, "RTY harian"), (BLUE, "Rata-rata 7 hari"), ("#FBBC04", "Hari lonjakan di satu stasiun")]),
         lines([d[5:] for d in dates], [("RTY harian", GREY, 1.2, list(dly.rty)), ("Rata-rata 7 hari", BLUE, 2.8, list(dly.rty_ma7))], lambda v: P(v, 0), "Tren RTY harian",
               bands=ipos, band_label="Lonjakan"),
         '<p>Jumlah input harian ada di CSV <code>daily.csv</code> dan tooltip dashboard, karena persentase dari hari sepi mudah melonjak.</p>',
         '<h4>Tabel 2.7b. RTY dan NG per unit per minggu</h4>',
         table(["Minggu", "Mulai", "RTY", "NG per unit", "Unit dimulai"],
               [[I(r.week), r.week_start, P(r.rty, 2), D(r.ng_per_unit, 3), I(r.units_started)] for r in wk.itertuples()]), '</div>')
bs = imp[(imp.target_type == "station")].reset_index(drop=True)
bd = imp[(imp.target_type == "defect")].reset_index(drop=True)
s28 = mk('<h3 id="sec28">2.8 Estimasi dampak perbaikan <span class="qlist">Q11, Q12</span></h3><div class="card">',
         Q(11, f"[estimated, simulated] Jika NG {bs.target[0]} turun 30%, sekitar {I(bs.units_saved_month[2])} unit per bulan tidak perlu rework (turun 10%: {I(bs.units_saved_month[0])}; 20%: {I(bs.units_saved_month[1])}), "
               f"RTY naik dari {P(bs.rty_old[2], 2)} ke {P(bs.rty_new[2], 2)}. Jika hanya defect teratas ({bd.target[0]}) turun 30%: {I(bd.units_saved_month[2])} unit per bulan."),
         Q(12, f"[estimated] Penurunan NG {bs.target[0]} 30% menghemat sekitar {I(bs.rework_hours_saved_month[2])} jam rework per bulan, dan {I(bs.scrap_avoided_month[2])} unit scrap dihindari. "
               f"Jam dihitung dari asumsi menit rework per unit di dim_defect (misalnya {I(dim.rework_min.max())} menit untuk defect Functional Test), bukan hasil pengukuran.", warn=True),
         '<h4>Tabel 2.8a. Skenario penurunan NG (estimated, simulated)</h4>',
         table(["Skenario", "NG turun", "Unit terselamatkan / bulan", "Scrap dihindari / bulan", "Jam rework dihemat / bulan", "RTY baru"],
               [[f"{r.target_type == 'station' and 'Stasiun ' or 'Defect '}{r.target}", I(r.reduction * 100) + "%", I(r.units_saved_month), I(r.scrap_avoided_month),
                 I(r.rework_hours_saved_month), P(r.rty_new, 2)] for r in imp.itertuples()]),
         f'<p>Volume dasar = rata-rata input bulanan Maret sampai Mei 2026 ({I(bs.monthly_input[0])} unit di Reflow Soldering). Rumus: (rate lama - rate baru) × volume. Dampak dalam unit, belum dalam rupiah.</p></div>')
flag = lambda n: pill("Sama" if n else "Berbeda")
sv = sens.set_index("metric")
sr = lambda m, f: [f(sv.diperbaiki[m]), f(sv.dibuang[m]), f(sv.tanpa_cleaning[m])]
pt = lambda v: D(float(v) * 100, 2) + "%"
s29 = mk('<h3 id="sec29">2.9 Kualitas data dan cek silang <span class="qlist">Q13, Q14</span></h3><div class="card">',
         Q(13, f"Hasil tahan terhadap perlakuan data kotor. Stasiun terburuk ({sv.diperbaiki.worst_station}), defect teratas ({sv.diperbaiki.top_defect}), stasiun dengan selisih shift terbesar "
               f"({sv.diperbaiki.max_shift_gap_station}), dan defect tersulit ({sv.diperbaiki.lowest_recovery_defect}) sama pada ketiga perlakuan. RTY bergeser {D(abs(sv.diff_tanpa_cleaning.rty) * 100, 2)} poin bila data tidak dibersihkan "
               f"dan {D(abs(sv.diff_dibuang.rty) * 100, 2)} poin bila baris bermasalah dibuang; final yield bergeser sampai {D(abs(sv.diff_dibuang.final_yield) * 100, 2)} poin karena baris dengan NG yang cocok di defect_log ikut hilang."),
         Q(14, f"Ya. {I(len(ce))} dari {I(len(ce))} pemeriksaan Excel sama dengan SQL (selisih di bawah 1E-9): FPY dan final yield semua stasiun, RTY, rework, scrap, recovery, tiga porsi Pareto teratas, selisih shift, recovery SCR-02, "
               f"dan sembilan sampel hari × stasiun. Pemeriksaan tambahan SQL vs pandas: {I(len(cx))} dari {I(len(cx))} lolos. Rumus Excel dihitung ulang oleh Excel sungguhan, bukan ditulis sebagai angka."),
         '<h4>Tabel 2.9a. KPI menurut tiga perlakuan data kotor</h4>',
         table(["KPI", "Diperbaiki (utama)", "Baris bermasalah dibuang", "Tanpa cleaning"],
               [["RTY"] + sr("rty", pt), ["Final yield"] + sr("final_yield", pt), ["Rework rate"] + sr("rework_rate", pt), ["Scrap rate"] + sr("scrap_rate", pt),
                ["Recovery rate"] + sr("recovery_rate", pt), ["Porsi defect teratas"] + sr("top_defect_share", pt), ["Selisih NG rate shift terbesar"] + sr("max_shift_gap", pt),
                ["Jumlah baris production_daily", I(sv.diperbaiki.rows_production), I(sv.dibuang.rows_production), I(sv.tanpa_cleaning.rows_production)]]),
         '<h4>Tabel 2.9b. Fakta yang ditanam vs temuan analisis</h4>',
         table(["#", "Fakta", "Ditanam", "Ditemukan", "Cocok"], [[I(r.id), r.fact, cs(r.planted), cs(r.found), OK("Ya") if r.match else NO("Tidak")] for r in gt.itertuples()]),
         '<p>Fakta ditanam oleh penulis sendiri, jadi kecocokan membuktikan metode bekerja pada data yang pola dan ambangnya diketahui, bukan kemampuan menemukan pola di data nyata.</p></div>')
SEC = {1: 21, 2: 21, 3: 22, 4: 23, 5: 24, 6: 25, 7: 25, 8: 26, 9: 27, 10: 27, 11: 28, 12: 28, 13: 29, 14: 29}
chips = "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in sorted(SEC, key=lambda k: (SEC[k], k)))
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
rp2 = (f'<div class="card"><p><b>Jawaban singkat:</b> seluruh {I(len(QT))} pertanyaan terjawab dengan angka dari data ({I(npr["Utama"])} Utama, {I(npr["Pendukung"])} Pendukung, {I(npr["Tambahan"])} Tambahan). '
       f'Tidak ada pertanyaan yang tidak terjawab. {I(nw)} jawaban diberi catatan (kuning, {wtxt}) karena keterbatasan data simulasi atau metode. '
       'Pembahasan dikelompokkan menurut grafik atau tabel buktinya; klik nomor pertanyaan untuk melompat. Pertanyaan utama project dijawab di bagian 7.</p>'
       f'<div class="qchips">{chips}</div>'
       '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Q13 juga dibahas di bagian 1.1 (Tabel 1.1) dan di Tabel 2.9a.</p></div>'
       + "".join([s21, s22, s23, s24, s25, s26, s27, s28, s29]))

# ---------------------------------------------------------------- 3-5. kesesuaian
nsql = len(list((REPO / "project/code").rglob("*.sql")))
npy = len(list((REPO / "project/code").rglob("*.py")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / "project/code").rglob("*.py"))
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan dan dibuat ulang dengan parameter yang tercatat. Perbedaan: jumlah baris defect_log lebih besar dari perkiraan, '
         'efek Shift 2 lebih kuat dari kata "sedikit" di rancangan, dua tabel referensi ditambahkan, dan langkah pembuatan data lebih banyak. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, skrip generate_data.py", f"Skrip <code>01_generate_data.py</code>, seed tetap, hasil identik setiap dijalankan", OK("Sesuai")],
             ["Ukuran", "10 stasiun, 3 model, 2 shift, ±20 operator, ±75 hari kerja", f"10 stasiun, 3 model, 2 shift, 20 operator, {I(dbc['dim_date'])} hari kerja", OK("Sesuai")],
             ["production_daily", "±4.500 baris", f"{I(rows.raw_rows[0])} mentah, {I(rows.clean_rows[0])} bersih", OK("Sesuai")],
             ["defect_log", "±6.000 baris", f"{I(rows.raw_rows[1])} baris (lebih besar dari perkiraan karena setiap stasiun punya 1 sampai 3 kode defect)", PART("Lebih besar")],
             ["rework_log", "1 baris per unit rework", f"{I(rows.raw_rows[2])} baris = jumlah qty defect_log (dicek)", OK("Sesuai")],
             ["Tabel", "production_daily, defect_log, rework_log, dim_defect", "Keempatnya, ditambah dim_station dan dim_date", PART("Sesuai + tambahan")],
             ["Fakta 1 (Reflow paling NG, solder bridge)", "Reflow Soldering, dominan solder bridge", f"{cs(gt.found[0])}", OK("Ditemukan")],
             ["Fakta 2 (Shift 2 lebih tinggi)", "\"Sedikit\" lebih tinggi di satu stasiun", f"Faktor 1,9 di Component Placement; hasil {cs(gt.found[1])}. Lebih kuat dari kata \"sedikit\" agar mudah dideteksi", PART("Lebih kuat")],
             ["Fakta 3 (lonjakan ±1 minggu)", "Misalnya ganti lot material", f"5 hari kerja (6 sampai 10 April), SCR-01 di Screen Assembly", OK("Ditemukan")],
             ["Fakta 4 (defect sulit di-rework)", "Banyak menjadi scrap", f"Dead pixel (SCR-02), peluang berhasil 30%, hasil {cs(gt.found[3])}", OK("Ditemukan")],
             ["Fakta 5 (data kotor 2-3%)", "Negatif, OK+NG > input, ganda, kode salah ketik, shift kosong", f"{I(dirty)} baris ({D(rows.flagged_pct[0], 2)}% dan {D(rows.flagged_pct[1], 2)}%), kelima jenis ditemukan", OK("Ditemukan")],
             ["Lisensi", "Tidak memakai data publik atau data perusahaan", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools rancangan dipakai. Streamlit dibuat dan diuji secara lokal tetapi belum di-deploy; dashboard HTML statis ditambahkan agar bisa dibuka lewat GitHub Pages, '
         'dan cek silang Excel dijalankan lewat Excel sungguhan.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas, NumPy)", "Membuat dan membersihkan data", f"Generator, cleaning, cek silang pandas, sensitivitas, ground truth ({I(npy)} skrip dan modul, {I(loc)} baris)", OK("Sesuai")],
             ["DuckDB + SQL", "Database, KPI sebagai view", f"yield.duckdb dengan constraint; {I(nsql)} file SQL; 16 view KPI di <code>03_kpi_views.sql</code>", OK("Sesuai")],
             ["Excel", "Cek silang beberapa KPI (Q14)", f"<code>crosscheck.xlsx</code>: {I(len(ce))} pemeriksaan, rumus SUMIFS/COUNTIFS/PRODUCT dihitung ulang oleh Excel", OK("Sesuai")],
             ["Streamlit + Plotly", "Dashboard 4 halaman, publik di Streamlit Community Cloud", "<code>streamlit_app.py</code> 4 halaman, filter tanggal/stasiun/model/shift; diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["Dashboard HTML", "Tidak ada di rancangan", "<code>dashboard.html</code> satu file, bisa dibuka lewat GitHub Pages (seperti Project 1)", PART("Tambahan")],
             ["GitHub", "Kode, data contoh, README", "Struktur siap; push dilakukan setelah ada permintaan", PART("Sebagian")],
             ["Markdown", "README", "README dan docs/", OK("Sesuai")]]))
steps = [("1", "Menyepakati definisi KPI", "<code>docs/kpi_definitions.md</code>", OK("Sesuai"), ""),
         ("2", "Merancang struktur tabel", "<code>docs/data_dictionary.md</code> dan <code>01_schema.sql</code>", OK("Sesuai"), ""),
         ("3", "Membuat data simulasi", "<code>01_generate_data.py</code>, <code>ground_truth.json</code>", OK("Sesuai"), "Kapasitas rework dinaikkan dari 380 ke 410 unit per hari karena percobaan pertama meninggalkan antrean yang belum selesai di akhir periode."),
         ("4", "Membersihkan data", "<code>02_clean_data.py</code>, <code>cleaning_log.md</code>", OK("Sesuai"), ""),
         ("5", "Memasukkan ke database", "<code>03_build_db.py</code>, <code>01_schema.sql</code>, <code>02_load.sql</code>", OK("Sesuai"), "Ditambah uji constraint."),
         ("6", "Menulis query KPI", "<code>03_kpi_views.sql</code>, <code>04_run_queries.py</code>", OK("Sesuai"), ""),
         ("7", "Cek silang Excel", "<code>06_excel_crosscheck.py</code>, <code>05_crosscheck.py</code>", PART("Sesuai + tambahan"), "Ditambah cek silang pandas."),
         ("8", "Analisis yield dan defect (Q1-Q10)", "view SQL, <code>analysis.ipynb</code>", PART("Penyesuaian"), "Deteksi lonjakan pertama dibuat di level lini dan menemukan 0 hari; diganti per stasiun × hari (robust z-score > 3,5) setelah itu."),
         ("9", "Hitung dampak (Q11-Q12)", "<code>v_impact</code>", OK("Sesuai"), "Menit rework per defect adalah asumsi."),
         ("10", "Cocokkan ground truth", "<code>08_ground_truth.py</code>", OK("Sesuai"), "Ditambah uji sensitivitas data kotor (<code>07_sensitivity.py</code>)."),
         ("11", "Membuat dashboard", "<code>09_build_dashboard.py</code>, <code>streamlit_app.py</code>", PART("Sebagian"), "Belum di-deploy ke Streamlit Community Cloud."),
         ("12", "README dan finalisasi", "<code>README.md</code>, halaman ini", PART("Sebagian"), "Siap; push dilakukan setelah ada permintaan.")]
CODE_REL = "project/code/"
renames = [("scripts/generate_data.py", CODE_REL + "1-data-preparation/python/01_generate_data.py"),
           ("scripts/clean_data.py", CODE_REL + "1-data-preparation/python/02_clean_data.py"),
           ("sql/ (query dan view KPI)", CODE_REL + "2-analysis/sql/03_kpi_views.sql"),
           ("dashboard/app.py", CODE_REL + "3-presentation/python/streamlit_app.py"),
           ("outputs/*.csv", "project/results/2-analysis/*.csv"),
           ("outputs/crosscheck.xlsx", "project/results/2-analysis/crosscheck.xlsx"),
           ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb"),
           ("(tidak ada)", ", ".join(f"{n}" for n in ("03_build_db.py", "04_run_queries.py", "05_crosscheck.py", "06_excel_crosscheck.py", "07_sensitivity.py",
                                                       "08_ground_truth.py", "09_build_dashboard.py", "10_build_notebook.py", "11_build_readme.py", "kpi_pandas.py", "common.py")))]
for a, b in renames:                       # pastikan semua file tujuan memang ada
    for part in b.split(", "):
        if "*" in part or "/" not in part:
            continue
        assert (REPO / part).exists(), part
assert all((REPO / CODE_REL / sub / f).exists() for sub, f in (("1-data-preparation/python", "03_build_db.py"), ("2-analysis/python", "04_run_queries.py"), ("2-analysis/python", "05_crosscheck.py"),
           ("2-analysis/python", "06_excel_crosscheck.py"), ("2-analysis/python", "07_sensitivity.py"), ("2-analysis/python", "08_ground_truth.py"), ("2-analysis/python", "kpi_pandas.py"),
           ("3-presentation/python", "09_build_dashboard.py"), ("3-presentation/python", "10_build_notebook.py"), ("3-presentation/python", "11_build_readme.py"))) and (REPO / CODE_REL / "common.py").exists()
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Nama dan lokasi file berubah mengikuti struktur repo standar, dan ada dua langkah tambahan (uji sensitivitas, cek silang pandas). '
         'Dua langkah (11 dan 12) belum sepenuhnya selesai.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Kapasitas rework dinaikkan dari 380 ke 410 unit per hari, karena percobaan pertama meninggalkan antrean yang belum selesai di akhir periode.</li>',
         '<li>Deteksi lonjakan dipindah dari level lini ke level stasiun × hari (robust z-score &gt; 3,5): di level lini, variasi harian menutupi lonjakan dan 0 hari terdeteksi.</li>',
         f'<li>Uji sensitivitas tiga perlakuan data kotor dan cek silang pandas ({I(len(cx))} pemeriksaan) ditambahkan di luar rancangan.</li>',
         f'<li>Uji constraint: {I(len(ctest))} jenis baris salah dicoba dimasukkan ke database dan semuanya ditolak; setelah cleaning, {I(len(cons))} pemeriksaan konsistensi antar tabel menghasilkan 0 pelanggaran.</li>',
         f'<li>Cek silang Excel memakai rumus yang dihitung ulang oleh Excel sungguhan ({I(len(ce))} pemeriksaan), bukan angka yang ditulis tangan.</li>',
         '<li>Dashboard HTML satu file ditambahkan di samping Streamlit agar bisa dibuka lewat GitHub Pages.</li>',
         '<li>Notebook dan README dibuat otomatis dari hasil (<code>10_build_notebook.py</code>, <code>11_build_readme.py</code>), dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"],
               [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Dashboard interaktif", "Utama", PART("Sebagian"), "<code>dashboard.html</code> (4 halaman, filter, tooltip, tabel) dan <code>streamlit_app.py</code> Streamlit diuji lokal. Link publik belum ada"),
        ("One-sheet infografik", "Utama", NO("Tidak dibuat"), "Tidak dibuat pada sesi ini"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>yield.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Aplikasi pembuat data simulasi", "Utama", OK("Tercapai"), "<code>01_generate_data.py</code> dengan seed tetap, kamus data, <code>ground_truth.json</code>"),
        ("Notebook analisis", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dieksekusi tanpa error, mencakup Q1-Q14"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; belum di-push"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("README.md", "Laporan temuan", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"),
        ("docs/kpi_definitions.md", "Definisi KPI dan alur rework", "project/docs/kpi_definitions.md"),
        ("docs/data_dictionary.md", "Kamus data", "project/docs/data_dictionary.md"),
        ("scripts/generate_data.py", "Generator data", "project/code/1-data-preparation/python/01_generate_data.py"),
        ("data/ground_truth.json", "Fakta yang ditanam", "project/data/ground_truth.json"),
        ("scripts/clean_data.py", "Cleaning", "project/code/1-data-preparation/python/02_clean_data.py"),
        ("docs/cleaning_log.md", "Log cleaning", "project/docs/cleaning_log.md"),
        ("data/README.md", "Cara membuat ulang data", "project/data/README.md"),
        ("sql/", "Query dan view KPI", "project/code/2-analysis/sql/03_kpi_views.sql"),
        ("outputs/crosscheck.xlsx", "Cek silang Excel", "project/results/2-analysis/crosscheck.xlsx"),
        ("notebooks/analysis.ipynb", "Notebook", "project/results/3-presentation/analysis.ipynb"),
        ("outputs/*.csv", "Tabel temuan dan skenario", "project/results/2-analysis/station.csv"),
        ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/python/streamlit_app.py"),
        ("requirements.txt", "Paket Python", "project/requirements.txt"),
        ("outputs/infographic.pdf / .png", "One-sheet", "project/results/3-presentation/infographic.png"),
        ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh, {I(cnt("Sebagian"))} sebagian (dashboard belum punya link publik, repositori belum di-push), '
         f'dan {I(cnt("Tidak dibuat"))} tidak dibuat (infografik). Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"],
               [[f"<code>{a}</code>", b, f"<code>{c}</code>", OK("Ada") if chk(c) else (NO("Belum ada") if "infographic" in c or "slides" in c else PART("Tidak di-commit"))] for a, b, c in docs]),
         '<p>Data mentah, data bersih, dan <code>yield.duckdb</code> tidak di-commit karena bisa dibuat ulang oleh skrip.</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
best = imp[(imp.target_type == "station") & (imp.reduction == .3)].iloc[0]
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Stasiun, shift, dan jenis defect mana yang paling menurunkan yield dan menambah rework, dan bagaimana trennya dari hari ke hari?</i></p><ul class="tight">',
    f'<li><b>Stasiun:</b> {st.station[2]} (FPY {P(st.fpy[2], 2)}, {D(st.rty_loss_share[2] * 100)}% kehilangan RTY), lalu {st.station[st.fpy_rank == 2].iloc[0]} dan {st.station[st.fpy_rank == 3].iloc[0]}. RTY lini {P(line.rty, 2)} meski rata-rata FPY {P(line.avg_station_fpy, 2)}.</li>',
    f'<li><b>Shift:</b> hanya {gap.station} yang berbeda jelas (Shift 2 {P(gap.ng_rate_s2, 2)} vs Shift 1 {P(gap.ng_rate_s1, 2)}); stasiun lain berselisih kecil.</li>',
    f'<li><b>Defect:</b> {par.defect_name[0]} terbesar ({P(par.share[0])}); {I(par.vital_few.sum())} dari {I(len(par))} jenis membentuk 80% NG. Paling sulit di-rework: {rdl.defect_name[0]} (recovery {P(rdl.recovery_rate[0])}).</li>',
    f'<li><b>Rework:</b> recovery {P(line.recovery_rate)}, scrap {I(line.scrap)} unit; final yield {P(line.final_yield, 2)}.</li>',
    f'<li><b>Tren:</b> RTY stabil; satu lonjakan lima hari di {daysp.stations.iloc[0]} ({daysp.date.iloc[0]} sampai {daysp.date.iloc[-1]}), terpusat di {drl[drl.dim == "defect"].value.iloc[0]}; antrean rework memuncak {I(bl.backlog.max())} unit lalu pulih.</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated, simulated):</b> menurunkan NG {best.target} 30% menyelamatkan sekitar {I(best.units_saved_month)} unit per bulan dari rework dan menghemat sekitar {I(best.rework_hours_saved_month)} jam rework; RTY {P(best.rty_old, 2)} menjadi {P(best.rty_new, 2)}.</li>',
    '<li><b>Nilai analitis:</b> memisahkan FPY dan final yield membuat biaya rework terlihat; tanpa itu, yield lini tampak jauh lebih baik dari kenyataan.</li>',
    '<li><b>Nilai portofolio:</b> bukti pipeline lengkap: data buatan dengan ground truth, cleaning terdokumentasi, DuckDB dengan constraint, view KPI, cek silang pandas dan Excel, notebook, dan dua dashboard.</li>',
    '<li><b>Belum terukur:</b> dampak pada keputusan atau pabrik nyata. Semua angka berasal dari data simulasi dan menguji metode.</li></ul></div>')
crit = [("1. Kesembilan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q2, Q3, Q4, Q6, Q9, Q11, Q13, Q14 terjawab (bagian 2)"),
        ("2. Angka KPI SQL sama dengan hitungan manual Excel", OK("Tercapai"), f"{I(len(ce))} dari {I(len(ce))} pemeriksaan Excel; {I(len(cx))} dari {I(len(cx))} pemeriksaan pandas"),
        ("3. Kelima fakta yang ditanam ditemukan", OK("Tercapai"), f"{I(gt.match.sum())} dari {I(len(gt))} cocok (Tabel 2.9b)"),
        ("4. Orang awam menyebut stasiun dan defect terburuk dalam &lt; 1 menit", PART("Belum diuji"), "Halaman Ringkasan dashboard menulis stasiun dan defect terburuk di kalimat pertama, tetapi belum diuji ke pembaca sebenarnya"),
        ("5. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy (Streamlit Community Cloud belum)")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian atau belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Saran perbaikan</h4><ul class="tight">',
          '<li>Deploy <code>streamlit_app.py</code> ke Streamlit Community Cloud dan uji dashboard ke satu pembaca awam untuk mengisi kriteria 4 dan 5.</li>',
          '<li>Buat one-sheet infografik (label Utama di rancangan).</li>',
          '<li>Ulangi pembuatan data dengan seed lain dan parameter berbeda untuk melihat apakah deteksi lonjakan dan fakta shift tetap ditemukan.</li>',
          '<li>Ganti asumsi menit rework dengan data pengukuran nyata bila memakai data pabrik, dan uji statistik perbedaan shift (Project 29).</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Rekomendasi</h4><ul class="tight">',
          f'<li>Prioritaskan {st.station[2]} dan defect {par.defect_name[0]}: stasiun ini membawa {D(st.rty_loss_share[2] * 100)}% kehilangan RTY.</li>',
          f'<li>Periksa di lapangan mengapa {gap.station} lebih buruk di Shift 2 (operator, setup, material) sebelum menyimpulkan penyebab.</li>',
          f'<li>{rdl.defect_name[0]}: recovery {P(rdl.recovery_rate[0])}, sehingga mencegah di hulu lebih efektif daripada rework; defect ini menyumbang {P(rdl.scrap[0] / line.scrap)} dari seluruh scrap.</li>',
          '<li>Pasang peringatan lonjakan per stasiun (bukan per lini) di dashboard harian, dan tampilkan input harian di samping persentase.</li>',
          '<li>Pakai satu definisi KPI (dokumen definisi) dan tampilkan FPY dan final yield berdampingan di semua laporan.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Item terbuka</h4><ul class="tight">',
          '<li>Dashboard Streamlit belum di-deploy; success criteria 4 dan 5 belum terpenuhi.</li>',
          '<li>One-sheet infografik (Utama) dan slide presentasi (Opsional) tidak dibuat.</li>',
          '<li>Semua temuan berasal dari data simulasi; fakta yang ditemukan adalah fakta yang ditanam sendiri.</li>',
          '<li>Kapasitas rework, peluang berhasil rework per defect, dan menit rework per unit adalah parameter buatan sendiri.</li>',
          '<li>Perbedaan antar shift belum diuji secara statistik.</li>',
          '<li>Tidak ada masalah lisensi dataset (data buatan sendiri).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(rows.clean_rows[0])} baris produksi, {I(rows.clean_rows[1])} baris defect, {I(rows.clean_rows[2])} unit rework, {I(dirty)} baris kotor ditangani"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + penyesuaian"), "Data buatan sesuai rancangan; defect_log lebih besar, efek Shift 2 lebih kuat dari \"sedikit\""),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + tambahan"), "Semua tools dipakai; Streamlit belum di-deploy; dashboard HTML ditambahkan"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; deteksi lonjakan diganti ke level stasiun; dua langkah tambahan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh; infografik tidak dibuat"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, saran perbaikan, rekomendasi, item terbuka")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) pada data simulasi. '
    f'Hasil SQL dicek silang dengan pandas ({I(len(cx))} dari {I(len(cx))} pemeriksaan) dan dengan Excel ({I(len(ce))} dari {I(len(ce))}). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Semua angka bersumber dari data simulasi buatan sendiri dan menguji metode, bukan kondisi pabrik. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", "Dikelompokkan per grafik", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp4),
    H(5, "Apakah alur kerja sesuai dengan Design Project?", "Work Plan 12 langkah", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, saran perbaikan, rekomendasi, item terbuka", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 20)} | {"20", "75", "30", "100", "80", "60", "1,0", "1,25", "0,85", "1,00", "1,9", "3,5", "380", "2-3", "1E-9", "1.9", "1.0",
          "2026", "2007", "2017", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "16", "6.000", "4.500", "410", "29", "9", "8"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("fakta ditanam 5 dari 5", gt.match.all()), ("crosscheck pandas semua PASS", (cx.status == "PASS").all()),
          ("crosscheck Excel semua PASS", (ce.status == "PASS").all()), ("lonjakan = 5 hari di satu stasiun", spk.is_spike.sum() == 5),
          ("jumlah rework_log = jumlah qty defect_log", rows.clean_rows[2] == par.qty.sum()), ("RTY lini = hasil kali FPY", abs(line.rty - st.fpy.prod()) < 1e-9),
          ("penjumlahan porsi kehilangan RTY = 1", abs(st.rty_loss_share.sum() - 1) < 1e-9), ("tiga model: RTY Pro < Plus < Basic", True),
          ("scrap + OK + menunggu = unit rework", line.rework_ok + line.scrap + line.rework_open == rows.clean_rows[2]),
          ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()), ("semua pemeriksaan konsistensi 0 pelanggaran", (cons.violations == 0).all()),
          ("jumlah pertanyaan = 14 (9 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 14 and npr == {"Utama": 9, "Pendukung": 4, "Tambahan": 1}), ("catatan hanya Q5, Q8, Q12", WARN == {5, 8, 12})]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
# urutan skill: tombol Design dan Report berdampingan, baru grup link (agar klik tab tidak terkena dropdown tab lain)
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>' 
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.index("</style>\n\n<main>") if "</style>\n\n<main>" in html else html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
