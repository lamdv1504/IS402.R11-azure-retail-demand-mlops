# Retail Demand Forecast API (L02)

From `backend/`, install dependencies with `python -m pip install -r requirements.txt` and start the service with `python -m uvicorn app.main:app --reload`. Open http://localhost:8000/docs for Swagger.

`/health` reports API and model status. `/items` reads the 300 MVP item IDs from `reports/Hung/m5_mvp_items.csv`. The additional `/dashboard` endpoint aggregates actual daily unit sales from the local processed Parquet file. `/predict` validates the request and returns 503 until HI05 provides a real model; `/model-info` also returns 503 until metadata is available. No OpenAPI example values are served as results.

Set `FRONTEND_ORIGINS` to a comma-separated list of browser origins if the frontend uses a different host or port. See [the GĐ2 local guide](../docs/Lam/gd2_run_local.md) for both services.
