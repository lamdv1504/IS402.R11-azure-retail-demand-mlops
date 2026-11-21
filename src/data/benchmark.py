"""H04: repeated, scoped M5 ETL/storage benchmarks; Azure is opt-in."""

import argparse
import csv
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
import uuid

import pandas as pd
import psutil

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data import preprocessing as h02
from src.data import upload_blob as h03

ROOT = Path(__file__).resolve().parents[2]
ETL_STAGES = {"scan_sales_raw", "read_calendar", "scan_prices_raw", "melt", "join_calendar", "join_prices", "downcast", "write_parquet"}


def measure(records, scope_size, repeat, stage, operation):
    """Wall time excludes frame diagnostics; RSS is sampled for the whole process."""
    process = psutil.Process()
    before = process.memory_info().rss
    samples = [before]
    stop = threading.Event()

    def sample():
        while not stop.wait(0.02):
            samples.append(process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        result = operation()
        elapsed = time.perf_counter() - started
    finally:
        stop.set()
        sampler.join()
    samples.append(process.memory_info().rss)
    record = {"items": scope_size, "repeat": repeat, "stage": stage,
              "seconds": elapsed, "rss_before_bytes": before, "rss_peak_sampled_bytes": max(samples)}
    if isinstance(result, pd.DataFrame):
        record.update(rows=len(result), columns=len(result.columns), dataframe_bytes=int(result.memory_usage(deep=True).sum()))
    records.append(record)
    return result


def choose_scope(catalog, size):
    if size < 1 or size > len(catalog):
        raise ValueError("Scope phải nằm trong catalog; không tự mở rộng ra ngoài MVP.")
    # Round-robin categories gives 34/33/33 for 100 items, retaining a stable subset.
    ordered = catalog.sort_values(["cat_id", "item_id"]).copy()
    ordered["rank"] = ordered.groupby("cat_id", observed=True).cumcount()
    return ordered.sort_values(["rank", "cat_id", "item_id"]).head(size).drop(columns="rank")


def read_prices(path, store, items):
    parts = []
    for chunk in pd.read_csv(path, chunksize=200_000):
        rows = chunk.loc[chunk.store_id.eq(store) & chunk.item_id.isin(items)]
        if not rows.empty:
            parts.append(rows)
    if not parts:
        raise ValueError("Thiếu giá cho scope benchmark.")
    prices = pd.concat(parts, ignore_index=True)
    if prices[h02.PRICE_KEYS].isna().any().any() or prices[h02.PRICE_KEYS].duplicated().any():
        raise ValueError("Khóa giá thiếu/trùng; dừng trước join.")
    return prices


def join_calendar(frame, calendar):
    if calendar.d.isna().any() or calendar.d.duplicated().any():
        raise ValueError("Khóa calendar thiếu hoặc trùng.")
    result = frame.merge(calendar, on="d", how="left", validate="many_to_one")
    if len(result) != len(frame) or result[["date", "wm_yr_wk"]].isna().any().any():
        raise ValueError("Join calendar đổi số dòng hoặc thiếu ngày.")
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    return result


def compact(frame):
    frame = frame.copy()
    frame["sales"] = pd.to_numeric(frame.sales, downcast="integer")
    for column in ["wm_yr_wk", "wday", "month", "year", "snap_CA", "snap_TX", "snap_WI"]:
        frame[column] = pd.to_numeric(frame[column], downcast="integer")
    frame["sell_price"] = pd.to_numeric(frame.sell_price, downcast="float")
    for column in ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id", "weekday", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]:
        frame[column] = frame[column].astype("category")
    return frame


def assert_same_values(actual, expected):
    if set(actual.columns) != set(expected.columns):
        raise ValueError("Các bản so sánh không cùng schema cột.")
    keys = ["store_id", "item_id", "d"]
    left = actual.sort_values(keys).reset_index(drop=True)[list(expected.columns)].copy()
    right = expected.sort_values(keys).reset_index(drop=True).copy()
    for column in right:
        if isinstance(right[column].dtype, pd.CategoricalDtype) or pd.api.types.is_string_dtype(right[column].dtype):
            left[column] = left[column].astype("string")
            right[column] = right[column].astype("string")
    pd.testing.assert_frame_equal(left, right, check_dtype=False, check_categorical=False, rtol=1e-5, atol=1e-5)


def local_benchmark(config, sizes, repeats, root=ROOT):
    scope_info = h03.inspect_processed(config, root)
    catalog = pd.read_csv(h03.project_path(root, config["scope_file"]))
    reference = pd.read_parquet(h03.project_path(root, config["processed_file"]))
    raw = h03.project_path(root, config["raw_dir"])
    records, scopes = [], []
    with TemporaryDirectory(prefix="m5-h04-") as directory:
        temporary = Path(directory)
        for size in sizes:
            selected = choose_scope(catalog, size)
            items = set(selected.item_id)
            store = scope_info["store_id"]
            expected = reference.loc[reference.item_id.isin(items)].copy()
            info = {"items": size, "store_id": store, "item_ids": sorted(items),
                    "categories": selected.cat_id.value_counts().sort_index().to_dict(),
                    "days": scope_info["day_count"], "rows_long": len(expected), "files": []}
            for repeat in range(1, repeats + 1):
                gc.collect()
                print(f"H04: CA_1 / {size} items, lần {repeat}/{repeats}", flush=True)
                def timed(stage, operation):
                    return measure(records, size, repeat, stage, operation)
                wide = timed("scan_sales_raw", lambda: h02.read_selected_sales(raw / "sales_train_evaluation.csv", store, items))
                calendar = timed("read_calendar", lambda: pd.read_csv(raw / "calendar.csv"))
                prices = timed("scan_prices_raw", lambda: read_prices(raw / "sell_prices.csv", store, items))
                day_columns = [name for name in wide if h02.DAY_PATTERN.fullmatch(name)]
                long = timed("melt", lambda: wide.melt(id_vars=h02.ID_COLUMNS, value_vars=day_columns, var_name="d", value_name="sales"))
                long = timed("join_calendar", lambda: join_calendar(long, calendar))
                before_join = len(long)
                long = timed("join_prices", lambda: long.merge(prices, on=h02.PRICE_KEYS, how="left", validate="many_to_one"))
                if len(long) != before_join or long[["item_id", "store_id", "d"]].duplicated().any():
                    raise ValueError("Join giá làm đổi số dòng hoặc nhân bản khóa.")
                long = timed("downcast", lambda: compact(long))
                assert_same_values(long, expected)
                parquet, long_csv, wide_csv = (temporary / name for name in ["scope.parquet", "long.csv", "wide.csv"])
                timed("write_parquet", lambda: long.to_parquet(parquet, index=False, engine="pyarrow"))
                timed("write_long_csv", lambda: long.to_csv(long_csv, index=False, date_format="%Y-%m-%d"))
                timed("write_wide_csv", lambda: wide.to_csv(wide_csv, index=False))
                reads = ["read_wide_mvp_csv", "read_long_mvp_csv", "read_mvp_parquet"]
                random.Random(42 + repeat).shuffle(reads)
                for stage in reads:
                    if stage == "read_wide_mvp_csv":
                        frame = timed(stage, lambda: pd.read_csv(wide_csv))
                        pd.testing.assert_frame_equal(frame, wide, check_dtype=False)
                    else:
                        operation = (lambda: pd.read_parquet(parquet)) if stage == "read_mvp_parquet" else (lambda: pd.read_csv(long_csv, parse_dates=["date"]))
                        frame = timed(stage, operation)
                        assert_same_values(frame, long)
                    del frame
                info["files"].append({"repeat": repeat, "wide_csv_bytes": wide_csv.stat().st_size,
                                      "long_csv_bytes": long_csv.stat().st_size, "parquet_bytes": parquet.stat().st_size})
                del wide, long, calendar, prices
            info["values_match_h02"] = True
            scopes.append(info)
    return {"status": "measured", "scopes": scopes, "samples": records, "rss_sample_interval_seconds": 0.02,
            "temporary_volume": Path(directory).anchor, "cache_policy": "OS cache uncontrolled; read order shuffled, not a cold-cache benchmark"}


def summarize(records):
    groups = {}
    for row in records:
        groups.setdefault((row["items"], row["stage"]), []).append(row)
    result = []
    for (items, stage), rows in sorted(groups.items()):
        times = [row["seconds"] for row in rows]
        result.append({"items": items, "stage": stage, "repeats": len(rows),
                       "mean_seconds": statistics.mean(times), "median_seconds": statistics.median(times),
                       "min_seconds": min(times), "max_seconds": max(times),
                       "stdev_seconds": statistics.stdev(times) if len(times) > 1 else 0,
                       "peak_process_rss_bytes": max(row["rss_peak_sampled_bytes"] for row in rows)})
    return result


def azure_benchmark(config, repeats, root=ROOT, service=None):
    from azure.core import MatchConditions
    from azure.storage.blob import ContentSettings

    source = h03.project_path(root, config["processed_file"])
    original = h03.fingerprint(source, root)
    run_id = uuid.uuid4().hex
    result = {"status": "measured", "run_id": run_id, "size_bytes": original["size_bytes"],
              "samples": [], "retained_blobs": [], "scope": "H02 Parquet, CA_1 / 300 items"}

    def run(client):
        for repeat in range(1, repeats + 1):
            name = f"benchmarks/h04/{run_id}/repeat-{repeat}.parquet"
            uri = f'https://{config["account_name"]}.blob.core.windows.net/{config["processed_container"]}/{name}'
            blob = client.get_blob_client(container=config["processed_container"], blob=name)
            if h03.fingerprint(source, root) != original:
                raise ValueError("File local thay đổi trước khi đo Blob.")
            started = time.perf_counter()
            with source.open("rb") as stream:
                blob.upload_blob(stream, overwrite=False, length=original["size_bytes"],
                                 metadata={"task": "H04", "data_version": config["data_version"]},
                                 content_settings=ContentSettings(content_type="application/octet-stream"))
            upload_seconds = time.perf_counter() - started
            result["retained_blobs"].append(uri)
            properties = blob.get_blob_properties()
            digest, downloaded = hashlib.sha256(), 0
            started = time.perf_counter()
            for block in blob.download_blob(etag=properties.etag, match_condition=MatchConditions.IfNotModified, max_concurrency=1).chunks():
                digest.update(block)
                downloaded += len(block)
            download_seconds = time.perf_counter() - started
            if downloaded != original["size_bytes"] or digest.hexdigest() != original["sha256"]:
                raise ValueError("Nội dung tải từ Blob không khớp local.")
            result["samples"].append({"repeat": repeat, "upload_seconds": upload_seconds,
                                      "download_and_hash_seconds": download_seconds, "downloaded_bytes": downloaded,
                                      "sha256_matches": True, "last_modified": properties.last_modified.isoformat()})
    try:
        if service is not None:
            run(service)
        else:
            with h03.open_service(config, root) as client:
                run(client)
    except Exception as error:
        result.update(status="failed", error=h03.safe_error(error))
    return result


def machine_info():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {"os": platform.platform(), "cpu": platform.processor(), "logical_cpus": psutil.cpu_count(),
            "physical_cpus": psutil.cpu_count(logical=False), "ram_bytes": psutil.virtual_memory().total,
            "python": platform.python_version(), "base_git_commit": commit,
            "source_sha256_lf": {path: hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                 for path in ["src/data/benchmark.py", "src/data/preprocessing.py", "src/data/upload_blob.py"]},
            "packages": {name: importlib.metadata.version(name) for name in ["pandas", "pyarrow", "psutil", "azure-storage-blob"]}}


def markdown_report(report, json_name, csv_name):
    lines = ["# H04 benchmark và quy trình ETL M5", "", f"Thời điểm UTC: {report['recorded_at']}. Data version: `{report['data_version']}`.", "",
             "Đo local trên một cửa hàng CA_1, các scope lấy từ catalog MVP. Không đo toàn bộ 30.490 chuỗi.", "",
             "## Điều kiện đo", "", f"Máy: {report['machine']['os']}; CPU: {report['machine']['cpu']}; RAM {report['machine']['ram_bytes'] / 2**30:.2f} GiB.",
             f"Python {report['machine']['python']}; lặp {report['repeats']} lần cho mỗi scope. Dữ liệu tạm nằm trên volume `{report['local']['temporary_volume']}`.",
             "Cache hệ điều hành không được xóa; thứ tự đọc CSV/Parquet đổi theo seed cố định. Đây không phải phép đo cold cache.",
             "RSS là RAM của toàn tiến trình, lấy mẫu mỗi 20 ms; có thể bỏ lỡ đỉnh ngắn và không phải RAM tăng riêng của từng bước.", "",
             "## Thời gian các bước", "", "| Item | Bước | Lặp | Trung bình s | Trung vị s | Min s | Max s | RSS đỉnh mẫu MiB |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in report["summary"]:
        lines.append(f"| {row['items']} | {row['stage']} | {row['repeats']} | {row['mean_seconds']:.6f} | {row['median_seconds']:.6f} | {row['min_seconds']:.6f} | {row['max_seconds']:.6f} | {row['peak_process_rss_bytes'] / 2**20:.2f} |")
    lines += ["", "## Dung lượng và đối chiếu cùng scope", "", "| Item | Dòng long | Wide CSV byte | Long CSV byte | Parquet byte | Long CSV / Parquet |", "| --- | --- | --- | --- | --- | --- |"]
    for scope in report["local"]["scopes"]:
        sizes = scope["files"][0]
        lines.append(f"| {scope['items']} | {scope['rows_long']} | {sizes['wide_csv_bytes']} | {sizes['long_csv_bytes']} | {sizes['parquet_bytes']} | {sizes['long_csv_bytes'] / sizes['parquet_bytes']:.2f} |")
    lines += ["", "Mỗi scope giữ cùng item và toàn bộ khoảng ngày. Long CSV và Parquet có cùng 22 cột, được kiểm tra giá trị với H02 (dung sai float 1e-5).",
              "Wide CSV chỉ gồm sales/định danh; Parquet có thêm lịch/giá. Không dùng wide/full raw so với Parquet MVP để kết luận hiệu quả nén.",
              "`scan_sales_raw` và `scan_prices_raw` đọc raw đầy đủ theo chunk rồi lọc scope; các bước `read_*_mvp_*` chỉ đọc file tạm của chính scope đó.", "",
              "## Nhận xét từ số đo", ""]
    for scope in report["local"]["scopes"]:
        rows = {row["stage"]: row for row in report["summary"] if row["items"] == scope["items"]}
        ratio = rows["read_long_mvp_csv"]["mean_seconds"] / rows["read_mvp_parquet"]["mean_seconds"]
        total = sum(row["mean_seconds"] for stage, row in rows.items() if stage in ETL_STAGES)
        lines.append(f"- {scope['items']} item: tỷ lệ thời gian đọc long CSV/Parquet = {ratio:.2f}; tổng thời gian trung bình của các bước ETL được đo = {total:.3f} s.")
    lines += ["", "Tỷ lệ trên chỉ áp dụng máy, cache và mẫu đang đo; không ngoại suy sang toàn M5. Scope lớn hơn MVP chưa được đo.", "",
              "## Azure Blob", "", f"Trạng thái: `{report['azure']['status']}`."]
    if report["azure"]["status"] == "not_run":
        lines.append("Chưa đo upload/download Azure trong lượt local; không có số thời gian cloud để báo cáo.")
    else:
        lines += ["", "| Lần | Upload s | Download và hash s | Byte | SHA khớp |", "| --- | --- | --- | --- | --- |"]
        for row in report["azure"]["samples"]:
            lines.append(f"| {row['repeat']} | {row['upload_seconds']:.6f} | {row['download_and_hash_seconds']:.6f} | {row['downloaded_bytes']} | {row['sha256_matches']} |")
        lines.append("Blob test dùng prefix riêng `benchmarks/h04/<run_id>/`, không ghi đè/xóa dữ liệu H03. Các Blob test được giữ lại; danh sách có trong JSON.")
    lines += ["", "## ETL và chạy lại", "", "Raw sales → lọc store/item → melt → join calendar → join giá → downcast → Parquet → Blob có data version.",
              "H04 dùng lại hàm đọc/filter H02; mọi file benchmark ở thư mục tạm, giữ nguyên raw, Parquet và log bàn giao H02/HI05.",
              "Cài `requirements-benchmark.txt`, chạy từ repo: `python src/data/benchmark.py --sizes 100 300 --repeats 3`.",
              "Sau khi cấu hình quyền Blob theo hướng dẫn H03, thêm `--azure` để đo upload/download; xác thực Portal không tự cấp phiên SDK local.",
              "Khi chạy lại, dùng `--output-dir reports/Hung/h04-rerun-01` để không ghi đè báo cáo cũ. Giữ JSON, data version và source hash cùng training run.",
              f"Số liệu gốc: [{json_name}]({json_name}); bảng tổng hợp: [{csv_name}]({csv_name}).",
              "H04 chỉ nghiệm thu đầy đủ khi có số đo Azure thật; phần local không thay thế benchmark Blob.", ""]
    return "\n".join(lines)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="H04: benchmark M5 trên cùng scope, không sửa dữ liệu H02")
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 300])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--azure", action="store_true", help="Đo thật upload/download vào prefix test riêng trên Blob")
    parser.add_argument("--config", default=h03.DEFAULT_CONFIG)
    parser.add_argument("--output-dir", default="reports/Hung")
    args = parser.parse_args(argv)
    if args.repeats < 2 or any(size < 1 for size in args.sizes) or len(set(args.sizes)) != len(args.sizes):
        parser.error("Cần ít nhất 2 lần lặp và các scope dương, không trùng.")
    output = h03.project_path(ROOT, args.output_dir)
    if not output.is_relative_to((ROOT / "reports/Hung").resolve()):
        parser.error("Báo cáo phải nằm dưới reports/Hung.")
    names = ["h04_benchmark_log.json", "h04_benchmark.csv", "benchmark.md"]
    if any((output / name).exists() for name in names):
        parser.error("Báo cáo đã có; chọn --output-dir mới để giữ số đo cũ.")
    config = h03.load_config(h03.project_path(ROOT, args.config), root=ROOT)
    paths = [config["processed_file"], config["scope_file"], config["h02_log"],
             *[str(Path(config["raw_dir"]) / name) for name in ["sales_train_evaluation.csv", "calendar.csv", "sell_prices.csv"]]]
    inputs = [h03.fingerprint(h03.project_path(ROOT, path), root=ROOT) for path in paths if path not in (config["scope_file"], config["h02_log"])]
    local = local_benchmark(config, args.sizes, args.repeats, root=ROOT)
    if any(h03.fingerprint(h03.project_path(ROOT, item["path"]), root=ROOT) != item for item in inputs):
        raise ValueError("Đầu vào thay đổi trong khi benchmark; không ghi kết quả.")
    azure = azure_benchmark(config, args.repeats, root=ROOT) if args.azure else {"status": "not_run", "reason": "Local run; Azure requires explicit --azure and credentials"}
    report = {"task": "H04", "recorded_at": datetime.now(timezone.utc).isoformat(), "data_version": config["data_version"],
              "repeats": args.repeats, "machine": machine_info(), "inputs": inputs,
              "local": local, "azure": azure, "summary": summarize(local["samples"])}
    output.mkdir(parents=True, exist_ok=True)
    (output / names[0]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / names[1]).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report["summary"][0]))
        writer.writeheader()
        writer.writerows(report["summary"])
    (output / names[2]).write_text(markdown_report(report, names[0], names[1]), encoding="utf-8")
    print(f"H04: local={local['status']}, Azure={azure['status']}; {output.relative_to(ROOT).as_posix()}/benchmark.md")
    return 1 if azure["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
