"""Khảo sát dữ liệu M5 gốc và xuất danh sách sản phẩm MVP có thể tạo lại.

Chạy từ thư mục gốc của repo: python src/data/profile_m5.py
"""

from pathlib import Path
import sys

import pandas as pd


RAW = Path("data/raw")
OUTPUT = Path("reports/Hung/m5_mvp_items.csv")
STORE = "CA_1"
ITEMS_PER_CATEGORY = 100
SEED = 42
SALES_ID_COLUMNS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
FILES = [
    "sales_train_validation.csv",
    "sales_train_evaluation.csv",
    "calendar.csv",
    "sell_prices.csv",
    "sample_submission.csv",
]


def csv_rows(path: Path) -> int:
    """Đếm số dòng trong CSV M5 mà không nạp toàn bộ file vào bộ nhớ."""
    with path.open("rb") as stream:
        return sum(block.count(b"\n") for block in iter(lambda: stream.read(1024 * 1024), b"")) - 1


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for name in FILES:
        path = RAW / name
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu file M5: {path}")
        header = pd.read_csv(path, nrows=0).columns
        print(f"{name}: {csv_rows(path):,} dòng, {len(header):,} cột, "
              f"{path.stat().st_size / 1024**2:.2f} MiB")

    validation_header = pd.read_csv(RAW / FILES[0], nrows=0).columns
    evaluation_header = pd.read_csv(RAW / FILES[1], nrows=0).columns
    assert validation_header[-1] == "d_1913"
    assert evaluation_header[-1] == "d_1941"

    metadata = pd.read_csv(RAW / FILES[1], usecols=SALES_ID_COLUMNS)
    assert metadata.id.is_unique
    print(f"Doanh số: {len(metadata):,} chuỗi, {metadata.item_id.nunique():,} sản phẩm, "
          f"{metadata.store_id.nunique()} cửa hàng, {metadata.state_id.nunique()} bang")
    print("Số chuỗi theo cửa hàng:", metadata.store_id.value_counts().sort_index().to_dict())
    print("Giá trị thiếu ở các cột định danh:", metadata.isna().sum().to_dict())

    calendar = pd.read_csv(RAW / "calendar.csv")
    assert calendar.d.is_unique
    print(f"Lịch: từ {calendar.date.min()} đến {calendar.date.max()}")
    print("Giá trị thiếu ở các cột lịch:", calendar.isna().sum().to_dict())

    price_rows = 0
    missing_price_cells = 0
    for chunk in pd.read_csv(RAW / "sell_prices.csv", chunksize=200_000):
        price_rows += len(chunk)
        missing_price_cells += int(chunk.isna().sum().sum())
    print(f"Bảng giá: {price_rows:,} dòng, {missing_price_cells:,} ô trống")

    store_rows = metadata.loc[metadata.store_id.eq(STORE)]
    selected = pd.concat(
        [group.sample(n=min(ITEMS_PER_CATEGORY, len(group)), random_state=SEED)
         for _, group in store_rows.groupby("cat_id", sort=True)],
        ignore_index=True,
    )[["store_id", "item_id", "dept_id", "cat_id", "state_id"]]
    selected = selected.sort_values(["cat_id", "item_id"]).reset_index(drop=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(OUTPUT, index=False)
    print(f"MVP: {STORE}, {len(selected)} sản phẩm; danh sách đã lưu tại {OUTPUT}")
    print("Số sản phẩm MVP theo nhóm:", selected.cat_id.value_counts().sort_index().to_dict())

    item_ids = set(selected.item_id)
    subset_parts = []
    for chunk in pd.read_csv(RAW / FILES[1], chunksize=1000):
        subset = chunk.loc[chunk.store_id.eq(STORE) & chunk.item_id.isin(item_ids)]
        if not subset.empty:
            subset_parts.append(subset)
    subset = pd.concat(subset_parts, ignore_index=True)
    day_columns = [column for column in subset if column.startswith("d_")]
    sales = subset[day_columns]
    print(f"Chuỗi MVP: {len(subset)}; số ngày: {len(day_columns)}; "
          f"ô doanh số thiếu: {int(sales.isna().sum().sum()):,}; "
          f"ô doanh số bằng 0: {int((sales == 0).sum().sum()):,} "
          f"({(sales == 0).sum().sum() / sales.size:.2%}); "
          f"tổng số lượng bán: {int(sales.sum().sum()):,}")


if __name__ == "__main__":
    main()
