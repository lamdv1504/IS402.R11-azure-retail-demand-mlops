# H04 kết quả kiểm thử benchmark và ETL

Ngày thực hiện: 21/11/2026. Task H04 của Hùng, GĐ5. Nhánh local:
`feature/hung-gd5-h04-benchmark-etl`. Git name/email hiện tại:
`THung1011 <23520562@gm.uit.edu.vn>`. Chưa commit hoặc push trong lượt triển khai.

## Đầu vào đã kiểm tra

Có đủ raw sales evaluation, calendar, sell_prices, catalog 300 item, Parquet H02,
log H02 và tài liệu Q02 của Quân. H04 không cần file model/frontend mới từ Hiếu
hoặc Lâm. File nguồn H02 và dữ liệu local được giữ nguyên; fingerprint trước/sau
lượt benchmark khớp. Thay đổi xóa `reports/Lam/.gitkeep` có sẵn trước khi làm H04
được giữ nguyên, không thuộc thay đổi H04.

## Số đo local thật

Đã chạy `python -B src/data/benchmark.py --sizes 100 300 --repeats 3`.
JSON có 78 mẫu (13 bước × 2 scope × 3 vòng), bảng tổng hợp có 26 nhóm.

| Scope | Dòng long | Ngày | Lặp |
| --- | --- | --- | --- |
| CA_1 / 100 item | 194.100 | 1.941 | 3 |
| CA_1 / 300 item | 582.300 | 1.941 | 3 |

Với 300 item, long CSV 75.568.422 byte, Parquet 620.521 byte. Thời gian đọc trung
bình long CSV 0,603649 s và Parquet 0,095807 s; tỷ lệ thời gian CSV/Parquet là 6,30
trong điều kiện lượt đo này. Mọi bản đọc long/Parquet và kết quả ETL đều đã đối
chiếu với H02 (dung sai float 1e-5); không dùng file raw đầy đủ để suy ra tỷ lệ nén
cho subset.

Pandas phát `DtypeWarning` khi suy luận hai cột sự kiện thưa trong long CSV.
Phép đo giữ nguyên suy luận CSV mặc định; kiểm tra giá trị sau đọc đã chuẩn hóa
cột chuỗi/category và vẫn đạt. Đây là khác biệt cách lưu/đọc CSV so với schema
được lưu sẵn trong Parquet; không khẳng định chúng có cùng dtype vật lý sau đọc.

RAM ghi trong JSON là RSS toàn tiến trình lấy mẫu 20 ms, bao gồm dữ liệu tham
chiếu H02. OS cache không được xóa và phép đo không phải cold cache. Scope lớn hơn
300 item chưa được đo. Xem [bảng benchmark và phương pháp](benchmark.md),
[JSON từng lần đo](h04_benchmark_log.json), [CSV tổng hợp](h04_benchmark.csv).

## Kiểm thử và dependency

| Kiểm tra | Kết quả |
| --- | --- |
| `test_benchmark.py` | PASS 9/9; dữ liệu tạm/fake SDK, không gọi Azure. |
| `test_project_paths.py` | PASS 2/2; checksum và liên kết cũ vẫn đúng. |
| `pip check` | PASS; không có dependency xung đột. |
| `git diff --check` | PASS; không có lỗi whitespace trong diff tracked. |

Test H04 kiểm tra chọn scope ổn định, bảo vệ dữ liệu gốc, ETL/đọc lại khớp H02,
thống kê riêng theo scope, từ chối giá trị sai/calendar trùng, từ chối ghi đè báo
cáo, Blob prefix UUID riêng, upload không ghi đè và download sai hash/lỗi SDK
không lộ secret. Đã cài psutil 7.2.2 qua `requirements-benchmark.txt`.

## Phần Azure còn lại

Kiểm tra xác thực SDK local trả `ClientAuthenticationError`; không có phiên đăng
nhập sẵn có và không mở đăng nhập tương tác. Không có `.env` hoặc biến connection
string trong lượt này. Phần Blob trong báo cáo là `not_run`; chưa có số đo upload/
download Azure thật. Test fake SDK không được dùng làm số liệu cloud.

Sau khi cấu hình xác thực theo [hướng dẫn H03](../../docs/Hung/h03_blob_handoff.md),
chạy H04 với `--azure` và thư mục báo cáo mới theo
[hướng dẫn H04](../../docs/Hung/h04_benchmark_etl.md). Script tạo Blob test mới dưới
`benchmarks/h04/<run_id>/`, giữ nguyên Blob H03; URI test được ghi để truy vết.
Chưa chốt H04 toàn bộ khi chưa có số đo Azure này.
