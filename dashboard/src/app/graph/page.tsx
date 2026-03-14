"use client";

import { useEffect, useState } from "react";
import Header from "@/components/header";
import GraphViewer from "@/components/graph-viewer";
import { fetchGraph, type GraphData } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

const DOMAINS = ["All domains", "Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"];
const PLATFORMS = ["Both platforms", "kalshi", "polymarket"];

const TYPE_COLORS: Record<string, string> = {
  Domain: "#a78bfa",
  Market: "#38bdf8",
  LLMForecast: "#fb923c",
  FailureMode: "#f87171",
  NewsItem: "#4ade80",
};

const EMPTY: GraphData = { nodes: [], links: [], stats: { node_count: 0, link_count: 0, node_types: {} } };

export default function GraphPage() {
  const [data, setData] = useState<GraphData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [domain, setDomain] = useState("All domains");
  const [platform, setPlatform] = useState("Both platforms");
  const [marketLimit, setMarketLimit] = useState(60);
  const [showMarkets, setShowMarkets] = useState(true);
  const [showForecasts, setShowForecasts] = useState(true);
  const [showNews, setShowNews] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchGraph({
      markets: showMarkets,
      forecasts: showForecasts,
      news: showNews,
      market_limit: marketLimit,
      domain: domain === "All domains" ? undefined : domain,
      platform: platform === "Both platforms" ? undefined : platform,
    })
      .then(setData)
      .catch(() => setData(EMPTY))
      .finally(() => setLoading(false));
  }, [domain, platform, marketLimit, showMarkets, showForecasts, showNews]);

  return (
    <div className="flex flex-col h-full">
      <Header title="Graph" />
      <div className="flex-1 flex overflow-hidden">
        {/* Main graph area */}
        <div className="flex-1 relative">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-3 card px-4 py-2">
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Knowledge Graph
            </span>
            <span className="badge badge-info">{data.stats.node_count} Nodes</span>
            <span className="badge badge-info">{data.stats.link_count} Links</span>
          </div>

          {/* Filters bar */}
          <div className="absolute top-16 left-4 z-10 card px-4 py-3 space-y-3 w-64">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium w-20" style={{ color: "var(--text-secondary)" }}>Domain</span>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="flex-1 text-xs border rounded-md px-2 py-1.5"
                style={{ borderColor: "var(--border)", color: "var(--text-primary)", background: "var(--bg-secondary)" }}
              >
                {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium w-20" style={{ color: "var(--text-secondary)" }}>Platform</span>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="flex-1 text-xs border rounded-md px-2 py-1.5"
                style={{ borderColor: "var(--border)", color: "var(--text-primary)", background: "var(--bg-secondary)" }}
              >
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Node Limit</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>{marketLimit}</span>
              </div>
              <input
                type="range" min={10} max={500} value={marketLimit}
                onChange={(e) => setMarketLimit(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
            <div className="space-y-1.5 pt-1 border-t" style={{ borderColor: "var(--border)" }}>
              {[
                { label: "Markets", checked: showMarkets, set: setShowMarkets },
                { label: "Forecasts", checked: showForecasts, set: setShowForecasts },
                { label: "News Items", checked: showNews, set: setShowNews },
              ].map((t) => (
                <label key={t.label} className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: "var(--text-primary)" }}>
                  <input
                    type="checkbox" checked={t.checked}
                    onChange={(e) => t.set(e.target.checked)}
                    className="accent-cyan-500"
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-full text-sm" style={{ color: "var(--text-muted)" }}>
              Loading graph...
            </div>
          ) : (
            <GraphViewer data={data} width={1200} height={800} />
          )}
        </div>

        {/* Statistics sidebar */}
        <div
          className="w-64 border-l shrink-0 p-4 overflow-auto"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            Statistics
          </h3>
          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="p-3 rounded-lg" style={{ background: "#f1f5f9" }}>
              <p className="text-lg font-bold" style={{ color: "var(--accent)" }}>
                {formatNumber(data.stats.node_count)}
              </p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Nodes</p>
            </div>
            <div className="p-3 rounded-lg" style={{ background: "#f1f5f9" }}>
              <p className="text-lg font-bold" style={{ color: "var(--accent)" }}>
                {formatNumber(data.stats.link_count)}
              </p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Links</p>
            </div>
          </div>

          <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
            Entities by Type
          </h4>
          <div className="space-y-2">
            {Object.entries(data.stats.node_types).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: TYPE_COLORS[type] || "#94a3b8" }} />
                  <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{type}</span>
                </div>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {formatNumber(count as number)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
