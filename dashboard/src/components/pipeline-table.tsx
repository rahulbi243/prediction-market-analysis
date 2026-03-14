import type { PipelineRun } from "@/lib/api";

function StatusBadge({ status }: { status: PipelineRun["status"] }) {
  const styles: Record<string, { bg: string; color: string }> = {
    success: { bg: "var(--success-bg)", color: "#15803d" },
    failed: { bg: "#fef2f2", color: "#b91c1c" },
    running: { bg: "#eff6ff", color: "#1d4ed8" },
  };
  const s = styles[status] || styles.running;
  return (
    <span
      className="badge"
      style={{ background: s.bg, color: s.color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: "currentColor" }} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default function PipelineTable({ runs }: { runs: PipelineRun[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b" style={{ borderColor: "var(--border)" }}>
            {["Run ID", "File", "Timestamp", "Entities", "Triples", "Status", "Violations"].map((h) => (
              <th
                key={h}
                className="text-left py-3 px-4 font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.length === 0 && (
            <tr>
              <td colSpan={7} className="py-8 text-center" style={{ color: "var(--text-muted)" }}>
                No pipeline runs recorded yet
              </td>
            </tr>
          )}
          {runs.map((run) => (
            <tr key={run.id} className="table-row">
              <td className="py-3 px-4 font-mono text-xs" style={{ color: "var(--text-muted)" }}>
                {run.id.slice(0, 8)}
              </td>
              <td className="py-3 px-4">
                <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                  {run.file}
                </span>
              </td>
              <td className="py-3 px-4" style={{ color: "var(--text-secondary)" }}>
                {new Date(run.started_at).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td className="py-3 px-4" style={{ color: "var(--text-primary)" }}>
                <span className="inline-flex items-center gap-1">
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>&#x25B2;</span>
                  {run.entities.toLocaleString()}
                </span>
              </td>
              <td className="py-3 px-4" style={{ color: "var(--text-primary)" }}>
                {run.triples.toLocaleString()}
              </td>
              <td className="py-3 px-4">
                <StatusBadge status={run.status} />
              </td>
              <td className="py-3 px-4" style={{ color: "var(--text-muted)" }}>
                {run.violations > 0 ? run.violations : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
