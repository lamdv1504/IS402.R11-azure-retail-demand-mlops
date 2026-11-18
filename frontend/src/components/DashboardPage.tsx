"use client";

import Link from "next/link";
import { ArrowUpRight, CalendarDays, Layers3, Package, Store } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { SalesChart } from "@/components/SalesChart";
import { formatDate, formatNumber, getDashboard, type DashboardData } from "@/lib/api";
import { action, dataCard, eyebrow, fact, heading, headingTitle, intro, metricCard, metricGrid, pill } from "@/lib/ui";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getDashboard().then(setData).catch(e => setError(e.message)); }, []);
  return <AppShell>
    <section className={`${intro} pt-[84px] max-sm:pt-14 md:grid-cols-[minmax(0,1fr)_auto]`}>
      <PageTitle eyebrow="Tổng quan / CA_1" title="Dự báo nhu cầu bán lẻ tại CA_1." description="Theo dõi lượng bán của 300 sản phẩm M5 và xem nhu cầu 28 ngày tới khi model sẵn sàng."/>
      <Link className={`${action} self-center max-sm:mt-6`} href="/forecast">Xem dự báo <ArrowUpRight size={19}/></Link>
      <div className={fact}><span className="grid size-7 place-items-center rounded-full bg-[#dcf8e6]"><Layers3 size={19}/></span><span>3 nhóm hàng · 300 chuỗi sản phẩm–cửa hàng</span></div>
    </section>
    {error ? <StatePanel title="Chưa có dữ liệu bán hàng" message={error} tone="warning"/> : !data ? <StatePanel title="Đang tải dữ liệu M5" message="Đang đọc bảng bán hàng đã xử lý."/> : <>
      <section className={metricGrid} aria-label="Chỉ số tổng quan">
        <div className={metricCard}><Store size={20} className="mb-4 text-[#198e5a]"/><span className="text-sm font-semibold text-muted">Cửa hàng</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">01</strong><small className="text-[13px] text-muted">{data.store_id}</small></div>
        <div className={metricCard}><Package size={20} className="mb-4 text-[#198e5a]"/><span className="text-sm font-semibold text-muted">Sản phẩm trong MVP</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">{formatNumber(data.item_count)}</strong><small className="text-[13px] text-muted">FOODS · HOBBIES · HOUSEHOLD</small></div>
        <div className={metricCard}><Layers3 size={20} className="mb-4 text-[#198e5a]"/><span className="text-sm font-semibold text-muted">Tổng lượng bán</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">{formatNumber(data.total_units_sold)}</strong><small className="text-[13px] text-muted">đơn vị sản phẩm</small></div>
        <div className={metricCard}><CalendarDays size={20} className="mb-4 text-[#198e5a]"/><span className="text-sm font-semibold text-muted">Trung bình mỗi ngày</span><strong className="mt-1 text-3xl font-extrabold tracking-tight">{formatNumber(data.average_units_per_day)}</strong><small className="text-[13px] text-muted">units / ngày</small></div>
      </section>
      <section className={dataCard}><div className={heading}><div><p className={`${eyebrow} mb-2`}>Lịch sử bán hàng</p><h2 className={headingTitle}>Lượng bán theo ngày</h2></div><span className={pill}>{formatDate(data.start_date)} — {formatDate(data.end_date)}</span></div><SalesChart data={data.daily_sales} field="sales"/><p className="mt-3.5 text-[13px] text-muted">Nguồn: dữ liệu M5 đã xử lý · đơn vị: sản phẩm bán ra</p></section>
    </>}
  </AppShell>;
}
