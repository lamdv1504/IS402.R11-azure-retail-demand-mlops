# L05 Kết nối frontend với API local và Azure ACI

Frontend Next.js gọi API thật để dự báo theo `store_id`, `item_id` và `horizon`
(mặc định 28). Bảng và biểu đồ dùng cùng response đã qua kiểm tra ngày liên tiếp,
số lượng không âm, tổng lượng bán và phiên bản model/data.

Trang Tổng quan hiển thị trạng thái hệ thống và mô hình, lấy trực tiếp từ
`/health` và `/model-info`. Thanh điều hướng được giữ ở đầu màn hình khi cuộn.
Trang này không gọi `/dashboard` và không cần dữ liệu lịch sử Parquet.

Đầu vào L03, catalog của Hùng, gói HI05 của Hiếu và URL Q06 của Quân đã có.
URL dưới đây lấy từ hai tài liệu bàn giao `b_n_giao_api_checklist_cho_l_m.md`
và `Báo cáo Q06.docx`. Không thiếu file bắt buộc để chạy dự báo L05.

## Chọn API và chạy frontend

[api-targets.json](../../frontend/api-targets.json) lưu hai URL công khai:

| Môi trường | API base URL |
| --- | --- |
| Local | `http://127.0.0.1:8000` |
| ACI Q06 | `http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000` |

Các lệnh sau chạy từ thư mục `frontend/`, sau khi cài dependency bằng `npm ci`:

```powershell
# Dùng API Azure đã bàn giao:
npm run dev:aci

# Hoặc dùng backend L03 local:
npm run dev:local
```

Chọn **một** lệnh dev và mở http://localhost:3000/forecast. Nếu đang có Next.js
ở cổng 3000, dùng terminal của tiến trình đó để dừng trước khi đổi chế độ.
CORS của ACI đã kiểm tra cho `http://localhost:3000` và `http://127.0.0.1:3000`;
không tự chuyển sang cổng 3001 khi cổng 3000 bận.

Để chạy backend local, dùng [hướng dẫn L03](l03_run_local.md). Có thể khởi động
từ thư mục gốc bằng:

```powershell
.\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Các lệnh `dev:local`, `dev:aci`, `build:local`, `build:aci` đặt
`NEXT_PUBLIC_API_URL` cho tiến trình tương ứng, ưu tiên hơn `.env.local`.
Muốn dùng URL khác, đặt biến này trong `frontend/.env.local`, rồi dùng
`npm run dev` hoặc `npm run build`. File `.env.local` trên máy thực hiện L05
đã cấu hình ACI và được Git bỏ qua; thành viên khác có thể dùng ngay `dev:aci`.

Next.js đưa `NEXT_PUBLIC_*` vào JavaScript lúc build. Khi đổi API của bản export,
phải build lại. Chỉ đưa URL công khai vào biến này, không đưa connection string,
SAS token hay khóa Azure.

## Kiểm tra model và dự báo

ACI cần được Start trước khi thử. Chờ `/health` trả `model_loaded: true`, sau đó:

1. Mở trang Tổng quan, kiểm tra dịch vụ, phiên bản API/model, phạm vi dữ liệu và
   chỉ số validation. **Làm mới trạng thái** tải lại hai API; mỗi phần có nút thử
   lại khi lỗi. Model sẵn sàng cần cả health hợp lệ, `model_loaded: true` và
   metadata `status: ready`.
2. Mở trang Dự báo, chọn cửa hàng `CA_1` và sản phẩm `FOODS_1_017`.
3. Giữ số ngày `28`, nhấn **Xem dự báo**. Form khóa trong lúc gửi để tránh trùng request.
4. Kiểm tra đủ 28 hàng từ `23/5/2016` đến `19/6/2016`, tổng `21,34` units và
   model `hi05-xgboost-cb3a08fa5e82` cho phiên bản Q06 đã kiểm tra ngày 21/11/2026.
   Khi Quân đổi model, đối chiếu theo `/model-info` mới thay vì cố giữ số cũ.
5. Đổi sản phẩm hoặc số ngày: kết quả cũ phải được xóa. Thử số ngày ngoài 1–28,
   trạng thái đang tải, lỗi API và nút **Thử lại**.

HTTP client giới hạn chờ 15 giây, báo lỗi mạng/CORS, lỗi validation và dữ liệu
JSON không hợp lệ. Kết quả dự báo sai chuỗi, thiếu ngày hoặc sai tổng bị chặn
trước khi đưa vào biểu đồ/bảng. Giao diện giữ Tailwind, Manrope và bố cục L04.

## Kiểm thử tự động và bằng chứng HTTP

```powershell
npm test
npm run test:local
npm run test:aci
npm run build:aci
```

`test:local` cần backend L03 cùng bundle HI05 và catalog MVP. `test:aci` cần
container đang chạy. Hai lệnh gọi **service frontend thật**, kiểm tra metadata/catalog,
dự báo 28 ngày, lỗi 404/422 và preflight/response CORS. Kết quả và JSON API được
lưu vào [báo cáo local](../../reports/Lam/l05_local_api_check.json) và
[báo cáo ACI](../../reports/Lam/l05_aci_api_check.json). Timeout được kiểm tra
riêng trong unit test, không cố tình dừng ACI để gây lỗi.

Hai JSON đính kèm lưu lượt kiểm tra lúc 21:22 ngày 21/11/2026 (GMT+7), trước khi
đổi trang Tổng quan sang trạng thái hệ thống. Vì vậy chúng còn ghi kiểm tra
`/dashboard`: local đạt, ACI cảnh báo thiếu Parquet. Script hiện hành đã bỏ kiểm
tra endpoint này. Chạy lại lệnh sẽ ghi đè JSON bằng kết quả và thời điểm mới.

Đây là kiểm thử Node/HTTP; bước nghiệm thu bằng trình duyệt còn cần thực hiện:

1. Mở F12 → Network, bật Preserve log và thực hiện dự báo 28 ngày.
2. Chọn request `predict`: xác nhận URL ACI đúng `http://` và cổng `8000`, method
   POST, status 200 và payload `CA_1` / `FOODS_1_017` / `28`.
3. Kiểm tra tab Response có đủ 28 ngày. Lưu ảnh Request/Payload/Response vào
   `reports/Lam/`, kèm ảnh bảng/biểu đồ ở desktop và mobile.
4. Kiểm tra Console không có lỗi CORS; xác nhận loading, nút thử lại, menu mobile
   và thao tác bàn phím. Không đưa token hay cookie vào ảnh/HAR.

## Giới hạn triển khai Q06

ACI hiện phục vụ **HTTP**, vì vậy mở frontend qua HTTP khi demo local. Website
HTTPS cần API HTTPS tương ứng; trình duyệt sẽ chặn request đến API HTTP.
Frontend phát hiện trường hợp này và hiển thị hướng dẫn, không gọi request bị chặn.

Trong lượt kiểm tra đã lưu, `/dashboard` trên ACI trả `503 DASHBOARD_NOT_READY`
vì Dockerfile Q05 chưa đưa `data/processed/m5_sales_processed.parquet` vào image.
Người dùng đã chọn đổi Tổng quan sang trạng thái hệ thống; giao diện hiện hành
không phụ thuộc endpoint này. Biểu đồ và bảng dự báo vẫn lấy từ `/predict`.

Nếu ACI vừa Start sau khi website đã mở, chờ API/model sẵn sàng rồi tải lại trang.
Nhãn trạng thái trên thanh điều hướng được kiểm tra khi trang được nạp. Nếu vẫn
báo chưa kết nối, mở Network kiểm tra Request URL và origin: dùng đúng URL ACI,
giao thức HTTP và cổng frontend 3000. Xem phản hồi `/health`, Console/CORS và
thông báo timeout để phân biệt lỗi; trạng thái Running trên Portal chưa tự xác
nhận trình duyệt gọi API thành công.

Chưa có endpoint AKS Q07 bàn giao, nên phạm vi demo L05 hiện là ACI. Không cần tạo
AKS mới cho lượt này. Sau khi demo, người quản lý Azure có thể Stop ACI để tiết
kiệm credit; frontend sẽ hiển thị lỗi kết nối khi API dừng.

Xem [báo cáo kiểm tra L05](../../reports/Lam/l05_integration_test_report.md) để
phân biệt phần đã xác minh với ảnh UI/Network còn cần bổ sung.
