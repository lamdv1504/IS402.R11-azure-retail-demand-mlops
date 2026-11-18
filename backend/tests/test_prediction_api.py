"""L03 HTTP tests against the actual HI05 model and packaged serving context."""

from datetime import date, timedelta
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
import pandas as pd

from app.main import app


BUNDLE = ROOT / "artifacts" / "hi05"
REQUEST = {"store_id": "CA_1", "item_id": "FOODS_1_017", "horizon": 28}


class PredictionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict("os.environ", {"MODEL_BUNDLE_DIR": str(BUNDLE)})
        cls.environment.start()
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.service = app.state.forecast_service
        if cls.service is None:
            raise AssertionError("The real HI05 bundle must load for L03 integration tests.")

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.environment.stop()

    def test_real_prediction_matches_saved_hi05_forecast(self):
        response = self.client.post("/predict", json=REQUEST)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        expected = pd.read_csv(ROOT / "reports/Hieu/hi05_future_predictions.csv")
        expected = expected.loc[expected.item_id.eq(REQUEST["item_id"])].sort_values("day_number")
        self.assertEqual(len(result["forecast"]), 28)
        self.assertEqual(result["model_version"], self.service.info.model_version)
        self.assertEqual(result["data_version"], "m5-ca1-300-v1")
        self.assertEqual(result["forecast_start_date"], "2016-05-23")
        for offset, (actual, recorded) in enumerate(zip(result["forecast"], expected.itertuples(index=False))):
            day = date(2016, 5, 23) + timedelta(days=offset)
            self.assertEqual(actual["date"], day.isoformat())
            self.assertEqual(actual["day_of_week"], day.strftime("%A"))
            self.assertEqual(actual["predicted_sales"], round(recorded.predicted_sales, 2))
            self.assertTrue(math.isfinite(actual["predicted_sales"]))
            self.assertGreaterEqual(actual["predicted_sales"], 0)
        self.assertEqual(result["total_predicted_sales"], round(sum(x["predicted_sales"] for x in result["forecast"]), 2))

    def test_short_and_default_horizons(self):
        for horizon in [1, 7, 28]:
            with self.subTest(horizon=horizon):
                response = self.client.post("/predict", json={**REQUEST, "horizon": horizon})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()["forecast"]), horizon)
        response = self.client.post("/predict", json={k: v for k, v in REQUEST.items() if k != "horizon"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["horizon"], 28)

    def test_unknown_store_or_item(self):
        for changed in [{"store_id": "CA_2"}, {"item_id": "UNKNOWN"}]:
            response = self.client.post("/predict", json={**REQUEST, **changed})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error_code"], "ITEM_NOT_FOUND")

    def test_invalid_horizon_and_request_types(self):
        for horizon in [0, 29, -1, 1.5, "28", True, None]:
            with self.subTest(horizon=horizon):
                response = self.client.post("/predict", json={**REQUEST, "horizon": horizon})
                self.assertEqual(response.status_code, 422, response.text)
        for body in [{}, {**REQUEST, "item_id": ""}, {**REQUEST, "item_id": 123}]:
            self.assertEqual(self.client.post("/predict", json=body).status_code, 422)

    def test_model_info_catalog_and_health_use_the_loaded_bundle(self):
        self.assertTrue(self.client.get("/health").json()["model_loaded"])
        response = self.client.get("/model-info")
        self.assertEqual(response.status_code, 200, response.text)
        info = response.json()
        self.assertEqual(info["model_version"], self.service.engine.metadata["model_version"])
        self.assertEqual(info["metrics"]["validation_subset_rmsse"], 0.7209842238186299)
        self.assertEqual(info["item_count"], 300)
        self.assertEqual(self.client.get("/items").json()["total_items"], 300)

    def test_model_is_reused_between_requests(self):
        with patch("app.services.predictor.load_service", side_effect=AssertionError("Unexpected reload")):
            for _ in range(2):
                self.assertEqual(self.client.post("/predict", json=REQUEST).status_code, 200)

    def test_model_not_ready_is_503(self):
        with patch.object(app.state, "forecast_service", None):
            self.assertFalse(self.client.get("/health").json()["model_loaded"])
            for response in [self.client.post("/predict", json=REQUEST), self.client.get("/model-info")]:
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error_code"], "MODEL_NOT_READY")

    def test_missing_history_or_a_gap_returns_503(self):
        history = self.service.history
        item_rows = history.index[history.item_id.eq(REQUEST["item_id"])]
        for invalid in [history.drop(item_rows[:-5]), history.drop(item_rows[10])]:
            with patch.object(self.service, "history", invalid):
                response = self.client.post("/predict", json=REQUEST)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()["error_code"], "FORECAST_DATA_NOT_READY")

    def test_incomplete_future_calendar_returns_503(self):
        with patch.object(self.service, "calendar", self.service.calendar.iloc[1:]):
            response = self.client.post("/predict", json=REQUEST)
            self.assertEqual(response.status_code, 503, response.text)

    def test_invalid_model_output_is_not_returned(self):
        original = self.client.post("/predict", json=REQUEST).json()
        for value in [float("nan"), float("inf"), -1]:
            invalid = {**original, "forecast": [dict(day) for day in original["forecast"]]}
            invalid["forecast"][0]["predicted_sales"] = value
            with patch.object(self.service.engine, "predict", return_value=invalid):
                response = self.client.post("/predict", json=REQUEST)
                self.assertEqual(response.status_code, 503)
        with patch.object(self.service.engine, "predict", return_value={**original, "forecast": original["forecast"][:-1]}):
            self.assertEqual(self.client.post("/predict", json=REQUEST).status_code, 503)

    def test_cors_and_swagger_remain_available(self):
        response = self.client.options("/predict", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertIn("/predict", self.client.get("/openapi.json").json()["paths"])


class StartupErrorTests(unittest.TestCase):
    def assert_unavailable(self, bundle):
        with patch.dict("os.environ", {"MODEL_BUNDLE_DIR": str(bundle)}):
            with self.assertLogs("app.main", level="ERROR"):
                with TestClient(app) as client:
                    self.assertFalse(client.get("/health").json()["model_loaded"])
                    response = client.post("/predict", json=REQUEST)
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json()["error_code"], "MODEL_NOT_READY")

    def test_missing_bundle_keeps_health_available(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_unavailable(Path(folder) / "missing")

    def test_corrupted_artifact_fails_checksum_before_serving(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle = Path(folder) / "bundle"
            shutil.copytree(BUNDLE, bundle)
            path = bundle / "feature_order.json"
            path.write_bytes(path.read_bytes() + b" ")
            self.assert_unavailable(bundle)

    def test_mismatched_metadata_is_not_reported_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle = Path(folder) / "bundle"
            shutil.copytree(BUNDLE, bundle)
            path = bundle / "model_info.json"
            info = json.loads(path.read_text(encoding="utf-8"))
            info["model_version"] = "wrong-version"
            path.write_text(json.dumps(info), encoding="utf-8")
            self.assert_unavailable(bundle)


if __name__ == "__main__":
    unittest.main()
