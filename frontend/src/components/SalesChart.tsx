"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDate, formatNumber } from "@/lib/api";

export function SalesChart({ data, field }: { data: { date: string; [key: string]: string | number }[]; field: "sales" | "predicted_sales" }) {
  return <div className="min-w-0"><p className="mb-2 text-sm text-muted">Lượng bán (units) · ngày/tháng</p><div className="h-[350px] w-full text-[13px] text-muted max-sm:h-[260px]" role="img" aria-label={field === "sales" ? "Biểu đồ lượng bán thực tế theo ngày, đơn vị units" : "Biểu đồ lượng bán dự báo theo ngày, đơn vị units"}>
    <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 16, right: 18, left: -14, bottom: 2 }}>
      <CartesianGrid stroke="#e7eeea" strokeDasharray="3 5" vertical={false}/>
      <XAxis dataKey="date" tickFormatter={value => String(value).slice(5).split("-").reverse().join("/")} minTickGap={32} tickLine={false} axisLine={false}/>
      <YAxis width={55} tickLine={false} axisLine={false}/>
      <Tooltip labelFormatter={value => formatDate(String(value))} formatter={value => [`${formatNumber(Number(value))} units`, "Lượng bán"]}/>
      <Area type="monotone" dataKey={field} stroke="#13945b" strokeWidth={2.5} fill="#e4f8e9" dot={false}/>
    </AreaChart></ResponsiveContainer>
  </div></div>;
}
