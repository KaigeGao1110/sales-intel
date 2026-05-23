"use client";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[100dvh] bg-[#fafafa]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
