# Báo cáo Thiết lập Hạ tầng Azure - Dự án M5 Retail Demand Forecasting

**Vai trò thực hiện:** Cloud Admin / DevOps (Võ Hồ Trung Quân)
**Giai đoạn hoàn thành:** Q01, Q02, Q03
**Trạng thái:** 🟢 Sẵn sàng bàn giao cho Data Engineer & Data Scientist

---

## 1. Tổng quan Kiến trúc (Architecture Overview)

Dự án áp dụng mô hình phân bổ tài nguyên lai (Hybrid Region) để tối ưu hóa giới hạn chính sách (Policy) của tài khoản Azure for Students, đảm bảo dự án vận hành trơn tru không bị gián đoạn.

*   **Resource Group:** `rg-mlops-retail`
    *   **Region:** `East US`
    *   **Vai trò:** Quản lý tập trung vòng đời, chi phí và quyền truy cập cấp cao nhất của toàn bộ dự án.

## 2. Kho lưu trữ dữ liệu (Data Lake / Storage)

Lưu trữ toàn bộ dữ liệu thô, dữ liệu đã qua xử lý và các kết quả huấn luyện mô hình. Đã cấu hình vượt qua giới hạn Policy bằng cách chuyển vùng linh hoạt.

*   **Storage Account:** `m5retailstore2026`
*   **Region:** `Japan East`
*   **Cấu trúc Containers:**
    *   `raw-data`: Chứa dữ liệu gốc ban đầu.
    *   `processed-data`: Chứa dữ liệu Parquet đã làm sạch.
    *   `model-artifacts`: Lưu trữ các phiên bản mô hình (Pickle/ONNX) sau khi train.
    *   `experiment-results`: Ghi nhận log và độ đo (metrics) của các lần thử nghiệm.

## 3. Môi trường Máy học (Azure Machine Learning Workspace)

Không gian làm việc trung tâm dành cho Data Scientist phát triển tính năng và huấn luyện mô hình dự đoán nhu cầu bán lẻ M5.

*   **ML Workspace:** `m5-ml-workspace`
*   **Region:** `Japan East`
*   **Datastore:** Đã tự động liên kết thành công với Storage Account `m5retailstore2026`.

## 4. Tài nguyên tính toán & Tối ưu chi phí (Compute & FinOps)

Hạ tầng Compute đã được cấp phát và cấu hình chặt chẽ để đảm bảo hiệu năng xử lý dữ liệu lớn đồng thời bảo vệ 100% ngân sách (Credit) của dự án.

*   **Tên máy ảo (Compute Name):** `m5-cpu-cluster`
*   **Cấu hình phần cứng (Size):** `Standard_DS11_v2` (2 cores, 14GB RAM, 28GB storage).
*   **Chiến lược tối ưu chi phí (FinOps):** 
    *   Kích hoạt **Auto Idle Shutdown**: Tự động tắt máy sau **15 phút** không hoạt động.
    *   Gắn nhãn quản lý (Tags): `Owner : Hieu` | `Project : M5-Retail`.
*   **Trạng thái hiện tại:** `Stopped` (Đang đóng băng tính phí).

## 5. Phân quyền và Bảo mật (IAM)

Tuân thủ nguyên tắc đặc quyền tối thiểu (Principle of Least Privilege).

*   **Quyền cấp phát Compute:** Máy ảo `m5-cpu-cluster` đã được gán đích danh (User Assignment) cho Data Scientist **Trần Đình Trung Hiếu**. Chỉ user này mới có toàn quyền quản trị máy.

## 6. Hướng dẫn Kết nối & Quản lý Thông tin xác thực (Credentials)

> **⚠️ CẢNH BÁO BẢO MẬT (SecOps):** Tuyệt đối KHÔNG hardcode (nhập cứng) các chuỗi Connection String, Access Keys hoặc mật khẩu trực tiếp vào mã nguồn hay đưa lên GitHub. Yêu cầu team sử dụng file `.env` hoặc Azure Key Vault.

**Kịch bản phân luồng kết nối cho các vai trò:**

**A. Đối với Data Engineer (Đẩy dữ liệu vào Storage):**
*   **Phương thức xác thực:** Sử dụng `Connection String`.
*   **Hướng dẫn lấy Key (Dành cho Admin/DE):** 
    1. Đăng nhập Azure Portal -> Mở Storage Account `m5retailstore2026`.
    2. Tại menu bên trái, tìm mục **Security + networking** -> Chọn **Access keys**.
    3. Nhấn *Show* và Copy chuỗi `Connection string` (ở Key 1).
*   **Quy trình làm việc:** Chuỗi này đã được Admin bàn giao bảo mật (qua Zalo/Teams). DE đưa chuỗi này vào file `.env` tại máy local để chạy code Python upload file `.parquet` lên container `processed-data`.

**B. Đối với Data Scientist (Train Model trên Workspace):**
*   **Phương thức xác thực:** Tích hợp ngầm qua Azure Active Directory (Không cần Key).
*   **Hướng dẫn sử dụng:** 
    1. Truy cập [https://ml.azure.com/](https://ml.azure.com/) bằng email đã được cấp quyền Contributor.
    2. Khởi động (Start) máy ảo `m5-cpu-cluster`.
    3. Trong file Jupyter Notebook, không cần cấu hình Connection String. Data Scientist chỉ cần dùng thư viện ML SDK gọi thẳng tên Datastore mặc định (`workspaceblobstore`) là có thể kéo dữ liệu về train model.