"""H04 integrity and measurement tests; Azure clients below are fakes."""

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from azure.core.exceptions import HttpResponseError
import pandas as pd

from src.data import benchmark as h04
from src.data import upload_blob as h03


class FakeBlob:
    def __init__(self, corrupt=False):
        self.payload = None
        self.corrupt = corrupt
        self.calls = []

    def upload_blob(self, stream, **kwargs):
        self.calls.append(kwargs)
        if self.payload is not None or kwargs["overwrite"] is not False:
            raise AssertionError("Must use a new blob without overwrite")
        self.payload = stream.read()

    def get_blob_properties(self):
        return SimpleNamespace(etag='"test"', last_modified=datetime(2026, 1, 1, tzinfo=timezone.utc))

    def download_blob(self, **kwargs):
        data = b"bad" if self.corrupt else self.payload
        return SimpleNamespace(chunks=lambda: iter([data]))


class FakeService:
    def __init__(self, corrupt=False):
        self.blobs = {}
        self.corrupt = corrupt

    def get_blob_client(self, container, blob):
        self.blobs[(container, blob)] = FakeBlob(self.corrupt)
        return self.blobs[(container, blob)]


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = json.loads((h04.ROOT / h03.DEFAULT_CONFIG).read_text(encoding="utf-8"))
        for folder in ["data/raw", "data/processed", "reports/Hung"]:
            (self.root / folder).mkdir(parents=True)
        wide = pd.DataFrame({"id": ["A_CA_1", "B_CA_1"], "item_id": ["A", "B"], "dept_id": ["X", "Y"],
                             "cat_id": ["FOODS", "HOBBIES"], "store_id": ["CA_1"] * 2, "state_id": ["CA"] * 2,
                             "d_1": [0, 3], "d_2": [1, 0]})
        calendar = pd.DataFrame({"d": ["d_1", "d_2"], "date": ["2011-01-29", "2011-01-30"], "wm_yr_wk": [1, 1],
                                 "weekday": ["Saturday", "Sunday"], "wday": [1, 2], "month": [1, 1], "year": [2011, 2011],
                                 "event_name_1": [None] * 2, "event_type_1": [None] * 2,
                                 "event_name_2": [None] * 2, "event_type_2": [None] * 2,
                                 "snap_CA": [0, 1], "snap_TX": [0, 1], "snap_WI": [0, 1]})
        prices = pd.DataFrame({"store_id": ["CA_1"] * 2, "item_id": ["A", "B"], "wm_yr_wk": [1, 1], "sell_price": [1.5, 2.5]})
        wide.to_csv(self.root / "data/raw/sales_train_evaluation.csv", index=False)
        calendar.to_csv(self.root / "data/raw/calendar.csv", index=False)
        prices.to_csv(self.root / "data/raw/sell_prices.csv", index=False)
        calendar = pd.read_csv(self.root / "data/raw/calendar.csv")
        long = wide.melt(id_vars=h04.h02.ID_COLUMNS, value_vars=["d_1", "d_2"], var_name="d", value_name="sales")
        reference = h04.compact(h04.join_calendar(long, calendar).merge(prices, on=h04.h02.PRICE_KEYS))
        self.processed = self.root / self.config["processed_file"]
        reference.to_parquet(self.processed, index=False)
        wide.drop(columns=["id", "d_1", "d_2"]).to_csv(self.root / self.config["scope_file"], index=False)
        log = {"store_id": "CA_1", "item_count": 2, "day_count": 2, "rows_after_price_join": 4,
               "parquet_size_bytes": self.processed.stat().st_size, "schema": {name: str(dtype) for name, dtype in reference.dtypes.items()}}
        (self.root / self.config["h02_log"]).write_text(json.dumps(log), encoding="utf-8")

    def test_repeated_local_etl_matches_h02_and_keeps_inputs_unchanged(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with redirect_stdout(io.StringIO()):
            result = h04.local_benchmark(self.config, [1, 2], 2, self.root)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(len(result["samples"]), 52)
        for scope in result["scopes"]:
            self.assertTrue(scope["values_match_h02"])
            self.assertEqual(scope["rows_long"], scope["items"] * 2)
            self.assertTrue(all(size["parquet_bytes"] > 0 for size in scope["files"]))
        self.assertTrue(all(row["seconds"] >= 0 and row["rss_peak_sampled_bytes"] > 0 for row in result["samples"]))
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(set(before), {path for path in self.root.rglob("*") if path.is_file()})

    def test_scope_is_deterministic_and_cannot_exceed_catalog(self):
        catalog = pd.read_csv(self.root / self.config["scope_file"])
        self.assertEqual(h04.choose_scope(catalog, 1).item_id.tolist(), ["A"])
        self.assertEqual(h04.choose_scope(catalog.iloc[::-1], 1).item_id.tolist(), ["A"])
        with self.assertRaises(ValueError):
            h04.choose_scope(catalog, 3)

    def test_summary_groups_stages_without_mixing_item_scopes(self):
        rows = [{"items": size, "stage": "read", "seconds": value, "rss_peak_sampled_bytes": 100}
                for size, value in [(1, 1), (1, 3), (2, 20), (2, 30)]]
        result = h04.summarize(rows)
        self.assertEqual([row["mean_seconds"] for row in result], [2, 25])
        self.assertEqual([row["repeats"] for row in result], [2, 2])

    def test_changed_values_are_rejected(self):
        expected = pd.read_parquet(self.processed)
        changed = expected.copy()
        changed.loc[0, "sales"] = 99
        with self.assertRaises(AssertionError):
            h04.assert_same_values(changed, expected)

    def test_duplicate_calendar_is_rejected(self):
        with self.assertRaises(ValueError):
            h04.join_calendar(pd.DataFrame({"d": ["d_1"]}), pd.DataFrame({"d": ["d_1", "d_1"]}))

    def test_azure_benchmark_uses_only_new_test_prefix_and_checks_download(self):
        service = FakeService()
        result = h04.azure_benchmark(self.config, 2, self.root, service)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(len(result["samples"]), 2)
        self.assertTrue(all(row["sha256_matches"] for row in result["samples"]))
        self.assertEqual(len(result["retained_blobs"]), 2)
        for (container, name), blob in service.blobs.items():
            self.assertEqual(container, "processed-data")
            self.assertTrue(name.startswith("benchmarks/h04/"))
            self.assertFalse(blob.calls[0]["overwrite"])
        other = h04.azure_benchmark(self.config, 2, self.root, FakeService())
        self.assertNotEqual(result["run_id"], other["run_id"])

    def test_corrupt_azure_download_fails_but_records_created_blob(self):
        result = h04.azure_benchmark(self.config, 2, self.root, FakeService(corrupt=True))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["retained_blobs"]), 1)
        self.assertFalse(result["samples"])

    def test_azure_errors_do_not_leak_sdk_secret_text(self):
        service = FakeService()
        with patch.object(service, "get_blob_client", side_effect=HttpResponseError("AccountKey=SECRET&sig=SECRET")):
            result = h04.azure_benchmark(self.config, 2, self.root, service)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_cli_rejects_overwriting_existing_reports(self):
        (self.root / "reports/Hung/benchmark.md").write_text("existing report", encoding="utf-8")
        with patch.object(h04, "ROOT", self.root), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            h04.main([])
        self.assertEqual((self.root / "reports/Hung/benchmark.md").read_text(encoding="utf-8"), "existing report")


if __name__ == "__main__":
    unittest.main()
