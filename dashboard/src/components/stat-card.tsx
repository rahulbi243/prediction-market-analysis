import { type ReactNode } from "react";

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  subtitle: string;
  accentColor?: string;
}

export default function StatCard({ icon, label, value, subtitle, accentColor = "var(--accent)" }: StatCardProps) {
  return (
    <div className="stat-card flex items-start gap-4">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${accentColor}18`, color: accentColor }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium mb-0.5" style={{ color: accentColor }}>
          {label}
        </p>
        <p className="text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
          {value}
        </p>
        <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
          {subtitle}
        </p>
      </div>
    </div>
  );
}
