import { CheckCircle2, XCircle } from "lucide-react";

interface HealthCheckRowProps {
  label: string;
  ok: boolean;
  detail: string;
}

export default function HealthCheckRow({ label, ok, detail }: HealthCheckRowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b last:border-b-0" style={{ borderColor: "var(--border)" }}>
      <div className="flex items-center gap-2">
        {ok ? (
          <CheckCircle2 size={18} style={{ color: "var(--success)" }} />
        ) : (
          <XCircle size={18} style={{ color: "var(--danger)" }} />
        )}
        <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          {label}
        </span>
      </div>
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
        {detail}
      </span>
    </div>
  );
}
