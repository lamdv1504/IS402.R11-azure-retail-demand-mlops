"use client";

import Link from "next/link";
import { Activity, CalendarRange, Cpu, Package, RefreshCw, Server } from "lucide-react";
import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { formatNumber, getHealth, getModelInfo } from "@/lib/api";
import { useApiResource } from "@/lib/useApiResource";
import { action, dataCard, eyebrow, fact, heading, headingTitle, intro, metricCard, metricGrid, pill } from "@/lib/ui";

export default function DashboardPage() {
  const { data: health, error: healthError, retry: retryHealth } = useApiResource(getHealth);
  const { data: model, error: modelError, retry: retryModel } = useApiResource(getModelInfo);
  const checking = (!health && !healthError) || (!model && !modelError);
  const modelReady = health?.status === "healthy" && health.model_loaded && model?.status === "ready";
  const apiStatus = health ? health.status === "healthy" ? "Hoạt động" : "Cần kiểm tra" : healthError ? "Chưa kết nối" : "Đang kiểm tra";
  const modelStatus = modelReady ? "Sẵn sàng" : modelError || healthError ? "Chưa kết nối" : checking ? "Đang kiểm tra" : "Chưa sẵn sàng";
  const checkedAt = health?.timestamp ? new Date(health.timestamp) : null;
  const checkedLabel = checkedAt && Number.isFinite(checkedAt.getTime())
    ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "medium", timeZone: "Asia/Ho_Chi_Minh" }).format(checkedAt)
    : "Chưa có thông tin";
  const healthRows = health ? [
    ["Dịch vụ", health.service], ["Phiên bản API", health.version],
    ["Trạng thái phản hồi", health.status], ["Lần kiểm tra (GMT+7)", checkedLabel],
  ] : [];
  const modelRows = model ? [
    ["Tên mô hình", model.model_name], ["Phiên bản mô hình", model.model_version],
    ["Thuật toán", model.algorithm], ["Phiên bản dữ liệu", model.data_version],
    ["Cửa hàng", model.store_scope?.join(", ")], ["Trạng thái mô hình", model.status],
  ] : [];

  function refresh() {
    retryHealth();
    retryModel();
  }

  return <AppShell>
    <section className={`${intro} pt-[84px] max-sm:pt-14 md:grid-cols-[minmax(0,1fr)_auto]`}>
      <PageTitle eyebrow="Tổng quan / Hệ thống" title="Trạng thái hệ thống và mô hình." description="Theo dõi kết nối dịch vụ, mô hình đang phục vụ và chất lượng dự báo từ API hiện hành."/>
      <Link className={`${action} self-center max-sm:mt-6`} href="/forecast"><CalendarRange size={19} aria-hidden="true"/>Xem dự báo</Link>
      <div className={fact}><Activity size={19} aria-hidden="true"/><span>Thông tin lấy trực tiếp từ dịch vụ dự báo</span></div>
    </section>
    <section className={metricGrid} aria-label="Trạng thái hệ thống và phạm vi mô hình" aria-live="polite">
      <div className={metricCard}><Server size={20} className="mb-4 text-[#198e5a]" aria-hidden="true"/><span className="text-sm font-semibold text-muted">Dịch vụ API</span><strong className="mt-1 text-2xl leading-snug font-extrabold tracking-tight text-balance">{apiStatus}</strong><span className="mt-1 text-sm text-muted">{health?.version ? `Phiên bản ${health.version}` : "Kiểm tra kết nối dịch vụ"}</span></div>
      <div className={metricCard}><Cpu size={20} className="mb-4 text-[#198e5a]" aria-hidden="true"/><span className="text-sm font-semibold text-muted">Mô hình dự báo</span><strong className="mt-1 text-2xl leading-snug font-extrabold tracking-tight text-balance">{modelStatus}</strong><span className="mt-1 text-sm break-words text-muted">{model?.algorithm || "Đang kiểm tra mô hình"}</span></div>
      <div className={metricCard}><Package size={20} className="mb-4 text-[#198e5a]" aria-hidden="true"/><span className="text-sm font-semibold text-muted">Sản phẩm trong MVP</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">{model ? formatNumber(model.item_count) : "—"}</strong><span className="mt-1 text-sm break-words text-muted">{model?.store_scope?.join(", ") || "Chưa có thông tin phạm vi"}</span></div>
      <div className={metricCard}><CalendarRange size={20} className="mb-4 text-[#198e5a]" aria-hidden="true"/><span className="text-sm font-semibold text-muted">Kỳ dự báo tối đa</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">{model ? `${model.forecast_horizon} ngày` : "—"}</strong><span className="mt-1 text-sm text-muted">Theo cấu hình mô hình</span></div>
    </section>

    <section className={dataCard} aria-label="Kết nối dịch vụ" aria-busy={!health && !healthError}>
      <div className={heading}>
        <div><p className={`${eyebrow} mb-2`}>Kết nối trực tiếp</p><h2 className={headingTitle}>Trạng thái dịch vụ</h2></div>
        <button type="button" onClick={refresh} disabled={checking} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-ground px-4 text-sm font-bold text-forest transition hover:bg-[#e4f8e9] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest disabled:cursor-wait disabled:opacity-60 max-sm:mt-4"><RefreshCw size={16} aria-hidden="true"/>{checking ? "Đang kiểm tra…" : "Làm mới trạng thái"}</button>
      </div>
      {healthError ? <StatePanel title="Chưa kết nối được dịch vụ" message={healthError} tone="warning" onRetry={retryHealth}/>
        : !health ? <StatePanel title="Đang kiểm tra kết nối" message="Đang lấy trạng thái mới nhất từ API."/>
        : <MetadataRows rows={healthRows}/>}
      {health && health.status !== "healthy" && <StatePanel title="Dịch vụ cần kiểm tra" message={`API đang phản hồi trạng thái ${health.status}. Vui lòng thử lại sau.`} tone="warning" onRetry={retryHealth}/>}
      {health && !health.model_loaded && <StatePanel title="Mô hình chưa được nạp" message="API đã phản hồi nhưng mô hình dự báo chưa sẵn sàng. Vui lòng thử lại sau." tone="warning" onRetry={refresh}/>}
    </section>

    <section className={dataCard} aria-label="Mô hình hiện hành" aria-busy={!model && !modelError}>
      <div className={heading}><div><p className={`${eyebrow} mb-2`}>Mô hình hiện hành</p><h2 className={headingTitle}>Thông tin đang phục vụ</h2></div>{model && <span className={pill}>{model.status}</span>}</div>
      {modelError ? <StatePanel title="Chưa tải được thông tin mô hình" message={modelError} tone="warning" onRetry={retryModel}/>
        : !model ? <StatePanel title="Đang tải thông tin mô hình" message="Đang lấy phiên bản, phạm vi và chỉ số đánh giá từ API."/>
        : <>
          {model.status !== "ready" && <StatePanel title="Mô hình chưa sẵn sàng" message={`Trạng thái hiện tại: ${model.status}.`} tone="warning" onRetry={retryModel}/>}
          <MetadataRows rows={modelRows}/>
        </>}
    </section>

    {model && <section className={dataCard} aria-label="Chỉ số đánh giá mô hình">
      <p className={`${eyebrow} mb-2`}>Đánh giá validation</p><h2 className={headingTitle}>Chất lượng mô hình</h2>
      <p className="mt-3 text-base text-muted">{model.temporal_split?.validation_period || "Chưa có thông tin thời gian validation"} · Phạm vi {model.store_scope?.join(", ") || "chưa được công bố"} / {formatNumber(model.item_count)} sản phẩm</p>
      <dl className="mt-5 grid grid-cols-4 gap-5 max-lg:grid-cols-2">{[["Subset RMSSE", model.metrics?.validation_subset_rmsse], ["Subset WRMSSE", model.metrics?.validation_subset_wrmsse], ["MAE (units)", model.metrics?.validation_mae], ["RMSE (units)", model.metrics?.validation_rmse]].map(([label, value]) => <div key={label} className="border-t border-line pt-4"><dt className="text-sm font-semibold text-muted">{label}</dt><dd className="mt-2 text-3xl font-extrabold text-forest">{typeof value === "number" && Number.isFinite(value) ? formatNumber(value) : "—"}</dd></div>)}</dl>
      {model.metrics?.metric_scope_note && <p className="mt-5 text-base leading-relaxed text-muted">{model.metrics.metric_scope_note}</p>}
    </section>}
  </AppShell>;
}

function MetadataRows({ rows }: { rows: (string | undefined)[][] }) {
  return <dl className="grid grid-cols-2 gap-x-8 max-sm:grid-cols-1">{rows.map(([label, value]) => <div className="min-w-0 border-t border-line py-4" key={label}><dt className="text-sm text-muted">{label}</dt><dd className="mt-2 text-base font-bold break-words text-forest [overflow-wrap:anywhere]">{value || "Chưa có thông tin"}</dd></div>)}</dl>;
}
