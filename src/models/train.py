"""HI04: train an XGBoost candidate and seasonal-naive baseline on one validation window.

Run from the repository root: python src/models/train.py
Final holdout data is never read or scored by HI04.
"""

import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.forecasting import (
    FORECAST_KEYS, forecast_direct, model_matrix, predict_direct,
    seasonal_naive, validate_feature_order, validate_window,
)
from src.models.split_data import SERIES_KEYS, describe_split, fingerprint


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def verify_artifact(path: Path, expected: dict) -> dict:
    actual = fingerprint(path)
    if actual["sha256"] != expected["sha256"]:
        raise ValueError(f"{path} không khớp bàn giao HI02/HI03; cần tái tạo đúng đầu vào.")
    return actual


def validation_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    error = np.asarray(actual, dtype=float) - np.asarray(predicted, dtype=float)
    if error.ndim != 1 or not len(error) or not np.isfinite(error).all():
        raise ValueError("Không thể chấm điểm các dự báo/nhãn rỗng hoặc không hữu hạn.")
    return {"mae": float(np.abs(error).mean()), "rmse": float(np.sqrt(np.square(error).mean()))}


def train(args: argparse.Namespace) -> dict:
    config_path = args.config
    paths = {
        "train": args.splits_dir / "train.parquet",
        "validation": args.splits_dir / "validation.parquet",
        "train_features": args.features_dir / "train_features.parquet",
        "validation_future_features": args.features_dir / "validation_future_features.parquet",
        "feature_schema": args.feature_schema, "feature_log": args.feature_log,
        "split_log": args.split_log, "training_config": config_path,
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError("Thiếu đầu vào bàn giao HI02/HI03: " + ", ".join(missing))
    config = read_json(config_path)
    schema = read_json(args.feature_schema)
    feature_log = read_json(args.feature_log)
    split_log = read_json(args.split_log)
    if config["strategy"] != "direct_horizon_safe" or config["horizon"] != 28:
        raise ValueError("HI04 hiện dùng direct horizon 28 ngày.")
    if config["horizon"] != split_log["config"]["horizon"]:
        raise ValueError("Horizon không khớp HI02.")
    if type(config["seed"]) is not int or config["seed"] < 0:
        raise ValueError("Seed phải là số nguyên không âm.")
    params = config["xgboost"]
    if (params.get("tree_method") != "hist" or not params.get("enable_categorical")
            or params.get("device") != "cpu" or "random_state" in params):
        raise ValueError("Dùng CPU hist, native categorical và seed từ training config.")
    feature_order = config["feature_order"]
    validate_feature_order(feature_order, schema)
    data_version = split_log["config"]["data_version"]
    if feature_log["data_version"] != data_version:
        raise ValueError("Phiên bản dữ liệu HI02 và HI03 không khớp.")
    inputs = {name: fingerprint(path) for name, path in paths.items()}
    inputs["training_code"] = fingerprint(Path(__file__))
    inputs["forecasting_code"] = fingerprint(Path(__file__).with_name("forecasting.py"))
    inputs["feature_builder_code"] = fingerprint(Path(__file__).resolve().parents[1] / "features" / "feature_engineering.py")
    verify_artifact(args.feature_schema, feature_log["schema"])
    for name in ("train", "validation"):
        verify_artifact(paths[name], split_log["splits"][name]["artifact"])
        verify_artifact(paths[name], feature_log["inputs"][name])
    for name in ("train_features", "validation_future_features"):
        verify_artifact(paths[name], feature_log["artifacts"][name]["fingerprint"])

    history = pd.read_parquet(paths["train"])
    validation = pd.read_parquet(paths["validation"])
    train_features = pd.read_parquet(paths["train_features"])
    future_features = pd.read_parquet(paths["validation_future_features"])
    sort_keys = SERIES_KEYS + ["day_number"]
    future_features = future_features.sort_values(sort_keys).reset_index(drop=True)
    origin = validate_window(history, future_features, config["horizon"])
    if origin != split_log["config"]["train_end_day"]:
        raise ValueError("Origin validation khác mốc HI02.")
    if len(train_features) != len(history) or int(train_features.day_number.max()) != origin:
        raise ValueError("Feature train khác phạm vi lịch sử HI02.")
    matched_train = train_features[FORECAST_KEYS + ["sales"]].merge(
        history[FORECAST_KEYS + ["sales"]], on=FORECAST_KEYS, how="outer",
        validate="one_to_one", suffixes=("_features", "_history"), indicator=True,
    )
    if (not matched_train["_merge"].eq("both").all()
            or not matched_train.sales_features.eq(matched_train.sales_history).all()):
        raise ValueError("Nhãn hoặc khóa feature train không khớp HI02.")
    ready = train_features[["lag_28", "lag_56"]].notna().all(axis=1)
    training_rows = train_features.loc[ready].sort_values(sort_keys).reset_index(drop=True)
    if training_rows.empty:
        raise ValueError("Không đủ lịch sử 56 ngày để huấn luyện.")
    x_train = model_matrix(training_rows, feature_order, schema)
    y_train = training_rows.sales.to_numpy(dtype=float)
    if not np.isfinite(y_train).all() or (y_train < 0).any():
        raise ValueError("Sales train phải hữu hạn và không âm.")

    from xgboost import XGBRegressor

    model = XGBRegressor(**params, random_state=config["seed"])
    print(f"Huấn luyện XGBoost: {len(training_rows):,} dòng, {len(feature_order)} feature, seed={config['seed']}", flush=True)
    started = time.perf_counter()
    model.fit(x_train, y_train, verbose=False)
    training_seconds = time.perf_counter() - started
    xgb_predictions = predict_direct(model, future_features, feature_order, schema)
    baseline_predictions = seasonal_naive(history, future_features, config["horizon"])

    # Verify the HI05 entry point rebuilds exactly the validation prediction from raw covariates.
    inference = forecast_direct(model, history, validation.drop(columns="sales"), feature_order, schema)
    inference = inference.sort_values(sort_keys).reset_index(drop=True)
    if not np.allclose(inference.predicted_sales, xgb_predictions, rtol=0, atol=1e-6):
        raise ValueError("Đặc trưng/suy luận tái tạo khác dự báo trên feature HI03.")
    predictions = future_features[FORECAST_KEYS].copy()
    predictions["seasonal_naive"] = baseline_predictions
    predictions["xgboost_prediction"] = xgb_predictions
    predictions = predictions.merge(validation[FORECAST_KEYS + ["sales"]], on=FORECAST_KEYS,
                                     how="outer", validate="one_to_one", indicator=True)
    if not predictions["_merge"].eq("both").all():
        raise ValueError("Dự báo và nhãn validation không cùng khóa item-store-day.")
    predictions = predictions.drop(columns="_merge").rename(columns={"sales": "actual_sales"})
    metrics = {
        "seasonal_naive": validation_metrics(predictions.actual_sales, predictions.seasonal_naive),
        "xgboost": validation_metrics(predictions.actual_sales, predictions.xgboost_prediction),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "xgboost.ubj"
    model.save_model(model_path)
    model_fingerprint = fingerprint(model_path)
    loaded = XGBRegressor(n_jobs=params["n_jobs"], enable_categorical=True)
    loaded.load_model(model_path)
    loaded_predictions = predict_direct(loaded, future_features, feature_order, schema)
    if not np.array_equal(loaded_predictions, xgb_predictions):
        raise ValueError("Model sau load không trả cùng dự báo validation.")
    package_paths = {
        "feature_order": args.output_dir / "feature_order.json",
        "feature_schema": args.output_dir / "feature_schema.json",
        "training_config": args.output_dir / "training_config.json",
        "metadata": args.output_dir / "model_metadata.json",
    }
    write_json(package_paths["feature_order"], feature_order)
    write_json(package_paths["feature_schema"], schema)
    write_json(package_paths["training_config"], config)
    metadata = {
        "task": "HI04", "model_name": "xgboost", "model_version": "hi04-xgb-" + model_fingerprint["sha256"][:12],
        "data_version": data_version, "status": "candidate_for_HI05", "strategy": config["strategy"],
        "horizon": config["horizon"], "seed": config["seed"], "minimum_history_days": 56,
        "categorical_handling": "Native XGBoost categories dùng vocabulary train HI03; mã -1 là missing.",
        "output_policy": "Float units, clip tại 0, không làm tròn số nguyên.",
        "pricing_policy": "Không dùng sell_price, price change hoặc is_active; không cần giá future đã biết.",
        "scope": {"stores": sorted(history.store_id.astype(str).unique().tolist()),
                  "series_count": len(history[SERIES_KEYS].drop_duplicates())},
        "training_window": describe_split(history), "validation_window": describe_split(validation),
        "holdout_evaluated": False,
    }
    write_json(package_paths["metadata"], metadata)
    args.predictions.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.predictions, index=False, date_format="%Y-%m-%d")
    versions = {name: importlib.metadata.version(name)
                for name in ["numpy", "pandas", "pyarrow", "scipy", "scikit-learn", "xgboost"]}
    log = {
        "task": "HI04", "data_version": data_version, "strategy": config["strategy"],
        "inputs": inputs, "config": config, "python_version": platform.python_version(), "packages": versions,
        "scope": metadata["scope"], "windows": {"train": describe_split(history),
                                               "validation": describe_split(validation)},
        "rows_used_for_fit": len(training_rows), "warmup_rows_excluded": int((~ready).sum()),
        "training_seconds": round(training_seconds, 3), "validation_metrics": metrics,
        "metric_scope": "MAE/RMSE chỉ trên CA_1 MVP 300 chuỗi, 28 ngày validation; chưa tính RMSSE/WRMSSE HI05.",
        "checks": {"future_labels_excluded": True, "complete_28_day_forecasts": True,
                   "finite_nonnegative_forecasts": True, "model_reload_predictions_equal": True,
                   "raw_inference_matches_feature_predictions": True, "holdout_read_or_evaluated": False},
        "artifacts": {"model": model_fingerprint, "validation_predictions": fingerprint(args.predictions),
                      **{name: fingerprint(path) for name, path in package_paths.items()}},
    }
    write_json(args.log, log)
    for name, entry in metrics.items():
        print(f"{name}: MAE={entry['mae']:.6f}; RMSE={entry['rmse']:.6f}", flush=True)
    print(f"Model: {model_path}; dự báo: {args.predictions}; log: {args.log}", flush=True)
    return log


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="HI04: XGBoost và seasonal naive trên validation 28 ngày")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("train_config.json"))
    parser.add_argument("--splits-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--features-dir", type=Path, default=Path("data/processed/features"))
    parser.add_argument("--feature-schema", type=Path, default=Path("reports/hi03_feature_schema.json"))
    parser.add_argument("--feature-log", type=Path, default=Path("reports/hi03_feature_log.json"))
    parser.add_argument("--split-log", type=Path, default=Path("reports/hi02_split_log.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/hi04"))
    parser.add_argument("--predictions", type=Path, default=Path("reports/hi04_validation_predictions.csv"))
    parser.add_argument("--log", type=Path, default=Path("reports/hi04_training_log.json"))
    args = parser.parse_args()
    try:
        train(args)
    except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        parser.exit(1, f"Dừng HI04: {exc}\n")


if __name__ == "__main__":
    main()
