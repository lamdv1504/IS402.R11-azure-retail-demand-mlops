# GĐ2 — L04: Frontend của Lâm

L04 xây bốn trang Next.js theo [L01](use_cases.md) và [wireframe](wireframes.md).
Giao diện dùng Tailwind CSS, font Manrope và bảng màu mint trong
[design.md](../../frontend/design.md). Các dữ liệu bán hàng/dự báo dùng đơn vị
sản phẩm (units); metric luôn ghi phạm vi CA_1 / 300 chuỗi, không phải toàn bộ M5.

## Đầu vào đã kiểm tra

- L01: use case, wireframe và [API contract](../api_contract.json) đã có.
- Hùng: [catalog 300 sản phẩm](../../reports/Hung/m5_mvp_items.csv) và file local
  `data/processed/m5_sales_processed.parquet` đã có; API L02 cung cấp `/items`, `/dashboard`.
- Hiếu: [gói HI05](../../artifacts/hi05/model_info.json) và
  [hướng dẫn inference](../Hieu/hi05_inference_handoff.md) đã có; backend L03 phục vụ model thật.
- Azure của Quân không phải đầu vào bắt buộc để chạy L04 local.

Không có file bàn giao bắt buộc nào bị thiếu khi thực hiện lượt này. File Parquet
là dữ liệu local bị loại khỏi Git; máy thành viên khác cần nhận hoặc tái tạo từ Hùng
để Dashboard có lịch sử. `/predict` dùng history/calendar trong gói HI05.

## Chạy ứng dụng

Từ thư mục gốc, mở terminal backend:

```powershell
.\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Nếu chưa có môi trường, làm theo [cài đặt L03](l03_run_local.md).
Mở terminal thứ hai:

```powershell
cd frontend
npm ci
npm run dev
```

Mở http://localhost:3000. Frontend mặc định gọi http://127.0.0.1:8000.
Muốn đổi API, đặt `NEXT_PUBLIC_API_URL` trong `frontend/.env.local` trước khi chạy
dev/build. Backend phải cho phép origin frontend qua `FRONTEND_ORIGINS`.
Không cần Azure cho lượt chạy này.

## Các trang và cách dùng

| Đường dẫn | Chức năng |
| --- | --- |
| `/` | Dashboard: phạm vi MVP, tổng/trung bình units và biểu đồ lịch sử từ Hùng. |
| `/forecast` | Chọn CA_1, nhóm hàng, item MVP, horizon nguyên 1–28 (mặc định 28); xem bảng và biểu đồ từ cùng response. |
| `/performance` | Metric validation có nhãn subset, model version, khoảng validation và ghi chú phạm vi. |
| `/model` | Trạng thái, version, thuật toán, phạm vi, danh sách feature, khoảng train/validation/holdout. |

Form khóa lựa chọn và chặn gửi trùng khi đang dự báo. Đổi nhóm/item/horizon sẽ
xóa kết quả cũ. `predictionService` kiểm tra đúng store/item/horizon, ngày bắt đầu
hợp lệ, các ngày liên tiếp, số ngày, units hữu hạn không âm, tổng khớp các ngày và
model/data version trước khi render. Ngày và thứ định dạng tiếng Việt theo UTC;
không dùng ngày hiện tại làm ngày bắt đầu dự báo.

Các trang có loading, lỗi kèm nút thử lại và trạng thái trống. Không có mock fallback
trong ứng dụng. Test dùng mẫu HI05 lưu sẵn và HTTP giả lập riêng để kiểm tra lỗi;
các fixture này không được import vào UI.

`src/app/` là pages/routing của Next.js App Router; `src/components/` chứa UI dùng
chung; `src/services/predictionService.ts` xử lý dự báo; `src/lib/` chứa HTTP client,
hook tải/thử lại và định dạng. CSS toàn cục chỉ khai báo Tailwind và design token.

## Kiểm tra và phần còn mở

Từ `frontend/`:

```powershell
npm test
npm run build
# Cần backend L03 đã chạy, model_loaded=true và dữ liệu Dashboard:
npm run test:live
```

Kết quả chi tiết ở [báo cáo kiểm tra L04](../../reports/Lam/l04_frontend_test_report.md).
Build xuất bốn trang vào `frontend/out/`. Chạy test HTTP không thay thế thao tác
người dùng trên trình duyệt.

Phần Actual vs Predicted theo ngày giữ empty state như L01: đã có
[validation CSV của Hiếu](../../reports/Hieu/hi05_validation_predictions.csv), nhưng
contract hiện chưa có endpoint đối chiếu. Kết nối dữ liệu đối chiếu thuộc luồng
tích hợp tiếp theo L05; không lấy forecast tương lai để giả làm validation.

Công cụ Browser chưa có kết nối trong lượt này, nên **chưa có ảnh UI và chưa xác
nhận trực quan responsive/thao tác form**. Chưa đánh dấu nghiệm thu đầy đủ đầu ra
“ảnh UI” của kế hoạch. Cần kiểm tra bốn trang ở desktop và mobile, thao tác chọn
nhóm/item/horizon, xem bảng đủ 28 ngày, đổi lựa chọn để xóa kết quả cũ, thử lỗi API
và menu mobile; sau đó lưu ảnh thật vào `reports/Lam/` trước khi chốt nghiệm thu UI.
