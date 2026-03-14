"use client";

import { useEffect, useState } from "react";
import Header from "@/components/header";
import { fetchSources, syncSource, type Source } from "@/lib/api";
import { Upload, Database, Cloud, Radio, Server, BarChart3, Ticket, RefreshCw } from "lucide-react";

const SOURCE_TYPE_ICONS: Record<string, React.ReactNode> = {
  parquet: <Upload size={24} />,
  postgresql: <Database size={24} />,
  s3: <Cloud size={24} />,
};

const COMING_SOON = [
  { name: "EMS / NMS", desc: "Connect to your Element or Network Management System", icon: <Radio size={24} /> },
  { name: "CMDB", desc: "Import configuration items and infrastructure assets", icon: <Server size={24} /> },
  { name: "Observability Stack", desc: "Ingest metrics, traces and logs from Prometheus, Grafana, Datadog", icon: <BarChart3 size={24} /> },
  { name: "ITSM", desc: "Sync tickets and incidents from ServiceNow, Jira, Remedy", icon: <Ticket size={24} /> },
];

const FALLBACK_SOURCES: Source[] = [
  { id: "kalshi", name: "Kalshi Markets", type: "parquet", description: "Parquet files from data/kalshi/markets/", status: "connected", last_sync: null, details: "data/kalshi/markets/" },
  { id: "polymarket", name: "Polymarket Markets", type: "parquet", description: "Parquet files from data/polymarket/markets/", status: "connected", last_sync: null, details: "data/polymarket/markets/" },
  { id: "fuseki", name: "Apache Fuseki", type: "postgresql", description: "SPARQL triple store at localhost:3030", status: "disconnected", last_sync: null, details: "localhost:3030/pmo" },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>(FALLBACK_SOURCES);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    fetchSources().then(setSources).catch(() => {});
  }, []);

  const handleSync = async (id: string) => {
    setSyncing(id);
    try {
      await syncSource(id);
    } catch {
      // noop
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Sources" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div>
          <h2 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
            Choose a data source
          </h2>
          <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
            Select how you want to bring data into the knowledge graph
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: "Upload Files", desc: "Drag & drop or browse CSV, Excel, JSON and more", icon: <Upload size={28} /> },
              { label: "PostgreSQL", desc: "Connect to a database and import tables directly", icon: <Database size={28} /> },
              { label: "S3 Bucket", desc: "Browse and import files from AWS S3", icon: <Cloud size={28} /> },
            ].map((c) => (
              <button
                key={c.label}
                className="card p-6 text-left hover:border-cyan-400 transition-colors cursor-pointer"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{c.label}</span>
                  <span style={{ color: "var(--accent)" }}>{c.icon}</span>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{c.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Saved connections */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
            Saved Connections
          </h3>
          <div className="space-y-2">
            {sources.map((src) => (
              <div
                key={src.id}
                className="card flex items-center justify-between px-5 py-4"
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ background: "#f1f5f9", color: "var(--text-secondary)" }}
                  >
                    {SOURCE_TYPE_ICONS[src.type] || <Database size={20} />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{src.name}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{src.details}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="badge"
                    style={{
                      background: src.status === "connected" ? "var(--success-bg)" : "#fef2f2",
                      color: src.status === "connected" ? "#15803d" : "#b91c1c",
                    }}
                  >
                    {src.status}
                  </span>
                  <button
                    onClick={() => handleSync(src.id)}
                    disabled={syncing === src.id}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                    style={{
                      background: "var(--accent)",
                      color: "#fff",
                      opacity: syncing === src.id ? 0.6 : 1,
                    }}
                  >
                    <RefreshCw size={12} className={syncing === src.id ? "animate-spin" : ""} />
                    Sync
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Coming soon */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
            Coming Soon
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {COMING_SOON.map((c) => (
              <div key={c.name} className="card p-5 opacity-60">
                <div className="flex items-center gap-3 mb-2">
                  <span style={{ color: "var(--accent)" }}>{c.icon}</span>
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{c.name}</span>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
