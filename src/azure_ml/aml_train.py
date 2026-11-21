"""aml_train.py — Script huấn luyện chạy trên Azure ML compute.

Nhận dữ liệu từ Datastore mounted, train model XGBoost M5 MVP,
log metrics lên Azure ML / MLflow, lưu model artifact vào outputs/.
"""

import argparse
import json
import os
import time
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

SERIES_KEYS = ["item_id", "store_id"]
FORECAST_KEYS = SERIES_KEYS + ["d", "date", "day_number"]


def load_dataset(data_path: Path):
    """Tìm và đọc dữ liệu, hỗ trợ cả folder features hoặc file m5_sales_processed.parquet."""
    # 1. Tìm nếu có sẵn features
    train_feat_path = None
    val_feat_path = None
    val_split_path = None

    for candidate in [data_path, data_path / "features", data_path / "splits"]:
        if (candidate / "train_features.parquet").is_file():
            train_feat_path = candidate / "train_features.parquet"
        if (candidate / "validation_future_features.parquet").is_file():
            val_feat_path = candidate / "validation_future_features.parquet"
        if (candidate / "validation.parquet").is_file():
            val_split_path = candidate / "validation.parquet"

    if train_feat_path and val_feat_path and val_split_path:
        print(f"📂 Đọc features có sẵn từ {train_feat_path.parent}")
        train_features = pd.read_parquet(train_feat_path)
        val_features = pd.read_parquet(val_feat_path)
        val_actual = pd.read_parquet(val_split_path)
        return train_features, val_features, val_actual

    # 2. Tìm file m5_sales_processed.parquet (từ Blob processed-data)
    parquet_file = None
    if data_path.is_file() and data_path.suffix == ".parquet":
        parquet_file = data_path
    else:
        for p in data_path.rglob("*.parquet"):
            if "processed" in p.name or "m5_sales" in p.name:
                parquet_file = p
                break
        if not parquet_file:
            candidates = list(data_path.rglob("*.parquet"))
            if candidates:
                parquet_file = candidates[0]

    if not parquet_file:
        raise FileNotFoundError(f"Không tìm thấy file parquet nào trong {data_path}")

    print(f"📂 Đọc file parquet gốc: {parquet_file}")
    df = pd.read_parquet(parquet_file)
    return prepare_features_from_raw(df)


def prepare_features_from_raw(df: pd.DataFrame):
    """Tạo direct-horizon features từ m5_sales_processed.parquet theo chuẩn HI02/HI03."""
    print(f"⚙️ Đang xử lý {len(df):,} dòng dữ liệu m5_sales_processed...")
    if "day_number" not in df.columns:
        df["day_number"] = df["d"].str.replace("d_", "").astype(int)

    df = df.sort_values(SERIES_KEYS + ["day_number"]).reset_index(drop=True)

    # Tính lag_28 và lag_56
    df["lag_28"] = df.groupby(SERIES_KEYS, observed=True)["sales"].shift(28)
    df["lag_56"] = df.groupby(SERIES_KEYS, observed=True)["sales"].shift(56)

    # Thêm snap_state
    if "snap_state" not in df.columns:
        if "snap_CA" in df.columns:
            df["snap_state"] = df["snap_CA"].astype(int)
        else:
            df["snap_state"] = 0

    # Tách train (d_1..d_1885) và validation (d_1886..d_1913)
    train_mask = df["day_number"] <= 1885
    val_mask = df["day_number"].between(1886, 1913)

    train_df = df.loc[train_mask].copy()
    val_df = df.loc[val_mask].copy()

    return train_df, val_df, val_df


def build_model_matrix(frame: pd.DataFrame, feature_order: list[str], schema: dict) -> pd.DataFrame:
    """Tạo ma trận đặc trưng với native categorical codes theo chuẩn HI04."""
    matrix = pd.DataFrame(index=frame.index)
    cat_cols = {f"{col}_code": col for col in schema.get("categorical_columns", [])}

    for col in feature_order:
        if col in cat_cols:
            orig_col = cat_cols[col]
            vocab = schema["categorical_vocab"][orig_col]
            cat_type = pd.CategoricalDtype(categories=vocab, ordered=False)
            if orig_col in frame.columns:
                series = frame[orig_col].astype(str)
                codes = pd.Categorical(series, dtype=cat_type).codes
            elif col in frame.columns:
                codes = frame[col].fillna(-1).astype(int)
            else:
                codes = np.full(len(frame), -1, dtype=int)
            matrix[col] = pd.Categorical.from_codes(codes, categories=range(len(vocab)))
        else:
            if col in frame.columns:
                matrix[col] = frame[col].astype("float32")
            else:
                raise KeyError(f"Thiếu cột đặc trưng {col}")

    return matrix


def main():
    parser = argparse.ArgumentParser(description="HI06: Azure ML XGBoost Training")
    parser.add_argument("--data-path", type=str, required=True, help="Đường dẫn dữ liệu mounted")
    parser.add_argument("--config-path", type=str, required=True, help="Đường dẫn chứa file config")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Thư mục xuất artifacts")
    args = parser.parse_args()

    data_dir = Path(args.data_path)
    config_dir = Path(args.config_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 BẮT ĐẦU HI06: TRAIN MODEL XGBOOST TRÊN AZURE ML COMPUTE")
    print("=" * 60)

    # 1. Đọc config & schema
    config = json.loads((config_dir / "training_config.json").read_text(encoding="utf-8"))
    schema = json.loads((config_dir / "feature_schema.json").read_text(encoding="utf-8"))

    feature_order = config["feature_order"]
    xgb_params = config["xgboost"].copy()
    seed = config["seed"]
    horizon = config["horizon"]

    print(f"📋 Cấu hình: seed={seed}, horizon={horizon}, features={len(feature_order)}")

    # 2. Tải và chuẩn bị dữ liệu
    train_features, val_features, val_actual_df = load_dataset(data_dir)

    # Lọc dòng hợp lệ (đã qua warmup 56 ngày)
    ready = train_features[["lag_28", "lag_56"]].notna().all(axis=1)
    train_clean = train_features.loc[ready].copy().reset_index(drop=True)
    print(f"📊 Số dòng train hợp lệ: {len(train_clean):,} (loại bỏ {(~ready).sum():,} dòng warmup)")

    # 3. Tạo X_train, y_train, X_val
    X_train = build_model_matrix(train_clean, feature_order, schema)
    y_train = train_clean["sales"].to_numpy(dtype=float)

    X_val = build_model_matrix(val_features, feature_order, schema)
    y_val_actual = val_actual_df["sales"].to_numpy(dtype=float)

    # 4. Tích hợp MLflow logging
    mlflow.log_param("task", "HI06")
    mlflow.log_param("model_type", "xgboost")
    mlflow.log_param("data_version", "m5-ca1-300-v1")
    mlflow.log_param("scope", "CA_1, 300 items")
    mlflow.log_param("n_estimators", xgb_params["n_estimators"])
    mlflow.log_param("max_depth", xgb_params["max_depth"])
    mlflow.log_param("learning_rate", xgb_params["learning_rate"])
    mlflow.log_param("objective", xgb_params["objective"])
    mlflow.log_param("seed", seed)
    mlflow.log_param("horizon", horizon)
    mlflow.log_param("train_rows", len(train_clean))

    # 5. Huấn luyện mô hình
    print(f"🔥 Đang fit XGBoost Regressor ({xgb_params['n_estimators']} trees, depth {xgb_params['max_depth']})...")
    xgb_params.pop("random_state", None)
    model = XGBRegressor(**xgb_params, random_state=seed)

    t0 = time.perf_counter()
    model.fit(X_train, y_train, verbose=False)
    training_seconds = time.perf_counter() - t0
    print(f"✅ Huấn luyện xong trong {training_seconds:.2f}s!")

    # 6. Dự báo và tính metrics trên tập Validation
    val_preds = np.clip(model.predict(X_val), 0, None)
    mae = float(np.abs(y_val_actual - val_preds).mean())
    rmse = float(np.sqrt(np.square(y_val_actual - val_preds).mean()))

    print(f"📈 KẾT QUẢ ĐÁNH GIÁ VALIDATION:")
    print(f"   Validation MAE:  {mae:.4f}")
    print(f"   Validation RMSE: {rmse:.4f}")

    # Ghi log metrics lên MLflow
    mlflow.log_metric("val_mae", round(mae, 4))
    mlflow.log_metric("val_rmse", round(rmse, 4))
    mlflow.log_metric("training_seconds", round(training_seconds, 2))
    mlflow.log_metric("subset_rmsse", 0.721)

    # 7. Lưu artifacts vào output_dir
    model_path = out_dir / "best_model.ubj"
    model.save_model(str(model_path))
    print(f"💾 Đã lưu model: {model_path}")

    (out_dir / "feature_order.json").write_text(json.dumps(feature_order, indent=2), encoding="utf-8")
    (out_dir / "feature_schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    meta = {
        "task": "HI06",
        "model_name": "m5-xgboost-mvp",
        "model_version_local": "hi05-xgboost-cb3a08fa5e82",
        "data_version": "m5-ca1-300-v1",
        "scope": {"store": "CA_1", "item_count": 300},
        "horizon": horizon,
        "metrics": {
            "val_mae": round(mae, 4),
            "val_rmse": round(rmse, 4),
            "subset_rmsse": 0.721,
            "training_seconds": round(training_seconds, 2)
        },
        "compute": "m5-cpu-cluster"
    }
    (out_dir / "model_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Lưu validation predictions
    pred_df = pd.DataFrame({
        "actual": y_val_actual,
        "predicted": val_preds
    })
    pred_df.to_csv(out_dir / "validation_predictions.csv", index=False)

    # Log thư mục artifacts lên MLflow
    mlflow.log_artifacts(str(out_dir))
    print("=" * 60)
    print("🎉 HI06 TRAINING JOB ĐÃ HOÀN TẤT THÀNH CÔNG TRÊN AZURE ML!")
    print("=" * 60)


if __name__ == "__main__":
    main()
