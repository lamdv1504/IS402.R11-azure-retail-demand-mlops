"""HI04: same-origin baselines, horizon-safe inputs, native model save/load and CLI handoff."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from src.features.feature_engineering import build_features
from src.models.forecasting import (
    forecast_direct, model_matrix, predict_direct, seasonal_naive,
    validate_feature_order, validate_window,
)
from src.models.split_data import fingerprint
from src.models.train import train, validation_metrics


class LagModel:
    def predict(self, matrix):
        return matrix.lag_28.to_numpy()


class TrainingTests(unittest.TestCase):
    def setUp(self):
        rows = []
        for item, scale in [("ITEM_A", 1), ("ITEM_B", 2)]:
            for day in range(1, 113):
                date = pd.Timestamp("2011-01-29") + pd.Timedelta(days=day - 1)
                rows.append({
                    "item_id": item, "dept_id": "FOODS_1", "cat_id": "FOODS",
                    "store_id": "CA_1", "state_id": "CA", "d": f"d_{day}",
                    "day_number": day, "date": date, "wm_yr_wk": 11101 + (day - 1) // 7,
                    "weekday": date.day_name(), "wday": (day - 1) % 7 + 1,
                    "month": date.month, "year": date.year,
                    "event_name_1": None, "event_type_1": None,
                    "event_name_2": None, "event_type_2": None,
                    "snap_CA": day % 2, "snap_TX": 0, "snap_WI": 0,
                    "sell_price": 2.0, "sales": day * scale,
                })
        panel = pd.DataFrame(rows)
        self.history = panel.loc[panel.day_number.le(84)].copy()
        self.validation = panel.loc[panel.day_number.gt(84)].copy()
        self.future = self.validation.drop(columns="sales")
        self.train_features, vocab = build_features(self.history)
        self.future_features, _ = build_features(self.history, self.future, category_vocab=vocab)
        categories = list(vocab)
        self.order = ["lag_28", "lag_56", "wday", "item_id_code", "event_name_1_code"]
        self.schema = {"feature_list": list(self.train_features),
                       "categorical_columns": categories, "categorical_vocab": vocab}

    def test_seasonal_naive_repeats_observed_week_for_all_28_days(self):
        predicted = seasonal_naive(self.history, self.future)
        np.testing.assert_array_equal(predicted[:28], np.tile(np.arange(78, 85), 4))
        np.testing.assert_array_equal(predicted[28:], np.tile(np.arange(78, 85) * 2, 4))
        shuffled = self.future.sample(frac=1, random_state=42).reset_index(drop=True)
        result = seasonal_naive(self.history, shuffled)
        expected = (78 + ((shuffled.day_number - 85) % 7)) * np.where(shuffled.item_id.eq("ITEM_A"), 1, 2)
        np.testing.assert_array_equal(result, expected)

    def test_inference_matches_features_and_ignores_future_prices(self):
        expected = predict_direct(LagModel(), self.future_features, self.order, self.schema)
        predicted = forecast_direct(LagModel(), self.history, self.future, self.order, self.schema)
        np.testing.assert_array_equal(predicted.predicted_sales, expected)
        changed = self.future.copy()
        changed["sell_price"] = float("nan")
        rebuilt = forecast_direct(LagModel(), self.history, changed, self.order, self.schema)
        assert_frame_equal(predicted, rebuilt)

    def test_window_rejects_future_labels_missing_days_and_unknown_series(self):
        with self.assertRaisesRegex(ValueError, "nhãn sales"):
            validate_window(self.history, self.validation)
        with self.assertRaisesRegex(ValueError, "horizon"):
            validate_window(self.history, self.future.iloc[1:])
        changed = self.future.copy()
        changed.loc[changed.item_id.eq("ITEM_A"), "item_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "cùng các chuỗi"):
            validate_window(self.history, changed)
        with self.assertRaisesRegex(ValueError, "Lịch sử thiếu ngày"):
            validate_window(self.history.drop(index=self.history.index[1]), self.future)

    def test_unsafe_feature_choices_are_rejected(self):
        for column in ("lag_1", "rolling_mean_7", "sell_price", "sales"):
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "Direct horizon"):
                validate_feature_order(self.order + [column], self.schema)

    def test_native_categories_unknown_code_and_missing_lag(self):
        changed = self.future_features.copy()
        changed.loc[0, "event_name_1_code"] = -1
        matrix = model_matrix(changed, self.order, self.schema)
        self.assertEqual(str(matrix.item_id_code.dtype), "category")
        self.assertTrue(pd.isna(matrix.loc[0, "event_name_1_code"]))
        changed.loc[0, "lag_28"] = float("nan")
        with self.assertRaisesRegex(ValueError, "56 ngày"):
            model_matrix(changed, self.order, self.schema)

    def test_predictions_clip_negative_values_and_reject_nan(self):
        with patch.object(LagModel, "predict", return_value=np.full(len(self.future_features), -2)):
            self.assertTrue((predict_direct(LagModel(), self.future_features, self.order, self.schema) == 0).all())
        with patch.object(LagModel, "predict", return_value=np.full(len(self.future_features), np.nan)):
            with self.assertRaisesRegex(ValueError, "không hữu hạn"):
                predict_direct(LagModel(), self.future_features, self.order, self.schema)

    def test_mae_rmse_comparison_values(self):
        metrics = validation_metrics(np.array([1, 3]), np.array([0, 1]))
        self.assertEqual(metrics["mae"], 1.5)
        self.assertAlmostEqual(metrics["rmse"], np.sqrt(2.5))

    def test_missing_handoff_stops_before_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "artifacts"
            result = subprocess.run([
                sys.executable, "-X", "utf8", "src/models/train.py", "--splits-dir", directory,
                "--output-dir", str(output),
            ], capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Thiếu đầu vào bàn giao", result.stderr)
            self.assertFalse(output.exists())

    @unittest.skipUnless(importlib.util.find_spec("xgboost"), "Cần requirements-ml.txt cho integration test")
    def test_training_exports_reloadable_model_and_never_reads_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.history.to_parquet(root / "train.parquet", index=False)
            self.validation.to_parquet(root / "validation.parquet", index=False)
            self.train_features.to_parquet(root / "train_features.parquet", index=False)
            self.future_features.to_parquet(root / "validation_future_features.parquet", index=False)
            # An unreadable holdout must not affect HI04's validation-only training.
            (root / "test.parquet").write_bytes(b"holdout-must-not-be-read")
            config = {
                "seed": 42, "horizon": 28, "strategy": "direct_horizon_safe", "feature_order": self.order,
                "xgboost": {"n_estimators": 3, "max_depth": 2, "learning_rate": 0.1,
                            "objective": "count:poisson", "tree_method": "hist", "device": "cpu",
                            "n_jobs": 1, "enable_categorical": True},
            }
            split_log = {
                "config": {"data_version": "fixture-v1", "horizon": 28, "train_end_day": 84},
                "splits": {name: {"artifact": fingerprint(root / f"{name}.parquet")}
                           for name in ("train", "validation")},
            }
            def save_json(name, value):
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            save_json("schema.json", self.schema)
            save_json("config.json", config)
            save_json("split_log.json", split_log)
            save_json("feature_log.json", {
                "data_version": "fixture-v1", "schema": fingerprint(root / "schema.json"),
                "inputs": {name: fingerprint(root / f"{name}.parquet") for name in ("train", "validation")},
                "artifacts": {name: {"fingerprint": fingerprint(root / f"{name}.parquet")}
                              for name in ("train_features", "validation_future_features")},
            })
            args = argparse.Namespace(
                config=root / "config.json", splits_dir=root, features_dir=root,
                feature_schema=root / "schema.json", feature_log=root / "feature_log.json",
                split_log=root / "split_log.json", output_dir=root / "model",
                predictions=root / "predictions.csv", log=root / "log.json",
            )
            read_parquet = pd.read_parquet
            def forbid_holdout(path, *arguments, **keywords):
                self.assertNotEqual(Path(path).name, "test.parquet")
                return read_parquet(path, *arguments, **keywords)
            with patch("src.models.train.pd.read_parquet", side_effect=forbid_holdout):
                log = train(args)
            self.assertTrue(log["checks"]["model_reload_predictions_equal"])
            self.assertTrue(log["checks"]["raw_inference_matches_feature_predictions"])
            self.assertFalse(log["checks"]["holdout_read_or_evaluated"])
            self.assertEqual(log["rows_used_for_fit"], 56)
            self.assertEqual(log["warmup_rows_excluded"], 112)
            self.assertEqual(len(pd.read_csv(args.predictions)), 56)
            self.assertTrue((args.output_dir / "xgboost.ubj").is_file())


if __name__ == "__main__":
    unittest.main()
