# L05 Báo cáo kết nối frontend với API Azure

Ngày kiểm tra: **21/11/2026**, người thực hiện: **Lâm**.
Phạm vi: kết nối L05 và trang Tổng quan trạng thái hệ thống, đã có trên `main`
sau PR #25 và #26. Nhánh lưu tài liệu: `docs/lam-gd4-l05-reports`.
Tài khoản GitHub đã xác minh: `LamDinh1504`.

**API local và ACI đã trả dự báo thật đủ 28 ngày qua service frontend.** Build
Next.js thành công. Nghiệm thu L05 còn bước thao tác trình duyệt và ảnh UI/Network;
công cụ Browser không có kết nối trong lượt thực hiện này.

Kết quả là các lượt kiểm tra đã thực hiện ngày 21/11/2026. Hai JSON giữ nguyên
bằng chứng trước khi đổi trang Tổng quan; bảng dưới phân biệt chúng với kiểm thử
sau thay đổi. Kết quả này không xác nhận endpoint luôn trực tuyến ở các thời điểm khác.

## Đầu vào và phạm vi

Đã đối chiếu dòng **L05 / GĐ4 / Lâm** trong
`Ke_hoach_M5_Azure_MLOps_14_ngay.xlsx`, URL trong
`b_n_giao_api_checklist_cho_l_m.md` và `Báo cáo Q06.docx` được người dùng cung cấp.
L03, catalog 300 sản phẩm của Hùng, bundle HI05 của Hiếu và endpoint Q06 của Quân
đều có. File Parquet local có sẵn cho kiểm tra Dashboard; không tạo thay file
bàn giao của thành viên khác.

Phần triển khai nằm ở frontend và cấu hình chọn API. Tổng quan hiện dùng
`/health` và `/model-info`, có loading, thử lại và làm mới từng phần. Dự báo tiếp
tục dùng `/predict`; thanh điều hướng giữ ở đầu màn hình khi cuộn.

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
| --- | --- |
| `npm test` | **24/24 đạt**: hợp đồng forecast, URL, lỗi 503/422/mạng, JSON sai, mixed content và abort sau 15 giây khi chờ header hoặc body. |
| `npm run test:local` trước thay đổi Tổng quan | **9/9 đạt**, gồm dự báo thật, CORS và lịch sử 1.941 ngày; lưu trong JSON local. |
| `npm run test:aci` trước thay đổi Tổng quan | **8 đạt, 1 cảnh báo**: `/dashboard` thiếu lịch sử; forecast và CORS đạt; lưu trong JSON ACI. |
| `npm run test:live` trên ACI sau thay đổi Tổng quan | **5/5 đạt**: health/metadata/catalog, dự báo 1/7/28 ngày và lỗi đầu vào; không gọi `/dashboard`. |
| `npm run build:aci` | Build và TypeScript đạt; export bốn trang `/`, `/forecast`, `/performance`, `/model`. |
| API URL trong bản export | URL ACI xuất hiện trong JavaScript browser được build. |
| HTTP trang frontend hiện có | `http://localhost:3000/forecast` trả 200; kết quả này chưa xác minh hydration hay thao tác form. |
| Đường dẫn và checksum bàn giao | 2/2 kiểm tra trong `tests/test_project_paths.py` đạt. |

Unit test dùng fixture HI05 và HTTP giả lập để chủ động gây lỗi. Hai lượt tích
hợp gọi API/model thật qua `api.ts` và `predictionService.ts`; không dùng fixture
làm dữ liệu dự báo. Hai origin kiểm tra CORS là `http://localhost:3000` và
`http://127.0.0.1:3000`, gồm OPTIONS và header trên response thật.

## Dự báo đã nhận từ ACI

API base URL:
`http://m5-retail-forecast-api-2026.arapascqfgcjasbc.japaneast.azurecontainer.io:8000`.

| Thuộc tính | Giá trị thực tế |
| --- | --- |
| Request | `POST /predict`, `CA_1`, `FOODS_1_017`, `horizon: 28` |
| HTTP status | 200 |
| Số ngày | 28 ngày liên tiếp, `2016-05-23` đến `2016-06-19` |
| Tổng dự báo | 21,34 units |
| Model version | `hi05-xgboost-cb3a08fa5e82` |
| Data version | `m5-ca1-300-v1` |
| Metadata | `/health`: `healthy`, `model_loaded: true`; `/model-info`: `ready` |
| Danh mục | 300 item duy nhất, mỗi nhóm FOODS/HOBBIES/HOUSEHOLD có 100 item |
| Lỗi đầu vào | Item ngoài MVP trả 404; horizon 29 trả 422 |

Response được service kiểm tra khớp store/item/horizon, ngày bắt đầu và ngày liên
tiếp, units hữu hạn không âm, tổng khớp từng ngày và version khớp `/model-info`.
Bảng và biểu đồ hiện dùng chung response này; việc render thực tế còn cần xác
nhận trên trình duyệt.

Bằng chứng request/response và thời điểm UTC nằm trong
[JSON local](l05_local_api_check.json) và [JSON ACI](l05_aci_api_check.json).
Các file chỉ ghi payload công khai và header CORS, không ghi thông tin xác thực.

## Tổng quan hiện hành và phần nghiệm thu còn lại

JSON ACI ghi **503 `DASHBOARD_NOT_READY`** cho `/dashboard` và trạng thái
`passed_with_warnings`. Đây là kết quả trước thay đổi giao diện. Tổng quan hiện
chỉ đọc trạng thái hệ thống và model từ hai endpoint còn lại, nên không cần
Parquet hay JSON tĩnh. Bộ kiểm tra hiện hành đã bỏ `/dashboard`; bằng chứng cũ
được giữ nguyên, không đổi cảnh báo thành đạt khi chưa có lượt đo tương ứng.

Các phần còn cần xác nhận trước khi đánh dấu L05 hoàn tất toàn bộ:

- Chọn item và gửi dự báo trên website; xác nhận bảng đủ 28 hàng, biểu đồ, loading,
  khóa form, xóa kết quả khi đổi lựa chọn và nút thử lại.
- Kiểm tra desktop/mobile và lưu ảnh UI, Network Request/Payload/Response thật
  vào `reports/Lam/` theo [hướng dẫn L05](../../docs/Lam/l05_cloud_api_integration.md).
- Kiểm tra Tổng quan lấy đúng thông tin live, nút làm mới/thử lại và thanh điều
  hướng khi cuộn; chưa có xác nhận bằng trình duyệt tự động.
- Người dùng báo nhãn “API chưa kết nối” sau các lượt kiểm thử trên. Nguyên nhân
  chưa được xác định; cần đối chiếu URL frontend, Request URL, origin/CORS và
  phản hồi health tại thời điểm gặp lỗi trước khi kết luận đã khắc phục.

ACI bàn giao dùng HTTP. Demo frontend qua HTTP tại cổng 3000; website HTTPS cần
API HTTPS tương ứng. Chưa có endpoint AKS Q07 nên không kiểm tra AKS. Kế hoạch
cho phép demo ACI khi Q07 chưa triển khai.
