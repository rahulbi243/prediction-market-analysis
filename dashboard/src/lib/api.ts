const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface OverviewData {
  total_entities: number;
  total_triples: number;
  entity_types: number;
  last_ingestion: string | null;
  entity_breakdown: { type: string; count: number; share: number }[];
  health: {
    backend: { ok: boolean; label: string };
    connectivity: { ok: boolean; label: string };
    shacl: { ok: boolean; label: string };
    triple_store: { ok: boolean; label: string };
  };
}

export interface OntologyNode {
  id: string;
  label: string;
  type: "class" | "enumeration" | "schema_root";
  description: string;
  count?: number;
}

export interface OntologyEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: "object_property" | "subclass";
}

export interface OntologyData {
  nodes: OntologyNode[];
  edges: OntologyEdge[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  size?: number;
  [key: string]: unknown;
}

export interface GraphLink {
  source: string;
  target: string;
  rel: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  stats: { node_count: number; link_count: number; node_types: Record<string, number> };
}

export interface PipelineRun {
  id: string;
  source: string;
  file: string;
  started_at: string;
  finished_at: string | null;
  entities: number;
  triples: number;
  status: "success" | "failed" | "running";
  violations: number;
}

export interface Source {
  id: string;
  name: string;
  type: "parquet" | "postgresql" | "s3" | "coming_soon";
  description: string;
  status: "connected" | "disconnected" | "coming_soon";
  last_sync: string | null;
  details: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sparql?: string;
  raw_results?: Record<string, unknown>[];
}

export interface ChatResponse {
  answer: string;
  sparql_query: string | null;
  raw_results: Record<string, unknown>[];
}

export function fetchOverview() {
  return apiFetch<OverviewData>("/api/overview");
}

export function fetchOntology() {
  return apiFetch<OntologyData>("/api/ontology");
}

export function fetchGraph(params: {
  markets?: boolean;
  forecasts?: boolean;
  news?: boolean;
  market_limit?: number;
  forecast_limit?: number;
  domain?: string;
  platform?: string;
}) {
  const sp = new URLSearchParams();
  if (params.markets !== undefined) sp.set("markets", String(params.markets));
  if (params.forecasts !== undefined) sp.set("forecasts", String(params.forecasts));
  if (params.news !== undefined) sp.set("news", String(params.news));
  if (params.market_limit !== undefined) sp.set("market_limit", String(params.market_limit));
  if (params.forecast_limit !== undefined) sp.set("forecast_limit", String(params.forecast_limit));
  if (params.domain) sp.set("domain", params.domain);
  if (params.platform) sp.set("platform", params.platform);
  return apiFetch<GraphData>(`/api/graph?${sp.toString()}`);
}

export function fetchPipelineRuns() {
  return apiFetch<PipelineRun[]>("/api/pipeline-runs");
}

export function fetchSources() {
  return apiFetch<Source[]>("/api/sources");
}

export function syncSource(id: string) {
  return apiFetch<{ run_id: string }>(`/api/sources/${id}/sync`, { method: "POST" });
}

export function sendChatMessage(question: string, history: { role: string; content: string }[]) {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}
