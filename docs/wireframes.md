# L01 — Wireframe ứng dụng M5

Bản phác thảo bố cục cho desktop. Khi màn hình hẹp, các khối xếp dọc; nội dung và trạng thái vẫn giữ nguyên. Đây là wireframe, **không phải ảnh giao diện đã chạy**. Chi tiết chức năng ở [use_cases.md](use_cases.md).

## Điều hướng chung

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Retail Demand Forecasting     Dashboard | Forecast | Performance | Model   │
│ MVP: CA_1 / 300 item            API: …            Model: …                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 1. Dashboard

```text
┌─ DASHBOARD ──────────────────────────────────────────────────────────────────┐
│ Phạm vi: CA_1  Category: [Tất cả / FOODS / HOBBIES / HOUSEHOLD ▼]          │
│ Khoảng ngày lịch sử: [từ] — [đến]                                           │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐                  │
│ │ Store: 1     │ │ Item: 300    │ │ TB units bán / ngày  │                  │
│ └──────────────┘ └──────────────┘ └──────────────────────┘                  │
│ ┌─ Tổng units bán theo ngày ──────────────────────────────────────────────┐ │
│ │ Trục X: ngày | Trục Y: units | nguồn: dữ liệu processed của Hùng        │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ [Đi tới Forecast →]                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

Số store/item là phạm vi MVP đã bàn giao. Số bán và biểu đồ phải tính từ dữ liệu thực; khi chưa có nguồn summary, thay vùng số liệu bằng “Chưa có dữ liệu tổng quan”.

## 2. Forecast

```text
┌─ FORECAST ───────────────────────────────────────────────────────────────────┐
│ Store: [CA_1 ▼]  Category: [Tất cả ▼]  Item: [chọn từ /items ▼]             │
│ Horizon: [1 ... 28 ngày; mặc định 28]      [Dự báo]                         │
│ [Đang tải... / lỗi input / lỗi kết nối / model chưa sẵn sàng]               │
│                                                                              │
│ Item: … | Model: … | Data version: … | Ngày bắt đầu: … | Tổng units: …     │
│ ┌─ Dự báo units/ngày ───────────────┐ ┌─ Bảng kết quả ───────────────────┐ │
│ │ Biểu đồ theo date, predicted_sales│ │ Ngày | Thứ | Predicted sales     │ │
│ │                                   │ │ ...  | ... | ...                 │ │
│ └───────────────────────────────────┘ └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Mặc định 28 ngày là luồng nghiệm thu GĐ1; contract cho phép chọn 1–28. Khi đổi item/horizon, xóa kết quả cũ. Bảng/biểu đồ chỉ vẽ khi `forecast.length === horizon` và từng giá trị hợp lệ. Không tự làm tròn về số nguyên.

## 3. Model Performance

```text
┌─ MODEL PERFORMANCE ──────────────────────────────────────────────────────────┐
│ Model version: …   Tập: validation   Phạm vi: CA_1 / 300 item subset      │
│ ┌───────────────┐ ┌────────────────┐ ┌──────────┐ ┌──────────┐           │
│ │ Subset RMSSE  │ │ Subset WRMSSE  │ │ MAE      │ │ RMSE     │           │
│ └───────────────┘ └────────────────┘ └──────────┘ └──────────┘           │
│ Metric scope note: …                                                        │
│ Store: [CA_1]  Item: [chọn item ▼]                                          │
│ ┌─ Actual vs Predicted trên validation ───────────────────────────────────┐ │
│ │ Trục X: ngày | Trục Y: units | 2 đường: actual, predicted               │ │
│ │ Chỉ hiện khi Hiếu bàn giao dữ liệu đối chiếu từng ngày.                  │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Nếu `/model-info` trả 503, hiện “Chưa có kết quả đánh giá”. Không lấy các số trong `example` của OpenAPI làm metric thật.

## 4. Model Information

```text
┌─ MODEL INFORMATION ──────────────────────────────────────────────────────────┐
│ Trạng thái model: [ready / training / uninitialized]                        │
│ Tên model: …                 Version: …                                      │
│ Thuật toán: …                Training date: …                                │
│ Data version: …             Store scope: …    Item count: …                 │
│ Forecast horizon: …         Features used: …                                │
│ Train / validation / holdout period: …                                       │
│ [Đi tới Performance →]      [Đi tới Forecast →]                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Nếu chưa có model, trường chưa biết ghi “Chưa có thông tin”; không tự đặt version, thuật toán hoặc ngày train.

## Trạng thái chung

- **Loading:** khóa nút dự báo khi request đang chạy, cho biết đang tải.
- **Empty:** giải thích thiếu dữ liệu Dashboard, metric, model hoặc lựa chọn item.
- **Error:** phân biệt input sai, item không tồn tại, model 503 và lỗi mạng; cho thử lại.
- **Success:** gắn kết quả với store/item/horizon và version trả về; số liệu mẫu (nếu dùng sau này) phải có nhãn “Mock/Minh họa”.
