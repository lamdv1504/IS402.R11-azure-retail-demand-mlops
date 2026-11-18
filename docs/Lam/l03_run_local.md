# GĐ3 — L03: API dự báo dùng model thật

L03 thuộc phần của Lâm trong kế hoạch. Đầu vào đã nhận từ Hiếu/Hùng:
gói HI05 tại `artifacts/hi05/`, hàm `src/models/predict.py`, danh sách
300 sản phẩm tại `reports/Hung/m5_mvp_items.csv` và
[hướng dẫn inference HI05](../Hieu/hi05_inference_handoff.md).

## Cài và chạy

Từ thư mục gốc repository, tạo môi trường một lần nếu chưa có:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Nếu đang ở `backend/`, chạy:

```powershell
..\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000/docs để dùng Swagger. `/health` phải có
`model_loaded: true`; `/model-info` phải trả phiên bản và metric từ HI05.
Không cần toàn bộ M5 CSV hoặc Azure cho `/predict`. Endpoint `/dashboard`
vẫn cần `data/processed/m5_sales_processed.parquet` để tổng hợp lịch sử.

## Gọi dự báo

Mở terminal thứ hai:

```powershell
$body = @{
    store_id = 'CA_1'
    item_id = 'FOODS_1_017'
    horizon = 28
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/predict' -ContentType 'application/json' -Body $body
```

Đây là dự báo từ dữ liệu M5 lịch sử: 28 ngày từ **23/05/2016 đến 19/06/2016**.
Với gói hiện tại, model là `hi05-xgboost-cb3a08fa5e82`, data version
`m5-ca1-300-v1`. Không truyền horizon thì mặc định 28; hỗ trợ số nguyên 1–28.
Response theo [API contract chung](../api_contract.json): metadata sản phẩm,
model/data version, ngày bắt đầu, số ngày và mảng `forecast`.
Giữ số thực không âm; mỗi ngày làm tròn 2 chữ số, tổng bằng tổng các ngày hiển thị.

## Nạp model và xử lý lỗi

Backend dùng lifespan để nạp model một lần mỗi worker, kiểm tra checksum cùng
version, scope, feature order và metric. History gồm 56 ngày quan sát cuối;
future calendar không có sales. API gọi đúng predictor HI05 và feature/multi-step
HI03–HI04, không fit lại model hoặc chấm lại holdout.

| Trường hợp | HTTP | Kết quả |
| --- | --- | --- |
| Item/store hợp lệ, đủ dữ liệu | 200 | Đúng horizon ngày từ model thật |
| Store/item không thuộc MVP/model | 404 | `ITEM_NOT_FOUND` |
| Horizon ngoài 1–28, boolean, số thập phân, chuỗi hoặc thiếu trường bắt buộc | 422 | Validation `detail[]` |
| Model/gói inference chưa nạp được | 503 | `MODEL_NOT_READY` |
| History thiếu ngày, không đủ lịch sử, calendar thiếu hoặc output không hợp lệ | 503 | `FORECAST_DATA_NOT_READY` |
| Catalog MVP chưa có | 503 | `CATALOG_NOT_READY` |
| Lỗi inference ngoài dự kiến | 500 | `INFERENCE_FAILED`, chi tiết ở log backend |

Khi startup thất bại, `/health` vẫn trả 200 nhưng `model_loaded: false`.
Xem log terminal, kiểm tra gói HI05 rồi khởi động lại. Không trả dự báo minh họa
thay cho model thật. Có thể đặt `MODEL_BUNDLE_DIR` để đổi gói; đường dẫn tương
đối tính từ thư mục gốc repository. Gói mới phải kèm history/calendar/metadata
và manifest tương ứng. Không chỉnh tay các file có checksum trong gói hiện tại.

`training_date` giữ nguyên thông tin Hiếu bàn giao; đây là ước lượng từ mtime
artifact HI04 như đã ghi trong metadata. Metric chỉ phản ánh subset 300 chuỗi CA_1.

## Kiểm thử và bàn giao

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv-ml\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
.\.venv-ml\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Test API dùng model HI05 thật cho dự báo hợp lệ; các fixture lỗi ở thư mục tạm.
Các trường hợp gồm output khớp dự báo lưu sẵn, horizon mặc định/ngắn/28 ngày,
store/item lạ, input sai kiểu, history thiếu/gãy ngày, calendar thiếu,
model chưa sẵn sàng, artifact sai checksum, metadata lệch version và CORS/Swagger.

L05 có thể dùng nguyên URL local cùng response contract để nối frontend.
L03 hiện phục vụ API local; triển khai Docker/Azure thực hiện ở các task sau.

Tham chiếu cách nạp và kiểm thử lifespan:
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) và
[kiểm thử startup/shutdown](https://fastapi.tiangolo.com/advanced/testing-events/).
