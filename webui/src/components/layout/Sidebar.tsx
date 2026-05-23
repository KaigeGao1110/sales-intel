"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Building2, GitBranch, Mail, Activity } from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/pipeline", label: "Pipeline", icon: GitBranch },
  { href: "/outreach", label: "Outreach", icon: Mail },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="p-5 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-500" />
          <span className="font-semibold text-gray-900 text-lg">Scout</span>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active ? "bg-blue-50 text-blue-600" : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
