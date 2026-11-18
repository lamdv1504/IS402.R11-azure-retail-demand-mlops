# src/models

Huấn luyện và dự báo Machine Learning — Hiếu.

HI02 chia dữ liệu theo thời gian, không shuffle:

```powershell
python -m pip install -r requirements-data.txt
python src/models/split_data.py
python -m unittest discover -s tests -p "test_split_data.py" -v
```

Chạy từ thư mục gốc repo. Cần Parquet H02, `data/raw/calendar.csv` và
`reports/m5_mvp_items.csv`. Script dừng khi thiếu đầu vào, không tạo dữ liệu giả.
Cấu hình nằm ở `src/models/split_config.json`; kết quả Parquet nằm trong
`data/processed/splits/` (được Git bỏ qua). Log và mapping được lưu tại
`reports/hi02_split_log.json` và `reports/hi02_day_mapping.csv`.

HI03/HI04 có thể nhập `prepare_data`, `split_data` và `make_backtest_context`
từ `src.models.split_data`. Lịch sử validation chỉ đến `d_1885`; lịch sử test
đến `d_1913` chỉ được dùng sau khi chọn model. `context.future` không có `sales`,
còn `context.labels` dành riêng cho chấm điểm. Không tính lag/rolling trên toàn
bộ dữ liệu có nhãn trước khi tách backtest.

Xem [báo cáo và quy tắc bàn giao HI02](../../reports/hi02_split.md).
