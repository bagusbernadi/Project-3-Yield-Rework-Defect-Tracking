# Definisi KPI dan alur rework

Satu unit = satu produk (smartphone). Setiap stasiun menerima `input_qty`, memeriksa hasilnya, dan memisahkan `ok_first_pass` (lolos percobaan pertama) dari `ng_qty` (NG). Unit NG masuk rework, diperbaiki dan diuji ulang paling banyak satu kali: hasilnya `OK` (kembali ke stasiun berikutnya) atau `Scrap` (dibuang). Unit yang belum selesai di akhir periode berstatus kosong (masih menunggu).

| KPI | Rumus | Dihitung di |
|---|---|---|
| FPY stasiun | `ok_first_pass / input_qty` | `v_station` |
| RTY lini | hasil kali FPY 10 stasiun | `v_line_kpi` |
| Final yield stasiun | `(ok_first_pass + rework OK dari stasiun itu) / input_qty` | `v_station` |
| Final yield lini | hasil kali final yield stasiun | `v_line_kpi` |
| Rework rate | unit NG / input stasiun pertama (unit NG per unit yang dimulai, bisa lebih dari satu per unit) | `v_line_kpi` |
| Scrap rate | unit scrap / input stasiun pertama | `v_line_kpi` |
| Recovery rate | `rework OK / (rework OK + scrap)`; unit yang masih menunggu tidak dihitung | `v_line_kpi`, `v_rework_defect` |
| Lead time rework | selisih urutan hari kerja `date_out - date_in` | `v_rework_lead` |
| Antrean rework | kumulatif (masuk - selesai) di akhir hari | `v_backlog_daily` |

Catatan penting:

- Produk yang lolos setelah rework tetap dihitung di final yield, tetapi tidak di FPY. Pemisahan ini membuat biaya rework terlihat.
- Unit hasil rework yang lolos masuk ke input stasiun berikutnya pada hari berikutnya (lihat `01_generate_data.py`), sehingga `input_qty` stasiun hilir sedikit lebih besar dari OK stasiun hulu. RTY memakai FPY per stasiun, tidak memakai input stasiun pertama sebagai penyebut tunggal.
- `station_origin` di `rework_log` adalah stasiun tempat defect terjadi, bukan tempat ditemukan.
- Lonjakan: pada satu stasiun dan satu hari, NG rate dengan robust z-score > 3,5 (median dan MAD per stasiun selama seluruh periode). Satu hari lonjakan = minimal satu stasiun melonjak. Deteksi di level lini tidak dipakai karena variasi harian lini menutupi lonjakan satu stasiun.
- Skenario dampak (`v_impact`): unit terselamatkan per bulan = (rate lama - rate baru) x input bulanan rata-rata (Maret sampai Mei 2026). Jam rework dihemat = unit x menit rework per unit (asumsi di `dim_defect.rework_min`). Semua berlabel `estimated`.
