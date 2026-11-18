"""HI03 checks that future labels cannot enter fixed-origin features."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from src.features.feature_engineering import (
    CALENDAR_COLUMNS, build_features, price_features,
    verify_calendar_join, verify_price_join,
)


class FeatureEngineeringTests(unittest.TestCase):
    def setUp(self):
        rows = []
        for item, scale in (("ITEM_A", 1), ("ITEM_B", 2)):
            for day in range(1, 69):
                week = (day - 1) // 7
                date = pd.Timestamp("2011-01-29") + pd.Timedelta(days=day - 1)
                rows.append({
                    "item_id": item, "dept_id": "FOODS_1", "cat_id": "FOODS",
                    "store_id": "CA_1", "state_id": "CA", "d": f"d_{day}",
                    "day_number": day, "date": date, "wm_yr_wk": 11101 + week,
                    "weekday": date.day_name(), "wday": day % 7 + 1,
                    "month": date.month, "year": date.year,
                    "event_name_1": None, "event_type_1": None,
                    "event_name_2": None, "event_type_2": None,
                    "snap_CA": day % 2, "snap_TX": 0, "snap_WI": 0,
                    "sell_price": float("nan") if week == 0 else (2.0 if week == 1 else 3.0),
                    "sales": day * scale,
                })
        self.all_rows = pd.DataFrame(rows)
        self.history = self.all_rows.loc[self.all_rows.day_number.le(60)].copy()
        self.future = self.all_rows.loc[self.all_rows.day_number.gt(60)].drop(columns="sales").copy()
        self.weekly = price_features(self.all_rows)

    def row(self, frame, item, day):
        return frame.loc[frame.item_id.eq(item) & frame.day_number.eq(day)].iloc[0]

    def test_lag_and_rolling_use_only_earlier_sales_of_same_series(self):
        frame, vocab = build_features(self.history, weekly_prices=self.weekly)
        a = self.row(frame, "ITEM_A", 29)
        b = self.row(frame, "ITEM_B", 29)
        self.assertEqual((a.lag_1, a.lag_7, a.lag_14, a.lag_28), (28, 22, 15, 1))
        self.assertEqual(a.rolling_mean_7, 25)
        self.assertEqual(a.rolling_mean_28, 14.5)
        self.assertEqual(b.lag_1, 56)
        self.assertEqual(b.rolling_mean_7, 50)
        self.assertTrue(pd.isna(self.row(frame, "ITEM_A", 1).lag_1))
        self.assertIn("__MISSING__", vocab["event_name_1"])

    def test_future_features_exclude_sales_and_do_not_invent_short_lags(self):
        _, vocab = build_features(self.history, weekly_prices=self.weekly)
        result, _ = build_features(self.history, self.future,
                                   weekly_prices=self.weekly, category_vocab=vocab)
        self.assertNotIn("sales", result.columns)
        self.assertEqual(self.row(result, "ITEM_A", 61).lag_1, 60)
        self.assertTrue(pd.isna(self.row(result, "ITEM_A", 62).lag_1))
        self.assertEqual(self.row(result, "ITEM_A", 67).lag_7, 60)
        self.assertTrue(pd.isna(self.row(result, "ITEM_A", 68).lag_7))
        self.assertEqual(self.row(result, "ITEM_A", 68).lag_28, 40)
        self.assertEqual(self.row(result, "ITEM_A", 61).rolling_mean_7, 57)
        self.assertTrue(pd.isna(self.row(result, "ITEM_A", 62).rolling_mean_7))
        altered = self.all_rows.loc[self.all_rows.day_number.gt(60)].copy()
        altered["sales"] = 999999
        repeated, _ = build_features(self.history, altered.drop(columns="sales"),
                                     weekly_prices=self.weekly, category_vocab=vocab)
        assert_frame_equal(result, repeated)
        with self.assertRaisesRegex(ValueError, "không được chứa"):
            build_features(self.history, altered, weekly_prices=self.weekly, category_vocab=vocab)

    def test_price_missing_before_launch_and_weekly_change(self):
        frame, _ = build_features(self.history, weekly_prices=self.weekly)
        before = self.row(frame, "ITEM_A", 1)
        launch = self.row(frame, "ITEM_A", 8)
        changed = self.row(frame, "ITEM_A", 15)
        self.assertEqual(before.is_active, 0)
        self.assertTrue(pd.isna(before.sell_price))
        self.assertEqual(launch.is_active, 1)
        self.assertTrue(pd.isna(launch.price_change_weekly))
        self.assertEqual(changed.price_lag_1_week, 2)
        self.assertEqual(changed.price_change_weekly, 0.5)
        self.assertEqual(changed.snap_state, changed.snap_CA)

    def test_calendar_and_price_joins_are_checked_against_raw_sources(self):
        calendar = self.all_rows[list(CALENDAR_COLUMNS)].drop_duplicates().copy()
        verify_calendar_join(self.all_rows, calendar)
        broken_calendar = calendar.copy()
        broken_calendar.loc[0, "snap_CA"] = 9
        with self.assertRaisesRegex(ValueError, "snap_CA"):
            verify_calendar_join(self.all_rows, broken_calendar)
        prices = self.all_rows[["store_id", "item_id", "wm_yr_wk", "sell_price"]].drop_duplicates()
        prices = prices.loc[prices.sell_price.notna()]
        with tempfile.TemporaryDirectory() as directory:
            price_file = Path(directory) / "sell_prices.csv"
            prices.to_csv(price_file, index=False)
            self.assertEqual(verify_price_join(self.all_rows, price_file)["source_price_rows"], 18)
            prices.loc[prices.index[0], "sell_price"] = 99
            prices.to_csv(price_file, index=False)
            with self.assertRaisesRegex(ValueError, "không khớp"):
                verify_price_join(self.all_rows, price_file)

    def test_unseen_calendar_category_maps_to_unknown_code(self):
        _, vocab = build_features(self.history, weekly_prices=self.weekly)
        future = self.future.copy()
        future.loc[future.day_number.eq(61), "event_name_1"] = "NEW_EVENT"
        result, _ = build_features(self.history, future,
                                   weekly_prices=self.weekly, category_vocab=vocab)
        self.assertEqual(self.row(result, "ITEM_A", 61).event_name_1_code, -1)


if __name__ == "__main__":
    unittest.main()
