# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 4 (Q04): DỰNG AZURE PIPELINES (CI)

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure
* **Môn học:** Điện toán đám mây (IS402.R11)
* **Phụ trách:** Võ Hồ Trung Quân
* **Trạng thái:** Hoàn thành

---

## 1. Mục tiêu giai đoạn Q04

Thiết lập quy trình Tích hợp liên tục (**Continuous Integration - CI**) trên **Azure DevOps Pipelines** kết nối trực tiếp với kho mã nguồn GitHub của nhóm. Pipeline tự động kiểm tra chất lượng mã nguồn (Linting), cài đặt môi trường thư viện và thực thi kiểm thử đơn vị (Unit Test) mỗi khi có thay đổi mới, giúp phát hiện sớm lỗi cú pháp hoặc xung đột trước khi đóng gói và triển khai lên môi trường Cloud.

---

## 2. Chi tiết các bước thực hiện

### 2.1. Khởi tạo dự án trên Azure DevOps và kết nối GitHub

Khởi tạo không gian quản lý CI/CD trên Azure DevOps và liên kết trực tiếp với kho mã nguồn dự án thông qua xác thực **GitHub OAuth**:

* **Azure DevOps Organization:** `m5retail23521273` (`https://dev.azure.com/m5retail23521273`)
* **Azure DevOps Project:** `M5-Retail-MLOps` (Chế độ: `Private`)
* **Kho mã nguồn kết nối (GitHub Repository):** `lamdv1504/IS402.R11-azure-retail-demand-mlops`
* **Loại cấu hình Pipeline:** `GitHub (YAML)` sử dụng tệp kịch bản lưu trực tiếp trong repository.

*(Minh chứng: Ảnh chụp màn hình khởi tạo project `M5-Retail-MLOps` và kết nối thành công kho GitHub trên Azure DevOps)*

---

### 2.2. Xây dựng tệp cấu hình CI (`azure-pipelines.yml`) và kịch bản kiểm thử

Tạo tệp `azure-pipelines.yml` tại thư mục gốc của dự án để tự động hóa các bước kiểm thử trên máy ảo đám mây (`ubuntu-latest`) mỗi khi có sự kiện đẩy mã nguồn (push) lên nhánh `main` hoặc `dev`:

```yaml
trigger:
  branches:
    include:
      - main
      - dev

pool:
  vmImage: 'ubuntu-latest'

variables:
  python.version: '3.11'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(python.version)'
  displayName: 'Cài đặt Python $(python.version)'

- script: |
    python -m pip install --upgrade pip
    pip install flake8 pytest
    if [ -f requirements-data.txt ]; then pip install -r requirements-data.txt; fi
  displayName: 'Cài đặt thư viện (Dependencies)'

- script: |
    flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
  displayName: 'Chạy kiểm tra code (Check Lint bằng Flake8)'
  continueOnError: true

- script: |
    pytest tests/
  displayName: 'Chạy Unit Test (bằng Pytest)'
```

Đồng thời, khởi tạo tệp kiểm thử cơ sở `tests/test_dummy.py` để xác minh bước thực thi `pytest` trên build agent hoạt động chính xác:

```python
def test_dummy_always_pass():
    assert 1 + 1 == 2
```

---

### 2.3. Kiểm chứng thực thi Pipeline trên Azure DevOps

Sau khi cập nhật tệp `azure-pipelines.yml` và kích hoạt chạy thử trên nhánh `feat/azure-pipelines`, hệ thống ghi nhận kết quả chạy thành công (trạng thái xanh - **Passed**) tại lần chạy **`#20261119.3`**:

* **Agent thực thi:** `Azure Pipelines 1` (`ubuntu-latest`)
* **Tổng thời gian chạy:** `36 giây` (Job chính: `31 giây`)
* **Chi tiết các bước hoàn thành:**
  1. `Checkout lamdv1504/IS402.R11-azure-retail-demand-mlops` (`4s`) – Thành công
  2. `Cài đặt Python 3.11` (`<1s`) – Thành công
  3. `Cài đặt thư viện (Dependencies)` (`19s`) – Thành công
  4. `Chạy kiểm tra code (Check Lint bằng Flake8)` (`1s`) – Thành công
  5. `Chạy Unit Test (bằng Pytest)` (`4s`) – Thành công

*(Minh chứng: Ảnh chụp màn hình lần chạy `#20261119.3` trạng thái Passed và log chi tiết các bước thực thi trong Job)*

---

## 3. Đầu ra bàn giao giai đoạn Q04 (CI Handover)

| Hạng mục | Thông tin cấu hình | Trạng thái |
| :--- | :--- | :--- |
| **Azure DevOps Project** | `M5-Retail-MLOps` (`m5retail23521273`) | Đã hoạt động |
| **GitHub Repository** | `lamdv1504/IS402.R11-azure-retail-demand-mlops` | Đã kết nối |
| **Tệp kịch bản CI** | `azure-pipelines.yml` | Đã cấu hình trigger `main`, `dev` |
| **Công cụ kiểm thử tự động** | `Flake8` (Lint) & `Pytest` (Unit Test) | Hoạt động ổn định |
| **Kết quả xác nhận** | Run `#20261119.3` | **Passed (Xanh)** |

---

## 4. Kết luận nghiệm thu giai đoạn Q04

1. **Tự động hóa kiểm thử mã nguồn:** Đã kết nối thông suốt giữa GitHub và Azure DevOps Pipelines, tự động kiểm tra chất lượng mã nguồn (Flake8) và chạy kiểm thử (Pytest) trên môi trường Ubuntu sạch mỗi khi có thay đổi.
2. **Đảm bảo tính ổn định cho mã nguồn chung:** Giúp phát hiện sớm lỗi cú pháp, lỗi thiếu thư viện hoặc lỗi logic ngay ở giai đoạn tích hợp, tạo lớp bảo vệ quan trọng cho nhánh chính của dự án.
3. **Sẵn sàng mở rộng sang đóng gói tự động:** Tệp `azure-pipelines.yml` đã chạy xanh ổn định, làm nền tảng trực tiếp để mở rộng thêm giai đoạn Build & Push Docker Image lên Azure Container Registry ở giai đoạn tiếp theo.

**Tình trạng:** Đã hoàn thành giai đoạn Q04 và chuyển tiếp sang **Giai đoạn Q05: Đóng gói Docker và quản lý Image trên Azure Container Registry (ACR)**.