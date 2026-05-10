import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Mono, Noto_Sans_SC, Noto_Serif_SC } from "next/font/google";
import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";

const sans = Noto_Sans_SC({
  weight: ["300", "400", "500", "600", "700", "900"],
  variable: "--font-sans",
  preload: false,
});

const serif = Noto_Serif_SC({
  weight: ["300", "400", "500", "600", "700", "900"],
  variable: "--font-serif",
  preload: false,
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "商品图生成 | AI 电商图片工作台",
  description: "面向电商运营的 AI 商品图生成工作台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="zh-CN" className={`${sans.variable} ${serif.variable} ${mono.variable}`}>
      <body className="font-sans antialiased min-h-screen bg-paper text-ink">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
