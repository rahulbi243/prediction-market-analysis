"use client";

import { useEffect, useState } from "react";
import Header from "@/components/header";
import PipelineTable from "@/components/pipeline-table";
import { fetchPipelineRuns, type PipelineRun } from "@/lib/api";

export default function PipelineRunsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPipelineRuns()
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Pipeline Runs" />
      <div className="flex-1 overflow-auto p-6">
        <div className="card p-0">
          <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Pipeline Runs
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              History of ingestion runs for this session. Upload files from{" "}
              <a href="/sources" className="underline" style={{ color: "var(--accent)" }}>Sources</a>.
            </p>
          </div>
          {loading ? (
            <div className="p-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              Loading pipeline runs...
            </div>
          ) : (
            <PipelineTable runs={runs} />
          )}
        </div>
      </div>
    </div>
  );
}
