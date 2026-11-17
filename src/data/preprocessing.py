"""Chuyển M5 sales sang dạng từng ngày, ghép lịch/giá và lưu Parquet.

Chạy từ thư mục gốc repo: python src/data/preprocessing.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd


ID_COLUMNS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
PRICE_KEYS = ["store_id", "item_id", "wm_yr_wk"]
DAY_PATTERN = re.compile(r"d_(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tiền xử lý dữ liệu M5 cho H02")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--item-list", type=Path, default=Path("reports/m5_mvp_items.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/m5_sales_processed.parquet"))
    parser.add_argument("--log", type=Path, default=Path("reports/h02_processing_log.json"))
    return parser.parse_args()


def read_scope(path: Path) -> tuple[str, set[str]]:
    scope = pd.read_csv(path)
    required = {"store_id", "item_id", "dept_id", "cat_id", "state_id"}
    if not required.issubset(scope.columns) or scope[list(required)].isna().any().any():
        raise ValueError("Danh sách MVP thiếu cột bắt buộc hoặc có giá trị trống")
    if scope[["store_id", "item_id"]].duplicated().any():
        raise ValueError("Danh sách MVP có cặp store_id–item_id trùng")
    stores = scope.store_id.unique()
    if len(stores) != 1:
        raise ValueError("H02 hiện chỉ xử lý một cửa hàng đã thống nhất")
    return str(stores[0]), set(scope.item_id)


def read_selected_sales(path: Path, store: str, items: set[str]) -> pd.DataFrame:
    parts = []
    for chunk in pd.read_csv(path, chunksize=1000):
        rows = chunk.loc[chunk.store_id.eq(store) & chunk.item_id.isin(items)]
        if not rows.empty:
            parts.append(rows)
    if not parts:
        raise ValueError("Không tìm thấy chuỗi sales nào trong phạm vi MVP")
    selected = pd.concat(parts, ignore_index=True)
    if selected[["store_id", "item_id"]].duplicated().any():
        raise ValueError("Nguồn sales có chuỗi sản phẩm–cửa hàng trùng")
    if set(selected.item_id) != items:
        missing = sorted(items - set(selected.item_id))
        raise ValueError(f"Thiếu {len(missing)} sản phẩm MVP trong sales: {missing[:5]}")
    return selected


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    store, items = read_scope(args.item_list)
    source = args.raw_dir / "sales_train_evaluation.csv"
    wide = read_selected_sales(source, store, items)
    day_columns = [column for column in wide if DAY_PATTERN.fullmatch(column)]
    day_numbers = sorted(int(DAY_PATTERN.fullmatch(column).group(1)) for column in day_columns)
    if day_numbers != list(range(1, 1942)):
        raise ValueError("Sales evaluation phải có đủ d_1 đến d_1941")
    if wide[ID_COLUMNS].isna().any().any():
        raise ValueError("Có giá trị thiếu trong các cột định danh sales")
    print(f"Đã chọn {len(wide)} chuỗi của cửa hàng {store}; bắt đầu chuyển dạng dữ liệu")

    long = wide.melt(id_vars=ID_COLUMNS, value_vars=day_columns,
                     var_name="d", value_name="sales")
    rows_after_melt = len(long)
    if long.sales.isna().any() or (long.sales < 0).any():
        raise ValueError("Sales có giá trị thiếu hoặc âm")

    calendar = pd.read_csv(args.raw_dir / "calendar.csv")
    if calendar.d.isna().any() or calendar.d.duplicated().any():
        raise ValueError("Khóa d của calendar thiếu hoặc trùng")
    long = long.merge(calendar, on="d", how="left", validate="many_to_one")
    if len(long) != rows_after_melt or long[["date", "wm_yr_wk"]].isna().any().any():
        raise ValueError("Ghép calendar làm thay đổi số dòng hoặc thiếu ngày/tuần")
    long["date"] = pd.to_datetime(long["date"], errors="raise")

    price_parts = []
    for chunk in pd.read_csv(args.raw_dir / "sell_prices.csv", chunksize=200_000):
        rows = chunk.loc[chunk.store_id.eq(store) & chunk.item_id.isin(items)]
        if not rows.empty:
            price_parts.append(rows)
    if not price_parts:
        raise ValueError("Không tìm thấy giá cho phạm vi MVP")
    prices = pd.concat(price_parts, ignore_index=True)
    if prices[PRICE_KEYS].isna().any().any() or prices[PRICE_KEYS].duplicated().any():
        raise ValueError("Khóa store_id–item_id–wm_yr_wk của bảng giá thiếu hoặc trùng")
    before_price_join = len(long)
    long = long.merge(prices, on=PRICE_KEYS, how="left", validate="many_to_one")
    if len(long) != before_price_join:
        raise ValueError("Ghép giá làm thay đổi số dòng")

    duplicate_keys = int(long[["item_id", "store_id", "d"]].duplicated().sum())
    if duplicate_keys:
        raise ValueError(f"Có {duplicate_keys} khóa item_id–store_id–d trùng")
    long["sales"] = pd.to_numeric(long.sales, downcast="integer")
    for column in ["wm_yr_wk", "wday", "month", "year", "snap_CA", "snap_TX", "snap_WI"]:
        long[column] = pd.to_numeric(long[column], downcast="integer")
    long["sell_price"] = pd.to_numeric(long.sell_price, downcast="float")
    for column in ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id",
                   "weekday", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]:
        long[column] = long[column].astype("category")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    long.to_parquet(args.output, engine="pyarrow", index=False)
    missing = {column: int(count) for column, count in long.isna().sum().items()}
    log = {
        "source": str(source), "scope_file": str(args.item_list), "store_id": store,
        "item_count": len(items), "series_count": len(wide), "day_count": len(day_columns),
        "rows_after_melt": rows_after_melt, "rows_after_calendar_join": before_price_join,
        "rows_after_price_join": len(long), "duplicate_item_store_day": duplicate_keys,
        "zero_sales_rows": int((long.sales == 0).sum()),
        "missing_values": missing, "price_rows_selected": len(prices),
        "source_size_bytes": source.stat().st_size,
        "parquet_size_bytes": args.output.stat().st_size,
        "output": str(args.output),
        "schema": {column: str(dtype) for column, dtype in long.dtypes.items()},
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã lưu {len(long):,} dòng vào {args.output}")
    print(f"Số dòng thiếu giá: {missing['sell_price']:,}; log: {args.log}")


if __name__ == "__main__":
    main()
