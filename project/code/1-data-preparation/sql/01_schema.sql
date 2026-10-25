-- Langkah 5: struktur tabel dengan aturan pengecekan agar data salah tidak bisa masuk.
-- Dijalankan dari folder project/ oleh 03_build_db.py.
DROP TABLE IF EXISTS rework_log;
DROP TABLE IF EXISTS defect_log;
DROP TABLE IF EXISTS production_daily;
DROP TABLE IF EXISTS dim_defect;
DROP TABLE IF EXISTS dim_station;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_station (
    station      VARCHAR PRIMARY KEY,
    seq          INTEGER NOT NULL UNIQUE CHECK (seq BETWEEN 1 AND 10)
);

CREATE TABLE dim_defect (
    defect_code  VARCHAR PRIMARY KEY CHECK (regexp_full_match(defect_code, '[A-Z]{3}-[0-9]{2}')),
    defect_name  VARCHAR NOT NULL,
    station      VARCHAR NOT NULL REFERENCES dim_station (station),
    category     VARCHAR NOT NULL,
    rework_min   INTEGER NOT NULL CHECK (rework_min > 0)      -- asumsi waktu rework per unit (estimated)
);

CREATE TABLE dim_date (
    date         DATE PRIMARY KEY,
    work_day     INTEGER NOT NULL UNIQUE,                     -- urutan hari kerja, dipakai untuk lead time
    week         INTEGER NOT NULL,
    month        VARCHAR NOT NULL
);

CREATE TABLE production_daily (
    date          DATE NOT NULL REFERENCES dim_date (date),
    shift         VARCHAR NOT NULL CHECK (shift IN ('Shift 1', 'Shift 2')),
    station       VARCHAR NOT NULL REFERENCES dim_station (station),
    model         VARCHAR NOT NULL CHECK (model IN ('Basic', 'Plus', 'Pro')),
    operator_id   VARCHAR NOT NULL,
    input_qty     INTEGER NOT NULL CHECK (input_qty >= 0),
    ok_first_pass INTEGER NOT NULL CHECK (ok_first_pass >= 0),
    ng_qty        INTEGER NOT NULL CHECK (ng_qty >= 0),
    CHECK (ok_first_pass + ng_qty = input_qty),
    PRIMARY KEY (date, shift, station, model)
);

CREATE TABLE defect_log (
    date         DATE NOT NULL,
    shift        VARCHAR NOT NULL,
    station      VARCHAR NOT NULL,
    model        VARCHAR NOT NULL,
    defect_code  VARCHAR NOT NULL REFERENCES dim_defect (defect_code),
    qty          INTEGER NOT NULL CHECK (qty > 0),
    PRIMARY KEY (date, shift, station, model, defect_code),
    FOREIGN KEY (date, shift, station, model) REFERENCES production_daily (date, shift, station, model)
);

CREATE TABLE rework_log (
    rework_id      VARCHAR PRIMARY KEY,
    date_in        DATE NOT NULL REFERENCES dim_date (date),
    date_out       DATE REFERENCES dim_date (date),           -- kosong = masih di antrean
    station_origin VARCHAR NOT NULL REFERENCES dim_station (station),
    model          VARCHAR NOT NULL,
    defect_code    VARCHAR NOT NULL REFERENCES dim_defect (defect_code),
    result         VARCHAR CHECK (result IN ('OK', 'Scrap')),
    CHECK (date_out IS NULL OR date_out >= date_in),
    CHECK ((result IS NULL) = (date_out IS NULL))
);
