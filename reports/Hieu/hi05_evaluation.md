# HI05 — Đánh giá và bàn giao model, GĐ3 của Hiếu

## Kết quả

Đã chọn **XGBoost** bằng trung bình RMSSE từng chuỗi trên validation
`d_1886...d_1913` (28/03/2016–24/04/2016). Phạm vi là 300 sản phẩm MVP tại
`CA_1`, cùng dữ liệu/version `m5-ca1-300-v1` và cấu hình HI04 seed 42.

| Model / cửa sổ | Subset RMSSE | Subset WRMSSE¹ | MAE | RMSE |
| --- | ---: | ---: | ---: | ---: |
| Seasonal naive / validation | 0,973038 | 1,062760 | 1,264524 | 2,724754 |
| XGBoost / validation | **0,720984** | **0,762847** | **1,030182** | **2,027791** |
| XGBoost / final holdout | 0,745556 | 0,721194 | 1,034657 | 1,937336 |

¹ Subset WRMSSE chỉ tính 300 chuỗi item–store ở cấp thấp nhất, chưa tổng hợp
12 cấp của M5; không phải điểm WRMSSE toàn cuộc thi.

## Quy trình tránh leakage

1. Kiểm tra đủ split/log HI02, gói/log HI04 và calendar Hùng bàn giao, đối chiếu
   SHA-256 cùng code feature/inference HI04.
2. Rebuild feature từ lịch sử `d_1...d_1885` và future không có sales; dự báo cả
   seasonal naive và XGBoost trên cùng 8.400 dòng validation.
3. Chọn theo validation Subset RMSSE, tie-break bằng tên model; ghi `selection.json`
   trước khi đọc file test. Không tune thêm tham số trong HI05.
4. Giữ nguyên estimator HI04 đã train đến `d_1885`. Sau khi chọn, dùng lịch sử
   quan sát đến `d_1913` để tạo lag và đánh giá một lần trên
   `d_1914...d_1941` (25/04/2016–22/05/2016, 8.400 dòng).
5. Sau đánh giá, dùng 56 ngày quan sát cuối đến `d_1941` làm context production;
   dự báo `d_1942...d_1969` (23/05/2016–19/06/2016, 8.400 dòng).
   Không refit, không chọn lại model bằng holdout.

Scale RMSSE tính từ lịch sử trước từng origin, bỏ đoạn zero trước lần bán đầu.
Trọng số là doanh thu `sales × sell_price` của 28 ngày trước origin, chuẩn hóa
trong 300 chuỗi. Cả hai model dùng cùng scale/weight trên validation. Khi đánh giá
holdout, scale và weight dùng lịch sử đã quan sát đến `d_1913`.
Nếu scale bằng 0, giá bị thiếu ở ngày có sales dương hoặc tổng doanh thu bằng 0,
script dừng rõ ràng; không thêm epsilon hay loại chuỗi âm thầm. Không dùng sMAPE.

Cách tính đối chiếu [M5 Competitors Guide](https://storage.googleapis.com/kaggle-forum-message-attachments/772349/15032/M5-Competitors-Guide-Final-10-March-2020.pdf).

## File bàn giao

- `artifacts/hi05/best_model.ubj`: model native, version `hi05-xgboost-cb3a08fa5e82`.
- `metrics.json`, `selection.json`, `feature_order.json`, `feature_schema.json`,
  `model_config.json`, `model_metadata.json`, `model_info.json` trong cùng gói.
- `inference_history.parquet`: 16.800 dòng, 56 ngày cuối của 300 chuỗi; khoảng 35 KB.
- `future_calendar.csv`: lịch 28 ngày production; không có nhãn sales hay giá tương lai.
- `src/models/predict.py`: predictor dùng cùng `forecast_direct` và feature builder
  đã dùng để đánh giá; output float không âm, API làm tròn 2 chữ số thập phân.
- `reports/Hieu/hi05_model_comparison.csv`, các file `hi05_*_series_metrics.csv` và
  `hi05_*_predictions.csv`: so sánh, metric từng chuỗi, dự báo validation/test/future.
- `reports/Hieu/hi05_sample_request.json`, `reports/Hieu/hi05_sample_response.json`: JSON thực.
- `reports/Hieu/hi05_evaluation_log.json`: fingerprint đầu vào/artifact/code và phiên bản thư viện.

Chi tiết chạy và tích hợp: [docs/Hieu/hi05_inference_handoff.md](../../docs/Hieu/hi05_inference_handoff.md).
API `/predict` dùng model thật là phần tiếp theo L03 của Lâm; model local chưa được
đăng ký Azure ML Model Registry (HI06).

## Kiểm chứng

- 35 test HI02–HI05 qua, bao gồm công thức RMSSE tính tay, leading zeros, scale
  không xác định, weight doanh thu, căn chỉnh khóa/ngày, biên thời gian và lỗi đầu vào.
- Model native load lại cho dự báo validation khớp hoàn toàn.
- Batch production đủ 300 × 28 = 8.400 dòng, không có sales tương lai làm đầu vào.
- CLI chạy thật với `FOODS_1_017`, trả đủ 28 ngày từ 23/05 đến 19/06/2016,
  tổng giá trị đã làm tròn là 21,34 đơn vị.
- `pip check` không phát hiện xung đột dependency.
- Request, response mẫu và model-info khớp schema trong API contract; response
  cũng qua Pydantic của backend, tổng đúng bằng tổng 28 giá trị ngày đã làm tròn.
- Chạy lại evaluate khi gói đã có sẽ dừng trước bước đọc/chấm holdout.

Model vẫn là estimator train đến `d_1885`; việc dùng lịch sử mới cho lag không
đồng nghĩa đã refit trên lịch sử đó. Trường training date trong payload model-info
ước lượng bằng mtime artifact HI04 vì HI04 chưa ghi timestamp fit. Đây là đánh
giá local trên một cửa sổ validation và một holdout, không khẳng định hiệu quả
trên toàn bộ M5 hoặc dữ liệu bán hàng hiện tại.
