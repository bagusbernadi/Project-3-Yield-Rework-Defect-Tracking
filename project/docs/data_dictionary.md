# Kamus data

Empat tabel utama, dua tabel referensi. Kunci utama dan hubungan dijaga oleh constraint di `code/1-data-preparation/sql/01_schema.sql`.

```
dim_station (station PK, seq)
dim_date (date PK, work_day, week, month)
dim_defect (defect_code PK, defect_name, station FK, category, rework_min)
production_daily (date, shift, station, model PK; operator_id, input_qty, ok_first_pass, ng_qty)
defect_log (date, shift, station, model, defect_code PK; qty)   FK -> production_daily, dim_defect
rework_log (rework_id PK; date_in, date_out, station_origin, model, defect_code, result)
```

| Tabel | 1 baris = | Kolom |
|---|---|---|
| `production_daily` | hasil satu stasiun, satu model, satu shift, satu hari | `date`, `shift` (Shift 1/Shift 2), `station`, `model` (Basic/Plus/Pro), `operator_id`, `input_qty`, `ok_first_pass`, `ng_qty`. Aturan: `ok_first_pass + ng_qty = input_qty`, semua >= 0 |
| `defect_log` | jumlah satu jenis defect di satu stasiun, model, shift, hari | `date`, `shift`, `station`, `model`, `defect_code`, `qty` (> 0). Jumlah `qty` per kunci = `ng_qty` |
| `rework_log` | satu unit NG yang masuk rework | `rework_id`, `date_in`, `date_out` (kosong = masih menunggu), `station_origin`, `model`, `defect_code`, `result` (OK/Scrap, kosong jika `date_out` kosong) |
| `dim_defect` | satu kode defect | `defect_code` (format AAA-00), `defect_name`, `station`, `category`, `rework_min` (asumsi menit rework per unit) |
| `dim_station` | satu stasiun | `station`, `seq` (urutan 1 sampai 10) |
| `dim_date` | satu hari kerja | `date`, `work_day` (urutan), `week` (blok 5 hari kerja), `month` |

`rework_log` tidak punya kolom `shift`, sehingga filter shift di dashboard tidak berlaku untuk rework. Jumlah baris `rework_log` sama dengan jumlah `qty` di `defect_log` (dicek di `02_clean_data.py`).
