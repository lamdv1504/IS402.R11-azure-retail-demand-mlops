# L03 — Báo cáo API dự báo local, GĐ3 của Lâm

## Phạm vi và đầu vào

Thực hiện task L03 theo kế hoạch `Ke_hoach_M5_Azure_MLOps_14_ngay.xlsx`.
Đã có đủ model, feature order/schema, inference function, metadata và serving
context của Hiếu tại `artifacts/hi05/`; catalog Hùng ở
`reports/Hung/m5_mvp_items.csv`. Các fingerprint bàn giao đã được kiểm tra.

Nhánh triển khai: `feature/lam-gd3-model-api-integration`.

## Kết quả triển khai

- `POST /predict` dùng model XGBoost thật qua `ForecastPredictor` HI05.
- Nạp gói một lần mỗi worker trong startup lifespan; kiểm tra checksum,
  version, scope, feature order, metric và history/calendar trước khi báo ready.
- `GET /health` trả trạng thái model thực; `GET /model-info` trả metadata/metric HI05.
- Response có đúng item/store, model/data version, đủ số ngày liên tục,
  số thực hữu hạn không âm và tổng bằng tổng các giá trị ngày đã làm tròn.
- Input horizon là số nguyên 1–28, mặc định 28. Lỗi request/item/model/data
  được ánh xạ sang 422/404/503; lỗi inference ngoài dự kiến trả 500.

Model đang phục vụ: `hi05-xgboost-cb3a08fa5e82`, dữ liệu `m5-ca1-300-v1`.
Context có 56 ngày quan sát `d_1886...d_1941`; dự báo tiếp theo là
`d_1942...d_1969`, 23/05/2016–19/06/2016. API dùng lại feature/multi-step HI05,
không cần sales hoặc giá tương lai, không train lại model hoặc chấm lại holdout.

## Kiểm thử

**14 test HTTP/API L03 đều qua**, dùng model thật cho các dự báo hợp lệ:

| Trường hợp | Kết quả |
| --- | --- |
| Dự báo `CA_1 / FOODS_1_017` | 200, đủ 28 ngày, khớp forecast HI05 lưu sẵn |
| Horizon 1, 7, 28 và mặc định | 200, số phần tử đúng horizon |
| Store/item không thuộc MVP | 404 `ITEM_NOT_FOUND` |
| Horizon ngoài khoảng, bool, float, chuỗi; request sai kiểu/thiếu trường | 422 |
| History quá ngắn hoặc gãy ngày | 503 `FORECAST_DATA_NOT_READY` |
| Calendar tương lai thiếu ngày | 503 |
| Model chưa nạp được | Health 200/model_loaded false, inference và model-info 503 |
| Artifact sai checksum hoặc metadata lệch version | Không báo model ready |
| Output NaN, infinity, âm hoặc thiếu ngày | Không trả output lỗi cho người dùng |
| Request liên tiếp | Tái sử dụng cùng model đã nạp |
| CORS và Swagger | Preflight cho frontend local và tài liệu API hoạt động |

**37 test hồi quy HI02–HI05 và đường dẫn đều qua**. `pip check` không có
xung đột; source, model và dữ liệu HI05 được giữ nguyên checksum.

Đã khởi động Uvicorn thật bằng môi trường `.venv-ml`, working directory
`backend/`, trên cổng localhost tạm và gọi HTTP qua socket:

- Health/model-info: model ready, metadata trả 200.
- Catalog: đủ 300 sản phẩm.
- Predict: 200, 28 ngày, tổng dự báo **21,34 units** cho `FOODS_1_017`.
- Unknown item: 404; horizon 29: 422.
- Tiến trình kiểm thử đã được dừng sau khi hoàn tất.

JSON request/response thực tế và kết quả kiểm tra HTTP nằm ở các file
`l03_sample_request.json`, `l03_sample_response.json`, `l03_http_check.json`
trong cùng thư mục báo cáo này.

## Môi trường kiểm chứng

| Thư viện | Phiên bản |
| --- | --- |
| FastAPI | 0.163.2 |
| Pydantic | 2.14.3 |
| Uvicorn | 0.54.0 |
| HTTPX | 0.28.1 |
| NumPy | 2.4.6 |
| pandas | 3.1.1 |
| PyArrow | 26.0.1 |
| scikit-learn | 1.9.1 |
| XGBoost | 3.2.0 |

Lệnh chạy và tái kiểm thử: [hướng dẫn L03](../../docs/Lam/l03_run_local.md).
L05 có thể sử dụng API local hiện tại để kết nối frontend; Docker/Azure là
phạm vi tiếp theo của nhóm. Metric model vẫn chỉ trên subset CA_1/300 item;
training date là ước lượng từ mtime artifact HI04 như tài liệu HI05 đã nêu.
