# H04 benchmark và quy trình ETL M5

Thời điểm UTC: 2026-11-21T12:23:46.912541+00:00. Data version: `m5-ca1-300-v1`.

Đo local trên một cửa hàng CA_1, các scope lấy từ catalog MVP. Không đo toàn bộ 30.490 chuỗi.

## Điều kiện đo

Máy: Windows-11-10.0.26300-SP0; CPU: AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD; RAM 7.41 GiB.
Python 3.13.3; lặp 3 lần cho mỗi scope. Dữ liệu tạm nằm trên volume `C:\`.
Cache hệ điều hành không được xóa; thứ tự đọc CSV/Parquet đổi theo seed cố định. Đây không phải phép đo cold cache.
RSS là RAM của toàn tiến trình, lấy mẫu mỗi 20 ms; có thể bỏ lỡ đỉnh ngắn và không phải RAM tăng riêng của từng bước.

## Thời gian các bước

| Item | Bước | Lặp | Trung bình s | Trung vị s | Min s | Max s | RSS đỉnh mẫu MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | downcast | 3 | 0.286172 | 0.292217 | 0.272399 | 0.293899 | 294.41 |
| 100 | join_calendar | 3 | 0.139693 | 0.139904 | 0.121572 | 0.157604 | 270.85 |
| 100 | join_prices | 3 | 0.198052 | 0.206542 | 0.177129 | 0.210485 | 287.70 |
| 100 | melt | 3 | 1.068017 | 1.056214 | 1.021282 | 1.126554 | 239.70 |
| 100 | read_calendar | 3 | 0.007495 | 0.005612 | 0.002798 | 0.014075 | 237.34 |
| 100 | read_long_mvp_csv | 3 | 0.192553 | 0.185046 | 0.180716 | 0.211898 | 379.87 |
| 100 | read_mvp_parquet | 3 | 0.024035 | 0.022015 | 0.020450 | 0.029642 | 318.11 |
| 100 | read_wide_mvp_csv | 3 | 0.038643 | 0.036462 | 0.035155 | 0.044313 | 322.83 |
| 100 | scan_prices_raw | 3 | 1.545525 | 1.513013 | 1.507629 | 1.615932 | 272.61 |
| 100 | scan_sales_raw | 3 | 4.610577 | 4.706697 | 4.410080 | 4.714956 | 366.20 |
| 100 | write_long_csv | 3 | 1.218830 | 1.171800 | 1.170462 | 1.314227 | 317.94 |
| 100 | write_parquet | 3 | 0.128912 | 0.118638 | 0.113707 | 0.154392 | 316.42 |
| 100 | write_wide_csv | 3 | 0.096653 | 0.088498 | 0.078989 | 0.122473 | 318.04 |
| 300 | downcast | 3 | 0.616989 | 0.623828 | 0.572801 | 0.654337 | 444.86 |
| 300 | join_calendar | 3 | 0.350414 | 0.320242 | 0.314473 | 0.416527 | 388.64 |
| 300 | join_prices | 3 | 0.301784 | 0.290059 | 0.284816 | 0.330479 | 399.61 |
| 300 | melt | 3 | 1.117721 | 1.136619 | 1.052463 | 1.164081 | 260.58 |
| 300 | read_calendar | 3 | 0.003662 | 0.003378 | 0.003306 | 0.004302 | 254.02 |
| 300 | read_long_mvp_csv | 3 | 0.603649 | 0.573114 | 0.562100 | 0.675732 | 667.38 |
| 300 | read_mvp_parquet | 3 | 0.095807 | 0.074058 | 0.067707 | 0.145654 | 477.21 |
| 300 | read_wide_mvp_csv | 3 | 0.054765 | 0.057521 | 0.046167 | 0.060607 | 489.27 |
| 300 | scan_prices_raw | 3 | 1.637380 | 1.719696 | 1.461788 | 1.730656 | 295.03 |
| 300 | scan_sales_raw | 3 | 4.530902 | 4.526197 | 4.338191 | 4.728319 | 496.37 |
| 300 | write_long_csv | 3 | 3.641329 | 3.686693 | 3.544402 | 3.692892 | 477.12 |
| 300 | write_parquet | 3 | 0.361614 | 0.356334 | 0.351673 | 0.376836 | 476.65 |
| 300 | write_wide_csv | 3 | 0.239451 | 0.238637 | 0.237429 | 0.242287 | 477.21 |

## Dung lượng và đối chiếu cùng scope

| Item | Dòng long | Wide CSV byte | Long CSV byte | Parquet byte | Long CSV / Parquet |
| --- | --- | --- | --- | --- | --- |
| 100 | 194100 | 411676 | 25186446 | 226734 | 111.08 |
| 300 | 582300 | 1214383 | 75568422 | 620521 | 121.78 |

Mỗi scope giữ cùng item và toàn bộ khoảng ngày. Long CSV và Parquet có cùng 22 cột, được kiểm tra giá trị với H02 (dung sai float 1e-5).
Wide CSV chỉ gồm sales/định danh; Parquet có thêm lịch/giá. Không dùng wide/full raw so với Parquet MVP để kết luận hiệu quả nén.
`scan_sales_raw` và `scan_prices_raw` đọc raw đầy đủ theo chunk rồi lọc scope; các bước `read_*_mvp_*` chỉ đọc file tạm của chính scope đó.

## Nhận xét từ số đo

- 100 item: tỷ lệ thời gian đọc long CSV/Parquet = 8.01; tổng thời gian trung bình của các bước ETL được đo = 7.984 s.
- 300 item: tỷ lệ thời gian đọc long CSV/Parquet = 6.30; tổng thời gian trung bình của các bước ETL được đo = 8.920 s.

Tỷ lệ trên chỉ áp dụng máy, cache và mẫu đang đo; không ngoại suy sang toàn M5. Scope lớn hơn MVP chưa được đo.

## Azure Blob

Trạng thái: `not_run`.
Chưa đo upload/download Azure trong lượt local; không có số thời gian cloud để báo cáo.

## ETL và chạy lại

Raw sales → lọc store/item → melt → join calendar → join giá → downcast → Parquet → Blob có data version.
H04 dùng lại hàm đọc/filter H02; mọi file benchmark ở thư mục tạm, giữ nguyên raw, Parquet và log bàn giao H02/HI05.
Cài `requirements-benchmark.txt`, chạy từ repo: `python src/data/benchmark.py --sizes 100 300 --repeats 3`.
Sau khi cấu hình quyền Blob theo hướng dẫn H03, thêm `--azure` để đo upload/download; xác thực Portal không tự cấp phiên SDK local.
Khi chạy lại, dùng `--output-dir reports/Hung/h04-rerun-01` để không ghi đè báo cáo cũ. Giữ JSON, data version và source hash cùng training run.
Số liệu gốc: [h04_benchmark_log.json](h04_benchmark_log.json); bảng tổng hợp: [h04_benchmark.csv](h04_benchmark.csv).
H04 chỉ nghiệm thu đầy đủ khi có số đo Azure thật; phần local không thay thế benchmark Blob.
