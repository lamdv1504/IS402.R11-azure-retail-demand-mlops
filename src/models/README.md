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

## HI04 — Huấn luyện và validation

Tạo môi trường ML riêng từ thư mục gốc repo (lần đầu), rồi chạy:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv-ml\Scripts\python.exe src/models/train.py
.\.venv-ml\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Cần các split và feature Parquet HI02/HI03 cùng log/schema tương ứng. Khi thiếu
file hoặc fingerprint không khớp, script dừng. XGBoost và baseline seasonal naive
được dự báo trên cùng 28 ngày validation CA_1/300 chuỗi. Cấu hình seed 42 và 16
feature nằm trong `train_config.json`; không đọc final holdout trong HI04.

Model native XGBoost và metadata nằm ở `artifacts/hi04/`, dự báo ở
`reports/hi04_validation_predictions.csv`, log ở `reports/hi04_training_log.json`.
`forecasting.py` cung cấp cùng đường suy luận direct cho validation và HI05;
lag_28/lag_56 không cần sales thực tế trong cửa sổ tương lai. HI05 tiếp tục
đánh giá RMSSE, chọn model và xử lý final holdout.

Xem [báo cáo huấn luyện HI04](../../reports/hi04_training.md).
