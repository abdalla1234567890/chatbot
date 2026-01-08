import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "شركة العامورية - شات بوت مواد البناء",
  description: "نظام طلبات مواد البناء - شركة العامورية",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
