# GĐ2 Lâm — chạy ứng dụng local

## Backend (L02)

Từ thư mục `backend/`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Mở http://localhost:8000/docs để xem Swagger. `/health` trả tình trạng API và cờ `model_loaded`. `/items` đọc danh sách MVP từ `reports/Hung/m5_mvp_items.csv`. `/dashboard` là endpoint bổ sung để tổng hợp lượng bán thật từ `data/processed/m5_sales_processed.parquet` trên máy local. Sau L03, `/model-info` và `/predict` dùng gói HI05 thật; trả 503 khi gói chưa sẵn sàng. Cài dependency ML và chạy theo [hướng dẫn L03](l03_run_local.md).

Backend mặc định cho phép frontend tại `localhost:3000` và `127.0.0.1:3000`. Nếu dùng origin khác, đặt `FRONTEND_ORIGINS` thành danh sách origin, phân tách bằng dấu phẩy.

## Frontend (L04)

Từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở http://localhost:3000. Frontend Next.js gọi backend tại `http://127.0.0.1:8000` theo mặc định. Muốn dùng backend khác, tạo `frontend/.env.local` với `NEXT_PUBLIC_API_URL=<API URL>`; file này được Git bỏ qua. Chạy `npm run build` để kiểm tra bản static export trong `frontend/out/`.

Bốn trang: Dashboard, Forecast, Model Performance và Model Information. Form dự báo dùng `CA_1`, danh sách 300 item từ `/items`, horizon 1–28 ngày và mặc định 28. Giao diện hiển thị rõ loading, lỗi và trạng thái trống. Biểu đồ dự báo chỉ xuất hiện khi API trả kết quả thật; số ví dụ trong OpenAPI không được dùng làm dữ liệu giao diện. Dữ liệu validation từng ngày của Hiếu đã có trong `reports/Hieu/hi05_validation_predictions.csv`; API hiện chỉ cung cấp metric tổng hợp, nên phần Actual vs Predicted giữ trạng thái trống chờ luồng tích hợp riêng ở L05.

[Hướng dẫn và tiêu chí L04](l04_frontend.md) ghi cấu trúc frontend, cách chạy kiểm tra và các mục cần nghiệm thu trên trình duyệt.
