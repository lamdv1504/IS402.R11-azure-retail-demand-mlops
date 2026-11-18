# Chia tập dữ liệu M5 theo thời gian — HI02 (Hiếu)

## Phạm vi và đầu vào

Đã chạy HI02 trên dữ liệu H02 của Hùng: **582.300 dòng, 300 chuỗi sản phẩm–cửa
hàng tại CA_1**, có nhãn từ `d_1` đến `d_1941`. Phụ thuộc cần thiết đều có trên
máy: `data/processed/m5_sales_processed.parquet`, `data/raw/calendar.csv`,
`reports/m5_mvp_items.csv` và schema trong `reports/h02_processing_log.json`.
Các mốc chia tuân theo HI01 tại `reports/ml_problem.md` và mục HI02 trong kế hoạch.

HI02 chạy local, không cần Azure Workspace, Blob hoặc model từ thành viên khác.
Script dừng trước khi xuất file nếu thiếu Parquet, calendar, danh sách MVP hoặc
cấu hình; không tự tạo dữ liệu thay thế.

## Cửa sổ và kết quả thực tế

| Tập | Mốc d | Ngày bắt đầu – kết thúc | Số ngày/chuỗi | Số dòng | Số chuỗi |
| --- | --- | --- | ---: | ---: | ---: |
| Train | d_1 – d_1885 | 2011-01-29 – 2016-03-27 | 1.885 | 565.500 | 300 |
| Validation | d_1886 – d_1913 | 2016-03-28 – 2016-04-24 | 28 | 8.400 | 300 |
| Test holdout | d_1914 – d_1941 | 2016-04-25 – 2016-05-22 | 28 | 8.400 | 300 |

Không chia ngẫu nhiên. Mỗi tập được sắp xếp theo `item_id`, `store_id` và
`day_number` (số nguyên tách từ `d`, tránh sắp xếp `d_10` trước `d_2`).
Các cột H02 được giữ lại, thêm `day_number` để thao tác theo thời gian.
Giá thiếu trước khi sản phẩm được bán vẫn giữ nguyên, không điền từ tương lai.

Nguồn chỉ có nhãn đến `d_1913` cũng được hỗ trợ: giữ nguyên train/validation,
không tạo test/test_future và ghi `test_available=false`. Nguồn thiếu ngày,
thiếu chuỗi hoặc chỉ có một phần holdout bị từ chối. Nếu thư mục đầu ra còn
file test từ lần chạy nguồn đầy đủ, script yêu cầu dùng thư mục đầu ra khác
để tránh nhầm dữ liệu cũ thành holdout mới.

## Chạy và tái tạo

Từ thư mục gốc repo:

```powershell
python -m pip install -r requirements-data.txt
python src/models/split_data.py
python -m unittest discover -s tests -p "test_split_data.py" -v
```

Mặc định đọc `src/models/split_config.json` với horizon 28 và tối thiểu
28 ngày lịch sử. `python src/models/split_data.py --help` liệt kê các tham số
`--input`, `--calendar`, `--item-list`, `--config`, `--output-dir`, `--log`,
`--day-mapping`. Khi thử nguồn khác, dùng thư mục/log/mapping riêng.

Các file bàn giao:

| File | Mục đích |
| --- | --- |
| `data/processed/splits/train.parquet` | Lịch sử huấn luyện đến d_1885 |
| `data/processed/splits/validation.parquet` | Dữ liệu có nhãn của 28 ngày validation; `sales` chỉ dùng chấm điểm cửa sổ này |
| `data/processed/splits/test.parquet` | Nhãn holdout cuối, chỉ dùng đánh giá sau khi chọn model |
| `data/processed/splits/validation_future.parquet` | Định danh/lịch/giá của cửa sổ validation, đã bỏ `sales` |
| `data/processed/splits/test_future.parquet` | Định danh/lịch/giá của cửa sổ test, đã bỏ `sales` |
| `reports/hi02_day_mapping.csv` | 1.941 dòng mapping `day_number,d,date,split` |
| `reports/hi02_split_log.json` | Cấu hình, schema, mốc ngày, số dòng/chuỗi, lịch sử từng backtest và SHA-256 đầu vào/đầu ra |

Parquet thuộc dữ liệu sinh lại, được `.gitignore` bỏ qua theo quy ước H02.
Thành viên khác cần nhận Parquet H02 và calendar từ Hùng hoặc nơi lưu dữ liệu
của nhóm trước khi chạy. Code, cấu hình, log và mapping có thể đưa vào Git.

## Ranh giới chống rò rỉ cho HI03/HI04

Hàm `make_backtest_context` tách ba đối tượng rõ ràng:

```python
import pandas as pd
from src.models.split_data import make_backtest_context

splits = {
    name: pd.read_parquet(f"data/processed/splits/{name}.parquet")
    for name in ("train", "validation", "test")
}
context = make_backtest_context(splits, "validation")
history = context.history  # Có sales, chỉ d_1..d_1885
future = context.future    # d_1886..d_1913, KHÔNG có sales
labels = context.labels    # Chỉ dùng khi chấm điểm dự báo
```

- Khi chọn model trên validation, chỉ dùng lịch sử đến `d_1885`.
- Sau khi chốt model, mới gọi `make_backtest_context(splits, "test")` để nhận
  lịch sử `train + validation` đến `d_1913`, fit lại và đánh giá test.
- Không tính lag/rolling trên bảng có toàn bộ nhãn rồi mới tách tập. Trong
  cửa sổ dự báo 28 ngày, lag ngắn cần dùng các dự báo trước đó theo cách đệ quy;
  phương án dự báo cùng lúc phải chọn lag/rolling bảo đảm chỉ dùng lịch sử
  đã biết tại mốc dự báo. Lag/rolling là phần triển khai HI03.
- `future` chứa lịch và giá đã ghép từ H02. Khi dùng giá làm đặc trưng, HI03/HI04
  phải chốt giả định giá nào biết trước tại mốc dự báo; việc bỏ `sales` không
  tự chứng minh mọi đặc trưng tương lai đều khả dụng khi triển khai thật.
- Các file validation/test có nhãn cần cho đánh giá. Không đưa `labels` vào
  inference của chính cửa sổ đó. HI02 chưa huấn luyện model hay công bố metric.

## Kiểm tra đã thực hiện

- 11 kiểm thử tự động đạt: thứ tự ngày dạng số, ranh giới cửa sổ, dữ liệu không
  bị mất, phạm vi MVP, mapping lịch, khóa trùng, lịch sử thiếu, sales không hợp
  lệ, trường hợp nguồn không có holdout và lệnh chạy thiếu đầu vào.
- Thay toàn bộ sales validation/test bằng giá trị khác không làm thay đổi
  history hoặc future của chính cửa sổ đó trong kiểm thử.
- Lệnh chạy thật xác nhận các cửa sổ không chồng ngày, đủ 300 chuỗi và đúng
  số dòng trong bảng trên; cả hai file future không chứa cột `sales`.
- Log lưu fingerprint dữ liệu/cấu hình để HI03/HI04 đối chiếu lần chạy.
