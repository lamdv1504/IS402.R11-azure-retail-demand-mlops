"""HI05 metric arithmetic, temporal boundaries, selection and inference contracts."""

import argparse
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.models.evaluate import evaluate
from src.models.forecasting import FORECAST_KEYS
from src.models.metrics import rmsse_scale, score_forecast, select_model
from src.models.predict import ForecastPredictor, make_future


def panel():
    rows = []
    for item, units, price in [("A", 1, 2), ("B", 2, 3)]:
        for day in range(1, 113):
            date = pd.Timestamp("2011-01-29") + pd.Timedelta(days=day - 1)
            rows.append({
                "item_id": item, "store_id": "CA_1", "dept_id": "FOODS_1",
                "cat_id": "FOODS", "state_id": "CA", "sales": day * units,
                "d": f"d_{day}", "day_number": day, "date": date,
                "sell_price": price, "wm_yr_wk": 11101 + (day - 1) // 7,
                "weekday": date.day_name(), "wday": (day - 1) % 7 + 1,
                "month": date.month, "year": date.year,
                "event_name_1": None, "event_type_1": None, "event_name_2": None,
                "event_type_2": None, "snap_CA": day % 2, "snap_TX": 0, "snap_WI": 0,
            })
    return pd.DataFrame(rows)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        data = panel()
        self.history = data.loc[data.day_number.le(84)].copy()
        self.labels = data.loc[data.day_number.gt(84)].copy()
        self.forecast = self.labels[FORECAST_KEYS].copy()
        self.forecast["predicted_sales"] = self.labels.sales - 2

    def test_scale_trims_leading_zeros_and_rejects_undefined_cases(self):
        self.assertEqual(rmsse_scale([0, 0, 2, 4, 3]), 2.5)
        for invalid in [[0, 0], [1, 1], [0, 2], [1, np.nan], [-1, 2]]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                rmsse_scale(invalid)

    def test_rmsse_and_revenue_weighted_score_hand_calculation(self):
        metrics, details = score_forecast(self.history, self.labels, self.forecast)
        self.assertEqual(metrics["subset_rmsse"], 1.5)  # A:2, B:1
        self.assertEqual(metrics["subset_wrmsse"], 1.25)  # revenue ratio 1:3
        self.assertEqual(metrics["mae"], 2)
        self.assertEqual(metrics["rmse"], 2)
        np.testing.assert_array_equal(details.scale, [1, 4])
        np.testing.assert_array_equal(details.weight, [.25, .75])
        self.assertEqual(metrics["weight_start_day"], 57)
        self.assertEqual(metrics["weight_end_day"], 84)

    def test_alignment_is_independent_of_row_order(self):
        expected, _ = score_forecast(self.history, self.labels, self.forecast)
        actual, _ = score_forecast(self.history.sample(frac=1, random_state=1),
                                   self.labels.sample(frac=1, random_state=2),
                                   self.forecast.sample(frac=1, random_state=3))
        self.assertEqual(actual, expected)

    def test_target_sales_and_prices_do_not_change_scales_or_weights(self):
        _, first = score_forecast(self.history, self.labels, self.forecast)
        changed = self.labels.copy()
        changed["sales"] = 999
        changed["sell_price"] = 999
        _, second = score_forecast(self.history, changed, self.forecast)
        np.testing.assert_array_equal(first[["scale", "weight"]], second[["scale", "weight"]])

    def test_invalid_forecasts_and_incomplete_windows_fail(self):
        for frame in [self.forecast.iloc[1:], pd.concat([self.forecast, self.forecast.iloc[:1]]),
                      self.forecast.assign(predicted_sales=np.nan),
                      self.forecast.assign(predicted_sales=-1), self.forecast.assign(sales=1)]:
            with self.subTest(rows=len(frame)), self.assertRaises(ValueError):
                score_forecast(self.history, self.labels, frame)
        with self.assertRaises(ValueError):
            score_forecast(self.history, self.labels.iloc[1:], self.forecast)

    def test_missing_price_for_positive_units_is_not_zero_weight(self):
        changed = self.history.copy()
        changed.loc[changed.day_number.eq(84), "sell_price"] = np.nan
        with self.assertRaisesRegex(ValueError, "price"):
            score_forecast(changed, self.labels, self.forecast)

    def test_selection_uses_validation_rmsse_with_deterministic_tie_break(self):
        self.assertEqual(select_model({"xgboost": {"subset_rmsse": .8, "mae": 100},
                                       "seasonal_naive": {"subset_rmsse": 1, "mae": 0}}), "xgboost")
        self.assertEqual(select_model({"xgboost": {"subset_rmsse": 1},
                                       "seasonal_naive": {"subset_rmsse": 1}}), "seasonal_naive")
        with self.assertRaises(ValueError):
            select_model({"xgboost": {"subset_rmsse": np.nan}})

    def test_future_calendar_needs_no_labels_or_prices(self):
        calendar = self.labels.drop(columns=["sales", "sell_price"]).drop_duplicates("d")
        future = make_future(self.history, calendar)
        self.assertNotIn("sales", future)
        self.assertEqual(len(future), 56)
        self.assertTrue(future.sell_price.isna().all())
        with self.assertRaisesRegex(ValueError, "sales"):
            make_future(self.history, self.labels.drop_duplicates("d"))
        with self.assertRaisesRegex(ValueError, "calendar"):
            make_future(self.history, calendar.iloc[1:])
        with self.assertRaises(ValueError):
            make_future(self.history, calendar, 29)

    def test_api_response_horizon_rounding_scope_and_history(self):
        # Exercise the baseline branch without an estimator or disk artifacts.
        predictor = ForecastPredictor.__new__(ForecastPredictor)
        predictor.metadata = {"series": [["A", "CA_1"], ["B", "CA_1"]],
                              "minimum_history_days": 7, "model_version": "test", "data_version": "test"}
        predictor.algorithm = "seasonal_naive"
        calendar = self.labels.drop(columns=["sales", "sell_price"]).drop_duplicates("d")
        for horizon in [1, 7, 28]:
            result = predictor.predict("CA_1", "A", self.history, calendar, horizon)
            self.assertEqual(len(result["forecast"]), horizon)
            self.assertEqual(result["forecast_start_date"], "2011-04-23")
            self.assertEqual(result["total_predicted_sales"], sum(r["predicted_sales"] for r in result["forecast"]))
        with self.assertRaises(KeyError):
            predictor.predict("CA_1", "UNKNOWN", self.history, calendar)
        for horizon in [0, 29, True, 1.5]:
            with self.assertRaises(ValueError):
                predictor.predict("CA_1", "A", self.history, calendar, horizon)
        with self.assertRaises(ValueError):
            predictor.predict("CA_1", "A", self.history.loc[self.history.day_number.gt(80)], calendar)

    def test_missing_handoff_stops_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = argparse.Namespace(training_log=root / "hi04.json", split_log=root / "hi02.json",
                                      calendar=root / "calendar.csv", splits_dir=root / "splits",
                                      candidate_dir=root / "hi04", output_dir=root / "hi05")
            with self.assertRaisesRegex(ValueError, "Thiếu đầu vào"):
                evaluate(args)
            self.assertFalse(args.output_dir.exists())


if __name__ == "__main__":
    unittest.main()
