export function resolveApiUrl(value = process.env.NEXT_PUBLIC_API_URL): string {
  const source = value?.trim() || "http://127.0.0.1:8000";
  try {
    const url = new URL(source);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error();
    return url.href.replace(/\/+$/, "");
  } catch {
    throw new Error("Cấu hình NEXT_PUBLIC_API_URL phải là URL HTTP hoặc HTTPS, không chứa thông tin đăng nhập hay query string.");
  }
}

export type Item = { item_id: string; dept_id: string; cat_id: string };
export type Catalog = { store_id: string; total_items: number; categories_breakdown: Record<string, number>; items: Item[] };
export type ForecastDay = { date: string; day_of_week: string; predicted_sales: number };
export type Prediction = { store_id: string; item_id: string; model_version: string; data_version: string; forecast_start_date: string; horizon: number; total_predicted_sales: number; forecast: ForecastDay[] };
export type ModelInfo = { model_name: string; model_version: string; algorithm: string; status: string; training_date: string; data_version: string; store_scope: string[]; item_count: number; forecast_horizon: number; features_used: string[]; temporal_split: Record<string, string>; metrics: { validation_subset_rmsse: number; validation_subset_wrmsse: number; validation_mae: number; validation_rmse: number; metric_scope_note: string } };
export type Health = { status: string; model_loaded: boolean; service?: string; version?: string; timestamp?: string };

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const baseUrl = resolveApiUrl();
    if (typeof window !== "undefined" && window.location.protocol === "https:" && baseUrl.startsWith("http:")) {
      throw new Error("Dịch vụ dự báo đang dùng HTTP. Hãy mở giao diện qua HTTP khi thử ACI hoặc cấu hình API HTTPS cho website HTTPS.");
    }
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
      signal: controller.signal,
    });
    const body: unknown = await response.json().catch(error => {
      if (controller.signal.aborted) throw error;
      return null;
    });
    if (!response.ok) {
      const fallback: Record<number, string> = {
        400: "Thông tin yêu cầu không hợp lệ.",
        404: "Không tìm thấy cửa hàng hoặc sản phẩm trong phạm vi MVP.",
        422: "Kiểm tra cửa hàng, sản phẩm và số ngày nguyên từ 1 đến 28.",
        503: "Mô hình hoặc dữ liệu chưa sẵn sàng. Vui lòng thử lại sau.",
      };
      const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
      throw new Error(typeof detail === "string" ? detail : fallback[response.status] || `API trả lỗi ${response.status}.`);
    }
    if (body === null || typeof body !== "object") throw new Error("API trả dữ liệu JSON không hợp lệ. Vui lòng thử lại hoặc kiểm tra dịch vụ dự báo.");
    return body as T;
  } catch (error) {
    if (controller.signal.aborted || (error instanceof DOMException && error.name === "AbortError")) throw new Error("API phản hồi quá chậm. Vui lòng thử lại.");
    if (error instanceof TypeError) throw new Error("Không kết nối được API. Hãy kiểm tra mạng, trạng thái dịch vụ dự báo và cấu hình CORS.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const getHealth = () => api<Health>("/health");
export const getCatalog = () => api<Catalog>("/items");
export const getModelInfo = () => api<ModelInfo>("/model-info");
export const formatNumber = (value: number) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(value);
export const formatDate = (value: string) => new Intl.DateTimeFormat("vi-VN", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
export const formatWeekday = (value: string) => new Intl.DateTimeFormat("vi-VN", { weekday: "long", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
