"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  Database,
  PlayCircle,
  Network,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/ontology", label: "Ontology", icon: GitBranch },
  { href: "/sources", label: "Sources", icon: Database },
  { href: "/pipeline-runs", label: "Pipeline Runs", icon: PlayCircle },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/chat", label: "Chat", icon: MessageSquare },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "h-screen flex flex-col transition-all duration-200 border-r",
        collapsed ? "w-16" : "w-56"
      )}
      style={{
        background: "var(--bg-sidebar)",
        borderColor: "var(--bg-sidebar-hover)",
      }}
    >
      <div className="flex items-center gap-3 px-4 h-14 border-b" style={{ borderColor: "var(--bg-sidebar-hover)" }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white text-sm"
          style={{ background: "var(--accent)" }}
        >
          KG
        </div>
        {!collapsed && (
          <span className="text-white font-semibold text-sm tracking-tight">
            PMO Dashboard
          </span>
        )}
      </div>

      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "text-white"
                  : "hover:text-white"
              )}
              style={{
                color: isActive ? "var(--text-sidebar-active)" : "var(--text-sidebar)",
                background: isActive ? "var(--bg-sidebar-active)" : "transparent",
              }}
              title={item.label}
            >
              <item.icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 mx-2 mb-3 rounded-lg transition-colors cursor-pointer"
        style={{ color: "var(--text-sidebar)", background: "var(--bg-sidebar-hover)" }}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
