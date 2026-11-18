# Huấn luyện M5 — HI04 (Hiếu)

## Đầu vào và phạm vi

Đã nhận đủ dữ liệu H02 của Hùng và đầu ra HI02/HI03: split train/validation,
feature Parquet, feature schema/vocabulary và log bàn giao. Script đối chiếu
SHA-256 Parquet với log; thiếu file hoặc không khớp thì dừng trước khi fit.
HI04 chạy local, không cần Azure Compute hoặc model của thành viên khác.

| Tập | Ngày | Số dòng | Chuỗi |
| --- | --- | ---: | ---: |
| Lịch sử train | d_1–d_1885, 2011-01-29–2016-03-27 | 565.500 | 300 |
| Dòng dùng fit sau warmup | d_57–d_1885 | 548.700 | 300 |
| Validation 28 ngày | d_1886–d_1913, 2016-03-28–2016-04-24 | 8.400 | 300 |

Tất cả chuỗi thuộc CA_1. Giữ các ngày sales bằng 0; chỉ bỏ 16.800 dòng đầu
chuỗi chưa có đủ lag_56. Final holdout d_1914–d_1941 không được đọc, fit,
dự báo hoặc chấm điểm trong HI04. Phần chọn model cuối và đánh giá holdout
thuộc HI05.

## Chiến lược và mô hình

Seasonal naive lặp lại 7 ngày cuối trước origin cho cả 4 tuần validation.
Ở tuần thứ hai trở đi, baseline vẫn dùng tuần đã quan sát trước origin,
không đọc sales thật của tuần đầu validation để tạo lag_7.

Model ứng viên là XGBoost `count:poisson`, CPU histogram, 300 cây, độ sâu 6,
learning rate 0,05, seed 42, 4 luồng. Tham số đầy đủ nằm trong
`src/models/train_config.json`; không tuning bằng holdout.

Model dùng 16 feature từ HI03: `lag_28`, `lag_56`, `wday`, `month`, `year`,
`snap_state` và 10 mã phân loại metadata/lịch. Các mã được chuyển thành
native categorical với đúng vocabulary train; mã chưa biết `-1` thành missing.
Giá future, `is_active`, lag ngắn và rolling shift(1) không được chọn vào
model này. Dự báo trực tiếp cho ngày T+h (h=1..28) chỉ cần sales T+h−28 và
T+h−56, đều không vượt qua origin T. Lịch/sự kiện/SNAP phải được cung cấp
cho 28 ngày dự báo.

Validation dùng `predict_direct` trên feature HI03. Hàm `forecast_direct`
tái tạo feature từ history và future không có sales, rồi gọi lại cùng
`predict_direct`. Lần chạy thật đã xác nhận hai đường trả cùng dự báo.
Sales nhãn chỉ được ghép sau khi đã có dự báo để tính MAE/RMSE.
Đầu ra là float units không âm; clip ở 0 và không làm tròn số nguyên.

## Kết quả validation

| Phương pháp | MAE (units) | RMSE (units) |
| --- | ---: | ---: |
| Seasonal naive | 1,264524 | 2,724754 |
| XGBoost ứng viên | 1,030182 | 2,027791 |

Đây là kết quả trên cùng 8.400 điểm item-store-day của MVP CA_1/300 sản phẩm,
không đại diện toàn bộ M5. HI04 mới so sánh MAE/RMSE; chưa tính hay tuyên bố
RMSSE/WRMSSE toàn cuộc thi. HI05 tiếp tục metric theo chuỗi, chọn model và
đánh giá holdout theo kế hoạch.

## Sản phẩm bàn giao

| File | Nội dung |
| --- | --- |
| `src/models/train.py` | Lệnh huấn luyện và xuất kết quả HI04 |
| `src/models/forecasting.py` | Baseline và suy luận direct dùng chung |
| `src/models/train_config.json` | Seed, thứ tự feature, tham số, horizon 28 |
| `artifacts/hi04/xgboost.ubj` | Model ứng viên đã fit |
| `artifacts/hi04/feature_order.json` | Thứ tự chính xác 16 feature |
| `artifacts/hi04/feature_schema.json` | Schema/vocabulary train HI03 |
| `artifacts/hi04/training_config.json` | Snapshot cấu hình lần chạy |
| `artifacts/hi04/model_metadata.json` | Phiên bản dựa theo hash model, data version, phạm vi, cửa sổ |
| `reports/Hieu/hi04_validation_predictions.csv` | 8.400 dòng gồm khóa, ngày, actual, seasonal naive và XGBoost |
| `reports/Hieu/hi04_training_log.json` | Fingerprint input/source/artifact, thư viện, thời gian fit, checks và metrics |

Model dùng định dạng native UBJSON để giữ thông tin phân loại theo
[hướng dẫn XGBoost](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).
Khi bàn giao cần giữ cả model, feature order và vocabulary cùng phiên bản.
Model không tự chứa dữ liệu lịch sử item-store; suy luận cần tối thiểu 56
ngày lịch sử liên tiếp, cùng lịch của cửa sổ tương lai và metadata H02.

## Chạy lại và nạp model

Đã chạy bằng Python 3.13.3 trong `.venv-ml`; phiên bản thư viện cụ thể được
ghi trong training log. Môi trường riêng tránh thay đổi Python hiện tại của nhóm.

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv-ml\Scripts\python.exe src/models/train.py
.\.venv-ml\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Chạy từ thư mục gốc repo. Parquet HI02/HI03 là dữ liệu sinh lại được Git bỏ
qua; cần nhận H02 từ Hùng và chạy hai bước trước nếu máy chưa có các file này.
Các tham số đường dẫn có trong `python src/models/train.py --help`.

Ví dụ kiểm tra inference validation bằng model đã lưu:

```python
import json
import pandas as pd
from xgboost import XGBRegressor
from src.models.forecasting import forecast_direct

model = XGBRegressor(n_jobs=4, enable_categorical=True)
model.load_model("artifacts/hi04/xgboost.ubj")
with open("artifacts/hi04/feature_order.json", encoding="utf-8") as source:
    order = json.load(source)
with open("artifacts/hi04/feature_schema.json", encoding="utf-8") as source:
    schema = json.load(source)
history = pd.read_parquet("data/processed/splits/train.parquet")
future = pd.read_parquet("data/processed/splits/validation.parquet").drop(columns="sales")
predictions = forecast_direct(model, history, future, order, schema)
```

## Kiểm tra đã thực hiện

- 25 kiểm thử HI02/HI03/HI04 đều đạt trong môi trường ML; dependency check đạt.
- 9 kiểm thử HI04 kiểm tra baseline lặp tuần đúng, thứ tự/loại feature,
  từ chối nhãn future và lịch thiếu, xử lý category chưa biết, clip dự báo,
  MAE/RMSE và dừng khi thiếu bàn giao.
- Integration test tạo model nhỏ, lưu/nạp lại, xuất đủ horizon và chặn mọi
  thao tác đọc `test.parquet`.
- Lần huấn luyện thật xác nhận đủ 28 ngày cho mỗi chuỗi, dự báo hữu hạn/không
  âm, native model nạp lại có dự báo giống hệt và inference từ dữ liệu gốc
  khớp với feature validation HI03.
