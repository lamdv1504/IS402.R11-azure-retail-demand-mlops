import csv
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services import predictor


router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]
ITEMS_FILE = ROOT / "reports" / "m5_mvp_items.csv"
PARQUET_FILE = ROOT / "data" / "processed" / "m5_sales_processed.parquet"
CATEGORIES = ("FOODS", "HOBBIES", "HOUSEHOLD")


def error(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error_code": code, "detail": detail, "timestamp": datetime.now(timezone.utc).isoformat()},
    )


@lru_cache(maxsize=1)
def catalog() -> list[dict[str, str]]:
    with ITEMS_FILE.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


@lru_cache(maxsize=1)
def dashboard_data() -> dict:
    import pandas as pd

    frame = pd.read_parquet(PARQUET_FILE, columns=["date", "sales"])
    daily = frame.groupby("date", sort=True, observed=True)["sales"].sum()
    return {
        "store_id": "CA_1",
        "item_count": len(catalog()),
        "total_units_sold": int(daily.sum()),
        "average_units_per_day": round(float(daily.mean()), 2),
        "start_date": daily.index.min().date().isoformat(),
        "end_date": daily.index.max().date().isoformat(),
        "daily_sales": [{"date": day.date().isoformat(), "sales": int(sales)} for day, sales in daily.items()],
    }


@router.get("/health", tags=["System"])
def health():
    return {
        "status": "healthy",
        "service": "retail-demand-forecast-api",
        "version": "0.1.0",
        "model_loaded": predictor.model_loaded(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/items", tags=["Metadata"])
def items(category: str | None = Query(default=None)):
    if category is not None and category not in CATEGORIES:
        return error(400, "INVALID_CATEGORY", "Category phải là FOODS, HOBBIES hoặc HOUSEHOLD.")
    try:
        rows = catalog()
    except FileNotFoundError:
        return error(503, "CATALOG_NOT_READY", "Danh sách sản phẩm MVP chưa có trên máy chủ.")
    return {
        "store_id": "CA_1",
        "total_items": len(rows),
        "categories_breakdown": {name: sum(row["cat_id"] == name for row in rows) for name in CATEGORIES},
        "items": [
            {"item_id": row["item_id"], "dept_id": row["dept_id"], "cat_id": row["cat_id"]}
            for row in rows if category is None or row["cat_id"] == category
        ],
    }


@router.get("/dashboard", tags=["Data"])
def dashboard():
    try:
        return dashboard_data()
    except (FileNotFoundError, ImportError):
        return error(503, "DASHBOARD_NOT_READY", "Dữ liệu tổng quan chưa sẵn sàng.")


@router.get("/model-info", tags=["Model"])
def model_info():
    return error(503, "MODEL_NOT_READY", "Mô hình chưa được bàn giao hoặc chưa được nạp.")


@router.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict(request: PredictionRequest):
    try:
        rows = catalog()
    except FileNotFoundError:
        return error(503, "CATALOG_NOT_READY", "Danh sách sản phẩm MVP chưa có trên máy chủ.")
    if request.store_id != "CA_1" or not any(
        row["store_id"] == request.store_id and row["item_id"] == request.item_id for row in rows
    ):
        return error(404, "ITEM_NOT_FOUND", "Store hoặc item không thuộc phạm vi MVP.")
    try:
        return predictor.predict(store_id=request.store_id, item_id=request.item_id, horizon=request.horizon)
    except predictor.ModelNotReadyError as exc:
        return error(503, "MODEL_NOT_READY", str(exc))
