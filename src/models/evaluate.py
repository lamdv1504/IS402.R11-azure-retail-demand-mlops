"""HI05: select on validation, freeze the model, then score the final holdout once."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import sys

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.features.feature_engineering import CALENDAR_COLUMNS
from src.models.forecasting import FORECAST_KEYS, forecast_direct, seasonal_naive
from src.models.metrics import SCOPE_NOTE, score_forecast, select_model
from src.models.predict import ForecastPredictor, make_future
from src.models.split_data import SERIES_KEYS, describe_split, fingerprint
from src.models.train import read_json, verify_artifact, write_json


def evaluate(args: argparse.Namespace) -> dict:
    required = [args.training_log, args.split_log, args.calendar,
                args.splits_dir / "train.parquet", args.splits_dir / "validation.parquet",
                args.splits_dir / "test.parquet"]
    required += [args.candidate_dir / name for name in
                 ["xgboost.ubj", "feature_order.json", "feature_schema.json",
                  "training_config.json", "model_metadata.json"]]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Thiếu đầu vào bàn giao HI02/HI04/Hùng: " + ", ".join(missing))
    # A completed or interrupted final evaluation must be reviewed, never silently rerun.
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Output directory is not empty; reuse the recorded holdout result.")
    training_log = read_json(args.training_log)
    split_log = read_json(args.split_log)
    for name, filename in {"model": "xgboost.ubj", "feature_order": "feature_order.json",
                           "feature_schema": "feature_schema.json", "training_config": "training_config.json",
                           "metadata": "model_metadata.json"}.items():
        verify_artifact(args.candidate_dir / filename, training_log["artifacts"][name])
    config = read_json(args.candidate_dir / "training_config.json")
    schema = read_json(args.candidate_dir / "feature_schema.json")
    order = read_json(args.candidate_dir / "feature_order.json")
    candidate_meta = read_json(args.candidate_dir / "model_metadata.json")
    if (split_log["config"] != read_json(Path(training_log["inputs"]["split_log"]["path"]))["config"]
            or config != training_log["config"] or order != config["feature_order"]
            or candidate_meta["data_version"] != split_log["config"]["data_version"]):
        raise ValueError("Candidate config/data version does not match HI02/HI04.")
    # Inference must use exactly the feature implementation that produced the candidate.
    for name in ["forecasting_code", "feature_builder_code"]:
        verify_artifact(Path(training_log["inputs"][name]["path"]), training_log["inputs"][name])
    verify_artifact(args.split_log, training_log["inputs"]["split_log"])
    verify_artifact(args.calendar, split_log["inputs"]["calendar"])
    for name in ["train", "validation"]:
        verify_artifact(args.splits_dir / f"{name}.parquet", split_log["splits"][name]["artifact"])
        verify_artifact(args.splits_dir / f"{name}.parquet", training_log["inputs"][name])
    history = pd.read_parquet(args.splits_dir / "train.parquet")
    validation = pd.read_parquet(args.splits_dir / "validation.parquet")
    if (history.day_number.max() != 1885 or validation.day_number.min() != 1886
            or validation.day_number.max() != 1913 or config["horizon"] != 28):
        raise ValueError("HI05 requires the fixed HI02 M5 28-day validation split.")
    from xgboost import XGBRegressor
    candidate = XGBRegressor(n_jobs=4, enable_categorical=True)
    candidate.load_model(args.candidate_dir / "xgboost.ubj")
    future = validation.drop(columns="sales")
    xgb = forecast_direct(candidate, history, future, order, schema)
    naive = future[FORECAST_KEYS].copy()
    naive["predicted_sales"] = seasonal_naive(history, future)
    validation_metrics, details, frames = {}, [], []
    for name, forecasts in [("seasonal_naive", naive), ("xgboost", xgb)]:
        validation_metrics[name], detail = score_forecast(history, validation, forecasts)
        detail["model"] = name
        details.append(detail)
        frame = forecasts.merge(validation[FORECAST_KEYS + ["sales"]], on=FORECAST_KEYS, validate="one_to_one")
        frame["model"] = name
        frames.append(frame)
    selected = select_model(validation_metrics)
    selection = {
        "selected_model": selected, "metric": "validation_subset_rmsse",
        "tie_break": "lexicographic model name", "validation_metrics": validation_metrics,
        "training_end_day": 1885, "validation_end_day": 1913,
        "refit_policy": "Keep the selected HI04 estimator unchanged for holdout and serving.",
        "holdout_used_for_selection": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "selection.json", selection)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(frames).to_csv(args.reports_dir / "hi05_validation_predictions.csv", index=False, date_format="%Y-%m-%d")
    pd.concat(details).to_csv(args.reports_dir / "hi05_validation_series_metrics.csv", index=False)
    pd.DataFrame([{"model": name, **metrics} for name, metrics in validation_metrics.items()]).to_csv(
        args.reports_dir / "hi05_model_comparison.csv", index=False)
    print(f"Selected {selected} using validation RMSSE; selection saved before reading holdout.", flush=True)

    # Selection and estimator are now locked. No fit, tuning or model comparison below.
    test_path = args.splits_dir / "test.parquet"
    test_fingerprint = verify_artifact(test_path, split_log["splits"]["test"]["artifact"])
    test = pd.read_parquet(test_path)
    if test.day_number.min() != 1914 or test.day_number.max() != 1941:
        raise ValueError("Final holdout must be d_1914...d_1941.")
    observed = pd.concat([history, validation], ignore_index=True)
    test_future = test.drop(columns="sales")
    if selected == "xgboost":
        test_forecast = forecast_direct(candidate, observed, test_future, order, schema)
    else:
        test_forecast = test_future[FORECAST_KEYS].copy()
        test_forecast["predicted_sales"] = seasonal_naive(observed, test_future)
    holdout_metrics, holdout_detail = score_forecast(observed, test, test_forecast)
    test_forecast.merge(test[FORECAST_KEYS + ["sales"]], on=FORECAST_KEYS, validate="one_to_one").to_csv(
        args.reports_dir / "hi05_test_predictions.csv", index=False, date_format="%Y-%m-%d")
    holdout_detail.to_csv(args.reports_dir / "hi05_test_series_metrics.csv", index=False)
    metrics = {"task": "HI05", "metric_scope_note": SCOPE_NOTE,
               "validation": validation_metrics, "selected_model": selected,
               "holdout": {selected: holdout_metrics}, "holdout_evaluation_count": 1,
               "scale_policy": "All observed history before each origin, trimmed at first nonzero demand.",
               "undefined_scale_policy": "Fail explicitly; do not silently exclude series or add epsilon."}
    write_json(args.output_dir / "metrics.json", metrics)
    if selected == "xgboost":
        candidate.save_model(args.output_dir / "best_model.ubj")
        model_hash = fingerprint(args.output_dir / "best_model.ubj")["sha256"]
    else:
        write_json(args.output_dir / "best_model.json", {"algorithm": selected, "period": 7})
        model_hash = fingerprint(args.output_dir / "best_model.json")["sha256"]
    write_json(args.output_dir / "feature_order.json", order if selected == "xgboost" else [])
    write_json(args.output_dir / "feature_schema.json", schema)
    write_json(args.output_dir / "model_config.json", {**config, "selected_algorithm": selected})

    # A small serving context suffices: 56 observed days and the next 28 calendar days.
    all_observed = pd.concat([observed, test], ignore_index=True)
    serving_history = all_observed.loc[all_observed.day_number.gt(1941 - 56)].copy()
    calendar = pd.read_csv(args.calendar)
    calendar["date"] = pd.to_datetime(calendar["date"])
    calendar["_day"] = calendar.d.str.removeprefix("d_").astype(int)
    future_calendar = calendar.loc[calendar._day.between(1942, 1969),
                                   list(dict.fromkeys([*CALENDAR_COLUMNS, "wm_yr_wk"]))]
    make_future(serving_history, future_calendar)
    serving_history.to_parquet(args.output_dir / "inference_history.parquet", index=False)
    future_calendar.to_csv(args.output_dir / "future_calendar.csv", index=False, date_format="%Y-%m-%d")
    metadata = {
        "task": "HI05", "algorithm": selected, "status": "ready",
        "model_version": "hi05-" + selected + "-" + model_hash[:12],
        "data_version": candidate_meta["data_version"], "forecast_horizon": 28,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "training_date": datetime.fromtimestamp(
            (args.candidate_dir / "xgboost.ubj").stat().st_mtime, timezone.utc).isoformat(),
        "training_date_source": "HI04 model file mtime (estimate; HI04 did not record fit timestamp).",
        "minimum_history_days": 56 if selected == "xgboost" else 7,
        "strategy": config["strategy"] if selected == "xgboost" else "repeat_final_observed_week",
        "series": sorted([list(row) for row in history[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None)]),
        "training_window": describe_split(history), "validation_window": describe_split(validation),
        "holdout_window": describe_split(test), "serving_history_window": describe_split(serving_history),
        "refit_after_selection": False,
        "output_policy": "Float units clipped at zero; metrics use full precision; API rounds daily units to 2 decimals and sums displayed daily values.",
        "pricing_policy": "No future prices required by selected features; future sell_price is missing.",
        "files": {p.name: fingerprint(p) for p in sorted(args.output_dir.iterdir()) if p.is_file()},
    }
    write_json(args.output_dir / "model_metadata.json", metadata)
    predictor = ForecastPredictor(args.output_dir)
    reloaded = predictor.forecast(history, future).sort_values(SERIES_KEYS + ["day_number"])
    expected = (xgb if selected == "xgboost" else naive).sort_values(SERIES_KEYS + ["day_number"])
    if not np.array_equal(reloaded.predicted_sales, expected.predicted_sales):
        raise ValueError("Reloaded best model differs from selected validation predictions.")
    production_future = make_future(serving_history, future_calendar)
    production = predictor.forecast(serving_history, production_future)
    production.to_csv(args.reports_dir / "hi05_future_predictions.csv", index=False, date_format="%Y-%m-%d")
    item_id, store_id = metadata["series"][0]
    request = {"store_id": store_id, "item_id": item_id, "horizon": 28}
    write_json(args.reports_dir / "hi05_sample_request.json", request)
    response = predictor.predict(**request, history=serving_history, calendar=future_calendar)
    write_json(args.reports_dir / "hi05_sample_response.json", response)
    chosen_metrics = validation_metrics[selected]
    write_json(args.output_dir / "model_info.json", {
        "model_name": "M5 Retail Demand " + selected, "model_version": metadata["model_version"],
        "algorithm": selected, "status": "ready", "training_date": metadata["training_date"],
        "data_version": metadata["data_version"], "store_scope": candidate_meta["scope"]["stores"],
        "item_count": len(metadata["series"]), "forecast_horizon": 28,
        "features_used": order if selected == "xgboost" else ["last_observed_week"],
        "temporal_split": {"train_period": "d_1...d_1885", "validation_period": "d_1886...d_1913",
                           "holdout_period": "d_1914...d_1941"},
        "metrics": {**{"validation_" + name: chosen_metrics[name]
                       for name in ["subset_rmsse", "subset_wrmsse", "mae", "rmse"]}, "metric_scope_note": SCOPE_NOTE},
    })
    log = {
        "task": "HI05", "selection": selection, "metrics": metrics,
        "inputs": {"hi04_log": fingerprint(args.training_log), "hi02_log": fingerprint(args.split_log),
                   "test": test_fingerprint, "calendar": fingerprint(args.calendar)},
        "source_code": {name: fingerprint(Path(__file__).with_name(name))
                        for name in ["evaluate.py", "metrics.py", "predict.py", "forecasting.py"]},
        "packages": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "pyarrow", "xgboost", "scikit-learn"]},
        "checks": {"selection_saved_before_holdout_read": True, "holdout_evaluations": 1,
                   "holdout_not_used_for_tuning": True, "model_reload_matches_validation": True,
                   "future_forecasts": len(production), "sample_response_days": len(response["forecast"]),
                   "future_sales_or_prices_required": False},
        "artifacts": {p.name: fingerprint(p) for p in sorted(args.output_dir.iterdir()) if p.is_file()},
        "reports": {p.name: fingerprint(p) for p in sorted(args.reports_dir.glob("hi05_*.csv"))},
    }
    write_json(args.reports_dir / "hi05_evaluation_log.json", log)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=Path("artifacts/hi04"))
    parser.add_argument("--training-log", type=Path, default=Path("reports/hi04_training_log.json"))
    parser.add_argument("--split-log", type=Path, default=Path("reports/hi02_split_log.json"))
    parser.add_argument("--splits-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--calendar", type=Path, default=Path("data/raw/calendar.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/hi05"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()
    try:
        result = evaluate(args)
        print(f"HI05 complete: {result['selected_model']}; final holdout evaluated once.")
    except (ValueError, KeyError, FileNotFoundError) as exc:
        parser.exit(1, f"HI05 stopped: {exc}\n")


if __name__ == "__main__":
    main()
