# Cleaning log

Dibuat otomatis oleh `code/1-data-preparation/python/02_clean_data.py`. Rincian per baris: `results/1-data-preparation/cleaning_log.csv`.

| Tabel | Masalah | Keputusan | Baris | Ditanam generator |
|---|---|---|---:|---:|
| defect_log | defect_code_typo | diperbaiki | 142 | 142 |
| production_daily | blank_shift | diperbaiki | 27 | 27 |
| production_daily | duplicate | dibuang | 35 | 35 |
| production_daily | negative_qty | diperbaiki | 22 | 22 |
| production_daily | ok_ng_over_input | diperbaiki | 28 | 28 |

Aturan keputusan:

- Baris ganda persis: dibuang, kemunculan pertama disimpan.
- Jumlah negatif: diperbaiki (tanda dibalik) jika OK + |NG| = input; selain itu dibuang.
- OK + NG > input: NG dicocokkan ke defect_log; jika sama, OK = input - NG; selain itu dibuang.
- Shift kosong: diisi dari operator_id karena setiap operator selalu bekerja di stasiun dan shift yang sama.
- Kode defect salah ketik: dinormalisasi (huruf besar, tanpa spasi, O menjadi 0, tanda hubung); kode yang tetap tidak dikenal dibuang.

Pemeriksaan konsistensi setelah cleaning (jumlah pelanggaran):

| Pemeriksaan | Pelanggaran |
|---|---:|
| ng_qty = jumlah defect_log per kunci | 0 |
| baris rework_log = qty defect_log per tanggal/stasiun/model/kode | 0 |
| rework date_out >= date_in | 0 |
| result kosong hanya jika date_out kosong | 0 |
| kunci production_daily unik | 0 |
| OK + NG = input | 0 |
