from datetime import date, timedelta
import math

from pydantic import BaseModel, Field, model_validator


class PredictionRequest(BaseModel):
    store_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    horizon: int = Field(default=28, ge=1, le=28, strict=True)


class DailyForecast(BaseModel):
    date: date
    day_of_week: str
    predicted_sales: float = Field(ge=0, allow_inf_nan=False)


class PredictionResponse(BaseModel):
    store_id: str
    item_id: str
    dept_id: str
    cat_id: str
    state_id: str
    model_version: str
    data_version: str
    forecast_start_date: date
    horizon: int = Field(ge=1, le=28)
    total_predicted_sales: float = Field(ge=0, allow_inf_nan=False)
    forecast: list[DailyForecast]

    @model_validator(mode="after")
    def validate_forecast(self):
        if len(self.forecast) != self.horizon:
            raise ValueError("Forecast length must match horizon.")
        expected = [self.forecast_start_date + timedelta(days=offset) for offset in range(self.horizon)]
        if [day.date for day in self.forecast] != expected:
            raise ValueError("Forecast dates must be consecutive from forecast_start_date.")
        total = round(sum(day.predicted_sales for day in self.forecast), 2)
        if not math.isclose(self.total_predicted_sales, total, rel_tol=0, abs_tol=1e-6):
            raise ValueError("Total must equal the sum of the displayed daily forecasts.")
        return self
