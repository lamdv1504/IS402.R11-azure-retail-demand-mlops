"""Typed metadata response matching the shared API contract."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    validation_subset_rmsse: float = Field(ge=0, allow_inf_nan=False)
    validation_subset_wrmsse: float = Field(ge=0, allow_inf_nan=False)
    validation_mae: float = Field(ge=0, allow_inf_nan=False)
    validation_rmse: float = Field(ge=0, allow_inf_nan=False)
    metric_scope_note: str


class TemporalSplit(BaseModel):
    train_period: str
    validation_period: str
    holdout_period: str


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    algorithm: str
    status: Literal["ready", "training", "uninitialized"]
    training_date: datetime
    data_version: str
    store_scope: list[str]
    item_count: int = Field(gt=0)
    forecast_horizon: int = Field(ge=1, le=28)
    features_used: list[str]
    temporal_split: TemporalSplit
    metrics: ModelMetrics
