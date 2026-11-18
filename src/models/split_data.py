"""HI02: split H02 data chronologically and prepare inputs for fixed-origin backtests.

Run from the repository root: python src/models/split_data.py
Validation/test sales are labels, never inputs for their own forecast window.
"""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd


SERIES_KEYS = ["item_id", "store_id"]
LABEL_COLUMNS = SERIES_KEYS + ["d", "date", "day_number", "sales"]


@dataclass(frozen=True)
class SplitConfig:
    data_version: str
    train_end_day: int
    validation_end_day: int
    test_end_day: int
    horizon: int
    min_history_days: int

    def validate(self) -> None:
        numbers = [self.train_end_day, self.validation_end_day, self.test_end_day,
                   self.horizon, self.min_history_days]
        if any(type(number) is not int or number <= 0 for number in numbers):
            raise ValueError("Các mốc ngày, horizon và min_history_days phải là số nguyên dương.")
        if not isinstance(self.data_version, str) or not self.data_version.strip():
            raise ValueError("Cần data_version từ bàn giao H02/HI01.")
        if self.validation_end_day - self.train_end_day != self.horizon:
            raise ValueError("Cửa sổ validation phải dài đúng horizon.")
        if self.test_end_day - self.validation_end_day != self.horizon:
            raise ValueError("Cửa sổ test phải dài đúng horizon.")
        if self.train_end_day < self.min_history_days:
            raise ValueError("Train không đủ lịch sử cho lag/rolling đã cấu hình.")


@dataclass(frozen=True)
class BacktestContext:
    history: pd.DataFrame
    future: pd.DataFrame
    labels: pd.DataFrame


def prepare_data(frame: pd.DataFrame, calendar: pd.DataFrame,
                 scope: pd.DataFrame, config: SplitConfig) -> pd.DataFrame:
    """Check H02 keys, calendar, labels, MVP scope and complete daily histories."""
    config.validate()
    required = set(SERIES_KEYS + ["d", "date", "sales"])
    if not required.issubset(frame.columns):
        raise ValueError(f"Parquet thiếu cột bắt buộc: {sorted(required - set(frame.columns))}")
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Parquet rỗng hoặc có khóa/ngày/sales bị thiếu.")
    data = frame.copy()
    day_text = data["d"].astype("string")
    if not day_text.str.fullmatch(r"d_[1-9]\d*").all():
        raise ValueError("Mã ngày phải có dạng d_1, d_2, ...")
    data["day_number"] = day_text.str.slice(2).astype("int32")
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    if data["date"].dt.tz is not None or not data["date"].eq(data["date"].dt.normalize()).all():
        raise ValueError("date phải là ngày không có múi giờ hoặc phần giờ.")
    sales = pd.to_numeric(data["sales"], errors="raise")
    if (sales < 0).any() or sales.isin([float("inf"), -float("inf")]).any() or sales.isna().any():
        raise ValueError("sales phải hữu hạn, không thiếu và không âm.")
    if not sales.eq(sales.round()).all():
        raise ValueError("Nhãn sales của H02 phải là số lượng sản phẩm nguyên.")
    data["sales"] = sales
    if data.duplicated(SERIES_KEYS + ["d"]).any():
        raise ValueError("Có khóa item_id-store_id-d trùng.")

    if not {"d", "date"}.issubset(calendar.columns):
        raise ValueError("calendar.csv thiếu d/date.")
    reference = calendar[["d", "date"]].copy()
    if reference.isna().any().any() or reference["d"].duplicated().any():
        raise ValueError("calendar.csv có d/date thiếu hoặc d trùng.")
    reference["date"] = pd.to_datetime(reference["date"], errors="raise")
    mapping = data[["d", "date", "day_number"]].drop_duplicates()
    if mapping["d"].duplicated().any() or mapping["date"].duplicated().any():
        raise ValueError("Mapping d/date không một-một.")
    matched = mapping.merge(reference, on="d", how="left", suffixes=("", "_calendar"),
                            validate="one_to_one")
    expected_dates = pd.Timestamp("2011-01-29") + pd.to_timedelta(matched["day_number"] - 1, unit="D")
    if not matched["date"].eq(matched["date_calendar"]).all() or not matched["date"].eq(expected_dates).all():
        raise ValueError("Mapping d/date không khớp calendar M5 (d_1 = 2011-01-29).")

    if not set(SERIES_KEYS).issubset(scope.columns) or scope[SERIES_KEYS].isna().any().any():
        raise ValueError("Danh sách MVP thiếu item_id/store_id.")
    if scope.duplicated(SERIES_KEYS).any():
        raise ValueError("Danh sách MVP có chuỗi trùng.")
    expected_series = set(scope[SERIES_KEYS].itertuples(index=False, name=None))
    actual_series = set(data[SERIES_KEYS].drop_duplicates().itertuples(index=False, name=None))
    if expected_series != actual_series:
        raise ValueError("Các chuỗi trong Parquet không khớp toàn bộ danh sách MVP.")

    last_day = int(data["day_number"].max())
    if last_day not in (config.validation_end_day, config.test_end_day):
        raise ValueError("Nguồn phải kết thúc ở validation_end_day hoặc test_end_day; không dùng cửa sổ thiếu ngày.")
    if sorted(data["day_number"].unique()) != list(range(1, last_day + 1)):
        raise ValueError("Nguồn có ngày bị thiếu hoặc không bắt đầu từ d_1.")
    counts = data.groupby(SERIES_KEYS, observed=True).size()
    if not counts.eq(last_day).all():
        raise ValueError("Mỗi chuỗi MVP phải có đủ lịch sử mỗi ngày, không được thiếu dòng.")
    return data.sort_values(SERIES_KEYS + ["day_number"], kind="stable").reset_index(drop=True)


def split_data(data: pd.DataFrame, config: SplitConfig) -> dict[str, pd.DataFrame]:
    """Accept the validated, sorted output of prepare_data; never shuffle rows."""
    config.validate()
    windows = {
        "train": (1, config.train_end_day),
        "validation": (config.train_end_day + 1, config.validation_end_day),
    }
    if int(data["day_number"].max()) == config.test_end_day:
        windows["test"] = (config.validation_end_day + 1, config.test_end_day)
    return {name: data.loc[data["day_number"].between(start, end)].reset_index(drop=True)
            for name, (start, end) in windows.items()}


def make_backtest_context(splits: dict[str, pd.DataFrame], window: str) -> BacktestContext:
    """Expose history before the origin, sales-free future covariates, and labels.

    Test history includes validation observations only after model selection.
    Feed history/future to HI03; labels are only for scoring predictions.
    """
    if window not in ("validation", "test") or window not in splits:
        raise ValueError(f"Không có cửa sổ backtest {window!r}; chưa có nhãn thì không được đánh giá test.")
    history_parts = [splits["train"]]
    if window == "test":
        history_parts.append(splits["validation"])
    history = pd.concat(history_parts, ignore_index=True).sort_values(SERIES_KEYS + ["day_number"])
    target = splits[window]
    if int(history["day_number"].max()) >= int(target["day_number"].min()):
        raise ValueError("Lịch sử chồng lấn cửa sổ dự báo.")
    return BacktestContext(
        history=history.reset_index(drop=True),
        future=target.drop(columns=["sales"]).copy(),
        labels=target[LABEL_COLUMNS].copy(),
    )


def describe_split(frame: pd.DataFrame) -> dict:
    start, end = int(frame["day_number"].min()), int(frame["day_number"].max())
    counts = frame.groupby(SERIES_KEYS, observed=True).size()
    return {
        "start_d": f"d_{start}", "end_d": f"d_{end}",
        "start_date": frame["date"].min().date().isoformat(),
        "end_date": frame["date"].max().date().isoformat(),
        "day_count": end - start + 1, "row_count": len(frame), "series_count": len(counts),
        "min_days_per_series": int(counts.min()), "max_days_per_series": int(counts.max()),
    }


def fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        name = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        name = path.as_posix()
    return {"path": name, "sha256": digest.hexdigest(), "size_bytes": path.stat().st_size}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="HI02: chia M5 theo cửa sổ thời gian, không random split")
    parser.add_argument("--input", type=Path, default=Path("data/processed/m5_sales_processed.parquet"))
    parser.add_argument("--calendar", type=Path, default=Path("data/raw/calendar.csv"))
    parser.add_argument("--item-list", type=Path, default=Path("reports/Hung/m5_mvp_items.csv"))
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("split_config.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/splits"))
    parser.add_argument("--log", type=Path, default=Path("reports/Hieu/hi02_split_log.json"))
    parser.add_argument("--day-mapping", type=Path, default=Path("reports/Hieu/hi02_day_mapping.csv"))
    args = parser.parse_args()
    inputs = {"parquet": args.input, "calendar": args.calendar,
              "item_list": args.item_list, "config": args.config}
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        parser.exit(1, "Dừng HI02: thiếu đầu vào bàn giao/cấu hình: " + ", ".join(missing) + "\n")
    try:
        config = SplitConfig(**json.loads(args.config.read_text(encoding="utf-8-sig")))
        data = prepare_data(pd.read_parquet(args.input),
                            pd.read_csv(args.calendar, usecols=["d", "date"]),
                            pd.read_csv(args.item_list), config)
        splits = split_data(data, config)
        contexts = {name: make_backtest_context(splits, name)
                    for name in ("validation", "test") if name in splits}
        if "test" not in splits and any((args.output_dir / name).exists()
                                         for name in ("test.parquet", "test_future.parquet")):
            raise ValueError("Output còn file test từ lần chạy trước. Dùng --output-dir khác để tránh bàn giao nhầm.")
        destinations = [args.output_dir / f"{name}.parquet" for name in splits]
        destinations += [args.output_dir / f"{name}_future.parquet" for name in contexts]
        destinations += [args.log, args.day_mapping]
        if len({path.resolve() for path in destinations}) != len(destinations):
            raise ValueError("Các đường dẫn đầu ra không được trùng nhau.")
        if {path.resolve() for path in destinations} & {path.resolve() for path in inputs.values()}:
            raise ValueError("Không được ghi đè đầu vào bằng file đầu ra.")
    except (ValueError, TypeError, OSError, KeyError) as exc:
        parser.exit(1, f"Dừng HI02: {exc}\n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for name, frame in splits.items():
        output = args.output_dir / f"{name}.parquet"
        frame.to_parquet(output, engine="pyarrow", index=False)
        summaries[name] = {**describe_split(frame), "artifact": fingerprint(output)}
        if name in contexts:
            future_output = args.output_dir / f"{name}_future.parquet"
            contexts[name].future.to_parquet(future_output, engine="pyarrow", index=False)
            summaries[name]["future_artifact"] = fingerprint(future_output)
            summaries[name]["history"] = describe_split(contexts[name].history)

    mapping = data[["day_number", "d", "date"]].drop_duplicates().sort_values("day_number")
    mapping["split"] = "train"
    mapping.loc[mapping["day_number"] > config.train_end_day, "split"] = "validation"
    mapping.loc[mapping["day_number"] > config.validation_end_day, "split"] = "test"
    args.day_mapping.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(args.day_mapping, index=False, date_format="%Y-%m-%d")
    log = {
        "task": "HI02", "config": asdict(config),
        "inputs": {name: fingerprint(path) for name, path in inputs.items()},
        "schema": {column: str(dtype) for column, dtype in data.dtypes.items()},
        "splits": summaries, "test_available": "test" in splits,
        "day_mapping": fingerprint(args.day_mapping),
        "checks": {"chronological_non_overlapping": True, "complete_daily_series": True,
                   "calendar_mapping_matches": True, "scope_matches": True,
                   "future_files_exclude_sales": True, "minimum_history_days": config.min_history_days},
        "usage": {
            "validation_history": "train",
            "test_history": "train + validation, chỉ sau khi chọn model" if "test" in splits else None,
            "labels": "sales trong validation/test chỉ để đánh giá, không dùng làm lag/rolling trong chính cửa sổ đó",
            "features": "HI03 dùng make_backtest_context; lag ngắn cần dự báo đệ quy, hoặc dùng lag an toàn >= horizon",
            "test_status": "Có nhãn để đánh giá; HI02 chưa huấn luyện hoặc đánh giá model" if "test" in splits
                           else "Không có nhãn holdout; không tạo test và không tuyên bố đánh giá d_1914..d_1941",
        },
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, summary in summaries.items():
        print(f"{name}: {summary['start_d']}..{summary['end_d']} | "
              f"{summary['start_date']}..{summary['end_date']} | "
              f"{summary['row_count']:,} dòng | {summary['series_count']} chuỗi")
    if "test" not in splits:
        print("Không có nhãn test: KHÔNG đánh giá d_1914..d_1941.")
    print(f"Log: {args.log}; mapping: {args.day_mapping}; Parquet: {args.output_dir}")


if __name__ == "__main__":
    main()
