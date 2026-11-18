import { api, type Prediction } from "../lib/api";

export type PredictionRequest = { store_id: string; item_id: string; horizon: number };

const DAY_MS = 86_400_000;

function parseDate(value: unknown): number {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return NaN;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? timestamp : NaN;
}

// Validate before either the table or chart consumes a response.
export function validatePrediction(value: unknown, request: PredictionRequest): Prediction {
  const result = value as Prediction | null;
  if (!result || result.store_id !== request.store_id || result.item_id !== request.item_id || result.horizon !== request.horizon) {
    throw new Error("Kết quả API không khớp cửa hàng, sản phẩm hoặc số ngày đã chọn.");
  }
  const start = parseDate(result.forecast_start_date);
  if (!Number.isFinite(start) || !Array.isArray(result.forecast) || result.forecast.length !== request.horizon || result.forecast.some((day, index) => (
    !day || parseDate(day.date) !== start + index * DAY_MS || !Number.isFinite(day.predicted_sales) || day.predicted_sales < 0
  ))) {
    throw new Error("API trả ngày dự báo hoặc lượng bán không hợp lệ. Các ngày phải liên tiếp và lượng bán không âm.");
  }
  const total = result.forecast.reduce((sum, day) => sum + day.predicted_sales, 0);
  if (!Number.isFinite(result.total_predicted_sales) || result.total_predicted_sales < 0 || Math.abs(total - result.total_predicted_sales) > 0.011) {
    throw new Error("Tổng lượng bán từ API không khớp bảng dự báo theo ngày.");
  }
  if (typeof result.model_version !== "string" || !result.model_version.trim() || typeof result.data_version !== "string" || !result.data_version.trim()) {
    throw new Error("API chưa cung cấp phiên bản mô hình hoặc dữ liệu cho kết quả này.");
  }
  return result;
}

export async function predictDemand(store_id: string, item_id: string, horizon: number): Promise<Prediction> {
  if (!store_id || !item_id || !Number.isInteger(horizon) || horizon < 1 || horizon > 28) {
    throw new Error("Chọn cửa hàng, sản phẩm và số ngày nguyên từ 1 đến 28.");
  }
  const request = { store_id, item_id, horizon };
  const result = await api<unknown>("/predict", { method: "POST", body: JSON.stringify(request) });
  return validatePrediction(result, request);
}
