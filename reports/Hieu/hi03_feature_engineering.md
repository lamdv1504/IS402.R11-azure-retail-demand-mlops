# Feature Engineering M5 — HI03 (Hiếu)

## Đầu vào và kết quả

HI03 dùng các file đã có của Hùng và HI02: Parquet H02, split HI02, `calendar.csv`
và `sell_prices.csv`. Đã đối chiếu 1.941 ngày lịch và 69.666 dòng giá gốc thuộc
phạm vi CA_1/300 sản phẩm; giá H02 khớp theo `store_id,item_id,wm_yr_wk`.
Log HI03 đối chiếu SHA-256 các split Parquet với bàn giao HI02 và ghi phiên bản
dữ liệu từ `reports/Hieu/hi02_split_log.json`.

| Đầu ra | Số dòng | Số chuỗi | Có nhãn sales? |
| --- | ---: | ---: | --- |
| `train_features.parquet` | 565.500 | 300 | Có, để huấn luyện |
| `validation_future_features.parquet` | 8.400 | 300 | Không |
| `test_future_features.parquet` | 8.400 | 300 | Không |

Các Parquet được tạo trong `data/processed/features/` và Git bỏ qua theo quy ước
dữ liệu của nhóm. Danh sách feature, từ vựng phân loại, cách xử lý null và
giả định suy luận nằm ở `reports/Hieu/hi03_feature_schema.json`; số dòng, số null,
fingerprint đầu vào/đầu ra nằm ở `reports/Hieu/hi03_feature_log.json`.

## Nhóm đặc trưng

- Sales theo từng `item_id,store_id`, sắp xếp bằng `day_number`: `lag_1`,
  `lag_7`, `lag_14`, `lag_28`, `lag_56`, `rolling_mean_7`, `rolling_mean_28`.
  Rolling luôn tính trên `sales.shift(1)`, tối thiểu đủ 7/28 ngày. Các dòng
  đầu chuỗi không đủ lịch sử giữ `NaN` (train: lag_1 thiếu 300, lag_28 thiếu
  8.400), không điền bằng 0.
- Lịch: giữ `weekday`, `wday`, `month`, `year`, hai cặp tên/loại sự kiện và
  tạo `snap_state` từ cột SNAP ứng với bang của chuỗi. Với `CA_1`, dùng
  `snap_CA`; không lấy `snap_TX` hay `snap_WI` làm feature.
- Giá: giữ `sell_price` do H02 ghép, thêm `price_lag_1_week` và
  `price_change_weekly = (giá hiện tại − giá tuần trước) / giá tuần trước`
  khi tuần trước có giá dương. Các tuần trước khi sản phẩm mở bán giữ thiếu;
  `is_active=0` khi `sell_price` thiếu. Trong train có 104.538 dòng giá thiếu
  ban đầu, validation/test không thiếu giá. Không forward-fill từ tương lai.
- Metadata `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id` được giữ;
  cùng `weekday` và sự kiện được mã hóa thành cột `*_code`. Từ vựng lấy từ
  train, ổn định theo thứ tự chữ; giá trị sự kiện trống có mã riêng
  `__MISSING__`, loại mới chỉ có ở future nhận mã `-1`.

## Ranh giới chống rò rỉ

Feature train dùng sales quá khứ của cùng chuỗi. Feature validation chỉ thấy
history đến `d_1885`; test chỉ thấy history đến `d_1913` sau khi chọn model.
Không cung cấp sales của cửa sổ dự báo cho hàm tạo feature. Ví dụ tại origin
validation, `lag_1` chỉ biết ở ngày đầu (`d_1886`) rồi trở thành `NaN` cho
27 ngày còn lại; `lag_28` luôn biết cho cả 28 ngày. Không dùng trực tiếp
nhãn validation/test để lấp các lag trống.

HI04 có hai lựa chọn: dự báo đệ quy rồi dùng dự báo trước đó lấp lag ngắn,
hoặc chọn bộ feature chỉ cần lịch sử đã biết tại origin. Rolling `shift(1)`
trong train là đặc trưng một bước; với dự báo trực tiếp 28 ngày, HI04 cần
thiết kế rolling neo tại origin thay vì dùng rolling chưa biết của từng ngày.
File future vẫn có giá theo H02. Khi đưa vào API thật, Hiếu/Lâm cần xác nhận
giá nào đã biết trước tại origin; không được giả định giá thực tế tương lai
luôn sẵn có. Các giới hạn này có trong feature schema để tránh sử dụng sai.

## Chạy lại và kiểm tra

```powershell
python src/features/feature_engineering.py
python -m unittest discover -s tests -p "test_feature_engineering.py" -v
```

Chạy từ thư mục gốc repo. Script dừng khi thiếu đầu vào H02/HI02, khi giá/lịch
không khớp hoặc fingerprint split HI02 không đúng. Có thể đổi đường dẫn bằng
`--splits-dir`, `--split-log`, `--calendar`, `--prices`, `--output-dir`,
`--schema`, `--log`.

Kiểm tra mẫu hai chuỗi xác nhận lag và rolling không lẫn item; đổi nhãn future
không đổi feature future; giá trước khi mở bán, thay đổi giá theo tuần,
SNAP đúng bang và event mới đều được kiểm thử. HI03 chưa huấn luyện hoặc
đánh giá model, nên không công bố metric.
