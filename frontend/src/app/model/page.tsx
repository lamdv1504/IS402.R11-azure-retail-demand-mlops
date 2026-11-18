"use client";

import { useEffect, useState } from "react";
import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { getModelInfo, type ModelInfo } from "@/lib/api";
import { dataCard, intro, pill } from "@/lib/ui";

export default function ModelPage() {
  const [data, setData] = useState<ModelInfo | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getModelInfo().then(setData).catch(e => setError(e.message)); }, []);
  const rows = data ? [["Tên mô hình", data.model_name], ["Phiên bản", data.model_version], ["Thuật toán", data.algorithm], ["Ngày huấn luyện", data.training_date], ["Phiên bản dữ liệu", data.data_version], ["Cửa hàng", data.store_scope?.join(", ")], ["Số sản phẩm", String(data.item_count)], ["Horizon", `${data.forecast_horizon} ngày`]] : [];
  return <AppShell><section className={intro}><PageTitle eyebrow="Model / Metadata" title="Thông tin mô hình đang phục vụ." description="Xem phiên bản, thuật toán, dữ liệu huấn luyện và trạng thái của model dự báo."/></section>
    {error ? <StatePanel title="Model chưa sẵn sàng" message={error} tone="warning"/> : !data ? <StatePanel title="Đang tải thông tin" message="Đang kiểm tra model hiện hành."/> : <section className={dataCard}><span className={pill}>{data.status}</span><div className="mt-5 grid grid-cols-2 gap-x-[30px] max-sm:grid-cols-1">{rows.map(([label, value]) => <div className="flex flex-col gap-2 border-t border-line py-[18px]" key={label}><span className="text-sm text-muted">{label}</span><strong className="text-base text-forest">{value || "Chưa có thông tin"}</strong></div>)}</div></section>}
  </AppShell>;
}
