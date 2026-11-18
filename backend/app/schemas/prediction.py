from datetime import date

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    store_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    horizon: int = Field(default=28, ge=1, le=28)


class DailyForecast(BaseModel):
    date: date
    day_of_week: str
    predicted_sales: float = Field(ge=0)


class PredictionResponse(BaseModel):
    store_id: str
    item_id: str
    dept_id: str
    cat_id: str
    state_id: str
    model_version: str
    data_version: str
    forecast_start_date: date
    horizon: int
    total_predicted_sales: float
    forecast: list[DailyForecast]
