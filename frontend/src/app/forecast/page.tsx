"use client";

import { ArrowUpRight, CalendarRange, ChevronDown } from "lucide-react";
import { useMemo, useRef, useState, type FormEvent } from "react";
import { AppShell, PageTitle, StatePanel } from "@/components/AppShell";
import { SalesChart } from "@/components/SalesChart";
import { formatDate, formatNumber, formatWeekday, getCatalog, type Prediction } from "@/lib/api";
import { useApiResource } from "@/lib/useApiResource";
import { predictDemand } from "@/services/predictionService";
import { action, dataCard, eyebrow, fact, heading, headingTitle, intro, pill } from "@/lib/ui";

const field = "flex min-w-0 flex-col gap-2 text-base font-bold text-forest";
const select = "h-[49px] w-full min-w-0 appearance-none rounded-[10px] border border-[#d6e4db] bg-white pr-9 pl-3.5 text-base text-forest focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest disabled:bg-[#f3f7f4] disabled:text-[#435b4b]";
const selectWrap = "relative [&>svg]:pointer-events-none [&>svg]:absolute [&>svg]:top-4 [&>svg]:right-3 [&>svg]:text-[#6b8679]";

export default function ForecastPage() {
  const { data: catalog, error: catalogError, retry: retryCatalog } = useApiResource(getCatalog);
  const [category, setCategory] = useState("all");
  const [item, setItem] = useState("");
  const [horizon, setHorizon] = useState("28");
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const inScope = catalog?.store_id === "CA_1";
  const items = useMemo(() => catalog?.items.filter(row => category === "all" || row.cat_id === category) || [], [catalog, category]);
  const validHorizon = horizon !== "" && Number.isInteger(Number(horizon)) && Number(horizon) >= 1 && Number(horizon) <= 28;
  const canPredict = inScope && items.some(row => row.item_id === item) && validHorizon;

  function clearResult() {
    setResult(null);
    setError("");
  }

  async function requestForecast() {
    if (pending.current || !canPredict || !catalog) return;
    pending.current = true;
    setBusy(true);
    clearResult();
    try {
      setResult(await predictDemand(catalog.store_id, item, Number(horizon)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể lấy dự báo.");
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void requestForecast();
  }

  return <AppShell>
    <section className={intro}>
      <PageTitle eyebrow="Dự báo / CA_1" title="Dự báo lượng bán của từng sản phẩm." description="Chọn mã sản phẩm trong danh sách MVP. Chu kỳ mặc định 28 ngày, có thể chọn từ 1 đến 28 ngày."/>
      <div className={fact}><CalendarRange size={19}/><span>Đơn vị kết quả: số sản phẩm bán dự kiến mỗi ngày</span></div>
    </section>
    <section className={`${dataCard} mt-0`} aria-busy={busy}>
      <div className={heading}>
        <div><p className={`${eyebrow} mb-2`}>Thiết lập dự báo</p><h2 className={headingTitle}>Chọn chuỗi sản phẩm</h2></div>
        <span className={pill}>CA_1 · 300 sản phẩm MVP</span>
      </div>
      <form className="grid grid-cols-4 items-end gap-4 max-lg:grid-cols-2 max-sm:grid-cols-1" onSubmit={submit}>
        <label className={field}>Cửa hàng<span className={selectWrap}><select className={select} value={inScope ? catalog.store_id : ""} disabled={!inScope || busy} onChange={clearResult} required><option value="" disabled>Chọn cửa hàng</option>{inScope && <option value={catalog.store_id}>{catalog.store_id}</option>}</select><ChevronDown size={17}/></span></label>
        <label className={field}>Nhóm hàng<span className={selectWrap}><select className={select} value={category} disabled={!inScope || busy} onChange={event => { setCategory(event.target.value); setItem(""); clearResult(); }}><option value="all">Tất cả nhóm hàng</option>{Object.keys(catalog?.categories_breakdown || {}).map(value => <option key={value} value={value}>{value}</option>)}</select><ChevronDown size={17}/></span></label>
        <label className={field}>Sản phẩm<span className={selectWrap}><select className={select} value={item} required disabled={!inScope || busy} onChange={event => { setItem(event.target.value); clearResult(); }}><option value="">Chọn mã sản phẩm</option>{items.map(row => <option key={row.item_id} value={row.item_id}>{row.item_id}</option>)}</select><ChevronDown size={17}/></span></label>
        <label className={field}>Số ngày dự báo<input className={select} type="number" min={1} max={28} step={1} value={horizon} required disabled={busy} aria-describedby="horizon-help" onChange={event => { setHorizon(event.target.value); clearResult(); }}/></label>
        <button className={`${action} h-[49px] min-h-[49px] border-0 max-sm:w-full`} disabled={!canPredict || busy}>{busy ? "Đang xử lý…" : "Xem dự báo"}<ArrowUpRight size={19}/></button>
      </form>
      <p id="horizon-help" className="mt-4 text-sm text-muted">Số ngày là số nguyên từ 1 đến 28. Mỗi kết quả gắn với đúng cửa hàng và sản phẩm đã chọn.</p>
      {catalogError ? <StatePanel title="Không tải được danh sách sản phẩm" message={catalogError} tone="warning" onRetry={retryCatalog}/> : !catalog ? <StatePanel title="Đang tải danh sách sản phẩm" message="Đang lấy các sản phẩm trong phạm vi MVP."/> : !inScope ? <StatePanel title="Danh mục ngoài phạm vi MVP" message="Giao diện hiện hỗ trợ cửa hàng CA_1. Vui lòng kiểm tra lại danh mục từ API." tone="warning" onRetry={retryCatalog}/> : <p className="mt-3 text-sm text-muted">{items.length} / {catalog.total_items} sản phẩm tại {catalog.store_id} theo nhóm hàng đã chọn.</p>}
      {inScope && items.length === 0 && <StatePanel title="Chưa có sản phẩm" message="Nhóm hàng này chưa có sản phẩm trong danh mục MVP."/>}
    </section>
    {busy ? <StatePanel title="Đang tạo dự báo" message={`Đang tính lượng bán trong ${horizon} ngày cho ${item}.`}/> : error ? <StatePanel title="Chưa có kết quả dự báo" message={error} tone="warning" onRetry={() => void requestForecast()}/> : !result ? <StatePanel title="Kết quả dự báo sẽ hiện ở đây" message="Chọn sản phẩm và nhấn Xem dự báo. Bảng và biểu đồ sẽ hiển thị sau khi có kết quả từ mô hình."/> : <section className={dataCard} aria-label="Kết quả dự báo">
      <div className={heading}>
        <div className="min-w-0"><p className={`${eyebrow} mb-2`}>Kết quả từ mô hình</p><h2 className={`${headingTitle} break-words`}>{result.item_id} · {result.horizon} ngày</h2></div>
        <span className={`${pill} [overflow-wrap:anywhere]`}>{result.model_version}</span>
      </div>
      <p className="mb-5 text-base leading-relaxed break-words text-muted">{result.store_id} · {formatDate(result.forecast_start_date)} — {formatDate(result.forecast.at(-1)!.date)} · Tổng {formatNumber(result.total_predicted_sales)} units · Dữ liệu {result.data_version}</p>
      <SalesChart data={result.forecast} field="predicted_sales"/>
      <div className="mt-5 max-h-[350px] overflow-auto rounded-xl border border-line" role="region" aria-label="Bảng dự báo theo ngày" tabIndex={0}>
        <table className="w-full border-collapse text-base [&_td]:border-b [&_td]:border-line [&_td]:px-[18px] [&_td]:py-[13px] [&_th]:sticky [&_th]:top-0 [&_th]:bg-ground [&_th]:px-[18px] [&_th]:py-[13px] [&_th]:text-left [&_th]:text-sm [&_th]:text-muted">
          <caption className="sr-only">Dự báo {result.horizon} ngày cho {result.item_id}, đơn vị sản phẩm (units)</caption>
          <thead><tr><th scope="col">Ngày</th><th scope="col">Thứ</th><th scope="col">Lượng bán dự kiến (units)</th></tr></thead>
          <tbody>{result.forecast.map(row => <tr key={row.date}><td className="whitespace-nowrap">{formatDate(row.date)}</td><td className="whitespace-nowrap">{formatWeekday(row.date)}</td><td className="tabular-nums">{formatNumber(row.predicted_sales)}</td></tr>)}</tbody>
        </table>
      </div>
    </section>}
  </AppShell>;
}
