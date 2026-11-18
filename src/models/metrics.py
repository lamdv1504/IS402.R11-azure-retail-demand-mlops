"""HI05 metrics for the MVP bottom-level item/store series (not full M5 WRMSSE)."""

import numpy as np
import pandas as pd

from src.models.forecasting import FORECAST_KEYS, validate_window
from src.models.split_data import SERIES_KEYS


SCOPE_NOTE = (
    "CA_1 MVP 300 item-store series only. Subset RMSSE is the unweighted mean; "
    "Subset WRMSSE is revenue-weighted at the bottom level only, not the official "
    "12-level/full-competition M5 score. Scales exclude leading zero demand; "
    "weights use the last 28 observed days before each forecast origin."
)


def rmsse_scale(sales) -> float:
    values = np.asarray(sales, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("RMSSE history must be finite, nonnegative and one-dimensional.")
    active = np.flatnonzero(values)
    values = values[active[0]:] if len(active) else np.array([])
    scale = float(np.square(np.diff(values)).mean()) if len(values) > 1 else 0.0
    if scale <= 0:
        raise ValueError("Undefined RMSSE: no positive scale after removing leading zeros.")
    return scale


def score_forecast(history: pd.DataFrame, labels: pd.DataFrame,
                   forecasts: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Strictly align 28 target days; scales and revenue never read target labels."""
    origin = validate_window(history, labels.drop(columns="sales"), 28)
    if "sales" in forecasts or "predicted_sales" not in forecasts:
        raise ValueError("Forecasts need predicted_sales and must not contain sales labels.")
    joined = labels[FORECAST_KEYS + ["sales"]].merge(
        forecasts[FORECAST_KEYS + ["predicted_sales"]], on=FORECAST_KEYS,
        how="outer", validate="one_to_one", indicator=True,
    )
    if not joined["_merge"].eq("both").all():
        raise ValueError("Forecast keys must exactly match the 28-day label window.")
    values = joined[["sales", "predicted_sales"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Labels and forecasts must be finite and nonnegative.")
    recent = history.loc[history.day_number.gt(origin - 28)].copy()
    if recent.groupby(SERIES_KEYS, observed=True).size().ne(28).any():
        raise ValueError("Revenue weights require 28 observed days per series.")
    price = recent.sell_price.to_numpy(dtype=float)
    units = recent.sales.to_numpy(dtype=float)
    if ((units > 0) & (~np.isfinite(price) | (price <= 0))).any():
        raise ValueError("Missing/invalid price for positive sales in revenue weights.")
    recent["revenue"] = np.where(units > 0, units * price, 0.0)
    revenue = recent.groupby(SERIES_KEYS, observed=True).revenue.sum()
    if revenue.sum() <= 0:
        raise ValueError("Undefined revenue weights: total revenue must be positive.")
    scales = history.sort_values(SERIES_KEYS + ["day_number"]).groupby(
        SERIES_KEYS, observed=True).sales.agg(rmsse_scale).rename("scale")
    joined["squared_error"] = np.square(joined.sales - joined.predicted_sales)
    detail = joined.groupby(SERIES_KEYS, observed=True).squared_error.mean().rename("mse").to_frame()
    detail = detail.join(scales).join(revenue)
    detail["weight"] = detail.revenue / detail.revenue.sum()
    detail["rmsse"] = np.sqrt(detail.mse / detail.scale)
    error = joined.sales - joined.predicted_sales
    summary = {
        "subset_rmsse": float(detail.rmsse.mean()),
        "subset_wrmsse": float((detail.weight * detail.rmsse).sum()),
        "mae": float(error.abs().mean()), "rmse": float(np.sqrt(np.square(error).mean())),
        "series_count": len(detail), "forecast_rows": len(joined), "horizon": 28,
        "origin_day": origin, "scale_history_start_day": int(history.day_number.min()),
        "weight_start_day": origin - 27, "weight_end_day": origin,
    }
    return summary, detail.reset_index()


def select_model(validation_metrics: dict) -> str:
    """Predeclared rule: validation mean RMSSE; model name breaks an exact tie."""
    if not validation_metrics or any(
        not np.isfinite(m["subset_rmsse"]) or m["subset_rmsse"] < 0
        for m in validation_metrics.values()
    ):
        raise ValueError("Selection requires finite nonnegative validation RMSSE.")
    return min(validation_metrics, key=lambda name: (validation_metrics[name]["subset_rmsse"], name))
