# Báo cáo khảo sát dữ liệu M5 — H01

Nguồn: [Kaggle M5 Forecasting – Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data). Báo cáo được lập từ 5 file CSV gốc trong `data/raw/`. Các file gốc được giữ nguyên và không đưa vào Git.

## Danh sách file và vai trò

| File | Số dòng | Số cột | Dung lượng (MiB) | Vai trò |
| --- | ---: | ---: | ---: | --- |
| `sales_train_validation.csv` | 30.490 | 1.919 | 114,45 | Doanh số theo sản phẩm và cửa hàng từ `d_1` đến `d_1913` |
| `sales_train_evaluation.csv` | 30.490 | 1.947 | 116,10 | Cùng các chuỗi doanh số, mở rộng đến `d_1941`; dùng để kiểm thử dự báo trên dữ liệu đã biết |
| `calendar.csv` | 1.969 | 14 | 0,10 | Ánh xạ mã ngày `d` sang ngày thực tế, tuần, sự kiện và cờ SNAP |
| `sell_prices.csv` | 6.841.121 | 4 | 193,97 | Giá theo `store_id`, `item_id` và `wm_yr_wk` |
| `sample_submission.csv` | 60.980 | 29 | 4,99 | Mẫu định dạng dự báo `F1`–`F28`; không chứa nhãn để huấn luyện |

Hai file sales có lịch sử trùng nhau từ `d_1` đến `d_1913`, vì vậy không được nối chúng thành các quan sát độc lập. File evaluation có thêm doanh số thực tế của `d_1914`–`d_1941`.

## Từ điển dữ liệu

| Trường | Ý nghĩa |
| --- | --- |
| `id` | Mã chuỗi, gồm sản phẩm, cửa hàng và hậu tố validation/evaluation |
| `item_id`, `dept_id`, `cat_id` | Mã sản phẩm, ngành hàng và nhóm sản phẩm |
| `store_id`, `state_id` | Mã cửa hàng và bang |
| `d_1`…`d_1941` | Số lượng sản phẩm bán mỗi ngày, lưu theo dạng nhiều cột |
| `d`, `date` | Mã ngày tương đối và ngày theo lịch |
| `wm_yr_wk` | Mã tuần Walmart, dùng để ghép bảng giá |
| `event_name_1/2`, `event_type_1/2` | Tên và loại sự kiện; thường để trống khi không có sự kiện |
| `snap_CA/TX/WI` | Cờ chương trình SNAP theo bang |
| `sell_price` | Giá bán của một sản phẩm tại một cửa hàng trong một tuần |
| `F1`…`F28` | Vị trí của 28 ngày dự báo trong file nộp mẫu, không phải doanh số thực tế |

## Kết quả kiểm tra ban đầu

- File evaluation có 30.490 mã chuỗi duy nhất, 3.049 sản phẩm, 10 cửa hàng và 3 bang. Mỗi cửa hàng có 3.049 chuỗi. Sáu cột định danh của sales đều không có giá trị thiếu.
- `calendar.csv` có 1.969 mã ngày duy nhất, từ 29/01/2011 đến 19/06/2016. Các cột ngày, tuần và SNAP không có giá trị thiếu. Cột sự kiện để trống trên ngày không có sự kiện: `event_name_1` và `event_type_1` cùng thiếu 1.807 dòng; `event_name_2` và `event_type_2` cùng thiếu 1.964 dòng.
- `sell_prices.csv` không có ô trống; giá quan sát được từ 0,01 đến 107,32. Kết quả này chưa chứng minh mọi tổ hợp sản phẩm–cửa hàng–tuần đều có giá. Cần kiểm tra tỷ lệ ghép giá thành công trong H02.
- `sample_submission.csv` có 60.980 mã duy nhất, gồm hai tập, mỗi tập 30.490 chuỗi.

## Phạm vi MVP đề xuất

Chọn cửa hàng `CA_1` và 300 sản phẩm: mỗi nhóm `FOODS`, `HOBBIES`, `HOUSEHOLD` lấy 100 sản phẩm bằng cách lấy mẫu với seed 42. Danh sách ID cụ thể nằm trong `reports/m5_mvp_items.csv` và có thể tạo lại bằng lệnh `python src/data/profile_m5.py`. Nhóm cần xác nhận danh sách này trước H02.

Trong 300 chuỗi đã chọn, file evaluation có 1.941 ngày và 582.300 ô doanh số. Không có doanh số thiếu; 378.662 ô (65,03%) có doanh số bằng 0. Tổng doanh số quan sát được là 748.327 sản phẩm. Các số liệu này chỉ áp dụng cho mẫu MVP, không đại diện cho toàn bộ dữ liệu M5.

Ở H02, lọc theo cửa hàng và sản phẩm trước khi chuyển dữ liệu sales từ dạng nhiều cột sang dạng từng dòng. Giữ các ngày doanh số bằng 0. Ghép lịch theo `d`, sau đó ghép giá theo `store_id`, `item_id`, `wm_yr_wk`.

## Thông tin bàn giao cho nhóm

- Hiếu: dùng `sales_train_evaluation.csv` để kiểm thử dự báo trên dữ liệu đã biết. Mốc đề xuất: huấn luyện đến `d_1885` (27/03/2016), tập kiểm định `d_1886`–`d_1913` (28/03–24/04/2016), tập kiểm tra cuối `d_1914`–`d_1941` (25/04–22/05/2016). Thống nhất danh sách sản phẩm trước khi huấn luyện.
- Quân: chuẩn bị các container Blob và quyền truy cập cho dữ liệu gốc, sau đó là Parquet. Các file CSV không được đưa vào Git.
- Lâm: dùng `store_id=CA_1` và các `item_id` trong danh sách MVP cho phạm vi API/giao diện đầu tiên; dự báo 28 ngày.

Nhóm còn cần xác nhận phạm vi MVP và cấu trúc dữ liệu trao đổi của API trước khi đánh dấu GĐ1 hoàn thành.
