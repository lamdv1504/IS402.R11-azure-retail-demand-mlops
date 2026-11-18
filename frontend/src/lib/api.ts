const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type Item = { item_id: string; dept_id: string; cat_id: string };
export type Catalog = { store_id: string; total_items: number; categories_breakdown: Record<string, number>; items: Item[] };
export type DaySales = { date: string; sales: number };
export type DashboardData = { store_id: string; item_count: number; total_units_sold: number; average_units_per_day: number; start_date: string; end_date: string; daily_sales: DaySales[] };
export type ForecastDay = { date: string; day_of_week: string; predicted_sales: number };
export type Prediction = { store_id: string; item_id: string; model_version: string; data_version: string; forecast_start_date: string; horizon: number; total_predicted_sales: number; forecast: ForecastDay[] };
export type ModelInfo = { model_name: string; model_version: string; algorithm: string; status: string; training_date: string; data_version: string; store_scope: string[]; item_count: number; forecast_horizon: number; features_used: string[]; temporal_split: Record<string, string>; metrics: { validation_subset_rmsse: number; validation_subset_wrmsse: number; validation_mae: number; validation_rmse: number; metric_scope_note: string } };
export type Health = { status: string; model_loaded: boolean };

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
      signal: controller.signal,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `API trả lỗi ${response.status}.`);
    return body as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw new Error("API phản hồi quá chậm. Vui lòng thử lại.");
    if (error instanceof TypeError) throw new Error("Không kết nối được API. Hãy kiểm tra backend tại cổng 8000.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const getHealth = () => api<Health>("/health");
export const getCatalog = () => api<Catalog>("/items");
export const getDashboard = () => api<DashboardData>("/dashboard");
export const getModelInfo = () => api<ModelInfo>("/model-info");
export const predictDemand = (store_id: string, item_id: string, horizon: number) =>
  api<Prediction>("/predict", { method: "POST", body: JSON.stringify({ store_id, item_id, horizon }) });

export const formatNumber = (value: number) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(value);
export const formatDate = (value: string) => new Intl.DateTimeFormat("vi-VN", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
