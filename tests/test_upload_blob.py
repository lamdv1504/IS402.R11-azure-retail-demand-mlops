"""H03 local/fake-SDK checks; no credentials or requests to Azure."""

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceNotFoundError, ResourceModifiedError
import pandas as pd

from src.data import upload_blob as h03


class FakeBlob:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.uploads = []
        self.downloads = []
        self.race = False

    def get_blob_properties(self):
        if self.error:
            raise self.error
        if self.payload is None:
            raise ResourceNotFoundError("missing")
        return SimpleNamespace(size=len(self.payload), etag='"revision-1"', last_modified=datetime(2026, 1, 1, tzinfo=timezone.utc))

    def download_blob(self, **kwargs):
        self.downloads.append(kwargs)
        return SimpleNamespace(chunks=lambda: (self.payload[index:index + 17] for index in range(0, len(self.payload), 17)))

    def upload_blob(self, source, **kwargs):
        self.uploads.append(kwargs)
        if self.race:
            self.payload = b"created-by-another-user"
        if self.payload is not None:
            raise ResourceExistsError("already exists")
        if kwargs["overwrite"] is not False:
            raise AssertionError("Existing blobs must never be overwritten")
        self.payload = source.read()


class FakeService:
    def __init__(self, blobs):
        self.blobs = blobs

    def get_blob_client(self, container, blob):
        return self.blobs[(container, blob)]


class UploadBlobTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = json.loads((h03.ROOT / h03.DEFAULT_CONFIG).read_text(encoding="utf-8"))
        for folder in ["data/raw", "data/processed", "reports/Hung", "src/data"]:
            (self.root / folder).mkdir(parents=True)
        for name in self.config["raw_files"]:
            (self.root / "data/raw" / name).write_bytes(b"fixture,only\n1,2\n")
        frame = pd.DataFrame({
            "store_id": ["CA_1"] * 4, "item_id": ["A", "B", "A", "B"],
            "d": ["d_1", "d_1", "d_2", "d_2"], "date": pd.to_datetime(["2011-01-29"] * 2 + ["2011-01-30"] * 2),
            "sales": [0, 1, 2, 0],
        })
        self.processed = self.root / self.config["processed_file"]
        frame.to_parquet(self.processed, index=False)
        self.h02 = {"store_id": "CA_1", "item_count": 2, "day_count": 2, "rows_after_price_join": 4,
                    "schema": {name: str(dtype) for name, dtype in frame.dtypes.items()}, "parquet_size_bytes": self.processed.stat().st_size}
        (self.root / self.config["h02_log"]).write_text(json.dumps(self.h02), encoding="utf-8")
        (self.root / self.config["scope_file"]).write_text("store_id,item_id\nCA_1,A\nCA_1,B\n", encoding="utf-8")
        self.config_path = self.root / h03.DEFAULT_CONFIG
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def plan(self, selection="all"):
        return h03.build_plan(self.config, selection, self.root)

    def service(self, report, existing=True):
        return FakeService({(entry["container"], entry["blob_name"]): FakeBlob((self.root / entry["local"]["path"]).read_bytes() if existing else None)
                            for entry in report["files"]})

    def test_local_plan_has_plain_uris_and_distinct_data_scopes(self):
        report = self.plan()
        self.assertEqual(report["status"], "planned")
        self.assertEqual(len(report["files"]), 6)
        self.assertEqual(report["processed_scope"]["row_count"], 4)
        self.assertEqual({entry["data_scope"] for entry in report["files"]}, {"full_m5_raw", "mvp_processed"})
        for entry in report["files"]:
            self.assertEqual(entry["remote"]["status"], "not_checked")
            self.assertNotIn("?", entry["uri"])
            self.assertEqual(len(entry["local"]["sha256"]), 64)

    def test_processed_only_does_not_require_raw_files(self):
        (self.root / "data/raw/calendar.csv").unlink()
        self.assertEqual(len(self.plan("processed")["files"]), 1)

    def test_existing_upload_in_container_root_can_be_verified(self):
        self.config["processed_prefix"] = ""
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        h03.load_config(self.config_path, self.root)
        report = self.plan("processed")
        self.assertEqual(report["files"][0]["blob_name"], self.processed.name)
        self.assertNotIn(".net/processed-data//", report["files"][0]["uri"])
        self.assertTrue(h03.process_blobs(report, self.config, self.service(report), "verify", self.root))

    def test_missing_required_raw_file_stops_local_preflight(self):
        (self.root / "data/raw/calendar.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.plan()

    def test_wrong_processed_scope_is_rejected(self):
        (self.root / self.config["scope_file"]).write_text("store_id,item_id\nCA_1,A\nCA_1,C\n", encoding="utf-8")
        with self.assertRaises(h03.H03Error):
            self.plan()

    def test_wrong_h02_row_count_is_rejected(self):
        self.h02["rows_after_price_join"] = 123
        (self.root / self.config["h02_log"]).write_text(json.dumps(self.h02), encoding="utf-8")
        with self.assertRaises(h03.H03Error):
            self.plan()

    def test_configuration_rejects_secret_fields_queries_and_path_escape(self):
        for key, value in [("connection_string", "SECRET"), ("raw_prefix", "raw?sig=SECRET"),
                           ("account_name", "https://host?sig=SECRET"), ("raw_files", ["../secret.csv"]),
                           ("raw_dir", "../outside"), ("processed_prefix", "../other"), ("raw_container", "raw--data")]:
            with self.subTest(key=key):
                changed = dict(self.config)
                changed[key] = value
                self.config_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(h03.H03Error) as caught:
                    h03.load_config(self.config_path, self.root)
                self.assertNotIn("SECRET", str(caught.exception))

    def test_verify_existing_portal_uploads_uses_sha256_and_etag_without_writes(self):
        report = self.plan()
        service = self.service(report)
        self.assertTrue(h03.process_blobs(report, self.config, service, "verify", self.root))
        self.assertEqual(report["status"], "verified")
        for blob in service.blobs.values():
            self.assertEqual(blob.uploads, [])
            self.assertEqual(blob.downloads[0]["match_condition"], MatchConditions.IfNotModified)
            self.assertEqual(blob.downloads[0]["etag"], '"revision-1"')
        self.assertTrue(report["files"][-1]["remote"]["schema_matches_local"])

    def test_missing_remote_blob_in_verify_mode_is_not_uploaded(self):
        report = self.plan("processed")
        service = self.service(report, existing=False)
        self.assertFalse(h03.process_blobs(report, self.config, service, "verify", self.root))
        self.assertEqual(report["files"][0]["remote"]["error"]["code"], "BLOB_MISSING")
        self.assertFalse(next(iter(service.blobs.values())).uploads)

    def test_upload_creates_only_missing_blobs_and_checks_download(self):
        report = self.plan()
        service = self.service(report)
        missing = service.blobs[(report["files"][0]["container"], report["files"][0]["blob_name"])]
        missing.payload = None
        self.assertTrue(h03.process_blobs(report, self.config, service, "upload", self.root))
        self.assertEqual(sum(len(blob.uploads) for blob in service.blobs.values()), 1)
        self.assertFalse(missing.uploads[0]["overwrite"])
        self.assertEqual(missing.uploads[0]["metadata"]["data_version"], self.config["data_version"])
        self.assertEqual(report["files"][0]["remote"]["action"], "uploaded_new")

    def test_equal_size_different_content_is_not_overwritten(self):
        report = self.plan("processed")
        service = self.service(report)
        blob = next(iter(service.blobs.values()))
        blob.payload = b"x" * len(blob.payload)
        self.assertFalse(h03.process_blobs(report, self.config, service, "upload", self.root))
        self.assertEqual(report["files"][0]["remote"]["error"]["code"], "HASH_MISMATCH")
        self.assertFalse(blob.uploads)

    def test_wrong_size_is_rejected_without_download_or_overwrite(self):
        report = self.plan("processed")
        service = self.service(report)
        blob = next(iter(service.blobs.values()))
        blob.payload = b"wrong"
        self.assertFalse(h03.process_blobs(report, self.config, service, "upload", self.root))
        self.assertEqual(report["files"][0]["remote"]["error"]["code"], "SIZE_MISMATCH")
        self.assertFalse(blob.downloads)
        self.assertFalse(blob.uploads)

    def test_upload_race_does_not_overwrite_other_users_blob(self):
        report = self.plan("processed")
        service = self.service(report, existing=False)
        blob = next(iter(service.blobs.values()))
        blob.race = True
        self.assertFalse(h03.process_blobs(report, self.config, service, "upload", self.root))
        self.assertEqual(blob.payload, b"created-by-another-user")
        self.assertEqual(report["files"][0]["remote"]["error"]["code"], "ResourceExistsError")

    def test_local_change_before_upload_stops_write(self):
        report = self.plan("processed")
        service = self.service(report, existing=False)
        self.processed.write_bytes(b"changed")
        self.assertFalse(h03.process_blobs(report, self.config, service, "upload", self.root))
        self.assertEqual(report["files"][0]["remote"]["error"]["code"], "LOCAL_FILE_CHANGED")
        self.assertFalse(next(iter(service.blobs.values())).uploads)

    def test_revision_change_during_download_is_not_marked_verified(self):
        report = self.plan("processed")
        service = self.service(report)
        blob = next(iter(service.blobs.values()))
        with patch.object(blob, "download_blob", side_effect=ResourceModifiedError("revision changed")):
            self.assertFalse(h03.process_blobs(report, self.config, service, "verify", self.root))
        self.assertEqual(report["status"], "failed")

    def test_sdk_error_text_is_not_written_to_report(self):
        report = self.plan("processed")
        service = self.service(report)
        next(iter(service.blobs.values())).error = HttpResponseError("AccountKey=SECRET&sig=SECRET")
        self.assertFalse(h03.process_blobs(report, self.config, service, "verify", self.root))
        self.assertNotIn("SECRET", json.dumps(report))

    def test_report_path_cannot_overwrite_h02_or_data(self):
        for value in ["reports/Hung/h02_processing_log.json", "data/processed/h03_blob.json", "../h03_blob.json"]:
            with self.subTest(value=value), self.assertRaises(h03.H03Error):
                h03.report_path(self.root, value)

    def test_cli_plan_does_not_authenticate_or_contact_azure(self):
        with patch.object(h03, "ROOT", self.root), patch.object(h03, "open_service", side_effect=AssertionError("network forbidden")), redirect_stdout(io.StringIO()):
            self.assertEqual(h03.main(["--mode", "plan"]), 0)
        report = json.loads((self.root / "reports/Hung/h03_blob_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "planned")

    def test_cli_auth_failure_returns_nonzero_without_secrets(self):
        output = io.StringIO()
        with patch.object(h03, "ROOT", self.root), patch.object(h03, "open_service", side_effect=HttpResponseError("sig=SECRET")), redirect_stdout(output):
            self.assertEqual(h03.main(["--mode", "verify", "--files", "processed"]), 1)
        log = (self.root / "reports/Hung/h03_blob_verify.json").read_text(encoding="utf-8")
        self.assertNotIn("SECRET", log + output.getvalue())
        self.assertEqual(json.loads(log)["status"], "failed")

    def test_connection_string_for_another_account_is_rejected(self):
        client = SimpleNamespace(url="https://otherstore.blob.core.windows.net", close=lambda: None)
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "SECRET"}, clear=True), patch("azure.storage.blob.BlobServiceClient.from_connection_string", return_value=client):
            with self.assertRaises(h03.H03Error) as caught:
                with h03.open_service(self.config, self.root):
                    self.fail("Wrong destination must not be used")
        self.assertEqual(caught.exception.code, "ACCOUNT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
