import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ITEMS_FILE, router
from app.services import predictor


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.forecast_service = None
    bundle_dir = Path(os.getenv("MODEL_BUNDLE_DIR", str(predictor.DEFAULT_BUNDLE)))
    if not bundle_dir.is_absolute():
        bundle_dir = predictor.ROOT / bundle_dir
    try:
        app.state.forecast_service = predictor.load_service(bundle_dir, ITEMS_FILE)
        logger.info("Loaded forecast model %s", app.state.forecast_service.info.model_version)
    except Exception:
        # Keep health/catalog available while inference reports a clear 503.
        logger.exception("Model or inference context could not be loaded from %s", bundle_dir)
    try:
        yield
    finally:
        app.state.forecast_service = None


app = FastAPI(title="Retail Demand Forecast API", version="0.1.0", lifespan=lifespan)
origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)
