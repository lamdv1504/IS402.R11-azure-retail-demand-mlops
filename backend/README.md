# Retail Demand Forecast API (L02 / L03)

From the repository root, use a dedicated environment and start the service:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

If `.venv-ml` already exists, reuse it. From `backend/`, the equivalent command is
`..\.venv-ml\Scripts\python.exe -m uvicorn app.main:app --reload`.
Open http://localhost:8000/docs for Swagger.

`/health` reports API and model readiness. `/items` reads the 300 MVP item IDs
from `reports/Hung/m5_mvp_items.csv`. `/predict` loads and uses the real HI05
model, observed history and future calendar from `artifacts/hi05/`. `/model-info`
returns that model's validated metadata and measured validation metrics.
The additional `/dashboard` endpoint requires the local processed Parquet file;
inference only needs the smaller context already included in the HI05 bundle.

Model loading happens once per server worker during startup. Missing/corrupted
artifacts or invalid serving context leave the model unavailable: health still
returns 200 with `model_loaded: false`, while prediction/model-info return 503.
The underlying error is logged on the server. After fixing the files, restart
the backend. `MODEL_BUNDLE_DIR` optionally selects another compatible HI05 bundle;
relative paths are resolved from the repository root.

Install `backend/requirements-dev.txt` and run the HTTP tests from the root:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv-ml\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
```

Set `FRONTEND_ORIGINS` to a comma-separated list of browser origins if the frontend uses a different host or port. See [the GĐ2 local guide](../docs/Lam/gd2_run_local.md) for both services.

See [L03 setup, errors and the inference contract](../docs/Lam/l03_run_local.md).
