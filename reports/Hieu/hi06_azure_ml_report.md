# Báo cáo HI06: Đưa Model lên Azure Machine Learning

> **Người thực hiện:** Trần Đình Trung Hiếu (ML Engineer)  
> **Nhiệm vụ:** HI06 – Chạy Azure ML training job, đăng ký Model Registry  
> **Giai đoạn:** GĐ4 – Azure Machine Learning, CI/CD và triển khai ACI  
> **Trạng thái:** 🟢 Hoàn thành 100% trên Azure ML Cloud  

---

## 1. Thông tin chung về hạ tầng Azure

| Tài nguyên | Giá trị thực tế |
|---|---|
| **Subscription ID** | `2fbbed78-b490-46ad-91e9-a58667d7367c` (Azure for Students) |
| **Resource Group** | `rg-mlops-retail` (East US) |
| **Azure ML Workspace** | `m5-ml-workspace` (Japan East) |
| **Storage Account** | `m5retailstore2026` |
| **Compute Target** | `m5-cpu-cluster` (`Standard_DS11_v2`: 2 vCPUs, 14GB RAM) |
| **Trạng thái Compute** | `Stopped` (Đã tắt ngay sau khi hoàn thành để tiết kiệm chi phí) |

---

## 2. Thông tin Azure ML Training Job

- **Run ID (Job Name):** `olive_kitten_3w1vbdr333`
- **Display Name:** `HI06-xgboost-m5-mvp`
- **Experiment:** `m5-retail-demand-forecasting`
- **Trạng thái (Status):** `Completed`
- **Môi trường (Environment):** `m5-xgboost-env` (Python 3.11, Ubuntu 20.04, XGBoost, MLflow)
- **Dữ liệu đầu vào (Data Asset):** `azureml:m5-processed-data:1` (trỏ trực tiếp vào `ds_processed_data` Blob `processed/m5/v1/m5_sales_processed.parquet`)
- **Cấu hình đầu vào (Config Asset):** `azureml:m5-training-config:1` (từ `artifacts/hi04/`)
- **Studio URL:** [Xem chi tiết Run trên Azure ML Studio](https://ml.azure.com/runs/olive_kitten_3w1vbdr333?wsid=/subscriptions/2fbbed78-b490-46ad-91e9-a58667d7367c/resourcegroups/rg-mlops-retail/workspaces/m5-ml-workspace&tid=2dff09ac-2b3b-4182-9953-2b548e0d0b39)

---

## 3. Kết quả đánh giá & Metrics (So sánh Local HI05 vs Azure ML HI06)

| Chỉ số / Metric | Local HI05 | Azure ML HI06 | Đánh giá |
|---|:---:|:---:|:---:|
| **Thuật toán** | XGBoost (count:poisson) | XGBoost (count:poisson) | Khớp 100% |
| **Số cây (n_estimators)** | 300 | 300 | Khớp 100% |
| **Độ sâu (max_depth)** | 6 | 6 | Khớp 100% |
| **Phạm vi (Scope)** | CA_1 (300 items) | CA_1 (300 items) | Khớp 100% |
| **Horizon dự báo** | 28 ngày | 28 ngày | Khớp 100% |
| **Validation MAE** | 1.03 | **1.03** | Khớp hoàn hảo |
| **Validation RMSE** | 2.03 | **2.03** | Khớp hoàn hảo |
| **Subset RMSSE** | 0.721 | **0.721** | Khớp hoàn hảo |

---

## 4. Đăng ký Model Registry

Model đã được đăng ký chính thức vào **Azure ML Model Registry**:

- **Model Name:** `m5-xgboost-mvp`
- **Model Version:** `1`
- **Asset Type:** `custom_model`
- **Model URI:** `azureml://jobs/olive_kitten_3w1vbdr333/outputs/artifacts/paths/outputs/best_model.ubj`
- **Model ID:** `/subscriptions/2fbbed78-b490-46ad-91e9-a58667d7367c/resourceGroups/rg-mlops-retail/providers/Microsoft.MachineLearningServices/workspaces/m5-ml-workspace/models/m5-xgboost-mvp/versions/1`
- **Tags đính kèm:**
  - `task`: `HI06`
  - `data_version`: `m5-ca1-300-v1`
  - `local_model_version`: `hi05-xgboost-cb3a08fa5e82`
  - `scope`: `CA_1, 300 items`
  - `horizon`: `28`
  - `subset_rmsse`: `0.721`
  - `val_mae`: `1.03`
  - `run_id`: `olive_kitten_3w1vbdr333`

---

## 5. Bàn giao cho đồng đội

1. **Bàn giao cho Quân (DevOps - Q04, Q05, Q06):**
   - Đã có Model Registry chính thức: `m5-xgboost-mvp` (version `1`).
   - Run ID: `olive_kitten_3w1vbdr333`.
   - Có thể kéo model trực tiếp từ Azure ML Model Registry hoặc download artifact từ Run để đóng gói Docker image (`Q05`) và deploy ACI (`Q06`).
2. **Bàn giao cho Lâm (Backend/Frontend - L03, L05):**
   - Xác nhận model trên Cloud cho ra dự báo 28 ngày đồng nhất với gói inference local `artifacts/hi05/`.
   - Payload API response tương thích 100% với `docs/api_contract.json`.

---

## 6. Checklist nghiệm thu đồ án (HI06)

- [x] Job thực sự chạy hoàn thành trên Azure ML Compute (Run ID: `olive_kitten_3w1vbdr333`).
- [x] Không ghi nhận job local là job Azure ML.
- [x] Model version `1` đã đăng ký và truy xuất được trong Azure ML Studio -> Models.
- [x] Gắn đầy đủ data version (`m5-ca1-300-v1`), commit ID và metrics.
- [x] Compute `m5-cpu-cluster` đã được STOP sau khi hoàn thành để tiết kiệm chi phí FinOps.
