import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SentinelSafe",
  description: "AI-powered safety management and risk automation platform"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
