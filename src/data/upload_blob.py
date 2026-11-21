"""H03: plan, verify or upload M5 files without overwriting existing blobs."""

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "src/data/blob_config.json"
CONFIG_KEYS = {
    "account_name", "data_version", "scope_file", "h02_log", "raw_dir",
    "processed_file", "raw_container", "processed_container", "raw_prefix",
    "processed_prefix", "raw_files",
}


class H03Error(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def project_path(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise H03Error("INVALID_PATH", "Đường dẫn phải nằm trong repository.")
    return path


def load_config(path, root=ROOT):
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise H03Error("INVALID_CONFIG", "Cấu hình H03 thiếu trường hoặc có trường không được hỗ trợ.")
    patterns = {
        "account_name": r"[a-z0-9]{3,24}",
        "data_version": r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}",
        "raw_container": r"[a-z0-9](?:[a-z0-9-]{1,61})[a-z0-9]",
        "processed_container": r"[a-z0-9](?:[a-z0-9-]{1,61})[a-z0-9]",
    }
    for key, pattern in patterns.items():
        if not isinstance(config[key], str) or not re.fullmatch(pattern, config[key]):
            raise H03Error("INVALID_CONFIG", "Account, container hoặc data version không hợp lệ.")
    if any("--" in config[key] for key in ("raw_container", "processed_container")):
        raise H03Error("INVALID_CONFIG", "Tên container không được có hai dấu gạch nối liên tiếp.")
    for key in ("raw_prefix", "processed_prefix"):
        prefix = config[key]
        if not isinstance(prefix, str) or (prefix and (not re.fullmatch(r"[A-Za-z0-9._/-]+", prefix) or any(part in ("", ".", "..") for part in prefix.split("/")))):
            raise H03Error("INVALID_CONFIG", "Blob prefix phải là đường dẫn tương đối không chứa query hoặc token.")
    files = config["raw_files"]
    if not isinstance(files, list) or not files or any(not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.csv", name) for name in files) or len(files) != len(set(files)):
        raise H03Error("INVALID_CONFIG", "Danh sách CSV raw không hợp lệ hoặc trùng tên.")
    for key in ("scope_file", "h02_log", "raw_dir", "processed_file"):
        if not isinstance(config[key], str):
            raise H03Error("INVALID_CONFIG", "Đường dẫn local phải là chuỗi.")
        project_path(root, config[key])
    return config


def fingerprint(path, root=ROOT):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise H03Error("LOCAL_FILE_CHANGED", "File local thay đổi trong lúc kiểm tra.")
    return {"path": path.relative_to(root).as_posix(), "size_bytes": after.st_size, "sha256": digest.hexdigest()}


def inspect_processed(config, root=ROOT):
    import pandas as pd
    import pyarrow.parquet as pq

    h02 = json.loads(project_path(root, config["h02_log"]).read_text(encoding="utf-8-sig"))
    with project_path(root, config["scope_file"]).open(encoding="utf-8-sig", newline="") as source:
        records = list(csv.DictReader(source))
    expected = {(row["store_id"], row["item_id"]) for row in records}
    if len(records) != len(expected) or not records or len({store for store, _ in expected}) != 1:
        raise H03Error("INVALID_SCOPE", "Catalog MVP thiếu dữ liệu, trùng chuỗi hoặc có nhiều cửa hàng.")
    path = project_path(root, config["processed_file"])
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows != h02["rows_after_price_join"] or set(parquet.schema_arrow.names) != set(h02["schema"]) or path.stat().st_size != h02["parquet_size_bytes"]:
        raise H03Error("H02_MISMATCH", "Kích thước, số dòng hoặc schema Parquet khác bàn giao H02.")
    frame = pd.read_parquet(path, columns=["store_id", "item_id", "date", "d"])
    actual = set(zip(frame["store_id"].astype(str), frame["item_id"].astype(str)))
    counts = frame.groupby(["store_id", "item_id"], observed=True).size()
    if actual != expected or len(expected) != h02["item_count"] or {store for store, _ in expected} != {h02["store_id"]} or frame[["store_id", "item_id", "d"]].duplicated().any() or not counts.eq(h02["day_count"]).all() or frame["date"].nunique() != h02["day_count"]:
        raise H03Error("H02_MISMATCH", "Phạm vi chuỗi hoặc ngày Parquet khác catalog/H02.")
    return {
        "store_id": h02["store_id"], "item_count": len(expected),
        "day_count": h02["day_count"], "row_count": len(frame),
        "column_count": parquet.metadata.num_columns,
        "start_date": str(frame["date"].min().date()),
        "end_date": str(frame["date"].max().date()),
        "schema": {field.name: str(field.type) for field in parquet.schema_arrow},
    }


def build_plan(config, selection="all", root=ROOT):
    scope = inspect_processed(config, root)
    files = []
    specs = []
    if selection in ("all", "raw"):
        specs.extend((project_path(root, config["raw_dir"]) / name, config["raw_container"], "/".join(filter(None, [config["raw_prefix"], name])), "full_m5_raw") for name in config["raw_files"])
    if selection in ("all", "processed"):
        path = project_path(root, config["processed_file"])
        specs.append((path, config["processed_container"], "/".join(filter(None, [config["processed_prefix"], path.name])), "mvp_processed"))
    for path, container, blob_name, data_scope in specs:
        # Resolve each file too: a symlink below raw_dir must not escape the repo.
        path = project_path(root, path)
        files.append({
            "local": fingerprint(path, root), "container": container,
            "blob_name": blob_name, "data_scope": data_scope,
            "uri": f'https://{config["account_name"]}.blob.core.windows.net/{container}/{quote(blob_name, safe="/")}',
            "remote": {"status": "not_checked"},
        })
    return {"task": "H03", "mode": "plan", "status": "planned", "recorded_at": timestamp(),
            "account_name": config["account_name"], "data_version": config["data_version"],
            "selection": selection, "processed_scope": scope, "files": files}


def safe_error(error):
    # Never serialize SDK exception text: it may contain request URLs or credentials.
    if isinstance(error, H03Error):
        return {"code": error.code, "detail": str(error)}
    result = {"code": type(error).__name__, "detail": "Kiểm tra file local, xác thực Azure, quyền Blob và kết nối mạng."}
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        result["http_status"] = status
    return result


@contextmanager
def open_service(config, root=ROOT):
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    from dotenv import load_dotenv

    load_dotenv(project_path(root, ".env"), override=False)
    configured_account = os.environ.get("AZURE_STORAGE_ACCOUNT", config["account_name"])
    if configured_account != config["account_name"]:
        raise H03Error("ACCOUNT_MISMATCH", "AZURE_STORAGE_ACCOUNT khác account trong blob_config.json.")
    connection = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    credential = None
    client = None
    try:
        if connection:
            client = BlobServiceClient.from_connection_string(connection, connection_timeout=10, read_timeout=60, retry_total=1)
        else:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            client = BlobServiceClient(f'https://{config["account_name"]}.blob.core.windows.net', credential=credential,
                                       connection_timeout=10, read_timeout=60, retry_total=1)
        destination = urlsplit(client.url)
        if destination.scheme != "https" or destination.netloc != f'{config["account_name"]}.blob.core.windows.net':
            raise H03Error("ACCOUNT_MISMATCH", "Thông tin xác thực không trỏ đến đúng Storage Account HTTPS.")
        yield client
    finally:
        if client is not None:
            client.close()
        if credential is not None:
            credential.close()


def verify_blob(blob, entry, properties=None):
    from azure.core import MatchConditions

    properties = properties or blob.get_blob_properties()
    entry["remote"].update({
        "size_bytes": properties.size, "etag": properties.etag,
        "last_modified": properties.last_modified.isoformat(),
    })
    created = getattr(properties, "creation_time", None)
    if created is not None:
        entry["remote"]["created_at"] = created.isoformat()
    if properties.size != entry["local"]["size_bytes"]:
        raise H03Error("SIZE_MISMATCH", "Blob có kích thước khác local; giữ nguyên Blob hiện có.")
    digest = hashlib.sha256()
    size = 0
    # ETag prevents verifying bytes from a different blob revision mid-download.
    download = blob.download_blob(etag=properties.etag, match_condition=MatchConditions.IfNotModified, max_concurrency=1)
    for chunk in download.chunks():
        size += len(chunk)
        digest.update(chunk)
    remote_hash = digest.hexdigest()
    entry["remote"]["sha256"] = remote_hash
    if size != properties.size or remote_hash != entry["local"]["sha256"]:
        raise H03Error("HASH_MISMATCH", "Nội dung Blob khác local; giữ nguyên Blob hiện có.")
    entry["remote"].update({"status": "verified", "verification": "download_sha256", "checked_at": timestamp()})
    if entry["data_scope"] == "mvp_processed":
        # Byte-identical Parquet implies the same schema and rows as local preflight.
        entry["remote"]["schema_matches_local"] = True


def process_blobs(report, config, service, mode, root=ROOT):
    from azure.core.exceptions import ResourceNotFoundError
    from azure.storage.blob import ContentSettings

    report["mode"] = mode
    for entry in report["files"]:
        try:
            blob = service.get_blob_client(container=entry["container"], blob=entry["blob_name"])
            try:
                properties = blob.get_blob_properties()
            except ResourceNotFoundError:
                if mode != "upload":
                    raise H03Error("BLOB_MISSING", "Không tìm thấy Blob ở đường dẫn cấu hình; kiểm tra vị trí upload.") from None
                path = project_path(root, entry["local"]["path"])
                if fingerprint(path, root) != entry["local"]:
                    raise H03Error("LOCAL_FILE_CHANGED", "File local thay đổi sau khi lập danh sách; dừng upload.")
                with path.open("rb") as source:
                    blob.upload_blob(source, overwrite=False, length=entry["local"]["size_bytes"],
                                     metadata={"data_version": config["data_version"], "sha256": entry["local"]["sha256"], "data_scope": entry["data_scope"]},
                                     content_settings=ContentSettings(content_type="text/csv" if path.suffix == ".csv" else "application/octet-stream"))
                entry["remote"].update({"action": "uploaded_new", "uploaded_at": timestamp()})
                properties = blob.get_blob_properties()
            else:
                entry["remote"]["action"] = "checked_existing"
            verify_blob(blob, entry, properties)
        except Exception as error:
            entry["remote"].update({"status": "failed", "error": safe_error(error)})
            report["status"] = "failed"
            return False
    report["status"] = "verified"
    return True


def report_path(root, value):
    path = project_path(root, value)
    if not path.is_relative_to((root / "reports/Hung").resolve()) or not re.fullmatch(r"h03_[A-Za-z0-9_-]+\.json", path.name):
        raise H03Error("INVALID_LOG", "Log H03 phải là reports/Hung/h03_<tên>.json để không ghi đè file dữ liệu/bàn giao khác.")
    return path


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="H03: kiểm tra dữ liệu M5 đã upload hoặc upload file còn thiếu")
    parser.add_argument("--mode", choices=["plan", "verify", "upload"], default="plan")
    parser.add_argument("--files", choices=["all", "processed", "raw"], default="all")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Cấu hình không chứa secret, đường dẫn tính từ repo")
    parser.add_argument("--log", help="Log JSON dưới reports/Hung, tên bắt đầu bằng h03_")
    args = parser.parse_args(argv)
    report = {"task": "H03", "mode": args.mode, "status": "failed", "recorded_at": timestamp()}
    output = None
    success = False
    try:
        output = report_path(ROOT, args.log or f"reports/Hung/h03_blob_{args.mode}.json")
        config = load_config(project_path(ROOT, args.config), root=ROOT)
        report = build_plan(config, args.files, root=ROOT)
        report["mode"] = args.mode
        if args.mode == "plan":
            success = True
        else:
            with open_service(config, root=ROOT) as service:
                success = process_blobs(report, config, service, args.mode, root=ROOT)
    except Exception as error:
        report.update({"status": "failed", "error": safe_error(error)})
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"H03: {report['status']}. Log: {output.relative_to(ROOT).as_posix()}")
    else:
        print("H03: đường dẫn log không hợp lệ.")
    if not success:
        print("Chưa xác minh đủ dữ liệu. Xem mã lỗi trong log; không có Blob cũ nào bị ghi đè.")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
