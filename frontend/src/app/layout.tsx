import type { Metadata } from "next";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "M5 Retail | Dự báo nhu cầu bán lẻ",
  description: "Theo dõi lượng bán và xem dự báo 28 ngày cho 300 sản phẩm tại cửa hàng CA_1.",
  other: { "page-type": "software", "site-kind": "software" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" data-type="software" data-radius="soft" data-motion="on">
      <body>{children}</body>
    </html>
  );
}
