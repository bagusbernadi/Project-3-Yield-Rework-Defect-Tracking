-- Langkah 5: memuat data bersih (data/clean/) ke DuckDB. Jalur relatif terhadap folder project/.
INSERT INTO dim_station
SELECT station, seq FROM read_csv('data/reference/dim_station.csv', header = true);

INSERT INTO dim_defect
SELECT * FROM read_csv('data/reference/dim_defect.csv', header = true);

INSERT INTO dim_date
SELECT date,
       row_number() OVER (ORDER BY date) AS work_day,
       (row_number() OVER (ORDER BY date) - 1) // 5 + 1 AS week,
       strftime(date, '%Y-%m') AS month
FROM (SELECT DISTINCT CAST(date AS DATE) AS date FROM read_csv('data/clean/production_daily.csv', header = true));

INSERT INTO production_daily
SELECT CAST(date AS DATE), shift, station, model, operator_id, input_qty, ok_first_pass, ng_qty
FROM read_csv('data/clean/production_daily.csv', header = true);

INSERT INTO defect_log
SELECT CAST(date AS DATE), shift, station, model, defect_code, qty
FROM read_csv('data/clean/defect_log.csv', header = true);

INSERT INTO rework_log
SELECT rework_id, CAST(date_in AS DATE), CAST(date_out AS DATE), station_origin, model, defect_code, result
FROM read_csv('data/clean/rework_log.csv', header = true, types = {'date_out': 'DATE', 'result': 'VARCHAR'});
