# BÁO CÁO THỰC HIỆN GIAI ĐOẠN 1 (Q01): CHUẨN BỊ NỀN TẢNG HẠ TẦNG AZURE

* **Dự án:** Hệ thống Dự báo Nhu cầu Bán lẻ (Retail Demand Forecasting) trên Microsoft Azure
* **Môn học:** Điện toán đám mây (IS402.R11)
* **Phụ trách:** Võ Hồ Trung Quân
* **Trạng thái:** Hoàn thành

---

## 1. Mục tiêu giai đoạn Q01
Thiết lập nền tảng hạ tầng đám mây ban đầu trên Microsoft Azure, kiểm tra hạn mức tài nguyên (Quota) của gói **Azure for Students** và khởi tạo vùng quản lý tập trung (**Resource Group**) làm cơ sở triển khai cho toàn bộ các dịch vụ dữ liệu, huấn luyện mô hình và API ở các giai đoạn tiếp theo.

---

## 2. Chi tiết các bước thực hiện

### 2.1. Đăng nhập Azure Portal và kiểm tra Subscription
* Đăng nhập thành công vào **Microsoft Azure Portal** bằng tài khoản sinh viên của trường (`23521273@ms.uit.edu.vn`).
* Kiểm tra gói đăng ký (Subscription): Xác nhận gói **Azure for Students** đang ở trạng thái hoạt động (**Active**) với vai trò quản trị cao nhất (**Owner**) để có đủ quyền khởi tạo tài nguyên và phân quyền truy cập (RBAC) cho các thành viên trong nhóm.

*(Minh chứng: Ảnh chụp màn hình đăng nhập Azure Portal và thông tin gói Azure for Students ở trạng thái Active)*

---

### 2.2. Kiểm tra hạn mức tài nguyên (Quota) và lựa chọn Region
Trước khi khởi tạo hạ tầng, tiến hành kiểm tra hạn mức cấp phát lõi xử lý (**vCPU**) cho các dịch vụ tính toán (Azure ML Compute và cụm container):
* **Khảo sát vùng triển khai (Region):** Gói **Azure for Students** bị giới hạn hoặc không cấp phát vCPU tại khu vực *Southeast Asia*. Qua kiểm tra thực tế, khu vực **Japan East** hỗ trợ đầy đủ các dịch vụ cần thiết cho đồ án với hạn mức tối đa là **6 vCPU** (`Total Regional vCPUs: 0 of 6` và `Standard DSv2 Family Cluster Dedicated vCPUs: 0 of 6`).
* **Quyết định kỹ thuật:**
  1. Chốt triển khai toàn bộ tài nguyên của đồ án tại khu vực **Japan East** để đảm bảo tính đồng nhất, giảm độ trễ mạng nội bộ và không gặp lỗi thiếu tài nguyên.
  2. Do giới hạn phần cứng tối đa là **6 vCPU**, nhóm thống nhất thu hẹp phạm vi dữ liệu huấn luyện ở mức MVP (giới hạn trên 1 cửa hàng của bộ dữ liệu M5) nhằm tránh tràn bộ nhớ RAM/CPU khi huấn luyện và tối ưu ngân sách credit sinh viên.

*(Minh chứng: Ảnh chụp màn hình kiểm tra Quota 6 vCPU tại khu vực Japan East)*

---

### 2.3. Khởi tạo Resource Group dùng chung
Tạo một Resource Group duy nhất để gom nhóm toàn bộ tài nguyên của đồ án, phục vụ việc quản lý vòng đời, theo dõi chi phí tập trung và phân quyền nhóm:
* **Tên Resource Group:** `rg-mlops-retail`
* **Subscription:** `Azure for Students`
* **Region (Khu vực):** `Japan East`
* **Tag quản lý:** `Project : M5-Retail`

*(Minh chứng: Ảnh chụp màn hình quá trình khởi tạo và màn hình Overview của Resource Group `rg-mlops-retail` tại Japan East)*

---

## 3. Đầu ra bàn giao hạ tầng Q01 (Infrastructure Handover)

| Thông số hạ tầng | Giá trị cấu hình | Ghi chú sử dụng cho các giai đoạn sau |
| :--- | :--- | :--- |
| **Subscription** | `Azure for Students` | Quản lý ngân sách & credit sinh viên |
| **Resource Group** | `rg-mlops-retail` | Dùng chung cho toàn bộ tài nguyên (Q02 – Q06) |
| **Region** | `Japan East` | Bắt buộc chọn đúng khu vực này khi tạo dịch vụ mới |
| **Giới hạn vCPU** | Tối đa `6 vCPU` | Giới hạn dữ liệu huấn luyện mức MVP; tắt Compute ngay sau khi train |

---

## 4. Kết luận giai đoạn Q01
1. **Thiết lập trung tâm quản lý:** Khởi tạo thành công Resource Group `rg-mlops-retail`, đóng vai trò là vùng chứa logic để quản lý tập trung, giám sát chi phí và phân quyền (IAM/RBAC) cho các thành viên.
2. **Xác định chiến lược vùng triển khai:** Chốt khu vực **Japan East** dựa trên kết quả kiểm tra Quota thực tế của gói Azure for Students.
3. **Định hướng tối ưu tài nguyên:** Xác định rõ ràng ràng buộc **6 vCPU**, làm cơ sở để nhóm chốt phạm vi dữ liệu xử lý và thiết lập kỷ luật tắt tài nguyên tính toán (`Stop`) ngay sau khi sử dụng.

**Tình trạng:** Nền tảng hạ tầng gốc đã sẵn sàng để chuyển sang **Giai đoạn Q02: Xây dựng kho lưu trữ dữ liệu (Azure Blob Storage)**.