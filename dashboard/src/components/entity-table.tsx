const TYPE_COLORS: Record<string, string> = {
  Domain: "#a78bfa",
  Market: "#38bdf8",
  LLMForecast: "#fb923c",
  FailureMode: "#f87171",
  NewsItem: "#4ade80",
};

interface EntityRow {
  type: string;
  count: number;
  share: number;
}

export default function EntityTable({ rows }: { rows: EntityRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b" style={{ borderColor: "var(--border)" }}>
            <th className="text-left py-3 px-4 font-medium" style={{ color: "var(--text-secondary)" }}>
              Entity Type
            </th>
            <th className="text-right py-3 px-4 font-medium" style={{ color: "var(--text-secondary)" }}>
              Count
            </th>
            <th className="text-right py-3 px-4 font-medium" style={{ color: "var(--text-secondary)" }}>
              Share
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.type} className="table-row">
              <td className="py-3 px-4 flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: TYPE_COLORS[row.type] || "#94a3b8" }}
                />
                <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                  {row.type}
                </span>
              </td>
              <td className="text-right py-3 px-4" style={{ color: "var(--text-primary)" }}>
                {row.count.toLocaleString()}
              </td>
              <td className="text-right py-3 px-4" style={{ color: "var(--text-muted)" }}>
                {(row.share * 100).toFixed(0)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
