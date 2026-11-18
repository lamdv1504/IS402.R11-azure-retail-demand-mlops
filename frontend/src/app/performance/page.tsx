"use client";

import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { formatNumber, getModelInfo } from "@/lib/api";
import { useApiResource } from "@/lib/useApiResource";
import { dataCard, eyebrow, headingTitle, intro, metricCard, metricGrid } from "@/lib/ui";

export default function PerformancePage() {
  const { data, error, retry } = useApiResource(getModelInfo);
  return <AppShell><section className={intro}><PageTitle eyebrow="Đánh giá / Validation" title="Hiệu suất mô hình trên tập MVP." description="RMSSE và WRMSSE áp dụng cho 300 sản phẩm CA_1, không đại diện điểm toàn bộ cuộc thi M5."/></section>
    {error ? <StatePanel title="Chưa có kết quả đánh giá" message={error} tone="warning" onRetry={retry}/> : !data ? <StatePanel title="Đang tải chỉ số" message="Đang kiểm tra model và dữ liệu validation."/> : data.status !== "ready" ? <StatePanel title="Chưa có kết quả đánh giá" message={`Trạng thái mô hình: ${data.status}.`} onRetry={retry}/> : <><p className="mb-4 text-sm break-words text-muted">Mô hình {data.model_version} · {data.temporal_split.validation_period}</p><section className={metricGrid}>{[["Subset RMSSE", data.metrics?.validation_subset_rmsse], ["Subset WRMSSE", data.metrics?.validation_subset_wrmsse], ["MAE", data.metrics?.validation_mae], ["RMSE", data.metrics?.validation_rmse]].map(([label, value]) => <div className={metricCard} key={label}><span className="text-sm font-semibold text-muted">{label}</span><strong className="mt-2 text-3xl font-extrabold">{typeof value === "number" && Number.isFinite(value) ? formatNumber(value) : "—"}</strong><small className="mt-1 text-[13px] text-muted">Validation · CA_1 subset</small></div>)}</section><p className="text-base leading-relaxed text-muted">{data.metrics?.metric_scope_note}</p></>}
    <section className={`${dataCard} min-h-44`}><p className={`${eyebrow} mb-2`}>Đối chiếu</p><h2 className={headingTitle}>Actual vs Predicted</h2><p className="mt-4 max-w-[650px] text-base leading-[1.7] text-muted">Chưa có dữ liệu đối chiếu theo ngày trên ứng dụng. Các chỉ số bên trên thể hiện chất lượng mô hình trên tập validation.</p></section>
  </AppShell>;
}
