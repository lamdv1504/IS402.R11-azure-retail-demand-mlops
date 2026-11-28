# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 5 (Q05): ĐÓNG GÓI DOCKER & ĐẨY LÊN AZURE CONTAINER REGISTRY (ACR)

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure
* **Môn học:** Điện toán đám mây (IS402.R11)
* **Phụ trách:** Võ Hồ Trung Quân
* **Trạng thái:** Hoàn thành

## 1. Mục tiêu giai đoạn Q05

Đóng gói toàn bộ mã nguồn Backend (**FastAPI**), thư viện môi trường và tệp mô hình học máy thành một **Docker image** độc lập thông qua `Dockerfile`. Đồng thời, khởi tạo kho lưu trữ image riêng tư (**Azure Container Registry - ACR**) và tích hợp trực tiếp vào **Azure DevOps Pipelines** để tự động hóa quy trình Build & Push image (`retail-forecast-api:v1`) lên Cloud mỗi khi mã nguồn vượt qua bước kiểm thử CI.

## 2. Chi tiết các bước thực hiện

### 2.1. Khởi tạo Azure Container Registry (ACR)

Khởi tạo kho lưu trữ Docker image riêng tư bên trong Resource Group chung của dự án tại khu vực `Japan East`:

* **Subscription:** `Azure for Students`
* **Resource Group:** `rg-mlops-retail`
* **Registry Name:** `m5retailacr2026`
* **Login Server:** `m5retailacr2026.azurecr.io`
* **Location (Region):** `Japan East`
* **Pricing Plan (SKU):** `Basic` (tối ưu chi phí cho phạm vi đồ án sinh viên)
* **Chế độ phân quyền & xác thực:** Cấu hình `RBAC Registry Permissions` và bật `Admin user` tại mục **Settings $\rightarrow$ Access keys** để hỗ trợ triển khai container trên Azure Container Instances (ACI) ở giai đoạn sau.

*(Minh chứng: Ảnh chụp màn hình khởi tạo `m5retailacr2026`, trạng thái `Provisioning state: Succeeded` và cấu hình Access keys)*

### 2.2. Thiết lập Service Connection kết nối Azure DevOps với ACR

Tại dự án **`M5-Retail-MLOps`** trên Azure DevOps (`Project settings` $\rightarrow$ `Service connections`), tạo kết nối dịch vụ mới để cấp quyền cho Pipeline tự động đẩy image lên ACR mà không cần lưu mật khẩu trong tệp YAML:

* **Loại kết nối:** `Docker Registry` (Azure Container Registry)
* **Phương thức xác thực:** `Service Principal`
* **Subscription:** `Azure for Students`
* **Azure Container Registry đích:** `m5retailacr2026`
* **Service Connection Name:** `ACR-Connection`
* **Phạm vi truy cập:** Bật `Grant access permission to all pipelines`.

*(Minh chứng: Ảnh chụp màn hình cấu hình và xác nhận tạo thành công Service Connection `ACR-Connection`)*

### 2.3. Xây dựng `Dockerfile` đóng gói FastAPI và mô hình dự báo

Viết tệp `Dockerfile` chuẩn hóa môi trường chạy suy luận trên nền ảnh nhẹ `python:3.11-slim`, cài đặt thư viện hệ thống `libgomp1` (phục vụ thực thi mô hình học máy), sao chép mã nguồn Backend cùng các tệp artifacts/báo cáo cần thiết và cấu hình khởi chạy máy chủ **Uvicorn** tại cổng `8000`:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-ml.txt /app/requirements-ml.txt
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ /app/backend/
COPY src/ /app/src/
COPY artifacts/hi05/ /app/artifacts/hi05/
COPY reports/Hung/ /app/reports/Hung/
ENV PYTHONPATH="/app:/app/backend"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Kết hợp cùng tệp `.dockerignore` để loại trừ các tệp tạm, môi trường cục bộ và dữ liệu thô dung lượng lớn, giúp giảm kích thước image và tăng tốc độ build/pull trên Cloud.

### 2.4. Kiểm chứng tự động hóa Build & Push Image trên Pipeline và ACR

Mở rộng tệp `azure-pipelines.yml` thành 2 giai đoạn nối tiếp (**Stage 1:** `CI: lint và test` $\rightarrow$ **Stage 2:** `Build and push API image to ACR`). Khi Stage 1 hoàn thành thành công, hệ thống tự động thực thi job **`BuildAndPushACR`** để đóng gói và đẩy image lên kho `m5retailacr2026`:

* **Lần chạy xác nhận:** Run **`#20261121.6`** (và đồng bộ tiếp trên nhánh `main` ở Run **`#20261121.7`**)
* **Kết quả thực thi:** Cả 2 giai đoạn đều đạt trạng thái xanh (**Passed**):
  * Stage 1 (`CI: lint và test`): `1 phút 03 giây` – Thành công
  * Stage 2 (`Build and push API image to ACR` / Job `BuildAndPushACR`): `2 phút 10 giây` – Thành công
  * Tổng thời gian chạy: `3 phút 25 giây`
* **Kiểm tra kho chứa trên Azure Portal:** Tại `m5retailacr2026` $\rightarrow$ **Services $\rightarrow$ Repositories**, xác nhận repository **`retail-forecast-api`** đã được tạo và chứa phiên bản image gắn thẻ **`v1`** (cùng các tag số thứ tự build như `10`, `11` để hỗ trợ quản lý phiên bản và rollback).

*(Minh chứng: Ảnh chụp màn hình log chạy xanh `BuildAndPushACR` ở Run `#20261121.6` và danh sách tags `v1` trong repository `retail-forecast-api` trên ACR)*

## 3. Đầu ra bàn giao giai đoạn Q05 (Containerization Handover)

| Hạng mục | Thông tin bàn giao | Trạng thái |
| :--- | :--- | :--- |
| **Container Registry (ACR)** | `m5retailacr2026` (`m5retailacr2026.azurecr.io`) | Đã hoạt động (`Basic` / `Japan East`) |
| **Service Connection** | `ACR-Connection` (Service Principal) | Đã kết nối với Azure DevOps |
| **Tệp đặc tả đóng gói** | `Dockerfile` & `.dockerignore` (cổng `8000`) | Đã hoàn thiện trong repository |
| **Repository & Image Tag** | `m5retailacr2026.azurecr.io/retail-forecast-api:v1` | Đã đẩy lên ACR thành công |
| **Kết quả Pipeline** | Run `#20261121.6` (2 Stages: CI + Build & Push) | **Passed (Xanh)** |

## 4. Kết luận nghiệm thu giai đoạn Q05

1. **Chuẩn hóa môi trường thực thi:** Đã đóng gói trọn vẹn FastAPI, các thư viện phụ thuộc và tệp mô hình vào Docker image `retail-forecast-api`, đảm bảo dịch vụ hoạt động đồng nhất khi đưa lên Cloud.
2. **Hoàn thiện tự động hóa Build & Push:** Kết nối thành công Azure DevOps với ACR `m5retailacr2026` qua `ACR-Connection`, giúp quy trình kiểm thử và đóng gói image diễn ra hoàn toàn tự động theo 2 giai đoạn.
3. **Quản lý phiên bản bảo mật:** Image được lưu trữ tập trung trong kho riêng tư với nhãn `v1` cùng các tag lịch sử build, sẵn sàng cho bước triển khai thành dịch vụ API công khai.

**Tình trạng:** Đã hoàn thành giai đoạn Q05 và sẵn sàng chuyển sang **Giai đoạn Q06: Triển khai API công khai trên Azure Container Instances (ACI)**.