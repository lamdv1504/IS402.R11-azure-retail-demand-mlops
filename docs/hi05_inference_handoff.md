# HI05 — Bàn giao inference cho Lâm và Quân

HI05 thuộc GĐ3. Gói local nằm ở `artifacts/hi05/`; dùng Python 3.13 và
`requirements-ml.txt`. Danh sách phiên bản đã chạy nằm trong
`reports/hi05_evaluation_log.json`. Chạy lệnh từ thư mục gốc repository.

## Chạy dự báo có sẵn

```powershell
.\.venv-ml\Scripts\python.exe src/models/predict.py --item-id FOODS_1_017
```

Nếu máy chưa có môi trường ML:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
```

Gói đã có lịch sử 56 ngày cuối (`d_1886...d_1941`, 16.800 dòng) và lịch
28 ngày tiếp theo (`d_1942...d_1969`). Đây là dữ liệu M5 lịch sử, nên ngày
dự báo là **23/05/2016 đến 19/06/2016**, không phải ngày hiện tại.
Không cần toàn bộ CSV M5 hoặc kết nối Azure để chạy gói local này.

## Tích hợp L03

Load predictor một lần khi FastAPI khởi động, rồi truyền lịch sử và calendar:

```python
from pathlib import Path
import pandas as pd
from src.models.predict import ForecastPredictor

bundle = Path("artifacts/hi05")
predictor = ForecastPredictor(bundle)
history = pd.read_parquet(bundle / "inference_history.parquet")
calendar = pd.read_csv(bundle / "future_calendar.csv")

response = predictor.predict(
    store_id="CA_1", item_id="FOODS_1_017", horizon=28,
    history=history, calendar=calendar,
)
```

Response khớp `PredictionResponse` trong `docs/api_contract.json`, gồm model/data
version, metadata sản phẩm và đúng `horizon` ngày. Ví dụ thực tế nằm ở
`reports/hi05_sample_request.json` và `reports/hi05_sample_response.json`.
`artifacts/hi05/model_info.json` là payload tham khảo cho `/model-info`.
Thời điểm training trong payload được ước lượng bằng mtime artifact HI04;
log HI04 chưa ghi thời điểm fit. Nguồn thời gian được ghi trong metadata.

L03 cần ánh xạ lỗi sang API hiện tại:

| Trường hợp | Lỗi predictor | HTTP L03 |
| --- | --- | --- |
| Store/item ngoài phạm vi | `KeyError` | 404 |
| Horizon ngoài 1–28, không phải số nguyên | `ValueError` | 400 hoặc validation 422 |
| Thiếu ngày lịch, lịch sử ngắn/đứt đoạn | `ValueError` | 503, kèm lý do dữ liệu |
| Thiếu artifact, sai checksum khi startup | `FileNotFoundError` / `ValueError` | model chưa sẵn sàng, 503 |

HI05 cung cấp hàm inference và gói bàn giao. Việc nối predictor vào route FastAPI
và kiểm thử HTTP thuộc L03 của Lâm.

## Dữ liệu và feature cần giữ nhất quán

- Mỗi chuỗi cần ít nhất 56 ngày liên tục, kết thúc ở cùng origin khi dự báo batch.
- History có `sales` thực tế; future/calendar không được có `sales`.
- Đầu vào history theo schema H02/HI02: `item_id`, `store_id`, `dept_id`, `cat_id`,
  `state_id`, `d`, `day_number`, `date`, `wm_yr_wk`, `sell_price`, các cột lịch/sự kiện/SNAP.
  Có thể dùng trực tiếp schema của `inference_history.parquet`.
- Calendar cần các cột `CALENDAR_COLUMNS` và `wm_yr_wk` trong HI03. Ngày phải khớp
  `d` và tiếp nối ngay sau history. `make_future` dựng future từ calendar và metadata.
- Predictor dùng lại `forecast_direct` HI04 và `build_features` HI03, cùng thứ tự
  16 feature và vocabulary đã fit trên train. Chỉ chọn lag_28, lag_56, lịch và
  mã phân loại; không cần giá tương lai hoặc sales tương lai.
- Giữ số thực không âm khi tính metric. Response làm tròn từng ngày 2 chữ số;
  tổng bằng tổng các giá trị ngày đã làm tròn.
- Gói xác minh SHA-256 các file được liệt kê trong `model_metadata.json` trước khi load.
  Khi cập nhật lịch sử/calendar, cần tạo gói có phiên bản và manifest tương ứng.

## Artifact và đánh giá

`best_model.ubj` là định dạng XGBoost native, giữ được thông tin categorical.
`ForecastPredictor` cũng hỗ trợ seasonal naive nếu baseline được chọn; trường hợp
đó artifact là `best_model.json`. Không dùng pickle/joblib cho model XGBoost.

`selection.json` khóa lựa chọn bằng **validation Subset RMSSE** trước khi đọc
holdout. Model giữ nguyên trọng số từ HI04, không refit sau chọn. Holdout dùng
lịch sử quan sát đến `d_1913`; forecast production dùng lịch sử đến `d_1941`.
Các nhãn holdout chỉ được dùng làm lịch sử production sau khi đã chấm điểm.

`metrics.json` lưu RMSSE/Subset WRMSSE/MAE/RMSE; các bảng dự báo và metric từng
chuỗi ở `reports/hi05_*.csv`. Subset WRMSSE ở đây chỉ có 300 chuỗi item–store,
trọng số doanh thu 28 ngày trước origin; chưa tổng hợp 12 cấp của toàn cuộc thi.
Không diễn giải kết quả là WRMSSE M5 đầy đủ.

## Tái tạo đánh giá

```powershell
.\.venv-ml\Scripts\python.exe src/models/evaluate.py
.\.venv-ml\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Lệnh evaluate yêu cầu split/log HI02, gói/log HI04 và calendar gốc. Nó kiểm tra
file/checksum, dừng khi thiếu bàn giao. Các Parquet lớn HI02/HI03 không nằm trong
Git và phải được tái tạo theo hướng dẫn của các task đó.

Lệnh đánh giá dừng nếu `artifacts/hi05/` đã có nội dung để tránh ghi đè kết quả
holdout. Dùng báo cáo đã lưu cho quá trình tích hợp. Chỉ chạy đánh giá mới trong
một thư mục riêng khi có mục đích nghiên cứu rõ ràng; không chọn/tune lại bằng
điểm holdout đã xem.

Tham chiếu công thức: [M5 Competitors Guide, phần đánh giá](https://storage.googleapis.com/kaggle-forum-message-attachments/772349/15032/M5-Competitors-Guide-Final-10-March-2020.pdf).
Scale RMSSE bỏ các số 0 trước lần bán đầu tiên. Nếu scale bằng 0/không xác định,
script dừng và báo lỗi; không tự thêm epsilon hoặc loại chuỗi khỏi trung bình.
