"use client";

import { ArrowUpRight, CalendarRange, ChevronDown } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { SalesChart } from "@/components/SalesChart";
import { formatDate, formatNumber, getCatalog, predictDemand, type Catalog, type Prediction } from "@/lib/api";
import { action, dataCard, eyebrow, fact, heading, headingTitle, intro, pill } from "@/lib/ui";

const field = "flex flex-col gap-2 text-sm font-bold text-forest";
const select = "h-[49px] w-full appearance-none rounded-[10px] border border-[#d6e4db] bg-white px-3.5 text-[15px] text-forest disabled:bg-[#f3f7f4] disabled:text-[#435b4b]";
const selectWrap = "relative [&>svg]:pointer-events-none [&>svg]:absolute [&>svg]:top-4 [&>svg]:right-3 [&>svg]:text-[#6b8679]";

export default function ForecastPage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [category, setCategory] = useState("all");
  const [item, setItem] = useState("");
  const [horizon, setHorizon] = useState(28);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { getCatalog().then(setCatalog).catch(e => setCatalogError(e.message)); }, []);
  const items = useMemo(() => catalog?.items.filter(row => category === "all" || row.cat_id === category) || [], [catalog, category]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setResult(null); setError("");
    try {
      const response = await predictDemand("CA_1", item, Number(horizon));
      if (!Array.isArray(response.forecast) || response.forecast.length !== Number(horizon) || response.forecast.some(row => !Number.isFinite(row.predicted_sales) || row.predicted_sales < 0)) throw new Error("API trả số ngày hoặc lượng bán không hợp lệ.");
      setResult(response);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể lấy dự báo."); }
    finally { setBusy(false); }
  }
  return <AppShell>
    <section className={intro}><PageTitle eyebrow="Dự báo / CA_1" title="Dự báo lượng bán của từng sản phẩm." description="Chọn mã sản phẩm trong danh sách MVP. Chu kỳ mặc định 28 ngày, có thể chọn từ 1 đến 28 ngày."/><div className={fact}><CalendarRange size={19}/><span>Đơn vị kết quả: số sản phẩm bán dự kiến mỗi ngày</span></div></section>
    <section className={`${dataCard} mt-0`}><div className={heading}><div><p className={`${eyebrow} mb-2`}>Thiết lập dự báo</p><h2 className={headingTitle}>Chọn chuỗi sản phẩm</h2></div><span className={pill}>1 cửa hàng · 300 sản phẩm</span></div>
      <form className="grid grid-cols-4 items-end gap-4 max-lg:grid-cols-2 max-sm:grid-cols-1" onSubmit={submit}>
        <label className={field}>Cửa hàng<span className={selectWrap}><select className={select} value="CA_1" disabled><option>CA_1</option></select><ChevronDown size={17}/></span></label>
        <label className={field}>Nhóm hàng<span className={selectWrap}><select className={select} value={category} onChange={event => { setCategory(event.target.value); setItem(""); setResult(null); setError(""); }}><option value="all">Tất cả nhóm hàng</option><option value="FOODS">FOODS</option><option value="HOBBIES">HOBBIES</option><option value="HOUSEHOLD">HOUSEHOLD</option></select><ChevronDown size={17}/></span></label>
        <label className={field}>Sản phẩm<span className={selectWrap}><select className={select} value={item} required disabled={!catalog} onChange={event => { setItem(event.target.value); setResult(null); setError(""); }}><option value="">Chọn mã sản phẩm</option>{items.map(row => <option key={row.item_id} value={row.item_id}>{row.item_id}</option>)}</select><ChevronDown size={17}/></span></label>
        <label className={field}>Số ngày dự báo<input className={select} type="number" min={1} max={28} value={horizon} required onChange={event => { setHorizon(Number(event.target.value)); setResult(null); setError(""); }}/></label>
        <button className={`${action} h-[49px] min-h-[49px] border-0 max-sm:w-full`} disabled={!item || busy}>{busy ? "Đang xử lý…" : "Xem dự báo"}<ArrowUpRight size={19}/></button>
      </form>
      {catalogError && <StatePanel title="Không tải được danh sách sản phẩm" message={catalogError} tone="warning"/>}
      {catalog && <p className="mt-5 text-sm text-muted">{catalog.total_items} sản phẩm hợp lệ tại {catalog.store_id}. Kết quả được lấy trực tiếp từ API khi model đã sẵn sàng.</p>}
    </section>
    {error ? <StatePanel title="Chưa có kết quả dự báo" message={error} tone="warning"/> : !result ? <StatePanel title="Kết quả dự báo sẽ hiện ở đây" message="Chọn một sản phẩm để yêu cầu dự báo. Ở GĐ2, model chưa được bàn giao nên API sẽ báo chưa sẵn sàng."/> : <section className={dataCard}><div className={heading}><div><p className={`${eyebrow} mb-2`}>Kết quả từ API</p><h2 className={headingTitle}>{result.item_id} · {result.horizon} ngày</h2></div><span className={pill}>{result.model_version}</span></div><p className="mb-5 text-[15px] leading-relaxed text-muted">Từ {formatDate(result.forecast_start_date)} · Tổng {formatNumber(result.total_predicted_sales)} units · Dữ liệu {result.data_version}</p><SalesChart data={result.forecast} field="predicted_sales"/><div className="mt-5 max-h-[350px] overflow-auto rounded-xl border border-line"><table className="w-full border-collapse text-sm [&_td]:border-b [&_td]:border-line [&_td]:px-[18px] [&_td]:py-[13px] [&_th]:sticky [&_th]:top-0 [&_th]:bg-ground [&_th]:px-[18px] [&_th]:py-[13px] [&_th]:text-left [&_th]:text-xs [&_th]:tracking-wide [&_th]:text-muted [&_th]:uppercase"><thead><tr><th>Ngày</th><th>Thứ</th><th>Lượng bán dự kiến (units)</th></tr></thead><tbody>{result.forecast.map(row => <tr key={row.date}><td>{formatDate(row.date)}</td><td>{row.day_of_week}</td><td>{formatNumber(row.predicted_sales)}</td></tr>)}</tbody></table></div></section>}
  </AppShell>;
}
