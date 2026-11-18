# GĐ2 Lâm — chạy ứng dụng local

## Backend (L02)

Từ thư mục `backend/`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Mở http://localhost:8000/docs để xem Swagger. `/health` trả tình trạng API và cờ `model_loaded`. `/items` đọc danh sách MVP từ `reports/m5_mvp_items.csv`. `/dashboard` là endpoint bổ sung để tổng hợp lượng bán thật từ `data/processed/m5_sales_processed.parquet` trên máy local. `/model-info` và `/predict` trả 503 khi chưa có model và metadata do Hiếu bàn giao trong HI05.

Backend mặc định cho phép frontend tại `localhost:3000` và `127.0.0.1:3000`. Nếu dùng origin khác, đặt `FRONTEND_ORIGINS` thành danh sách origin, phân tách bằng dấu phẩy.

## Frontend (L04)

Từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở http://localhost:3000. Frontend Next.js gọi backend tại `http://127.0.0.1:8000` theo mặc định. Muốn dùng backend khác, tạo `frontend/.env.local` với `NEXT_PUBLIC_API_URL=<API URL>`; file này được Git bỏ qua. Chạy `npm run build` để kiểm tra bản static export trong `frontend/out/`.

Bốn trang: Dashboard, Forecast, Model Performance và Model Information. Form dự báo dùng `CA_1`, danh sách 300 item từ `/items`, horizon 1–28 ngày và mặc định 28. Giao diện hiển thị rõ loading, lỗi và trạng thái trống. Biểu đồ dự báo chỉ xuất hiện khi API trả kết quả thật; số ví dụ trong OpenAPI không được dùng làm dữ liệu giao diện. Biểu đồ actual vs predicted cần Hiếu bàn giao dữ liệu validation từng ngày ở giai đoạn sau.
