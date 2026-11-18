# L04 — Kết quả kiểm tra frontend

Ngày kiểm tra: 18/11/2026. Người phụ trách task: Lâm. Nhánh:
`feature/lam-gd2-l04-frontend-integration`.

## Phạm vi

Đối chiếu dòng L04 trong sheet `23 cong viec goc` và `Lam` của
`Ke_hoach_M5_Azure_MLOps_14_ngay.xlsx`: bốn trang, form MVP/horizon 28, bảng/biểu đồ,
prediction service, loading/error/empty, UI local và ảnh UI. Phụ thuộc chính L01
đã có; các file Hùng/Hiếu dùng trong lượt kiểm tra cũng có đầy đủ.

Frontend có sẵn từ L02 được hoàn thiện kiểm tra response, khóa form khi pending,
chặn request trùng, retry, metadata feature/split, định dạng ngày và đơn vị rõ ràng.
Giữ Next.js/Tailwind/Manrope/mint theo [thiết kế](../../frontend/design.md).

## Kết quả đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `npm run build` | PASS; compile, TypeScript, static export `/`, `/forecast`, `/performance`, `/model`. |
| `npm test` | PASS 19/19; response đúng/sai phạm vi, thiếu/trùng/gãy ngày, ngày không tồn tại, số âm/NaN/Infinity, tổng sai, version thiếu/sai kiểu, JSON request, input sai, 503/422/network/timeout. |
| `npm run test:live` | PASS 5/5; gọi service frontend qua backend L03 thật, không mock. |
| HTTP GET bốn route trên `localhost:3000` | Cả bốn trả 200; đây là kiểm tra HTTP, không chứng minh hydration/thao tác browser. |
| CORS preflight `/predict` | PASS; backend cho phép origin `http://localhost:3000` và POST JSON. |
| `test_project_paths.py` | PASS 2/2; các liên kết tài liệu và checksum bàn giao vẫn đúng. |
| `git diff --check` | PASS; không có lỗi whitespace trong diff. |

Node v22.22.2; Next.js 16.4.6. API đang chạy tại `127.0.0.1:8000`:
`model_loaded=true`, model `hi05-xgboost-cb3a08fa5e82`, data `m5-ca1-300-v1`.
Catalog trả 300 item duy nhất, mỗi nhóm FOODS/HOBBIES/HOUSEHOLD 100 item.
Dashboard trả 1.941 ngày lịch sử.

| Item | Horizon | Ngày đầu | Ngày cuối | Tổng units |
| --- | --- | --- | --- | --- |
| FOODS_1_017 | 1 | 23/05/2016 | 23/05/2016 | 0,77 |
| FOODS_1_017 | 7 | 23/05/2016 | 29/05/2016 | 5,27 |
| FOODS_1_017 | 28 | 23/05/2016 | 19/06/2016 | 21,34 |

Service đã xác nhận số ngày, tính liên tiếp, units, tổng, scope và version cho các
response trên. Dự báo dùng dữ liệu M5 lịch sử, không phải ngày hiện tại.

## Giới hạn nghiệm thu

- Browser runtime trả `No browser is available`, danh sách browser rỗng. Chưa chụp
  ảnh UI, chưa thao tác form/menu/retry và chưa kiểm tra overflow tại các kích thước.
- Bảng và chart cùng lấy `result.forecast` trong code; việc hiển thị trực quan
  đúng 28 dòng/điểm vẫn cần kiểm tra trong browser.
- Phần Actual vs Predicted có empty state; CSV validation của Hiếu đã có, nhưng
  endpoint đối chiếu chưa có trong API contract. Tích hợp luồng này tiếp ở L05.
- Chưa có ảnh UI theo đầu ra kế hoạch, vì vậy chưa tuyên bố L04 nghiệm thu 100%.

[Hướng dẫn chạy và checklist UI còn lại](../../docs/Lam/l04_frontend.md).
