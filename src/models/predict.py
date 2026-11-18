"""HI05 reloadable predictor and CLI handoff for L03 (run from repository root)."""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.features.feature_engineering import CALENDAR_COLUMNS
from src.models.forecasting import FORECAST_KEYS, forecast_direct, seasonal_naive, validate_window
from src.models.split_data import SERIES_KEYS
from src.models.train import read_json, verify_artifact, write_json


def make_future(history: pd.DataFrame, calendar: pd.DataFrame, horizon: int = 28) -> pd.DataFrame:
    """Calendar-only future: no future labels or future prices are required."""
    if type(horizon) is not int or not 1 <= horizon <= 28:
        raise ValueError("Horizon must be an integer from 1 to 28.")
    if history.empty:
        raise ValueError("History is empty.")
    if "sales" in calendar:
        raise ValueError("Future calendar must not contain sales.")
    origin = int(history.day_number.max())
    required = list(dict.fromkeys([*CALENDAR_COLUMNS, "wm_yr_wk"]))
    calendar = calendar[required].copy()
    calendar["day_number"] = calendar.d.astype(str).str.removeprefix("d_").astype(int)
    calendar = calendar.loc[calendar.day_number.between(origin + 1, origin + horizon)]
    if len(calendar) != horizon or calendar.day_number.duplicated().any():
        raise ValueError("Future calendar must cover every requested day exactly once.")
    calendar["date"] = pd.to_datetime(calendar["date"])
    identity = SERIES_KEYS + ["dept_id", "cat_id", "state_id"]
    identities = history[identity].drop_duplicates()
    if identities.duplicated(SERIES_KEYS).any():
        raise ValueError("Series metadata must be consistent.")
    future = identities.merge(calendar, how="cross")
    future["sell_price"] = np.nan
    validate_window(history, future, horizon)
    return future.sort_values(SERIES_KEYS + ["day_number"]).reset_index(drop=True)


class ForecastPredictor:
    """Load once at API startup. History/future are explicit and never fetched remotely."""

    def __init__(self, bundle_dir: Path | str = "artifacts/hi05"):
        self.bundle_dir = Path(bundle_dir)
        self.metadata = read_json(self.bundle_dir / "model_metadata.json")
        for name, expected in self.metadata["files"].items():
            verify_artifact(self.bundle_dir / name, expected)
        self.order = read_json(self.bundle_dir / "feature_order.json")
        self.schema = read_json(self.bundle_dir / "feature_schema.json")
        self.algorithm = self.metadata["algorithm"]
        self.model = None
        if self.algorithm == "xgboost":
            from xgboost import XGBRegressor
            self.model = XGBRegressor(n_jobs=4, enable_categorical=True)
            self.model.load_model(self.bundle_dir / "best_model.ubj")
        elif self.algorithm != "seasonal_naive":
            raise ValueError("Unsupported algorithm in model metadata.")

    def forecast(self, history: pd.DataFrame, future: pd.DataFrame, horizon: int = 28) -> pd.DataFrame:
        scope = {tuple(row) for row in self.metadata["series"]}
        pairs = set(history[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None))
        if not pairs or not pairs.issubset(scope):
            raise KeyError("Item/store is outside the trained MVP scope.")
        minimum = self.metadata["minimum_history_days"]
        if history.groupby(SERIES_KEYS, observed=True).size().lt(minimum).any():
            raise ValueError(f"Each series needs at least {minimum} consecutive history days.")
        if self.algorithm == "xgboost":
            return forecast_direct(self.model, history, future, self.order, self.schema, horizon)
        result = future[FORECAST_KEYS].copy()
        result["predicted_sales"] = seasonal_naive(history, future, horizon)
        return result

    def predict(self, store_id: str, item_id: str, history: pd.DataFrame,
                calendar: pd.DataFrame, horizon: int = 28) -> dict:
        if type(horizon) is not int or not 1 <= horizon <= 28:
            raise ValueError("Horizon must be an integer from 1 to 28.")
        if [item_id, store_id] not in self.metadata["series"]:
            raise KeyError("Item/store is outside the trained MVP scope.")
        observed = history.loc[history.store_id.eq(store_id) & history.item_id.eq(item_id)].copy()
        future = make_future(observed, calendar, horizon)
        forecast = self.forecast(observed, future, horizon).sort_values("day_number")
        identity = observed.sort_values("day_number").iloc[-1]
        daily = [{"date": row.date.strftime("%Y-%m-%d"),
                  "day_of_week": row.date.day_name(), "predicted_sales": round(float(row.predicted_sales), 2)}
                 for row in forecast.itertuples(index=False)]
        return {
            "store_id": store_id, "item_id": item_id,
            **{name: str(identity[name]) for name in ["dept_id", "cat_id", "state_id"]},
            "model_version": self.metadata["model_version"], "data_version": self.metadata["data_version"],
            "forecast_start_date": daily[0]["date"], "horizon": horizon,
            "total_predicted_sales": round(sum(row["predicted_sales"] for row in daily), 2),
            "forecast": daily,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, default=Path("artifacts/hi05"))
    parser.add_argument("--store-id", default="CA_1")
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--horizon", type=int, default=28)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        predictor = ForecastPredictor(args.bundle_dir)
        response = predictor.predict(
            args.store_id, args.item_id,
            pd.read_parquet(args.bundle_dir / "inference_history.parquet"),
            pd.read_csv(args.bundle_dir / "future_calendar.csv"), args.horizon,
        )
        if args.output:
            write_json(args.output, response)
        else:
            import json
            print(json.dumps(response, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, FileNotFoundError) as exc:
        parser.exit(1, f"HI05 inference stopped: {exc}\n")


if __name__ == "__main__":
    main()
