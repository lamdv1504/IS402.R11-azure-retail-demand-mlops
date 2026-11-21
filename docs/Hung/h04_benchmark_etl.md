# H04 benchmark và ETL của Hùng

H04 thuộc GĐ5. Script [benchmark.py](../../src/data/benchmark.py) đo lặp các bước
đọc CSV, melt, join lịch/giá, giảm kiểu dữ liệu, ghi/đọc Parquet và truyền file qua
Blob. Kết quả chỉ áp dụng scope và cấu hình máy đã đo; không đại diện toàn M5.

## Đầu vào và phạm vi

Đầu vào local đã có từ [H02](../../reports/Hung/h02_processing.md):
`data/raw/sales_train_evaluation.csv`, `calendar.csv`, `sell_prices.csv`, catalog
`reports/Hung/m5_mvp_items.csv`, Parquet và log H02. Cấu hình Blob dùng lại
[H03](h03_blob_handoff.md) và [Q02 của Quân](../Quan/azure_infrastructure_report.md).
H04 không cần thêm model, frontend hoặc file bàn giao của Hiếu/Lâm.

Scope mặc định là CA_1 / 100 và 300 item, giữ đủ 1.941 ngày. Mẫu 100 item được
chọn ổn định bằng cách xen kẽ category từ catalog, nên có 34 FOODS, 33 HOBBIES,
33 HOUSEHOLD. Danh sách item chính xác và số dòng nằm trong JSON của lần đo.
Script từ chối scope lớn hơn catalog; không tự tải hoặc suy diễn toàn dataset.

## Chạy benchmark local

Từ thư mục gốc repository:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-benchmark.txt
.\.venv-ml\Scripts\python.exe -B src/data/benchmark.py --sizes 100 300 --repeats 3
```

Nếu chưa có môi trường Python, tạo `.venv-ml` trước bằng `python -m venv .venv-ml`.
Lượt mặc định không gọi Azure. Báo cáo được lưu theo cấu trúc thành viên:

- `reports/Hung/benchmark.md`: bảng đo và nhận xét.
- `reports/Hung/h04_benchmark_log.json`: từng mẫu thời gian/RAM, máy, data version,
  base Git commit, source hash chuẩn hóa LF và fingerprint dữ liệu local.
- `reports/Hung/h04_benchmark.csv`: tổng hợp mean, median, min, max, stdev theo bước/scope.

Chạy lại với một thư mục báo cáo mới để giữ nguyên kết quả cũ:

```powershell
.\.venv-ml\Scripts\python.exe -B src/data/benchmark.py --sizes 100 300 --repeats 3 --output-dir reports/Hung/h04-rerun-01
```

Script không ghi đè báo cáo đã có. Các CSV/Parquet phục vụ phép đo được tạo trong
thư mục tạm riêng rồi tự dọn; không sửa raw, file Parquet H02 hoặc log/model của
các thành viên. Sau phép đo, fingerprint dữ liệu đầu vào được đối chiếu lại.

## Đọc số liệu đúng phạm vi

`scan_sales_raw` và `scan_prices_raw` quét file raw theo chunk rồi lọc item/store;
số dòng đầu ra của chúng là subset, nhưng thời gian bao gồm việc quét raw lớn.
Không so sánh hai bước này với Parquet MVP như phép đo tốc độ đọc cùng dung lượng.

Các bước `read_wide_mvp_csv`, `read_long_mvp_csv`, `read_mvp_parquet` chỉ đọc file
của chính scope đang đo. Wide chứa sales/định danh; long CSV và Parquet có cùng
các cột lịch/giá. Tỷ lệ nén được tính giữa long CSV và Parquet cùng scope/cột.
Sau mỗi vòng, dữ liệu ETL và các bản đọc lại được kiểm tra giá trị với H02,
giữ zero sales, giá thiếu và số dòng; dung sai float là 1e-5.

Thời gian dùng `time.perf_counter`, đơn vị giây. Thứ tự ba phép đọc được hoán đổi
theo seed cố định; không xóa OS cache và không gọi kết quả là cold-cache benchmark.
Các bước chạy trong cùng tiến trình. RSS lấy mẫu mỗi 20 ms là RAM toàn tiến trình,
bao gồm dữ liệu H02 tham chiếu đang giữ trong RAM; không phải RAM tăng riêng của
một thao tác và có thể không bắt được đỉnh rất ngắn.

## Đo Azure Blob khi có xác thực

Lượt local hiện chưa cung cấp số đo cloud. Cần cấu hình Entra ID/SDK hoặc
connection string local theo hướng dẫn H03; không gửi key/token qua GitHub/chat.
Tài khoản ghi Blob phải có quyền phù hợp trên `processed-data`.

```powershell
.\.venv-ml\Scripts\python.exe -B src/data/benchmark.py --sizes 100 300 --repeats 3 --azure --output-dir reports/Hung/h04-with-azure-01
```

Chế độ này đo upload file Parquet H02 có kích thước xác định (scope 300 item), sau
đó download theo ETag và đối chiếu SHA-256. Thời gian download bao gồm cả tính hash,
không được mô tả là băng thông mạng thuần. Chỉ tạo các Blob test mới ở:

```text
processed-data/benchmarks/h04/<run_id>/repeat-<n>.parquet
```

`run_id` là UUID mới, `overwrite=False`; không sửa Blob sản xuất H03 và không tạo
container. Blob test được giữ lại để truy vết; URI cụ thể có trong JSON. Mỗi lần
lặp giữ thêm một bản Parquet khoảng 620 KB; Quân/Hùng có thể dọn đúng các URI test
sau khi lưu minh chứng. Script không tự xóa Blob.

Azure có trạng thái `measured`, `failed` hoặc `not_run`. Test fake SDK không được
ghi nhận là đo Azure thật. Nếu Azure lỗi, JSON giữ những mẫu/hành động đã thực
hiện và thông tin lỗi đã lọc secret; tiến trình trả exit code 1.

## Quy trình ETL và liên kết training run

Raw sales → lọc catalog store/item → melt wide sang long → join calendar theo `d`
→ join giá theo `store_id,item_id,wm_yr_wk` → downcast → Parquet → Blob.

H02 là script xử lý dữ liệu chính; H04 dùng cùng hàm đọc/filter và đối chiếu kết
quả ETL với Parquet H02. H03 chuyển dữ liệu lên đường dẫn có version như
`processed/m5/v1/`. Data version hiện tại là `m5-ca1-300-v1`.

Khi bàn giao cho một training run, giữ data version, URI Blob thực tế, SHA-256,
code commit/source hash và báo cáo H04 cùng run ID/model version của HI06.
Run ID và metric lấy từ lượt Azure thật của Hiếu, không tự gán từ benchmark local.
H04 chưa được chốt toàn bộ khi chưa có thời gian upload/download thật trên Blob.

## Kiểm thử

```powershell
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_benchmark.py -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_project_paths.py -v
```

Test dùng dữ liệu tạm/fake SDK để kiểm tra giá trị ETL, nhóm thống kê, scope,
bảo vệ file gốc, prefix Blob riêng và lỗi download/secret. CI chạy test này cần
cài `requirements-benchmark.txt` cùng dependencies cho các test ML khác.
