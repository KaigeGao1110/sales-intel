"use client";
import { useHealth } from "@/lib/use-api";
import { Circle } from "lucide-react";

export function TopBar() {
  const { data: health } = useHealth();
  const ok = health?.status === "ok";
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <span className="text-sm font-medium text-gray-500">Sales Intelligence</span>
      <div className="flex items-center gap-2">
        <Circle
          className="w-2 h-2"
          fill={ok ? "#22c55e" : "#ef4444"}
          color={ok ? "#22c55e" : "#ef4444"}
        />
        <span className="text-xs text-gray-500">{ok ? "API Online" : "API Offline"}</span>
      </div>
    </header>
  );
}
