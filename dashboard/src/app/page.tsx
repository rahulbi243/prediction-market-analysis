"use client";

import { useEffect, useState } from "react";
import Header from "@/components/header";
import StatCard from "@/components/stat-card";
import EntityTable from "@/components/entity-table";
import HealthCheckRow from "@/components/health-check";
import { fetchOverview, type OverviewData } from "@/lib/api";
import { formatNumber, timeAgo } from "@/lib/utils";
import { Box, Triangle, Clock } from "lucide-react";

const FALLBACK: OverviewData = {
  total_entities: 20_034,
  total_triples: 209_180,
  entity_types: 5,
  last_ingestion: null,
  entity_breakdown: [
    { type: "Market", count: 20_000, share: 0.82 },
    { type: "Domain", count: 7, share: 0.0 },
    { type: "LLMForecast", count: 0, share: 0.0 },
    { type: "FailureMode", count: 3, share: 0.0 },
    { type: "NewsItem", count: 0, share: 0.0 },
  ],
  health: {
    backend: { ok: false, label: "Unavailable" },
    connectivity: { ok: false, label: "Unavailable" },
    shacl: { ok: false, label: "Unavailable" },
    triple_store: { ok: false, label: "Unavailable" },
  },
};

export default function OverviewPage() {
  const [data, setData] = useState<OverviewData>(FALLBACK);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview()
      .then(setData)
      .catch(() => setData(FALLBACK))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Overview" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            icon={<Box size={20} />}
            label="Total Entities"
            value={formatNumber(data.total_entities)}
            subtitle={`${data.entity_types} entity types`}
            accentColor="#6366f1"
          />
          <StatCard
            icon={<Triangle size={20} />}
            label="Total Triples"
            value={formatNumber(data.total_triples)}
            subtitle="RDF triples in graph"
            accentColor="#06b6d4"
          />
          <StatCard
            icon={<Clock size={20} />}
            label="Last Ingestion"
            value={data.last_ingestion ? timeAgo(data.last_ingestion) : "N/A"}
            subtitle={data.last_ingestion ? new Date(data.last_ingestion).toLocaleString() : "No ingestion recorded"}
            accentColor="#8b5cf6"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Entity breakdown */}
          <div className="card p-0">
            <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Entity Breakdown
              </h2>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                Counts by entity type in the graph
              </p>
            </div>
            {loading ? (
              <div className="p-6 text-sm" style={{ color: "var(--text-muted)" }}>Loading...</div>
            ) : (
              <EntityTable rows={data.entity_breakdown} />
            )}
          </div>

          {/* Data health */}
          <div className="card p-0">
            <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Data Health
              </h2>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                Schema validation and connectivity
              </p>
            </div>
            <div className="px-6 py-2">
              <HealthCheckRow label="Backend Service" ok={data.health.backend.ok} detail={data.health.backend.label} />
              <HealthCheckRow label="Graph Connectivity" ok={data.health.connectivity.ok} detail={data.health.connectivity.label} />
              <HealthCheckRow label="SHACL Validation" ok={data.health.shacl.ok} detail={data.health.shacl.label} />
              <HealthCheckRow label="Triple Store" ok={data.health.triple_store.ok} detail={data.health.triple_store.label} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
