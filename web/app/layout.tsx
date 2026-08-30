import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Survivorship Tax",
  description:
    "Measuring how much of a quantitative factor backtest is an artifact of its own shortcuts: a five-rung bias ladder over a point-in-time S&P 500 universe, 2012-2026.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
