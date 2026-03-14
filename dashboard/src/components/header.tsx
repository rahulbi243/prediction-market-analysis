"use client";

import { Circle } from "lucide-react";

export default function Header({ title }: { title: string }) {
  return (
    <header
      className="h-14 flex items-center justify-between px-6 border-b shrink-0"
      style={{ background: "var(--bg-secondary)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </h1>
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--success)" }}>
          <Circle size={8} fill="currentColor" />
          Live
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          Prediction Market Ontology
        </span>
      </div>
    </header>
  );
}
