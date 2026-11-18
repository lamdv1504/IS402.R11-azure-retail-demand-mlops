"use client";

import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { getModelInfo } from "@/lib/api";
import { useApiResource } from "@/lib/useApiResource";
import { dataCard, eyebrow, headingTitle, intro, pill } from "@/lib/ui";

export default function ModelPage() {
  const { data, error, retry } = useApiResource(getModelInfo);
  const rows = data ? [["Tên mô hình", data.model_name], ["Phiên bản", data.model_version], ["Thuật toán", data.algorithm], ["Ngày huấn luyện", data.training_date], ["Phiên bản dữ liệu", data.data_version], ["Cửa hàng", data.store_scope?.join(", ")], ["Số sản phẩm", String(data.item_count)], ["Horizon", `${data.forecast_horizon} ngày`]] : [];
  return <AppShell><section className={intro}><PageTitle eyebrow="Model / Metadata" title="Thông tin mô hình đang phục vụ." description="Xem phiên bản, thuật toán, dữ liệu huấn luyện và trạng thái của model dự báo."/></section>
    {error ? <StatePanel title="Model chưa sẵn sàng" message={error} tone="warning" onRetry={retry}/> : !data ? <StatePanel title="Đang tải thông tin" message="Đang kiểm tra model hiện hành."/> : <>
      <section className={dataCard}><h2 className={`${headingTitle} mb-4`}>Thông tin và phạm vi</h2><span className={pill}>{data.status}</span><dl className="mt-5 grid grid-cols-2 gap-x-[30px] max-sm:grid-cols-1">{rows.map(([label, value]) => <div className="flex min-w-0 flex-col gap-2 border-t border-line py-[18px]" key={label}><dt className="text-sm text-muted">{label}</dt><dd className="text-base font-bold break-words text-forest">{value || "Chưa có thông tin"}</dd></div>)}</dl></section>
      <section className={dataCard}><p className={`${eyebrow} mb-2`}>Đầu vào mô hình</p><h2 className={headingTitle}>Đặc trưng sử dụng</h2>{data.features_used.length ? <ul className="mt-5 flex flex-wrap gap-2" aria-label="Danh sách feature">{data.features_used.map(feature => <li key={feature} className={`${pill} mt-0 max-sm:mt-0`}>{feature}</li>)}</ul> : <p className="mt-4 text-muted">Chưa có thông tin đặc trưng.</p>}</section>
      <section className={dataCard}><p className={`${eyebrow} mb-2`}>Dữ liệu theo thời gian</p><h2 className={headingTitle}>Train, validation và holdout</h2><dl className="mt-5 grid grid-cols-3 gap-5 max-sm:grid-cols-1">{[["Train", data.temporal_split.train_period], ["Validation", data.temporal_split.validation_period], ["Holdout", data.temporal_split.holdout_period]].map(([label, value]) => <div key={label} className="border-t border-line pt-4"><dt className="text-sm text-muted">{label}</dt><dd className="mt-2 text-base font-bold break-words text-forest">{value || "Chưa có thông tin"}</dd></div>)}</dl></section>
    </>}
  </AppShell>;
}
