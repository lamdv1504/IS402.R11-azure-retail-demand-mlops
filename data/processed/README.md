# data/processed

Dữ liệu M5 đã xử lý cho H02 được tạo bằng lệnh `python src/data/preprocessing.py` từ thư mục gốc repo. Cài thư viện bằng `python -m pip install -r requirements-data.txt` trước khi chạy.

File đầu ra là `m5_sales_processed.parquet`. File Parquet được bỏ qua trong Git vì có thể tạo lại từ 5 CSV gốc và danh sách MVP trong `reports/Hung/m5_mvp_items.csv`. Xem `reports/Hung/h02_processing.md` và `reports/Hung/h02_processing_log.json` để biết phạm vi, schema và kết quả kiểm tra.
