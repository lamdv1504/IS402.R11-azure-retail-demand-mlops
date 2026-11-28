# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 6 (Q06): TRIỂN KHAI LÊN AZURE CONTAINER INSTANCES (ACI)

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure

* **Môn học:** Điện toán đám mây (IS402.R11)

* **Phụ trách:** Võ Hồ Trung Quân

* **Trạng thái:** Hoàn thành

## 1. Mục tiêu giai đoạn Q06

Triển khai Docker image `retail-forecast-api:v1` từ kho chứa riêng tư **Azure Container Registry** (`m5retailacr2026`) thành một dịch vụ Web API công khai trên **Azure Container Instances (ACI)**. Cấu hình tài nguyên tính toán phù hợp, mở cổng mạng `8000`, kiểm chứng hoạt động thực tế của các endpoint suy luận và bàn giao địa chỉ **Live URL (FQDN)** để tích hợp trực tiếp vào **Frontend Dashboard**.

## 2. Chi tiết các bước thực hiện

### 2.1. Khởi tạo Azure Container Instances (ACI) từ kho ACR

Khởi tạo container serverless bên trong Resource Group `rg-mlops-retail` tại khu vực `Japan East`, kéo trực tiếp image đã đóng gói từ giai đoạn Q05:

* **Subscription:** `Azure for Students`

* **Resource Group:** `rg-mlops-retail`

* **Container Name:** `aci-retail-forecast-api`

* **Region (Khu vực):** `Japan East`

* **SKU / OS Type:** `Standard` / `Linux`

* **Image Source:** `Azure Container Registry` (`Private`)

* **Image:** `m5retailacr2026.azurecr.io/retail-forecast-api:v1`

* **Cấu hình tài nguyên tính toán (Size):** `2 vCPUs`, `4 GiB Memory`, `0 GPUs` (đảm bảo đủ bộ nhớ nạp mô hình dự báo và xử lý mượt các yêu cầu suy luận).

* **Chính sách giám sát & khởi động lại:** Bật `Enable container instance logs` (kết nối `m5mlworkspace2287205203`) và đặt `Restart policy: On failure`.

*(Minh chứng: Ảnh chụp màn hình cấu hình Basics, Change container size và Review + create đạt Validation passed)*

### 2.2. Cấu hình mạng công khai (Networking) và mở cổng `8000`

Thiết lập kết nối mạng công khai và cấp phát tên miền chuẩn **FQDN** để Frontend và người dùng có thể truy cập trực tiếp qua Internet:

* **Networking Type:** `Public`

* **DNS Name Label:** `m5-retail-forecast-api-2026` (`Scope reuse: Tenant`)

* **Ports:** Mở cổng **`8000`** giao thức **`TCP`** (khớp trực tiếp với cổng lắng nghe của máy chủ FastAPI/Uvicorn khai báo trong `Dockerfile`).

Sau khi triển khai hoàn tất, màn hình **Overview** xác nhận container chạy ổn định ở trạng thái **`Running`** với địa chỉ **FQDN** chính thức:
`m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io`

*(Minh chứng: Ảnh chụp màn hình cấu hình Networking cổng 8000 TCP và màn hình Overview trạng thái `Running`)*

### 2.3. Kiểm tra nhật ký khởi chạy (Container Logs) và kiểm chứng API trực tiếp

#### a. Kiểm tra Container Logs
Tại mục **Settings** $\rightarrow$ **Containers** $\rightarrow$ **Logs**, máy chủ ứng dụng khởi động thành công không phát sinh lỗi:

```text
INFO:     Started server process [19]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

#### b. Kiểm chứng các Endpoint công khai trên trình duyệt
Tiến hành kiểm thử trực tiếp các endpoint trên địa chỉ Live URL cổng `8000`:

1. **Endpoint kiểm tra sức khỏe dịch vụ (`GET /health`):**
   * URL: `http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000/health`
   * Kết quả trả về (HTTP 200):

```json
{
  "status": "healthy",
  "service": "retail-demand-forecast-api",
  "version": "0.1.0",
  "model_loaded": true,
  "timestamp": "2026-11-21T13:48:09.576172+00:00"
}
```

2. **Endpoint thông tin mô hình (`GET /model-info`):**
   * URL: `http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000/model-info`
   * Kết quả xác nhận mô hình **`M5 Retail Demand xgboost`** (phiên bản `hi05-xgboost-cb3a08fa5e82`, phạm vi `CA_1` với `300` sản phẩm, `forecast_horizon: 28`) đã ở trạng thái `ready`, kèm đầy đủ các chỉ số đánh giá (`validation_mae: 1.030`, `validation_rmse: 2.028`, `validation_subset_rmsse: 0.721`, `validation_subset_wrmsse: 0.763`).

3. **Giao diện tài liệu và kiểm thử tương tác (`GET /docs` - Swagger UI):**
   * URL: `http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000/docs`
   * Hiển thị đầy đủ danh sách API của hệ thống gồm: `GET /health`, `GET /items`, `GET /dashboard`, `GET /model-info` và `POST /predict`.

*(Minh chứng: Ảnh chụp màn hình Container Logs, kết quả JSON từ `/health`, `/model-info` và giao diện Swagger `/docs`)*

## 3. Đầu ra bàn giao giai đoạn Q06 (Deployment Handover)

| Hạng mục | Thông tin bàn giao | Trạng thái |
| ----- | ----- | ----- |
| **Tên Container (ACI)** | `aci-retail-forecast-api` (`Japan East`, 2 vCPU / 4 GiB RAM) | Đã triển khai thành công |
| **Base Live URL** | `http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000` | Đã bàn giao cho Frontend |
| **Health Check Endpoint** | `.../health` (`status: healthy`, `model_loaded: true`) | HTTP 200 OK |
| **Model Info Endpoint** | `.../model-info` (`xgboost`, `status: ready`) | HTTP 200 OK |
| **Swagger UI Endpoint** | `.../docs` (Đầy đủ `/items`, `/dashboard`, `/predict`) | Hoạt động ổn định |
| **Quản trị chi phí** | Chủ động **Stop** container khi không kiểm thử/demo, **Start** lại trước khi sử dụng | Đã áp dụng |

## 4. Kết luận nghiệm thu giai đoạn Q06

1. **Hoàn thiện triển khai dịch vụ công khai:** Đã triển khai thành công Docker image `retail-forecast-api:v1` từ ACR lên Azure Container Instances (`aci-retail-forecast-api`), mở cổng `8000` qua địa chỉ FQDN công khai.
2. **Xác minh hoạt động ổn định:** Log khởi chạy Uvicorn sạch lỗi, các endpoint `/health`, `/model-info` và `/docs` phản hồi chính xác với mô hình XGBoost đã nạp sẵn trong bộ nhớ.
3. **Khép kín chuỗi MLOps End-to-End (Q01 – Q06):** Đã bàn giao Live URL thay thế hoàn toàn môi trường `localhost` để tích hợp vào Frontend Dashboard, đồng thời áp dụng cơ chế bật/tắt chủ động (Start/Stop) giúp kiểm soát chặt chẽ chi phí gói Azure for Students.

**Tình trạng:** Đã hoàn thành toàn bộ lộ trình triển khai hạ tầng Cloud & MLOps (Q01 – Q06), hệ thống sẵn sàng phục vụ tích hợp cuối, quay video demo và bảo vệ đồ án.