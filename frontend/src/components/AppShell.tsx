"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, ArrowUpRight, ChartNoAxesCombined, Database, Menu, X } from "lucide-react";
import { getHealth, type Health } from "@/lib/api";
import { eyebrow, state } from "@/lib/ui";

const routes = [
  { href: "/", label: "Tổng quan", icon: ChartNoAxesCombined },
  { href: "/forecast", label: "Dự báo", icon: ArrowUpRight },
  { href: "/performance", label: "Hiệu suất", icon: Activity },
  { href: "/model", label: "Mô hình", icon: Database },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [health, setHealth] = useState<Health | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { getHealth().then(setHealth).catch(() => setHealth(null)); }, []);
  return <div className="min-h-screen bg-ground font-sans text-ink antialiased">
    <a className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-6 focus:z-50 focus:rounded-lg focus:bg-forest focus:px-5 focus:py-3 focus:text-white" href="#main">Đi tới nội dung</a>
    <header className="sticky top-0 z-40 bg-ground/95 px-6 pt-5 pb-3 backdrop-blur-md max-sm:px-3 max-sm:pt-3">
      <div className="relative mx-auto flex min-h-[74px] max-w-[1480px] items-center justify-between gap-6 rounded-[20px] border border-line bg-white/95 px-7 py-3 shadow-[0_3px_0_#0d3b2e0b] max-lg:gap-3 max-lg:px-4 max-sm:min-h-16 max-sm:rounded-2xl max-sm:px-3.5 max-sm:py-2">
        <Link className="flex items-center gap-2.5 text-xl font-extrabold tracking-[-0.055em] whitespace-nowrap max-sm:text-lg" href="/" aria-label="M5 Retail - Tổng quan"><span className="grid size-[34px] -rotate-[8deg] place-items-center rounded-[11px_11px_11px_3px] bg-mint text-base text-forest">M<span className="text-[11px]">5</span></span><span>M5 <b className="text-[#0d7045]">Retail</b></span></Link>
        <button className="hidden size-11 place-items-center text-forest max-sm:grid" type="button" aria-label={menuOpen ? "Đóng menu" : "Mở menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={22}/> : <Menu size={22}/>}</button>
        <nav className={`${menuOpen ? "max-sm:flex" : "max-sm:hidden"} flex items-center gap-2 max-sm:absolute max-sm:top-[calc(100%+8px)] max-sm:right-0 max-sm:left-0 max-sm:z-20 max-sm:flex-col max-sm:items-stretch max-sm:rounded-2xl max-sm:border max-sm:border-line max-sm:bg-white max-sm:p-2.5 max-sm:shadow-xl`} aria-label="Điều hướng chính">{routes.map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={() => setMenuOpen(false)} className={`flex min-h-11 items-center gap-2 rounded-xl px-4 text-[15px] font-bold transition hover:-translate-y-px max-lg:px-2.5 max-sm:px-4 ${pathname === href ? "bg-forest text-white shadow-sm" : "text-muted hover:bg-[#edf6ef] hover:text-forest"}`} aria-current={pathname === href ? "page" : undefined}><Icon size={17} strokeWidth={2}/>{label}</Link>)}</nav>
        <div className="flex min-h-10 items-center gap-2 rounded-[10px] border border-line bg-[#f5faf6] px-3 text-[13px] font-bold whitespace-nowrap text-forest max-lg:hidden"><span className={`size-2 rounded-full ${health?.model_loaded ? "bg-mint" : "bg-[#dca34c]"}`}/>{health?.model_loaded ? "Model sẵn sàng" : health ? "Model chưa sẵn sàng" : "API chưa kết nối"}</div>
      </div>
    </header>
    <main id="main" tabIndex={-1} className="mx-auto max-w-[1424px] scroll-mt-32 px-10 pb-24 max-lg:px-7 max-sm:scroll-mt-28 max-sm:px-[18px] max-sm:pb-14">{children}</main>
    <footer className="mx-auto flex max-w-[1344px] justify-between gap-5 border-t border-line px-4 pt-6 pb-10 text-[13px] text-muted max-sm:mx-[18px] max-sm:block max-sm:px-0 max-sm:pb-8 max-sm:[&>span]:block max-sm:[&>span]:mb-1.5"><span>M5 Retail · CA_1 / 300 sản phẩm</span><span>Dữ liệu bán hàng theo đơn vị sản phẩm (units)</span></footer>
  </div>;
}

export function PageTitle({ eyebrow: label, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="max-w-[820px]"><p className={eyebrow}>{label}</p><h1 className="max-w-[820px] text-[clamp(34px,4vw,60px)] leading-[1.14] font-extrabold tracking-[-0.055em] text-balance max-sm:text-4xl">{title}</h1><p className="mt-6 max-w-[670px] text-lg leading-[1.7] text-muted max-sm:mt-4 max-sm:text-base">{description}</p></div>;
}

export function StatePanel({ title, message, tone = "normal", onRetry }: { title: string; message: string; tone?: "normal" | "warning"; onRetry?: () => void }) {
  return <div className={`${state} ${tone === "warning" ? "border-[#efe2d1] bg-[#fffdfa]" : ""}`} role={tone === "warning" ? "alert" : "status"}><span className={`grid size-[34px] shrink-0 place-items-center rounded-full text-2xl font-bold ${tone === "warning" ? "bg-[#fff1da] text-lg text-[#9d702e]" : "bg-[#e4f8e9] text-[#159a54]"}`}>{tone === "warning" ? "!" : "·"}</span><div className="min-w-0"><strong className="text-[17px] text-forest">{title}</strong><p className="mt-2 text-[15px] leading-[1.65] break-words text-muted">{message}</p>{onRetry && <button type="button" onClick={onRetry} className="mt-3 min-h-11 rounded-lg border border-line bg-white px-4 text-sm font-bold text-forest transition hover:bg-ground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest">Thử lại</button>}</div></div>;
}
