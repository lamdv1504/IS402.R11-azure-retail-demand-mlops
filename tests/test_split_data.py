"""HI02: verify temporal boundaries and isolation of future sales labels."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from src.models.split_data import SplitConfig, make_backtest_context, prepare_data, split_data


class SplitDataTests(unittest.TestCase):
    def setUp(self):
        self.config = SplitConfig("fixture-v1", 10, 14, 18, 4, 7)
        self.calendar = pd.DataFrame({
            "d": [f"d_{day}" for day in range(1, 19)],
            "date": pd.date_range("2011-01-29", periods=18),
        })
        self.scope = pd.DataFrame({"item_id": ["ITEM_A", "ITEM_B"], "store_id": ["CA_1", "CA_1"]})
        self.frame = pd.concat([
            self.calendar.assign(item_id=item, store_id="CA_1", sales=range(18), sell_price=2.0)
            for item in self.scope["item_id"]
        ], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)

    def prepare(self, frame=None):
        return prepare_data(self.frame if frame is None else frame, self.calendar, self.scope, self.config)

    def test_numeric_day_order_complete_windows_and_no_lost_rows(self):
        data = self.prepare()
        splits = split_data(data, self.config)
        self.assertEqual(data.loc[data.item_id.eq("ITEM_A"), "day_number"].tolist(), list(range(1, 19)))
        self.assertEqual({name: len(rows) for name, rows in splits.items()},
                         {"train": 20, "validation": 8, "test": 8})
        self.assertEqual(sum(map(len, splits.values())), len(self.frame))
        day_sets = {name: set(rows["d"]) for name, rows in splits.items()}
        self.assertFalse(day_sets["train"] & day_sets["validation"])
        self.assertFalse(day_sets["validation"] & day_sets["test"])
        self.assertEqual(splits["validation"].date.min(), pd.Timestamp("2011-02-08"))

    def test_validation_labels_cannot_change_its_history_or_future_inputs(self):
        splits = split_data(self.prepare(), self.config)
        before = make_backtest_context(splits, "validation")
        splits["validation"].loc[:, "sales"] = 999
        after = make_backtest_context(splits, "validation")
        assert_frame_equal(before.history, after.history)
        assert_frame_equal(before.future, after.future)
        self.assertNotIn("sales", after.future.columns)
        self.assertTrue(after.labels.sales.eq(999).all())
        self.assertEqual(int(after.history.day_number.max()), 10)

    def test_test_uses_refit_history_only_through_validation_end(self):
        splits = split_data(self.prepare(), self.config)
        before = make_backtest_context(splits, "test")
        splits["test"].loc[:, "sales"] = 999
        after = make_backtest_context(splits, "test")
        assert_frame_equal(before.history, after.history)
        assert_frame_equal(before.future, after.future)
        self.assertEqual(int(after.history.day_number.max()), 14)
        self.assertEqual(len(after.history), 28)
        self.assertNotIn("sales", after.future.columns)

    def test_validation_only_source_does_not_invent_holdout_labels(self):
        frame = self.frame.loc[~self.frame.d.isin([f"d_{day}" for day in range(15, 19)])]
        splits = split_data(self.prepare(frame), self.config)
        self.assertEqual(set(splits), {"train", "validation"})
        with self.assertRaisesRegex(ValueError, "chưa có nhãn"):
            make_backtest_context(splits, "test")

    def test_reject_duplicate_key_and_missing_day_in_one_series(self):
        for frame in [pd.concat([self.frame, self.frame.iloc[[0]]]), self.frame.iloc[1:]]:
            with self.subTest(rows=len(frame)), self.assertRaises(ValueError):
                self.prepare(frame)

    def test_reject_incorrect_calendar_and_wrong_day_number(self):
        frame = self.frame.copy()
        frame.loc[frame.d.eq("d_10"), "date"] += pd.Timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "Mapping"):
            self.prepare(frame)
        frame = self.frame.copy()
        frame.loc[0, "d"] = "day_18"
        with self.assertRaisesRegex(ValueError, "Mã ngày"):
            self.prepare(frame)

    def test_reject_unknown_or_missing_series(self):
        frame = self.frame.copy()
        frame.loc[frame.item_id.eq("ITEM_A"), "item_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "danh sách MVP"):
            self.prepare(frame)

    def test_reject_invalid_sales_but_preserve_zero_sales_and_missing_price(self):
        for value in [-1, float("nan"), float("inf"), 1.5]:
            frame = self.frame.copy()
            frame["sales"] = frame.sales.astype(float)
            frame.loc[0, "sales"] = value
            with self.subTest(sales=value), self.assertRaises(ValueError):
                self.prepare(frame)
        frame = self.frame.copy()
        frame.loc[0, "sell_price"] = float("nan")
        result = self.prepare(frame)
        self.assertEqual(int(result.sales.eq(0).sum()), 2)
        self.assertEqual(int(result.sell_price.isna().sum()), 1)

    def test_reject_partial_holdout_and_insufficient_history(self):
        with self.assertRaisesRegex(ValueError, "thiếu ngày"):
            self.prepare(self.frame.loc[self.frame.d.ne("d_18")])
        with self.assertRaisesRegex(ValueError, "đủ lịch sử"):
            replace(self.config, min_history_days=11).validate()
        with self.assertRaisesRegex(ValueError, "đúng horizon"):
            replace(self.config, validation_end_day=13).validate()

    def test_cli_missing_handoff_exits_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "splits"
            result = subprocess.run([
                sys.executable, "-X", "utf8", "src/models/split_data.py",
                "--input", str(Path(directory) / "missing.parquet"),
                "--output-dir", str(output),
            ], capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("thiếu đầu vào", result.stderr)
            self.assertFalse(output.exists())

    def test_cli_exports_splits_sales_free_inputs_mapping_and_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.frame.to_parquet(root / "source.parquet", index=False)
            self.calendar.to_csv(root / "calendar.csv", index=False)
            self.scope.to_csv(root / "scope.csv", index=False)
            config = {
                "data_version": "fixture-v1", "train_end_day": 10, "validation_end_day": 14,
                "test_end_day": 18, "horizon": 4, "min_history_days": 7,
            }
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            result = subprocess.run([
                sys.executable, "-X", "utf8", "src/models/split_data.py",
                "--input", str(root / "source.parquet"), "--calendar", str(root / "calendar.csv"),
                "--item-list", str(root / "scope.csv"), "--config", str(root / "config.json"),
                "--output-dir", str(root / "splits"), "--log", str(root / "log.json"),
                "--day-mapping", str(root / "mapping.csv"),
            ], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            log = json.loads((root / "log.json").read_text(encoding="utf-8"))
            self.assertTrue(log["test_available"])
            self.assertEqual(log["splits"]["test"]["history"]["end_d"], "d_14")
            self.assertEqual(len(pd.read_csv(root / "mapping.csv")), 18)
            for name in ("validation", "test"):
                self.assertNotIn("sales", pd.read_parquet(root / "splits" / f"{name}_future.parquet").columns)
            self.assertEqual(len(pd.read_parquet(root / "splits/train.parquet")), 20)


if __name__ == "__main__":
    unittest.main()
