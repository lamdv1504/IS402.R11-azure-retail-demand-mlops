# H03 kết quả kiểm tra upload và bàn giao Blob

Ngày kiểm tra local: 21/11/2026. Task H03 của Hùng, GĐ2; nhánh
`feature/hung-gd2-h03-azure-blob-upload`.

## Đầu vào và trạng thái Azure

Đã có [bàn giao Q02](../../docs/Quan/azure_infrastructure_report.md),
[H02](h02_processing.md), catalog MVP, đủ 5 CSV và Parquet local. Không thiếu file
đầu vào bắt buộc từ thành viên khác khi triển khai phần code.
Người dùng cho biết đã upload lên Azure bằng Portal, dự kiến dùng tài khoản Quân.
Tên tài khoản thực tế và kết quả quyền đọc của Hiếu cần xác nhận ở bước nghiệm thu.

Máy hiện chưa có Azure CLI/phiên đăng nhập SDK, `.env` hoặc biến connection string.
Vì vậy chưa chạy xác minh với Azure thật. URI trong manifest được dựng từ Q02 và
cấu hình, chưa phải bằng chứng file đã tồn tại ở chính đường dẫn đó.

## Kết quả kiểm tra local

Lệnh `python -B src/data/upload_blob.py --mode plan` đã chạy thành công trong
`.venv-ml`; [manifest](h03_blob_plan.json) có `status=planned`, 6 file đều
`remote.status=not_checked`.

| Dữ liệu | Kết quả local |
| --- | --- |
| CSV raw | 5 file, tổng 450.472.284 byte; giữ nguyên phạm vi M5 gốc. |
| Parquet H02 | 620.521 byte; 582.300 dòng, 22 cột; CA_1 / 300 sản phẩm. |
| Khoảng ngày Parquet | 29/01/2011 đến 22/05/2016; 1.941 ngày trên mỗi chuỗi. |
| SHA-256 Parquet | `b00292494f0056a0c281ecb9c144110a93b52b415dddb1397b93eee9bed70aff` |
| Đối chiếu H02/catalog | Kích thước, cột, số dòng, phạm vi chuỗi và số ngày khớp; schema Arrow đã được ghi vào manifest. |

## Script và kiểm thử

[upload_blob.py](../../src/data/upload_blob.py) hỗ trợ `plan`, `verify`, `upload`.
`verify` chỉ đọc metadata/download. `upload` chỉ tạo Blob thiếu với
`overwrite=False`, sau đó xác minh bằng SHA-256; không tạo container, xóa hoặc
sửa Blob hiện có. Log lỗi SDK không chứa thông điệp thô có thể kèm secret.

Test chạy bằng unittest với file tạm/fake SDK, không gọi Azure. Các trường hợp:
manifest local, thiếu file, sai catalog/H02, cấu hình có query hoặc đường dẫn
ngoài repo, URI không chứa SAS, upload có sẵn ở gốc container, xác minh upload
Portal, thiếu Blob, upload bổ sung, size/hash không khớp, upload race, local file
thay đổi, ETag đổi giữa lúc tải, lỗi SDK có secret, log bảo vệ file H02, account
khác cấu hình và CLI trả đúng exit code.

Lệnh kiểm tra:

```powershell
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_upload_blob.py -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_project_paths.py -v
.\.venv-ml\Scripts\python.exe -m pip check
```

| Kiểm tra | Kết quả |
| --- | --- |
| Unit test H03 | PASS 20/20; fake SDK, không gọi Azure. |
| Liên kết tài liệu và checksum bàn giao | PASS 2/2. |
| `pip check` | PASS, không có dependency bị xung đột. |
| `git diff --check` | PASS, không có lỗi whitespace trong các thay đổi tracked. |
| Kiểm tra Git ignore | `.env`, `.env.local`, `.env.production` được bỏ qua; `.env.example` có thể commit. |

Phiên bản đã cài: Python 3.13; azure-storage-blob 12.31.1, azure-identity 1.27.0,
azure-core 1.41.0, python-dotenv 1.2.4, pandas 3.1.1, pyarrow 26.0.1.

## Bước nghiệm thu Azure còn lại

1. Đối chiếu Blob URI thực tế với cấu hình, xác thực SDK local bằng Entra ID hoặc
   connection string trong `.env` riêng của máy.
2. Chạy `verify --files processed`, sau đó `verify` cho toàn bộ dữ liệu; cần log
   `status=verified`, từng file trùng SHA-256 và có metadata thời gian thật.
3. Lưu ảnh Portal thể hiện account, container, path và size; không chụp secret.
4. Hiếu/identity chạy training xác nhận đọc được đúng Parquet, schema và data version.

Đã có code và hướng dẫn để thực hiện các bước trên; chưa đánh dấu H03 hoàn tất
toàn bộ khi chưa có minh chứng Azure và xác nhận đọc dữ liệu của Hiếu.
[Hướng dẫn truy cập và bàn giao](../../docs/Hung/h03_blob_handoff.md).
