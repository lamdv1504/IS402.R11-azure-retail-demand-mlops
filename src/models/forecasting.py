"""HI04 shared fixed-origin forecast rules for validation and later inference."""

import numpy as np
import pandas as pd

from src.models.split_data import SERIES_KEYS


FORECAST_KEYS = SERIES_KEYS + ["d", "date", "day_number"]
SAFE_NUMERIC_FEATURES = {"lag_28", "lag_56", "wday", "month", "year", "snap_state"}


def validate_window(history: pd.DataFrame, future: pd.DataFrame, horizon: int = 28) -> int:
    """Reject incomplete series, gaps, target-bearing future rows and overlapping dates."""
    if type(horizon) is not int or not 1 <= horizon <= 28:
        raise ValueError("Horizon phải từ 1 đến 28 ngày.")
    if "sales" in future:
        raise ValueError("Đầu vào future không được chứa nhãn sales.")
    for name, frame, required in [("history", history, FORECAST_KEYS + ["sales"]),
                                   ("future", future, FORECAST_KEYS)]:
        if frame.empty or not set(required).issubset(frame.columns):
            raise ValueError(f"{name} rỗng hoặc thiếu cột bắt buộc.")
        if frame[required].isna().any().any() or frame.duplicated(SERIES_KEYS + ["day_number"]).any():
            raise ValueError(f"{name} có khóa/ngày/nhãn thiếu hoặc trùng.")
        if not frame["d"].astype(str).eq("d_" + frame.day_number.astype(str)).all():
            raise ValueError("Mã d không khớp day_number.")
    if not np.isfinite(history.sales.to_numpy(dtype=float)).all() or (history.sales < 0).any():
        raise ValueError("Sales lịch sử phải hữu hạn và không âm.")
    history_pairs = set(history[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None))
    future_pairs = set(future[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None))
    if history_pairs != future_pairs:
        raise ValueError("History và future phải có cùng các chuỗi item-store.")
    origin = int(history.day_number.max())
    stats = history.groupby(SERIES_KEYS, observed=True).day_number.agg(["min", "max", "count"])
    if not stats["max"].eq(origin).all() or not stats["count"].eq(stats["max"] - stats["min"] + 1).all():
        raise ValueError("Lịch sử thiếu ngày hoặc các chuỗi không cùng mốc dự báo.")
    for _, rows in future.groupby(SERIES_KEYS, observed=True):
        if sorted(rows.day_number.tolist()) != list(range(origin + 1, origin + horizon + 1)):
            raise ValueError("Mỗi chuỗi future phải đủ horizon ngày liên tiếp sau origin.")
    mapping = pd.concat([history[FORECAST_KEYS], future[FORECAST_KEYS]])[["day_number", "date"]].drop_duplicates()
    mapping["date"] = pd.to_datetime(mapping["date"])
    if mapping.day_number.duplicated().any():
        raise ValueError("Mapping ngày không nhất quán giữa các chuỗi.")
    first = mapping.sort_values("day_number").iloc[0]
    expected = first["date"] + pd.to_timedelta(mapping.day_number - first.day_number, unit="D")
    if not mapping["date"].eq(expected).all():
        raise ValueError("Ngày lịch không liên tục với day_number.")
    return origin


def seasonal_naive(history: pd.DataFrame, future: pd.DataFrame, horizon: int = 28) -> np.ndarray:
    """Repeat the final observed week for all 28 days; never read future actual sales."""
    origin = validate_window(history, future, horizon)
    sources = history.loc[history.day_number.between(origin - 6, origin),
                          SERIES_KEYS + ["day_number", "sales"]].rename(columns={"day_number": "_source_day"})
    targets = future[SERIES_KEYS].copy()
    targets["_source_day"] = origin - 6 + ((future.day_number - origin - 1) % 7)
    matched = targets.merge(sources, on=SERIES_KEYS + ["_source_day"], how="left", validate="many_to_one")
    if matched.sales.isna().any():
        raise ValueError("Baseline seasonal naive cần đủ 7 ngày lịch sử cho từng chuỗi.")
    return matched.sales.to_numpy(dtype=float)


def validate_feature_order(feature_order: list[str], schema: dict) -> None:
    if not feature_order or len(set(feature_order)) != len(feature_order):
        raise ValueError("Feature order rỗng hoặc có cột trùng.")
    categorical = {f"{name}_code" for name in schema["categorical_columns"]}
    allowed = SAFE_NUMERIC_FEATURES | categorical
    if set(feature_order) - allowed or not {"lag_28", "lag_56"}.issubset(feature_order):
        raise ValueError("Direct horizon chỉ dùng lag_28/56, lịch và mã phân loại; không dùng lag ngắn/giá future.")
    if not set(feature_order).issubset(schema["feature_list"]):
        raise ValueError("Feature order không thuộc schema HI03.")


def model_matrix(frame: pd.DataFrame, feature_order: list[str], schema: dict) -> pd.DataFrame:
    """Use HI03's fixed vocabulary as native XGBoost categories; -1 becomes missing."""
    validate_feature_order(feature_order, schema)
    if not set(feature_order).issubset(frame.columns):
        raise ValueError("Dữ liệu thiếu cột trong feature order.")
    matrix = frame[feature_order].copy()
    categorical = {f"{name}_code": name for name in schema["categorical_columns"]}
    for name in feature_order:
        values = pd.to_numeric(matrix[name], errors="raise")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"Feature {name} thiếu/không hữu hạn; cần đủ 56 ngày lịch sử.")
        if name in categorical:
            size = len(schema["categorical_vocab"][categorical[name]])
            if not values.eq(values.round()).all() or not values.between(-1, size - 1).all():
                raise ValueError(f"Mã phân loại {name} không khớp từ vựng HI03.")
            matrix[name] = pd.Categorical.from_codes(values.astype(int), categories=range(size))
        else:
            matrix[name] = values.astype("float32")
    return matrix


def predict_direct(model, future_features: pd.DataFrame, feature_order: list[str], schema: dict) -> np.ndarray:
    """Use this same prediction path in validation and HI05 inference."""
    if "sales" in future_features:
        raise ValueError("Đầu vào future không được chứa nhãn sales.")
    predictions = np.asarray(model.predict(model_matrix(future_features, feature_order, schema)), dtype=float)
    if predictions.shape != (len(future_features),) or not np.isfinite(predictions).all():
        raise ValueError("Model trả sai kích thước hoặc dự báo không hữu hạn.")
    return np.maximum(predictions, 0.0)


def forecast_direct(model, history: pd.DataFrame, future: pd.DataFrame,
                    feature_order: list[str], schema: dict, horizon: int = 28) -> pd.DataFrame:
    """Build HI03 features from observed history and reuse validation's direct predictor.

    Future sell_price may be missing: selected features never use price or short rolling.
    Model fitting and selection remain separate from this function.
    """
    from src.features.feature_engineering import build_features

    validate_window(history, future, horizon)
    features, _ = build_features(history, future, category_vocab=schema["categorical_vocab"])
    output = features[FORECAST_KEYS].copy()
    output["predicted_sales"] = predict_direct(model, features, feature_order, schema)
    return output
