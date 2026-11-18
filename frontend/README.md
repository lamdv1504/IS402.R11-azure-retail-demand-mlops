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

`npm run build` tạo static export trong `out/`. Dashboard và danh mục sản phẩm lấy dữ liệu thật từ Hùng. `/predict` và `/model-info` báo model chưa sẵn sàng cho đến khi Hiếu bàn giao HI05; các số ví dụ trong OpenAPI không được dùng làm kết quả.
