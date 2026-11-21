# M5 Retail frontend (Next.js)

Ứng dụng của Lâm gồm bốn trang: Tổng quan, Dự báo, Hiệu suất và Mô hình. Giao diện dùng Tailwind CSS, font Manrope và bảng màu mint trong `design.md`, kết nối API FastAPI local hoặc Azure ACI. Các lớp dùng chung nằm ở `src/lib/ui.ts`; `src/app/globals.css` chỉ khai báo Tailwind và màu/font.

## Chạy local

Mở hai terminal từ thư mục gốc của repo.

Terminal backend:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Terminal frontend:

```powershell
cd frontend
npm install
npm run dev
```

Mở http://localhost:3000. Swagger ở http://localhost:8000/docs.

Frontend gọi `http://127.0.0.1:8000` theo mặc định. Khi cần đổi backend, tạo `frontend/.env.local` chứa `NEXT_PUBLIC_API_URL=<API URL>`, sau đó khởi động lại Next. Vì đây là biến public, không đặt khóa bí mật vào đó.

`npm run build` tạo static export trong `out/`. Backend L03 hỗ trợ gói HI05 cho `/predict` và `/model-info`; cài môi trường ML theo [hướng dẫn L03](../docs/Lam/l03_run_local.md). Khi model hoặc dữ liệu thiếu, UI hiển thị lỗi và cho thử lại. Các số ví dụ trong OpenAPI không được dùng làm kết quả.

## Tổng quan trạng thái hệ thống và mô hình

Trang Tổng quan lấy dữ liệu trực tiếp từ `/health` và `/model-info`: trạng thái dịch vụ, phiên bản API/model, thời điểm kiểm tra (GMT+7), phạm vi sản phẩm, kỳ dự báo và các chỉ số validation. Nút **Làm mới trạng thái** tải lại hai API. Từng phần có trạng thái đang tải, lỗi và nút thử lại riêng; các chỉ số chưa có hiển thị dấu `—`.

Trang này không gọi `/dashboard` và không cần Parquet lịch sử hay JSON tĩnh. Vì vậy, lỗi `503 DASHBOARD_NOT_READY` của image ACI hiện tại không ảnh hưởng trang Tổng quan. Chỉ số RMSSE/WRMSSE luôn ghi phạm vi subset theo metadata của model.

Để dùng endpoint ACI trong `api-targets.json`, chạy từ `frontend/`:

```powershell
npm run dev:aci
# Build bản export với cùng API:
npm run build:aci
```

Mở http://localhost:3000. Dừng tiến trình dev cũ trước khi chạy lại để giữ đúng cổng CORS 3000. Container ACI cần đang chạy. Với backend local, dùng `npm run dev:local`.

## Kiểm thử

```powershell
npm test
npm run build
# Mở backend L03 trước khi chạy kiểm tra HTTP với dữ liệu thật:
npm run test:live
# Hoặc kiểm tra endpoint ACI đã cấu hình, gồm CORS:
npm run test:aci
```

`npm test` kiểm tra service dự báo, ngày, đơn vị, phạm vi, tổng và xử lý lỗi. `test:live` yêu cầu API đang chạy và gói HI05; không cần dữ liệu Dashboard local. Đây là kiểm tra HTTP, chưa thay thế kiểm thử trình duyệt. Biến `NEXT_PUBLIC_API_URL` phải đặt trước khi chạy dev/build; khi chạy test Node, đặt biến này trong môi trường terminal nếu API khác mặc định. `test:aci` tự đặt URL theo cấu hình và lưu bằng chứng HTTP vào `reports/Lam/`.

Routing nằm ở `src/app/`, giao diện dùng chung ở `src/components/`, `predictionService` ở `src/services/`; `src/lib/` chứa HTTP client, hook tải dữ liệu và định dạng. Chi tiết tiêu chí và giới hạn nghiệm thu: [L04 frontend](../docs/Lam/l04_frontend.md).
