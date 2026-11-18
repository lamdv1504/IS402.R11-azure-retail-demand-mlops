"""HI03: M5 features with fixed-origin validation and test inputs.

Run from the repository root: python src/features/feature_engineering.py
Future sales labels are never supplied to the feature builder.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.split_data import SERIES_KEYS, fingerprint, make_backtest_context


LAGS = (1, 7, 14, 28, 56)
ROLLING_WINDOWS = (7, 28)
CATEGORICAL_COLUMNS = ("item_id", "dept_id", "cat_id", "store_id", "state_id",
                       "weekday", "event_name_1", "event_type_1", "event_name_2", "event_type_2")
CALENDAR_COLUMNS = ("d", "date", "weekday", "wday", "month", "year",
                    "event_name_1", "event_type_1", "event_name_2", "event_type_2",
                    "snap_CA", "snap_TX", "snap_WI")
PRICE_KEYS = ["store_id", "item_id", "wm_yr_wk"]
MISSING_CATEGORY = "__MISSING__"


def check_frame(frame: pd.DataFrame, *, needs_sales: bool) -> None:
    required = set(SERIES_KEYS + ["day_number", "d", "date", "wm_yr_wk",
                                  "state_id", "sell_price", *CALENDAR_COLUMNS])
    if needs_sales:
        required.add("sales")
    missing = required - set(frame.columns)
    if missing or frame.empty:
        raise ValueError(f"Thiếu dữ liệu HI02/H02 hoặc tập rỗng: {sorted(missing)}")
    if frame[SERIES_KEYS + ["day_number", "date", "wm_yr_wk"]].isna().any().any():
        raise ValueError("Khóa chuỗi/ngày/tuần không được thiếu.")
    if frame.duplicated(SERIES_KEYS + ["day_number"]).any():
        raise ValueError("Có khóa item-store-day trùng.")
    if needs_sales and frame["sales"].isna().any():
        raise ValueError("Lịch sử train không được thiếu sales.")


def verify_calendar_join(frame: pd.DataFrame, calendar: pd.DataFrame) -> None:
    """Compare H02 calendar covariates against the original M5 calendar."""
    columns = list(CALENDAR_COLUMNS)
    if set(columns) - set(calendar.columns):
        raise ValueError("calendar.csv thiếu cột sự kiện hoặc SNAP.")
    observed = frame[columns].drop_duplicates().copy()
    if observed["d"].duplicated().any() or calendar["d"].duplicated().any():
        raise ValueError("Lịch H02/calendar có mã ngày trùng hoặc không nhất quán.")
    matched = observed.merge(calendar[columns], on="d", how="left", validate="one_to_one",
                             suffixes=("_h02", "_raw"), indicator=True)
    if not matched["_merge"].eq("both").all():
        raise ValueError("Ngày H02 không có trong calendar.csv.")
    for column in columns[1:]:
        left, right = matched[f"{column}_h02"], matched[f"{column}_raw"]
        if column == "date":
            equal = pd.to_datetime(left).eq(pd.to_datetime(right))
        else:
            equal = left.astype("string").fillna(MISSING_CATEGORY).eq(
                right.astype("string").fillna(MISSING_CATEGORY))
        if not equal.all():
            raise ValueError(f"Cột lịch {column} của H02 khác calendar.csv.")


def verify_price_join(frame: pd.DataFrame, price_path: Path) -> dict:
    """Check H02's weekly prices against the Hùng handoff without loading all M5 prices."""
    scope = frame[SERIES_KEYS].drop_duplicates()
    stores = set(scope["store_id"].astype(str))
    items = set(scope["item_id"].astype(str))
    pieces = []
    for chunk in pd.read_csv(price_path, chunksize=200_000):
        subset = chunk.loc[chunk.store_id.isin(stores) & chunk.item_id.isin(items)]
        if not subset.empty:
            pieces.append(subset)
    if not pieces:
        raise ValueError("Không tìm thấy giá gốc của phạm vi MVP.")
    raw = pd.concat(pieces, ignore_index=True)
    if raw.duplicated(PRICE_KEYS).any():
        raise ValueError("Bảng giá gốc có khóa tuần trùng.")
    observed = frame[PRICE_KEYS + ["sell_price"]].drop_duplicates()
    if observed.duplicated(PRICE_KEYS).any():
        raise ValueError("H02 có nhiều giá trong cùng item-store-week.")
    matched = observed.merge(raw, on=PRICE_KEYS, how="outer", validate="one_to_one",
                             suffixes=("_h02", "_raw"), indicator=True)
    matched = matched.loc[~matched["_merge"].eq("right_only")]
    left, right = matched["sell_price_h02"], matched["sell_price_raw"]
    equal = np.isclose(left, right, rtol=1e-6, atol=1e-6, equal_nan=True)
    if not equal.all():
        raise ValueError("Giá H02 không khớp sell_prices.csv theo item-store-week.")
    return {"source_price_rows": len(raw), "observed_weeks": len(observed),
            "missing_price_weeks": int(observed.sell_price.isna().sum())}


def price_features(all_rows: pd.DataFrame) -> pd.DataFrame:
    """A missing weekly price stays missing; prior price is the previous calendar week."""
    weekly = all_rows[PRICE_KEYS + ["day_number", "sell_price"]].copy()
    weekly = weekly.sort_values(SERIES_KEYS + ["day_number"]).drop_duplicates(PRICE_KEYS)
    weekly["price_lag_1_week"] = weekly.groupby(SERIES_KEYS, observed=True)["sell_price"].shift(1)
    previous = weekly["price_lag_1_week"]
    weekly["price_change_weekly"] = ((weekly["sell_price"] - previous) / previous).where(previous > 0)
    return weekly[PRICE_KEYS + ["price_lag_1_week", "price_change_weekly"]]


def build_features(history: pd.DataFrame, future: pd.DataFrame | None = None,
                   *, weekly_prices: pd.DataFrame | None = None,
                   category_vocab: dict[str, list[str]] | None = None) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Calculate lags/rolling per series from known sales only.

    With future supplied, returned rows are future only. Unknown future sales stay NaN:
    lag_1 after day 1, short rolling windows, etc. HI04 must either use a
    recursive forecast or select horizon-safe features for direct forecasting.
    """
    check_frame(history, needs_sales=True)
    if future is not None:
        check_frame(future, needs_sales=False)
        if "sales" in future.columns:
            raise ValueError("Future đầu vào không được chứa nhãn sales.")
        if int(history.day_number.max()) >= int(future.day_number.min()):
            raise ValueError("Cửa sổ future chồng lấn lịch sử.")
        work = pd.concat([history.assign(_future=False),
                          future.assign(sales=np.nan, _future=True)], ignore_index=True)
    else:
        work = history.assign(_future=False).copy()
    work = work.sort_values(SERIES_KEYS + ["day_number"], kind="stable").reset_index(drop=True)
    grouped = work.groupby(SERIES_KEYS, observed=True, sort=False)["sales"]
    for lag in LAGS:
        work[f"lag_{lag}"] = grouped.shift(lag).astype("float32")
    for window in ROLLING_WINDOWS:
        work[f"rolling_mean_{window}"] = grouped.transform(
            lambda sales: sales.shift(1).rolling(window, min_periods=window).mean()
        ).astype("float32")
    state = work["state_id"].astype("string")
    if state.isna().any() or not state.isin(["CA", "TX", "WI"]).all():
        raise ValueError("state_id không có cột SNAP tương ứng.")
    work["snap_state"] = np.select(
        [state.eq("CA"), state.eq("TX"), state.eq("WI")],
        [work.snap_CA, work.snap_TX, work.snap_WI], default=0,
    ).astype("int8")
    work["is_active"] = work.sell_price.notna().astype("int8")
    if weekly_prices is None:
        weekly_prices = price_features(work)
    work = work.merge(weekly_prices, on=PRICE_KEYS, how="left", validate="many_to_one")
    if work["price_lag_1_week"].notna().sum() == 0:
        raise ValueError("Không có đủ lịch sử giá theo tuần.")

    vocab = {} if category_vocab is None else category_vocab
    for column in CATEGORICAL_COLUMNS:
        values = work[column].astype("string").fillna(MISSING_CATEGORY)
        if category_vocab is None:
            vocab[column] = sorted(values.loc[~work["_future"]].unique().tolist())
        codes = values.map({value: index for index, value in enumerate(vocab[column])})
        work[f"{column}_code"] = codes.fillna(-1).astype("int16")
    result = work.loc[work["_future"] if future is not None else ~work["_future"]].drop(
        columns=["_future", "sales"] if future is not None else ["_future"]
    ).reset_index(drop=True)
    return result, vocab


def main() -> None:
    parser = argparse.ArgumentParser(description="HI03: tạo đặc trưng M5 không dùng nhãn future")
    parser.add_argument("--splits-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--split-log", type=Path, default=Path("reports/hi02_split_log.json"))
    parser.add_argument("--calendar", type=Path, default=Path("data/raw/calendar.csv"))
    parser.add_argument("--prices", type=Path, default=Path("data/raw/sell_prices.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/features"))
    parser.add_argument("--schema", type=Path, default=Path("reports/hi03_feature_schema.json"))
    parser.add_argument("--log", type=Path, default=Path("reports/hi03_feature_log.json"))
    args = parser.parse_args()
    paths = {name: args.splits_dir / f"{name}.parquet" for name in ("train", "validation", "test")}
    required = [paths["train"], paths["validation"], args.split_log, args.calendar, args.prices]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        parser.exit(1, "Dừng HI03: thiếu đầu vào H02/HI02: " + ", ".join(missing) + "\n")
    if not paths["test"].is_file() and (args.output_dir / "test_future_features.parquet").exists():
        parser.exit(1, "Dừng HI03: output còn test cũ; dùng --output-dir khác.\n")

    try:
        split_log = json.loads(args.split_log.read_text(encoding="utf-8-sig"))
        data_version = split_log["config"]["data_version"]
        if not isinstance(data_version, str) or not data_version:
            raise ValueError("Log HI02 thiếu phiên bản dữ liệu.")
        for name, path in paths.items():
            if path.is_file() and fingerprint(path)["sha256"] != split_log["splits"][name]["artifact"]["sha256"]:
                raise ValueError(f"{name}.parquet không khớp fingerprint bàn giao HI02.")
        if paths["test"].is_file() != split_log["test_available"]:
            raise ValueError("Trạng thái test không khớp log HI02.")
        splits = {name: pd.read_parquet(path) for name, path in paths.items() if path.is_file()}
        all_rows = pd.concat(splits.values(), ignore_index=True)
        check_frame(all_rows, needs_sales=True)
        verify_calendar_join(all_rows, pd.read_csv(args.calendar))
        price_check = verify_price_join(all_rows, args.prices)
        weekly = price_features(all_rows)
        train, vocab = build_features(splits["train"], weekly_prices=weekly)
        futures = {}
        for name in ("validation", "test"):
            if name in splits:
                context = make_backtest_context(splits, name)
                futures[name], _ = build_features(context.history, context.future,
                                                  weekly_prices=weekly, category_vocab=vocab)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Dừng HI03: {exc}\n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name, frame in {"train_features": train, **{f"{name}_future_features": frame
                                             for name, frame in futures.items()}}.items():
        path = args.output_dir / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        artifacts[name] = {"rows": len(frame), "series": frame[SERIES_KEYS].drop_duplicates().shape[0],
                           "lag_1_missing": int(frame.lag_1.isna().sum()),
                           "price_missing": int(frame.sell_price.isna().sum()),
                           "fingerprint": fingerprint(path)}
    feature_list = [f"lag_{lag}" for lag in LAGS] + [f"rolling_mean_{n}" for n in ROLLING_WINDOWS]
    feature_list += ["wday", "month", "year", "snap_state", "sell_price",
                     "price_lag_1_week", "price_change_weekly", "is_active"]
    feature_list += [f"{column}_code" for column in CATEGORICAL_COLUMNS]
    schema = {"task": "HI03", "feature_list": feature_list,
              "categorical_columns": list(CATEGORICAL_COLUMNS), "categorical_vocab": vocab,
              "unknown_category_code": -1, "missing_category": MISSING_CATEGORY,
              "missing_policy": "Lag/rolling/price chưa biết là NaN; event trống dùng __MISSING__; không điền sales hay giá bằng 0.",
              "forecast_policy": "Validation/test là fixed-origin; lag ngắn/rolling dùng sales trong future phải NaN cho đến khi HI04 dự báo đệ quy.",
              "pricing_assumption": "Giá future từ H02; HI04/Lâm phải xác nhận giá thực sự biết trước tại mốc triển khai."}
    args.schema.parent.mkdir(parents=True, exist_ok=True)
    args.schema.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log = {"task": "HI03", "data_version": data_version, "inputs": {
        **{name: fingerprint(path) for name, path in paths.items() if path.is_file()},
        "hi02_split_log": fingerprint(args.split_log),
        "calendar": fingerprint(args.calendar), "prices": fingerprint(args.prices)},
        "checks": {"calendar_join_matches": True, "price_join_matches": True,
                   "future_sales_excluded": all("sales" not in frame for frame in futures.values())},
        "price_join": price_check, "artifacts": artifacts, "schema": fingerprint(args.schema)}
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, entry in artifacts.items():
        print(f"{name}: {entry['rows']:,} dòng, {entry['series']} chuỗi; lag_1 trống {entry['lag_1_missing']:,}")
    print(f"Feature schema: {args.schema}; log: {args.log}")


if __name__ == "__main__":
    main()
