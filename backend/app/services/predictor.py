"""L03 adapter for the verified HI05 bundle. No fitting or holdout scoring here."""

import csv
import logging
from pathlib import Path
import sys

from app.schemas.model import ModelInfoResponse
from app.schemas.prediction import PredictionResponse


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUNDLE = ROOT / "artifacts" / "hi05"
logger = logging.getLogger(__name__)

# Support `uvicorn app.main:app` from backend/ as well as --app-dir from the root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ModelNotReadyError(RuntimeError):
    pass


class ForecastDataError(RuntimeError):
    pass


class ItemNotFoundError(LookupError):
    pass


class InferenceError(RuntimeError):
    pass


class ForecastService:
    def __init__(self, engine, history, calendar, info: ModelInfoResponse):
        self.engine = engine
        self.history = history
        self.calendar = calendar
        self.info = info
        self.scope = frozenset(tuple(pair) for pair in engine.metadata["series"])

    def predict(self, *, store_id: str, item_id: str, horizon: int) -> PredictionResponse:
        if (item_id, store_id) not in self.scope:
            raise ItemNotFoundError("Store hoặc item không thuộc phạm vi model.")
        try:
            response = self.engine.predict(store_id, item_id, self.history, self.calendar, horizon)
            return PredictionResponse.model_validate(response)
        except (ValueError, KeyError) as exc:
            raise ForecastDataError("Lịch sử, lịch tương lai hoặc dữ liệu dự báo không hợp lệ.") from exc
        except Exception as exc:
            logger.exception("Inference failed for %s/%s", store_id, item_id)
            raise InferenceError("Không thể tạo dự báo. Vui lòng thử lại sau.") from exc


def load_service(bundle_dir: Path, catalog_path: Path) -> ForecastService:
    """Verify checksum, versions, scope and serving context before reporting ready."""
    import pandas as pd
    from src.models.predict import ForecastPredictor, make_future
    from src.models.split_data import SERIES_KEYS
    from src.models.train import read_json

    engine = ForecastPredictor(bundle_dir)
    required_manifest_entries = {"inference_history.parquet", "future_calendar.csv", "metrics.json"}
    if not required_manifest_entries.issubset(engine.metadata["files"]):
        raise ValueError("Gói HI05 thiếu checksum cho dữ liệu inference/metric.")
    history = pd.read_parquet(bundle_dir / "inference_history.parquet")
    calendar = pd.read_csv(bundle_dir / "future_calendar.csv")
    info = ModelInfoResponse.model_validate(read_json(bundle_dir / "model_info.json"))
    if (info.model_version != engine.metadata["model_version"]
            or info.data_version != engine.metadata["data_version"]
            or info.algorithm != engine.algorithm or info.status != "ready"
            or info.forecast_horizon != 28):
        raise ValueError("Model-info không khớp phiên bản model HI05.")
    metrics = read_json(bundle_dir / "metrics.json")["validation"][engine.algorithm]
    for name in ["subset_rmsse", "subset_wrmsse", "mae", "rmse"]:
        if getattr(info.metrics, "validation_" + name) != metrics[name]:
            raise ValueError("Model-info không khớp metric đã đánh giá trong HI05.")
    with catalog_path.open(encoding="utf-8-sig", newline="") as source:
        catalog = list(csv.DictReader(source))
    expected = {tuple(pair) for pair in engine.metadata["series"]}
    actual = set(history[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None))
    catalog_pairs = {(row["item_id"], row["store_id"]) for row in catalog}
    if (len(catalog_pairs) != len(catalog) or actual != expected or catalog_pairs != expected
            or info.item_count != len(expected)
            or set(info.store_scope) != {store for _, store in expected}):
        raise ValueError("Phạm vi catalog/history không khớp model HI05.")
    if history.groupby(SERIES_KEYS, observed=True).size().lt(engine.metadata["minimum_history_days"]).any():
        raise ValueError("Gói HI05 không đủ ngày lịch sử cho inference.")
    if info.features_used != engine.order and engine.algorithm == "xgboost":
        raise ValueError("Feature order không khớp model-info.")
    # This validates observed labels, key/date continuity and a sales-free future.
    make_future(history, calendar, 28)
    return ForecastService(engine, history, calendar, info)
