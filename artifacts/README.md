# artifacts

Mô hình và kết quả huấn luyện — Hiếu.

`hi04/` là gói model ứng viên bàn giao từ HI04 sang HI05:

- `xgboost.ubj`: model XGBoost native, đã kiểm tra load lại và dự báo khớp.
- `feature_order.json`: thứ tự 16 cột đầu vào của model.
- `feature_schema.json`: schema/vocabulary HI03 để mã hóa phân loại nhất quán.
- `training_config.json`: seed, horizon, chiến lược multi-step và tham số fit.
- `model_metadata.json`: phiên bản model/dữ liệu, phạm vi và cửa sổ train/validation.

Nguồn tạo gói: `python src/models/train.py` trong môi trường có
`requirements-ml.txt`. Log/fingerprint và dự báo validation nằm trong
`reports/Hieu/hi04_training_log.json` và `reports/Hieu/hi04_validation_predictions.csv`.
Đây là ứng viên cho HI05; chưa đánh giá final holdout hoặc đăng ký Model Registry.

`hi05/` là gói đã chọn qua validation, gồm model tốt nhất, metric, schema/config,
metadata và context lịch sử/calendar nhỏ để chạy inference local. Dùng
`src/models/predict.py` để load và kiểm tra gói. Hướng dẫn bàn giao cho Lâm/Quân
nằm ở [docs/Hieu/hi05_inference_handoff.md](../docs/Hieu/hi05_inference_handoff.md).
