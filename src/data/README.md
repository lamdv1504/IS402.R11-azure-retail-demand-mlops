# src/data

Xử lý dữ liệu và ETL của Hùng.

- H01: `profile_m5.py` khảo sát raw và chọn danh sách MVP.
- H02: `preprocessing.py` tạo Parquet và log chất lượng dữ liệu.
- H03: `upload_blob.py` lập danh sách local, kiểm tra Blob đã có hoặc upload file còn thiếu.
- H04: `benchmark.py` đo lặp ETL/CSV/Parquet cùng scope, RAM và Blob khi có xác thực.

H03 đọc cấu hình không chứa secret từ `blob_config.json`; cài dependency bằng
`python -m pip install -r requirements-storage.txt` từ gốc repo. Chế độ mặc định
`plan` chỉ kiểm tra local. Với dữ liệu đã upload, dùng `--mode verify` sau khi
xác thực trên máy. Không ghi đè Blob có sẵn.

[Hướng dẫn và URI bàn giao H03](../../docs/Hung/h03_blob_handoff.md).

[Hướng dẫn benchmark và ETL H04](../../docs/Hung/h04_benchmark_etl.md).
