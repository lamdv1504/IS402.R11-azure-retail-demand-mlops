# Báo cáo xử lý dữ liệu M5 — H02 (Hùng)

## Đầu vào và phạm vi

- Nguồn có nhãn: `data/raw/sales_train_evaluation.csv`, từ `d_1` đến `d_1941`. Không nối thêm `sales_train_validation.csv` vì lịch sử của hai file trùng nhau.
- Phạm vi nhóm đã xác nhận: cửa hàng `CA_1` và 300 sản phẩm trong `reports/Hung/m5_mvp_items.csv` (100 sản phẩm mỗi nhóm `FOODS`, `HOBBIES`, `HOUSEHOLD`). Script lọc phạm vi này trước khi chuyển dữ liệu từ dạng nhiều cột sang từng dòng.
- Bảng bổ sung: `data/raw/calendar.csv` và `data/raw/sell_prices.csv`.

Chạy lại từ thư mục gốc repo:

```powershell
python -m pip install -r requirements-data.txt
python src/data/preprocessing.py
```

## Quy trình và kết quả

1. Đọc 300 chuỗi sales thuộc phạm vi MVP và chuyển 1.941 cột ngày thành các dòng `item_id`–`store_id`–`d`–`sales`.
2. Ghép lịch theo `d`; số dòng trước và sau ghép đều là **582.300**. Mỗi `d` ánh xạ được sang `date` và `wm_yr_wk`.
3. Lọc 69.666 dòng giá của các sản phẩm MVP, ghép theo `store_id`, `item_id`, `wm_yr_wk`; số dòng sau ghép vẫn là **582.300**.
4. Giảm kiểu số phù hợp và dùng kiểu phân loại cho các cột định danh/sự kiện. Xuất `data/processed/m5_sales_processed.parquet` gồm **22 cột**, kích thước **620.521 byte**. File Parquet đọc lại được.

File sales gốc có kích thước 121.736.518 byte và bao gồm toàn bộ 30.490 chuỗi; file Parquet chỉ gồm 300 chuỗi MVP. Vì phạm vi khác nhau, hai kích thước này không dùng để đánh giá trực tiếp hiệu quả nén.

## Kiểm tra chất lượng

| Kiểm tra | Kết quả |
| --- | ---: |
| Chuỗi sản phẩm–cửa hàng | 300 |
| Ngày trên mỗi chuỗi | 1.941 |
| Số dòng trước/sau ghép lịch và giá | 582.300 / 582.300 / 582.300 |
| Khóa `item_id`–`store_id`–`d` trùng | 0 |
| Doanh số thiếu hoặc âm | 0 |
| Dòng doanh số bằng 0 được giữ | 378.662 |
| Tổng số lượng bán | 748.327 |
| Dòng thiếu `date` hoặc `wm_yr_wk` | 0 |
| Dòng thiếu `sell_price` | 104.538 (17,95%) |

Tất cả 104.538 dòng thiếu giá nằm trước tuần đầu tiên có giá của chính sản phẩm đó tại `CA_1`. Không có dòng thiếu giá từ tuần đầu tiên có giá trở về sau. Script giữ nguyên các giá trị thiếu này để Hiếu quyết định quy tắc xử lý khi tạo đặc trưng; không tự điền giá. Các cột sự kiện lịch cũng để trống vào ngày không có sự kiện.

## Schema và bàn giao

- Định danh: `id`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id` (kiểu phân loại).
- Thời gian: `d` (chuỗi), `date` (ngày), `wm_yr_wk` (số nguyên), cùng `weekday`, `wday`, `month`, `year`.
- Doanh số: `sales` (số nguyên; giữ giá trị 0).
- Sự kiện và SNAP: `event_name_1/2`, `event_type_1/2`, `snap_CA/TX/WI`.
- Giá: `sell_price` (float32, có thể thiếu ở giai đoạn đầu).

Schema từng cột, số dòng, giá trị thiếu và kích thước được ghi trong `reports/Hung/h02_processing_log.json`. Hiếu có thể đọc dữ liệu bằng:

```python
import pandas as pd
data = pd.read_parquet("data/processed/m5_sales_processed.parquet")
```

File Parquet được giữ ngoài Git. Khi bàn giao cho Hiếu, cần chuyển file qua nơi lưu trữ dữ liệu của nhóm; bước đưa lên Azure Blob thuộc H03 sau khi Quân chuẩn bị Storage Account và quyền truy cập.
