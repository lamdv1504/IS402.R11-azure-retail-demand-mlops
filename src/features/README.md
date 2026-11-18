# src/features

Feature Engineering — Hiếu (HI03).

Chạy từ thư mục gốc repo sau khi có Parquet H02 và đầu ra HI02:

```powershell
python -m pip install -r requirements-data.txt
python src/features/feature_engineering.py
python -m unittest discover -s tests -p "test_feature_engineering.py" -v
```

Script cần `data/processed/splits/train.parquet`, `validation.parquet`,
`reports/Hieu/hi02_split_log.json`, `data/raw/calendar.csv` và
`data/raw/sell_prices.csv`; dùng test Parquet khi HI02 có nhãn holdout.
Kết quả nằm ở `data/processed/features/` (Parquet được Git bỏ qua),
`reports/Hieu/hi03_feature_schema.json` và `reports/Hieu/hi03_feature_log.json`.

Đầu ra train có `sales` để huấn luyện; các file `*_future_features.parquet`
không có `sales`. Lag/rolling không tính từ nhãn tương lai: các giá trị cần
sales chưa biết ở validation/test được giữ `NaN`. HI04 cần chọn mô hình đệ quy
hoặc chỉ chọn các feature biết trước tại mốc dự báo. Xem chi tiết tại
[báo cáo HI03](../../reports/Hieu/hi03_feature_engineering.md).
