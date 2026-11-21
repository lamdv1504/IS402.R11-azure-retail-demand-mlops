# H03 đưa dữ liệu M5 lên Azure Blob

H03 thuộc GĐ2 của Hùng. Dữ liệu H02 và tài liệu Q02 đã có đủ; người dùng cho biết
đã upload bằng Portal. Script [upload_blob.py](../../src/data/upload_blob.py)
kiểm tra các Blob hiện có bằng cách tải từng khối và đối chiếu SHA-256 với local.
Các Blob cũ được giữ nguyên, kể cả khi khác nội dung.

## Dữ liệu và địa chỉ bàn giao cho Hiếu

Theo [Q02 của Quân](../Quan/azure_infrastructure_report.md), Storage Account là
`m5retailstore2026`, thuộc Resource Group `rg-mlops-retail`. Cấu hình mặc định nằm
trong [blob_config.json](../../src/data/blob_config.json). Cần đối chiếu với URL
file thực tế trên Portal nếu đã upload bằng một đường dẫn khác.
Nếu file đã nằm ngay ở gốc container, có thể đặt prefix tương ứng thành chuỗi
rỗng để xác minh đúng vị trí. Đây không phải đường dẫn version `v1` mặc định;
cần thống nhất vị trí bàn giao có version trước khi chốt H03. Script không di
chuyển hoặc sửa các Blob đã có.

| Dữ liệu local | Container | Blob path |
| --- | --- | --- |
| 5 CSV trong `data/raw/` | `raw-data` | `raw/m5/<tên-file>.csv` |
| `data/processed/m5_sales_processed.parquet` | `processed-data` | `processed/m5/v1/m5_sales_processed.parquet` |

Blob URI Parquet theo cấu hình:

```text
https://m5retailstore2026.blob.core.windows.net/processed-data/processed/m5/v1/m5_sales_processed.parquet
```

Data version là `m5-ca1-300-v1`. Parquet gồm CA_1, 300 sản phẩm, 1.941 ngày,
582.300 dòng và 22 cột, từ 29/01/2011 đến 22/05/2016. File raw vẫn là dữ liệu M5
gốc có phạm vi lớn hơn MVP; không mô tả các CSV này là dữ liệu chỉ có 300 item.
[H02](../../reports/Hung/h02_processing.md) mô tả schema và cách giữ zero sales,
giá thiếu. Không cần chạy lại H02 để xác minh một upload đã có.

URI trên là địa chỉ dự kiến từ cấu hình. Chỉ khi lệnh `verify` trả `verified` mới
có minh chứng nội dung Blob trùng local. `plan` không truy cập Azure.

## Cài thư viện và lập danh sách local

Chạy từ thư mục gốc repository:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-storage.txt
.\.venv-ml\Scripts\python.exe -B src/data/upload_blob.py --mode plan
```

Nếu máy chưa có `.venv-ml`, tạo bằng `python -m venv .venv-ml` trước khi cài.
Lệnh `plan` kiểm tra H02/catalog, cột và số dòng Parquet, số ngày trên mỗi chuỗi,
phạm vi item/store; ghi schema Arrow, dung lượng, SHA-256 và URI của từng file.
Log mặc định: [h03_blob_plan.json](../../reports/Hung/h03_blob_plan.json).
Trạng thái `planned` và `remote.status=not_checked` chỉ xác nhận dữ liệu local.

## Xác thực trên máy local

Chọn một trong hai cách. Không cần đăng nhập tài khoản của mọi thành viên.
Hiện có thể dùng tài khoản Quân được cho phép để thực hiện H03; ghi đúng tài khoản
thực tế trong phần minh chứng, không suy ra danh tính từ tên task.

**Microsoft Entra ID:** Quân cấp quyền dữ liệu Blob thích hợp cho tài khoản đăng
nhập. Đọc/xác minh cần `Storage Blob Data Reader`; upload cần
`Storage Blob Data Contributor`. Mở container trên Portal còn cần quyền quản lý
`Reader` trên Storage Account hoặc cấp cao hơn.

Nếu đã cài Azure CLI, đăng nhập vào directory của nhóm trước khi chạy script:

```powershell
az login --tenant <TENANT_ID_CUA_NHOM>
```

Script sử dụng `DefaultAzureCredential`, không tự mở trình duyệt để đăng nhập.
Đăng nhập Azure Portal không tự tạo phiên đăng nhập cho SDK local.

**Connection string:** cách Q02 đã mô tả. Sao chép nội dung
[.env.example](../../.env.example) thành `.env` tại gốc repo, rồi tự điền
`AZURE_STORAGE_CONNECTION_STRING` trên máy local. File `.env` được Git bỏ qua.
Script tự đọc file này và không ghi đè biến môi trường đã có. Nếu dùng Entra ID,
để biến connection string trống và xóa giá trị cũ khỏi môi trường terminal.

Không đặt key, connection string hoặc SAS token trong JSON cấu hình, commit, ảnh
hay chat nhóm. Script không nhận secret qua tham số CLI và không lưu thông điệp
lỗi thô của SDK vào log. Cấu hình và manifest chỉ chứa URI thuần, không kèm query.

## Xác minh những file đã upload

Vì dữ liệu đã được upload, bắt đầu bằng Parquet để kiểm tra đường dẫn/quyền:

```powershell
.\.venv-ml\Scripts\python.exe -B src/data/upload_blob.py --mode verify --files processed --log reports/Hung/h03_processed_verify.json
```

Sau khi Parquet đạt, xác minh cả 6 file:

```powershell
.\.venv-ml\Scripts\python.exe -B src/data/upload_blob.py --mode verify
```

`verify` chỉ đọc metadata và download, không upload hay sửa metadata. Chế độ này
tải toàn bộ nội dung để tính SHA-256, nên kiểm tra 5 CSV sẽ truyền khoảng 430 MiB
raw, ngoài file Parquet. Log ghi size, ETag, thời điểm last modified và thời điểm
xác minh. ETag ràng buộc phiên bản trong lúc download. Parquet trùng SHA-256 cũng
đảm bảo schema và số dòng trùng bản local đã kiểm tra.

Log mặc định là `reports/Hung/h03_blob_verify.json`. Exit code 0 và
`status=verified` xác nhận các file đã chọn; exit code 1 là chưa đạt. Chạy chỉ
`--files processed` không xác nhận các CSV raw.

## Upload bổ sung khi thiếu file

Chỉ dùng chế độ này khi muốn bổ sung file chưa có trên Blob:

```powershell
.\.venv-ml\Scripts\python.exe -B src/data/upload_blob.py --mode upload
```

File có sẵn được kiểm tra; file chưa có mới được upload với `overwrite=False`,
sau đó download để xác minh. Không có thao tác tạo container, đổi quyền public,
xóa Blob hoặc ghi đè. Sai size/hash sẽ dừng và ghi lỗi. Nếu đã upload một số file
mới trước khi lỗi ở file tiếp theo, log giữ các hành động đã hoàn tất; có thể chạy
lại sau khi xử lý nguyên nhân. Container và quyền truy cập cần Quân chuẩn bị trước.

## Lỗi thường gặp

| Mã lỗi | Xử lý |
| --- | --- |
| `BLOB_MISSING` | Đối chiếu container/prefix với URL file đã upload; sửa cấu hình hoặc bổ sung file thiếu. |
| `SIZE_MISMATCH`, `HASH_MISMATCH` | Blob khác local; giữ nguyên, trao đổi với nhóm để xác định bản đúng hoặc dùng version/prefix mới. |
| `ACCOUNT_MISMATCH` | Kiểm tra account trong `.env`, biến môi trường và cấu hình; script từ chối gửi dữ liệu sang account khác. |
| `H02_MISMATCH`, `INVALID_SCOPE` | Kiểm tra Parquet, catalog và bàn giao H02 trước khi tiếp tục. |
| `ClientAuthenticationError` hoặc HTTP 403 | Kiểm tra đăng nhập SDK, RBAC và mạng Storage Account. Không bật public để sửa lỗi quyền. |
| `ResourceExistsError`, `ResourceModifiedError` | Blob thay đổi trong lúc chạy; kiểm tra lại rồi chạy `verify`. |

## Hiếu truy cập dữ liệu để huấn luyện

Gửi Hiếu URI thuần, account/container/path, data version, phạm vi, schema và log
`verified`; không gửi secret. Quân cấp quyền đọc cho Hiếu và identity thực sự chạy
Azure ML job. Hiếu có thể download bằng Portal với quyền tương ứng hoặc khai báo
Azure ML datastore trỏ đúng container `processed-data`.

Datastore mặc định `workspaceblobstore` có thể trỏ một container khác; cần kiểm tra
account và container thay vì suy ra từ việc workspace liên kết cùng Storage Account.
Khi dùng datastore có tên `<datastore_name>`, đường dẫn job là:

```text
azureml://datastores/<datastore_name>/paths/processed/m5/v1/m5_sales_processed.parquet
```

Đăng ký datastore/chạy training job thuộc HI06; H03 bàn giao dữ liệu và quyền đọc.

## Kiểm thử và nghiệm thu

```powershell
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_upload_blob.py -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s tests -p test_project_paths.py -v
```

Các test H03 dùng file tạm và fake SDK, không gọi Azure. CI chạy các test này cần
cài `requirements-storage.txt` ngoài dependencies của những test ML khác.
Kết quả local và phần cần xác minh Azure ở
[báo cáo H03](../../reports/Hung/h03_verification_report.md).

Để chốt H03 cần log `verified` trên dữ liệu thật, ảnh Blob trên Portal và Hiếu
xác nhận đọc được bằng đúng tài khoản/identity. Thông báo upload thành công trên
Portal hoặc `plan` local chưa thay thế các bước này.

## Tài liệu Azure

- [Blob SDK và xác thực Python](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python)
- [Quyền đọc dữ liệu trên Portal](https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-data-operations-portal)
- [Azure ML datastore và container mặc định](https://learn.microsoft.com/en-us/azure/machine-learning/concept-data?view=azureml-api-2)
