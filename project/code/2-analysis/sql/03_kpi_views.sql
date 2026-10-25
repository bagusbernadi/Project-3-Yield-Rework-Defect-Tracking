-- Langkah 6: view KPI. Rumus mengikuti docs/kpi_definitions.md agar dashboard dan laporan memakai rumus yang sama.

-- Hasil rework per stasiun asal (unit yang masih di antrean dihitung sebagai belum lolos)
CREATE OR REPLACE VIEW v_rework_by_station AS
SELECT station_origin AS station,
       count(*)                                   AS rework_in,
       count(*) FILTER (WHERE result = 'OK')      AS rework_ok,
       count(*) FILTER (WHERE result = 'Scrap')   AS scrap,
       count(*) FILTER (WHERE result IS NULL)     AS rework_open
FROM rework_log GROUP BY 1;

-- Q1, Q2: KPI per stasiun
CREATE OR REPLACE VIEW v_station AS
WITH p AS (
    SELECT station, sum(input_qty) AS input_qty, sum(ok_first_pass) AS ok_first_pass, sum(ng_qty) AS ng_qty
    FROM production_daily GROUP BY 1
)
SELECT s.seq, p.station, p.input_qty, p.ok_first_pass, p.ng_qty,
       r.rework_in, r.rework_ok, r.scrap, r.rework_open,
       p.ok_first_pass / p.input_qty                       AS fpy,
       (p.ok_first_pass + r.rework_ok) / p.input_qty       AS final_yield,
       p.ng_qty / p.input_qty                              AS rework_rate,
       r.scrap / p.input_qty                               AS scrap_rate,
       r.rework_ok / (r.rework_ok + r.scrap)               AS recovery_rate,
       p.ng_qty / sum(p.ng_qty) OVER ()                    AS ng_share,
       ln(p.ok_first_pass / p.input_qty) / sum(ln(p.ok_first_pass / p.input_qty)) OVER () AS rty_loss_share,
       rank() OVER (ORDER BY p.ok_first_pass / p.input_qty) AS fpy_rank
FROM p JOIN dim_station s USING (station) JOIN v_rework_by_station r USING (station)
ORDER BY s.seq;

-- Q1, Q2, Q6: KPI seluruh lini (satu baris)
CREATE OR REPLACE VIEW v_line_kpi AS
SELECT (SELECT input_qty FROM v_station WHERE seq = 1)              AS units_started,
       (SELECT ok_first_pass + rework_ok FROM v_station WHERE seq = 10) AS units_packed,
       exp(sum(ln(fpy)))                                            AS rty,
       exp(sum(ln(final_yield)))                                    AS final_yield,
       avg(fpy)                                                     AS avg_station_fpy,
       sum(ng_qty)                                                  AS ng_events,
       sum(ng_qty) / (SELECT input_qty FROM v_station WHERE seq = 1) AS rework_rate,
       sum(scrap) / (SELECT input_qty FROM v_station WHERE seq = 1)  AS scrap_rate,
       sum(rework_ok)                                               AS rework_ok,
       sum(scrap)                                                   AS scrap,
       sum(rework_open)                                             AS rework_open,
       sum(rework_ok) / (sum(rework_ok) + sum(scrap))               AS recovery_rate,
       sum(scrap) / (sum(rework_ok) + sum(scrap))                   AS scrap_share_of_rework
FROM v_station;

-- Q3: FPY per model per stasiun dan RTY per model
CREATE OR REPLACE VIEW v_model_station AS
SELECT model, s.seq, station, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_qty,
       sum(ok_first_pass) / sum(input_qty) AS fpy
FROM production_daily JOIN dim_station s USING (station)
GROUP BY ALL ORDER BY model, s.seq;

CREATE OR REPLACE VIEW v_model AS
SELECT model, exp(sum(ln(fpy))) AS rty, sum(ng_qty) AS ng_qty,
       max(input_qty) FILTER (WHERE seq = 1) AS units_started,
       sum(ng_qty) / max(input_qty) FILTER (WHERE seq = 1) AS rework_rate
FROM v_model_station GROUP BY 1 ORDER BY 1;

-- Q4: Pareto defect seluruh lini
CREATE OR REPLACE VIEW v_pareto_line AS
WITH d AS (
    SELECT defect_code, sum(qty) AS qty FROM defect_log GROUP BY 1
), r AS (
    SELECT d.*, dd.defect_name, dd.station, dd.category,
           qty / sum(qty) OVER () AS share,
           sum(qty) OVER (ORDER BY qty DESC, defect_code ROWS UNBOUNDED PRECEDING) / sum(qty) OVER () AS cum_share,
           row_number() OVER (ORDER BY qty DESC, defect_code) AS rank
    FROM d JOIN dim_defect dd USING (defect_code)
)
SELECT *, coalesce(lag(cum_share) OVER (ORDER BY rank), 0) < 0.8 AS vital_few FROM r ORDER BY rank;

-- Q4: Pareto defect per stasiun
CREATE OR REPLACE VIEW v_pareto_station AS
WITH d AS (SELECT station, defect_code, sum(qty) AS qty FROM defect_log GROUP BY 1, 2)
SELECT s.seq, d.station, d.defect_code, dd.defect_name, d.qty,
       d.qty / sum(d.qty) OVER (PARTITION BY d.station) AS share_in_station,
       row_number() OVER (PARTITION BY d.station ORDER BY d.qty DESC, d.defect_code) AS rank_in_station
FROM d JOIN dim_defect dd USING (defect_code) JOIN dim_station s ON s.station = d.station
ORDER BY s.seq, rank_in_station;

-- Q5: NG per shift per stasiun (selisih Shift 2 - Shift 1 dalam poin persen NG rate)
CREATE OR REPLACE VIEW v_shift_station AS
WITH x AS (
    SELECT station, shift, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_qty, sum(ng_qty) / sum(input_qty) AS ng_rate
    FROM production_daily GROUP BY 1, 2
)
SELECT s.seq, a.station, a.input_qty AS input_s1, b.input_qty AS input_s2,
       a.ng_rate AS ng_rate_s1, b.ng_rate AS ng_rate_s2, b.ng_rate - a.ng_rate AS gap,
       b.ng_rate / a.ng_rate AS ratio
FROM x a JOIN x b ON a.station = b.station AND a.shift = 'Shift 1' AND b.shift = 'Shift 2'
JOIN dim_station s ON s.station = a.station ORDER BY s.seq;

-- Q5: tabel silang defect x shift (defect rate terhadap input stasiun asal defect)
CREATE OR REPLACE VIEW v_defect_shift AS
WITH d AS (SELECT station, shift, defect_code, sum(qty) AS qty FROM defect_log GROUP BY ALL),
     i AS (SELECT station, shift, sum(input_qty) AS input_qty FROM production_daily GROUP BY ALL)
SELECT d.defect_code, dd.defect_name, d.station,
       sum(d.qty / i.input_qty) FILTER (WHERE d.shift = 'Shift 1') AS rate_s1,
       sum(d.qty / i.input_qty) FILTER (WHERE d.shift = 'Shift 2') AS rate_s2,
       sum(d.qty) FILTER (WHERE d.shift = 'Shift 1') AS qty_s1,
       sum(d.qty) FILTER (WHERE d.shift = 'Shift 2') AS qty_s2
FROM d JOIN i USING (station, shift) JOIN dim_defect dd USING (defect_code)
GROUP BY ALL ORDER BY rate_s2 - rate_s1 DESC;

-- Q6, Q7, Q8: hasil rework per jenis defect (lead time dalam hari kerja)
CREATE OR REPLACE VIEW v_rework_defect AS
SELECT r.defect_code, dd.defect_name, dd.station, dd.rework_min,
       count(*) AS rework_in,
       count(*) FILTER (WHERE result = 'OK')    AS rework_ok,
       count(*) FILTER (WHERE result = 'Scrap') AS scrap,
       count(*) FILTER (WHERE result IS NULL)   AS rework_open,
       count(*) FILTER (WHERE result = 'OK') / count(result) AS recovery_rate,
       avg(o.work_day - i.work_day) AS avg_lead_wd
FROM rework_log r JOIN dim_defect dd USING (defect_code)
JOIN dim_date i ON i.date = r.date_in LEFT JOIN dim_date o ON o.date = r.date_out
GROUP BY ALL ORDER BY recovery_rate;

-- Q8: distribusi lead time rework (hari kerja)
CREATE OR REPLACE VIEW v_rework_lead AS
SELECT coalesce(CAST(o.work_day - i.work_day AS VARCHAR), 'open') AS lead_wd, count(*) AS units,
       count(*) / sum(count(*)) OVER () AS share
FROM rework_log r JOIN dim_date i ON i.date = r.date_in LEFT JOIN dim_date o ON o.date = r.date_out
GROUP BY 1 ORDER BY 1;

-- Q8: antrean rework harian (unit menunggu di akhir hari)
CREATE OR REPLACE VIEW v_backlog_daily AS
WITH a AS (SELECT date_in AS date, count(*) AS rework_in FROM rework_log GROUP BY 1),
     b AS (SELECT date_out AS date, count(*) AS rework_out FROM rework_log WHERE date_out IS NOT NULL GROUP BY 1)
SELECT d.date, coalesce(a.rework_in, 0) AS rework_in, coalesce(b.rework_out, 0) AS rework_out,
       sum(coalesce(a.rework_in, 0) - coalesce(b.rework_out, 0)) OVER (ORDER BY d.date) AS backlog
FROM dim_date d LEFT JOIN a USING (date) LEFT JOIN b USING (date) ORDER BY d.date;

-- Q9: tren harian (RTY harian = hasil kali FPY 10 stasiun pada hari itu) dan rata-rata bergerak 7 hari
CREATE OR REPLACE VIEW v_daily AS
WITH st AS (
    SELECT date, station, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_qty, sum(ok_first_pass) / sum(input_qty) AS fpy
    FROM production_daily GROUP BY 1, 2
), d AS (
    SELECT date, exp(sum(ln(fpy))) AS rty, sum(ng_qty) AS ng_qty,
           max(input_qty) FILTER (WHERE station = 'Solder Paste Printing') AS units_started
    FROM st GROUP BY 1
)
SELECT d.date, dt.week, units_started, ng_qty, ng_qty / units_started AS ng_per_unit, rty,
       avg(rty) OVER w AS rty_ma7, avg(ng_qty / units_started) OVER w AS ng_per_unit_ma7
FROM d JOIN dim_date dt USING (date)
WINDOW w AS (ORDER BY d.date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY d.date;

CREATE OR REPLACE VIEW v_weekly AS
WITH st AS (
    SELECT dt.week, min(p.date) AS week_start, station, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_qty,
           sum(ok_first_pass) / sum(input_qty) AS fpy
    FROM production_daily p JOIN dim_date dt USING (date) GROUP BY 1, 3
)
SELECT week, min(week_start) AS week_start, exp(sum(ln(fpy))) AS rty, sum(ng_qty) AS ng_qty,
       max(input_qty) FILTER (WHERE station = 'Solder Paste Printing') AS units_started,
       sum(ng_qty) / max(input_qty) FILTER (WHERE station = 'Solder Paste Printing') AS ng_per_unit
FROM st GROUP BY 1 ORDER BY 1;

-- Q9: lonjakan dideteksi per stasiun per hari: robust z-score NG rate > 3,5
-- (median dan MAD per stasiun selama seluruh periode). Satu hari lonjakan = minimal satu stasiun melonjak.
CREATE OR REPLACE VIEW v_station_daily AS
WITH x AS (
    SELECT date, station, sum(input_qty) AS input_qty, sum(ng_qty) AS ng_qty, sum(ng_qty) / sum(input_qty) AS ng_rate
    FROM production_daily GROUP BY 1, 2
), m AS (SELECT station, median(ng_rate) AS med FROM x GROUP BY 1),
   s AS (SELECT station, median(abs(ng_rate - med)) * 1.4826 AS mad FROM x JOIN m USING (station) GROUP BY 1)
SELECT x.*, m.med, (x.ng_rate - m.med) / s.mad AS robust_z, (x.ng_rate - m.med) / s.mad > 3.5 AS is_spike
FROM x JOIN m USING (station) JOIN s USING (station) ORDER BY date, station;

CREATE OR REPLACE VIEW v_spike_days AS
SELECT date, count(*) FILTER (WHERE is_spike) AS stations_flagged,
       string_agg(station, '; ' ORDER BY station) FILTER (WHERE is_spike) AS stations,
       max(robust_z) AS max_z, bool_or(is_spike) AS is_spike
FROM v_station_daily GROUP BY 1 ORDER BY 1;

-- Q10: dari mana kelebihan NG pada hari lonjakan (dibanding rata-rata harian hari normal)
CREATE OR REPLACE VIEW v_spike_drill AS
WITH flag AS (SELECT date, is_spike FROM v_spike_days),
     n AS (SELECT count(*) FILTER (WHERE is_spike) AS n_spike, count(*) FILTER (WHERE NOT is_spike) AS n_norm FROM flag),
     long AS (
        SELECT 'station' AS dim, station AS value, date, qty FROM defect_log
        UNION ALL SELECT 'defect', defect_code, date, qty FROM defect_log
        UNION ALL SELECT 'model', model, date, qty FROM defect_log
        UNION ALL SELECT 'shift', shift, date, qty FROM defect_log
     ), agg AS (
        SELECT dim, value,
               sum(qty) FILTER (WHERE f.is_spike) / any_value(n.n_spike) AS per_day_spike,
               sum(qty) FILTER (WHERE NOT f.is_spike) / any_value(n.n_norm) AS per_day_normal
        FROM long JOIN flag f USING (date), n GROUP BY 1, 2
     )
SELECT dim, value, per_day_spike, per_day_normal, per_day_spike - per_day_normal AS excess_per_day,
       greatest(per_day_spike - per_day_normal, 0) / sum(greatest(per_day_spike - per_day_normal, 0)) OVER (PARTITION BY dim) AS share_of_excess  -- pangsa dari kelebihan positif
FROM agg ORDER BY dim, excess_per_day DESC;

-- Q11, Q12: skenario dampak untuk stasiun FPY terendah dan defect teratas (estimated)
CREATE OR REPLACE VIEW v_impact AS
WITH vol AS (
    SELECT station, avg(input_qty) AS monthly_input FROM (
        SELECT p.station, dt.month, sum(input_qty) AS input_qty
        FROM production_daily p JOIN dim_date dt USING (date)
        WHERE dt.month IN ('2026-03', '2026-04', '2026-05') GROUP BY 1, 2) GROUP BY 1
), tgt AS (
    SELECT 'station' AS target_type, station AS target, station, fpy, ng_qty / input_qty AS rate_old,
           scrap / (rework_ok + scrap) AS scrap_share,
           (SELECT sum(r.rework_min * r.rework_in) / sum(r.rework_in) FROM v_rework_defect r WHERE r.station = v.station) AS rework_min
    FROM v_station v WHERE fpy_rank = 1
    UNION ALL
    SELECT 'defect', p.defect_code, p.station, v.fpy, p.qty / v.input_qty,
           r.scrap / (r.rework_ok + r.scrap), r.rework_min
    FROM v_pareto_line p JOIN v_station v USING (station) JOIN v_rework_defect r USING (defect_code) WHERE p.rank = 1
), sc AS (SELECT unnest([0.10, 0.20, 0.30]) AS reduction)
SELECT t.target_type, t.target, t.station, sc.reduction, vol.monthly_input, t.rate_old,
       t.rate_old * (1 - sc.reduction) AS rate_new,
       (t.rate_old - t.rate_old * (1 - sc.reduction)) * vol.monthly_input AS units_saved_month,
       (t.rate_old - t.rate_old * (1 - sc.reduction)) * vol.monthly_input * t.scrap_share AS scrap_avoided_month,
       (t.rate_old - t.rate_old * (1 - sc.reduction)) * vol.monthly_input * t.rework_min / 60 AS rework_hours_saved_month,
       (SELECT rty FROM v_line_kpi) AS rty_old,
       (SELECT rty FROM v_line_kpi) / t.fpy * (t.fpy + t.rate_old * sc.reduction) AS rty_new
FROM tgt t JOIN vol USING (station), sc ORDER BY t.target_type DESC, sc.reduction;
