# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 3 (Q03): THIẾT LẬP AZURE MACHINE LEARNING WORKSPACE

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure
* **Môn học:** Điện toán đám mây (IS402.R11)
* **Phụ trách:** Võ Hồ Trung Quân
* **Trạng thái:** Hoàn thành

## 1. Mục tiêu giai đoạn Q03

Khởi tạo không gian làm việc trung tâm (**Azure Machine Learning Workspace**) để quản lý vòng đời học máy (MLOps), cấp phát tài nguyên tính toán (**Compute**) có cơ chế tự động tắt tối ưu chi phí, cấu hình phân quyền truy cập (**IAM**) cho thành viên Data Scientist và liên kết trực tiếp dữ liệu từ **Azure Blob Storage** (`m5retailstore2026`) thông qua hệ thống **Datastores**.

## 2. Chi tiết các bước thực hiện

### 2.1. Khởi tạo Azure Machine Learning Workspace

Tạo Workspace dùng chung trong Resource Group `rg-mlops-retail` tại khu vực `Japan East`, đồng thời liên kết trực tiếp với Storage Account đã khởi tạo ở giai đoạn Q02:

* **Workspace Name:** `m5-ml-workspace`
* **Subscription:** `Azure for Students`
* **Resource Group:** `rg-mlops-retail`
* **Region (Khu vực):** `Japan East`
* **Storage Account liên kết:** `m5retailstore2026`
* **Tài nguyên phụ trợ tự động khởi tạo:** Key Vault (`m5mlworkspace3362745321`) và Application Insights (`m5mlworkspace2649560386`).
* **Chế độ truy cập & Identity:** `Public` và sử dụng `System assigned` Managed Identity.

*(Minh chứng: Ảnh chụp màn hình cấu hình Basics, Validation passed và giao diện Overview của `m5-ml-workspace`)*

### 2.2. Cấp phát tài nguyên tính toán (Compute) và tối ưu chi phí

Truy cập **Azure Machine Learning Studio** (`https://ml.azure.com/`), tiến hành khởi tạo cụm xử lý CPU phục vụ chạy Notebook, tạo đặc trưng (Feature Engineering) và huấn luyện mô hình dự báo M5:

* **Tên tài nguyên Compute:** `m5-cpu-cluster`
* **Loại máy ảo (Virtual machine type):** `CPU`
* **Cấu hình phần cứng (VM size):** `Standard_DS11_v2` (2 vCPUs, 14 GB RAM, 28 GB Storage - thuộc nhóm *Memory optimized*, phù hợp xử lý dữ liệu chuỗi thời gian M5 và nằm trọn trong hạn mức 6 vCPU của vùng Japan East).
* **Cấu hình tối ưu chi phí (Idle Shutdown):** Bật chế độ tự động tắt sau **15 phút** không hoạt động (`Enable idle shutdown: 15 Minutes of inactivity`) và chủ động đặt trạng thái mặc định là **`Stopped`** sau khi khởi tạo xong để bảo toàn ngân sách credit sinh viên.
* **Phân quyền sử dụng (User Assignment):** Gán trực tiếp cho thành viên **Trần Đình Trung Hiếu** (Data Scientist).

*(Minh chứng: Ảnh chụp màn hình tạo Compute `Standard_DS11_v2`, thiết lập Idle shutdown 15 phút và trạng thái `Stopped`)*

### 2.3. Phân quyền truy cập Workspace (Azure RBAC)

Tại mục **Access control (IAM)** của `m5-ml-workspace`, thực hiện cấp quyền cho thành viên phụ trách huấn luyện mô hình theo đúng nguyên tắc đặc quyền tối thiểu:

* **Vai trò (Role):** `AzureML Data Scientist` (cho phép chạy thực nghiệm, tạo job huấn luyện, thao tác trên Notebook/Compute và đăng ký mô hình lên Model Registry mà không làm thay đổi cấu hình hạ tầng gốc của Workspace).
* **Đối tượng được cấp quyền:** Trần Đình Trung Hiếu (`User`).

*(Minh chứng: Ảnh chụp màn hình Add role assignment `AzureML Data Scientist` cho Trần Đình Trung Hiếu)*

### 2.4. Liên kết dữ liệu từ Blob Storage vào Workspace (Datastores)

Kết nối 4 container từ Storage Account `m5retailstore2026` vào mục **Data** $\rightarrow$ **Datastores** của Azure ML Studio để các script huấn luyện có thể đọc/ghi dữ liệu trực tiếp qua giao thức cloud mà không cần lưu khóa kết nối trong mã nguồn:

| Tên Datastore | Loại dịch vụ | Storage Account | Blob Container đích | Mục đích sử dụng |
| :--- | :--- | :--- | :--- | :--- |
| `ds_raw_data` | Azure Blob Storage | `m5retailstore2026` | `raw-data` | Đọc dữ liệu M5 gốc phục vụ kiểm tra |
| `ds_processed_data` | Azure Blob Storage | `m5retailstore2026` | `processed-data` | Nguồn dữ liệu Parquet chính cho huấn luyện |
| `ds_model_artifacts` | Azure Blob Storage | `m5retailstore2026` | `model-artifacts` | Xuất và lưu trữ tệp mô hình sau khi train |
| `ds_experiment_results` | Azure Blob Storage | `m5retailstore2026` | `experiment-results` | Lưu kết quả đánh giá và chỉ số sai số |

*(Minh chứng: Ảnh chụp màn hình cấu hình `Create datastore` và danh sách 4 Datastores đã kết nối thành công)*

## 3. Đầu ra bàn giao hạ tầng Q03 (Infrastructure Handover)

| Hạng mục | Thông tin bàn giao | Trạng thái |
| :--- | :--- | :--- |
| **Azure ML Workspace** | `m5-ml-workspace` (`Japan East`) | Đã hoạt động (`Succeeded`) |
| **Studio Web URL** | `https://ml.azure.com/` | Sẵn sàng truy cập |
| **CPU Compute** | `m5-cpu-cluster` (`Standard_DS11_v2`, Idle shutdown 15 phút) | Sẵn sàng (`Stopped` để tiết kiệm credit) |
| **Datastores** | `ds_raw_data`, `ds_processed_data`, `ds_model_artifacts`, `ds_experiment_results` | Đã kết nối tới `m5retailstore2026` |
| **Phân quyền IAM** | Role `AzureML Data Scientist` & quyền sử dụng Compute cho Trần Đình Trung Hiếu | Đã kích hoạt |

## 4. Kết luận nghiệm thu giai đoạn Q03

1. **Hoàn thiện hạ tầng ML lõi:** Không gian làm việc `m5-ml-workspace` đã được khởi tạo thành công tại khu vực `Japan East`, tích hợp đồng bộ với Storage Account `m5retailstore2026`, Key Vault và Application Insights.
2. **Tối ưu hiệu năng và chi phí:** Cụm xử lý `m5-cpu-cluster` (`Standard_DS11_v2`) đáp ứng tốt nhu cầu bộ nhớ 14 GB RAM cho bài toán chuỗi thời gian M5, đồng thời được kiểm soát chi phí chặt chẽ nhờ tính năng tự động tắt sau 15 phút nhàn rỗi.
3. **Sẵn sàng bàn giao phát triển mô hình:** Hoàn tất phân quyền `AzureML Data Scientist` và ánh xạ đầy đủ 4 Datastores, sẵn sàng cho bước tạo đặc trưng (Feature Engineering), huấn luyện mô hình và đăng ký lên Model Registry.

**Tình trạng:** Hạ tầng huấn luyện trên Cloud đã sẵn sàng 100% để chuyển sang **Giai đoạn Q04: Huấn luyện mô hình & Tự động hóa CI với Azure DevOps Pipelines**.