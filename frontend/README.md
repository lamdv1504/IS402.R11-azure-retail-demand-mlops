# M5 Retail frontend (Next.js)

Ứng dụng GĐ2 của Lâm gồm bốn trang: Tổng quan, Dự báo, Hiệu suất và Mô hình. Giao diện dùng Tailwind CSS, font Manrope và bảng màu mint trong `design.md`, cùng API FastAPI ở cổng 8000. Các lớp dùng chung nằm ở `src/lib/ui.ts`; `src/app/globals.css` chỉ khai báo Tailwind và màu/font.

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

`npm run build` tạo static export trong `out/`. Dashboard và danh mục sản phẩm lấy dữ liệu thật từ Hùng. Backend L03 đã hỗ trợ gói HI05 cho `/predict` và `/model-info`; cài môi trường ML theo [hướng dẫn L03](../docs/Lam/l03_run_local.md). Khi model hoặc dữ liệu thiếu, UI hiển thị lỗi và cho thử lại. Các số ví dụ trong OpenAPI không được dùng làm kết quả.

## Kiểm tra L04

```powershell
npm test
npm run build
# Mở backend L03 trước khi chạy kiểm tra HTTP với dữ liệu thật:
npm run test:live
```

`npm test` kiểm tra service dự báo, ngày, đơn vị, phạm vi, tổng và xử lý lỗi. `test:live` yêu cầu backend, gói HI05 và dữ liệu Dashboard local; không phải kiểm thử trình duyệt. Biến `NEXT_PUBLIC_API_URL` phải đặt trước khi chạy dev/build; khi chạy test Node, đặt biến này trong môi trường terminal nếu API khác mặc định.

Routing nằm ở `src/app/`, giao diện dùng chung ở `src/components/`, `predictionService` ở `src/services/`; `src/lib/` chứa HTTP client, hook tải dữ liệu và định dạng. Chi tiết tiêu chí và giới hạn nghiệm thu: [L04 frontend](../docs/Lam/l04_frontend.md).
