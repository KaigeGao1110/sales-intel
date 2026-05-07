import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { AppLayout } from "@/components/layout/AppLayout";

export const metadata: Metadata = {
  title: "Scout — Sales Intelligence",
  description: "AI-powered sales intelligence and company monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
        <QueryProvider>
          <AppLayout>{children}</AppLayout>
        </QueryProvider>
      </body>
    </html>
  );
}
