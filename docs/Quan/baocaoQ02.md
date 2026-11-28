# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 2 (Q02): TẠO VÀ CẤU HÌNH AZURE BLOB STORAGE

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure
* **Môn học:** Điện toán đám mây (IS402.R11)
* **Phụ trách:** Võ Hồ Trung Quân
* **Trạng thái:** Hoàn thành

## 1. Mục tiêu giai đoạn Q02

Khởi tạo dịch vụ lưu trữ đối tượng tập trung (**Azure Storage Account**) bên trong Resource Group `rg-mlops-retail`, phân tầng cấu trúc thư mục (**Blob Containers**) theo vòng đời dữ liệu của bài toán M5 và thiết lập cơ chế phân quyền truy cập bảo mật (**Azure RBAC** & quản lý khóa bí mật) để bàn giao hạ tầng lưu trữ cho các thành viên thực hiện xử lý dữ liệu (ETL) và huấn luyện mô hình.

## 2. Chi tiết các bước thực hiện

### 2.1. Khởi tạo Azure Storage Account

Tạo tài khoản lưu trữ dùng chung cho toàn dự án với các thông số tối ưu cho phạm vi MVP và gói **Azure for Students**:

* **Subscription:** `Azure for Students`
* **Resource Group:** `rg-mlops-retail`
* **Storage Account Name:** `m5retailstore2026`
* **Region (Khu vực):** `Japan East` (đồng bộ với Resource Group)
* **Primary Service:** `Azure Blob Storage or Azure Data Lake Storage`
* **Performance:** `Standard` (General-purpose v2)
* **Redundancy:** `Locally redundant storage (LRS)` – tối ưu chi phí lưu trữ ở mức thấp nhất cho môi trường đồ án.
* **Cấu hình bảo mật mặc định:** Bật truyền tải bảo mật HTTPS (`Secure transfer: Enabled`), tắt truy cập ẩn danh công khai (`Blob anonymous access: Disabled`) và áp dụng chuẩn mã hóa TLS 1.2 trở lên.

*(Minh chứng: Ảnh chụp màn hình cấu hình Basics, Review + create và trạng thái triển khai thành công Storage Account `m5retailstore2026`)*

### 2.2. Khởi tạo cấu trúc 4 Blob Containers phân tầng dữ liệu

Bên trong Storage Account `m5retailstore2026`, khởi tạo đúng 4 container ở chế độ truy cập riêng tư (**Private**) nhằm tách bạch rõ ràng các giai đoạn xử lý dữ liệu và tránh ghi đè dữ liệu gốc:

| Tên Container | Chế độ truy cập | Mục đích lưu trữ trong hệ thống |
| :--- | :--- | :--- |
| `raw-data` | `Private` | Lưu trữ nguyên trạng 5 tệp CSV gốc của bộ dữ liệu Kaggle M5 (`sales_train_evaluation.csv`, `calendar.csv`, `sell_prices.csv`...). |
| `processed-data` | `Private` | Lưu trữ dữ liệu sạch sau quy trình ETL dưới định dạng cột tối ưu Parquet (`m5_sales_processed.parquet`). |
| `model-artifacts` | `Private` | Lưu trữ các tệp mô hình đã huấn luyện và thành phần phục vụ suy luận. |
| `experiment-results` | `Private` | Lưu trữ các bảng kết quả đánh giá, chỉ số sai số (`RMSE`, `MAE`) và dữ liệu thực nghiệm. |

*(Minh chứng: Ảnh chụp màn hình danh sách 4 containers `raw-data`, `processed-data`, `model-artifacts`, `experiment-results` ở trạng thái Private)*

### 2.3. Cấu hình phân quyền truy cập (Azure RBAC) và bảo mật thông tin kết nối

* **Phân quyền vai trò (Azure RBAC):** Áp dụng cơ chế kiểm soát truy cập dựa trên vai trò trực tiếp trên tài khoản Azure của từng thành viên (`Owner`, `Contributor`, `Storage Blob Data Contributor`) và Managed Identity của Azure ML Workspace (`m5-ml-workspace`) theo nguyên tắc đặc quyền tối thiểu.
* **Quản lý khóa truy cập (Access Key & Connection String):** Trích xuất thông tin kết nối phục vụ cho các script Python tự động hóa (upload/download dữ liệu từ môi trường cục bộ), đồng thời áp dụng quy tắc bảo mật nghiêm ngặt: **tuyệt đối không lưu trực tiếp khóa bí mật vào mã nguồn hay đẩy lên GitHub**.

*(Minh chứng: Ảnh chụp màn hình cấu hình Access Control (IAM) và Role assignments)*

## 3. Đầu ra bàn giao hạ tầng Q02 (Infrastructure Handover)

Thông tin hạ tầng lưu trữ được bàn giao cho nhóm (đặc biệt là thành viên phụ trách Data Engineering thực hiện bước ETL và upload tệp Parquet):

| Hạng mục | Thông tin bàn giao |
| :--- | :--- |
| **Storage Account Name** | `m5retailstore2026` |
| **Resource Group / Region** | `rg-mlops-retail` / `Japan East` |
| **Container đích (Upload Parquet)** | `processed-data` |
| **URL / Blob URI của container** | `https://m5retailstore2026.blob.core.windows.net/processed-data` |
| **Connection String (Mẫu biến môi trường)** | `DefaultEndpointsProtocol=https;AccountName=m5retailstore2026;AccountKey=<YOUR_STORAGE_ACCOUNT_KEY>;EndpointSuffix=core.windows.net` |

## 4. Lưu ý bảo mật vận hành

> **Cảnh báo bảo mật:** Toàn bộ 4 container trên `m5retailstore2026` đều thiết lập ở mức độ **Private**. Khi lập trình bằng Python để đọc/ghi dữ liệu lên Blob Storage, các thành viên bắt buộc phải lưu `Connection String` trong tệp `.env` cục bộ (đã được khai báo trong `.gitignore`), tuyệt đối không hard-code vào mã nguồn và đẩy lên kho GitHub chung để tránh nguy cơ rò rỉ khóa và phát sinh chi phí trái phép.

## 5. Kết luận giai đoạn Q02

1. **Hoàn thiện hạ tầng lưu trữ:** Đã khởi tạo thành công Storage Account `m5retailstore2026` tại khu vực `Japan East` với cấu hình `Standard LRS` tối ưu chi phí.
2. **Chuẩn hóa kiến trúc dữ liệu:** Tổ chức phân tầng 4 container (`raw-data`, `processed-data`, `model-artifacts`, `experiment-results`) giúp tách bạch dữ liệu thô, dữ liệu sạch dạng Parquet và kết quả mô hình.
3. **Đảm bảo an toàn truy cập:** Thiết lập đầy đủ phân quyền Azure RBAC và bàn giao thông tin kết nối an toàn cho khâu xử lý dữ liệu.

**Tình trạng:** Hạ tầng lưu trữ đám mây đã sẵn sàng để chuyển sang **Giai đoạn Q03: Thiết lập môi trường huấn luyện trên Azure Machine Learning**.