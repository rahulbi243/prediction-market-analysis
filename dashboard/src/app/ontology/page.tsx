"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/header";
import { fetchOntology, type OntologyData } from "@/lib/api";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const NODE_COLORS: Record<string, string> = {
  class: "#06b6d4",
  enumeration: "#f59e0b",
  schema_root: "#8b5cf6",
};

const FALLBACK_ONTOLOGY: OntologyData = {
  nodes: [
    { id: "Market", label: "Market", type: "class", description: "A single binary prediction market (YES/NO)", count: 20000 },
    { id: "Domain", label: "Domain", type: "enumeration", description: "One of 7 thematic buckets", count: 7 },
    { id: "LLMForecast", label: "LLMForecast", type: "class", description: "One LLM probability estimate for a market" },
    { id: "FailureMode", label: "FailureMode", type: "enumeration", description: "A named reasoning error pattern", count: 3 },
    { id: "NewsItem", label: "NewsItem", type: "class", description: "A news snippet used as forecast context" },
    { id: "schemaThing", label: "schema:Thing", type: "schema_root", description: "Root schema class" },
  ],
  edges: [
    { id: "e1", source: "Market", target: "Domain", label: "belongsToDomain", type: "object_property" },
    { id: "e2", source: "LLMForecast", target: "Market", label: "forecastsMarket", type: "object_property" },
    { id: "e3", source: "LLMForecast", target: "FailureMode", label: "exhibitsFailureMode", type: "object_property" },
    { id: "e4", source: "LLMForecast", target: "NewsItem", label: "usesNewsItem", type: "object_property" },
    { id: "e5", source: "Market", target: "schemaThing", label: "subClassOf", type: "subclass" },
    { id: "e6", source: "LLMForecast", target: "schemaThing", label: "subClassOf", type: "subclass" },
  ],
};

const POSITIONS: Record<string, { x: number; y: number }> = {
  schemaThing: { x: 400, y: 50 },
  Domain: { x: 100, y: 200 },
  Market: { x: 350, y: 200 },
  LLMForecast: { x: 350, y: 400 },
  FailureMode: { x: 100, y: 500 },
  NewsItem: { x: 600, y: 500 },
};

function toReactFlowNodes(data: OntologyData): Node[] {
  return data.nodes.map((n) => ({
    id: n.id,
    position: POSITIONS[n.id] || { x: Math.random() * 600, y: Math.random() * 400 },
    data: { label: n.label, description: n.description, nodeType: n.type, count: n.count },
    type: "default",
    style: {
      background: NODE_COLORS[n.type] || "#94a3b8",
      color: "#fff",
      border: "2px solid #fff",
      borderRadius: "50%",
      width: 100,
      height: 100,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 12,
      fontWeight: 600,
      boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    },
  }));
}

function toReactFlowEdges(data: OntologyData): Edge[] {
  return data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "default",
    animated: e.type === "subclass",
    style: { stroke: e.type === "subclass" ? "#94a3b8" : "#475569", strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15, color: "#475569" },
    labelStyle: { fontSize: 10, fill: "#475569" },
    labelBgStyle: { fill: "#f8fafc", fillOpacity: 0.9 },
    labelBgPadding: [4, 4] as [number, number],
  }));
}

const LEGEND = [
  { label: "Schema root", color: "#8b5cf6" },
  { label: "Enumeration", color: "#f59e0b" },
  { label: "Entity", color: "#06b6d4" },
];

export default function OntologyPage() {
  const [data, setData] = useState<OntologyData>(FALLBACK_ONTOLOGY);
  const [nodes, setNodes, onNodesChange] = useNodesState(toReactFlowNodes(FALLBACK_ONTOLOGY));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toReactFlowEdges(FALLBACK_ONTOLOGY));
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    fetchOntology()
      .then((d) => {
        setData(d);
        setNodes(toReactFlowNodes(d));
        setEdges(toReactFlowEdges(d));
      })
      .catch(() => {});
  }, [setNodes, setEdges]);

  const onNodeMouseEnter = useCallback((_: React.MouseEvent, node: Node) => {
    const d = node.data as { description?: string };
    if (d.description) {
      setTooltip({ x: node.position.x, y: node.position.y - 20, text: d.description as string });
    }
  }, []);

  const onNodeMouseLeave = useCallback(() => setTooltip(null), []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Ontology" />
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={20} color="#e2e8f0" />
          <Controls />
          <MiniMap
            nodeColor={(n) => {
              const t = (n.data as { nodeType?: string }).nodeType;
              return NODE_COLORS[t as string] || "#94a3b8";
            }}
          />
        </ReactFlow>

        {tooltip && (
          <div
            className="absolute bg-gray-800 text-white text-xs px-3 py-2 rounded-lg shadow-lg pointer-events-none z-50 max-w-xs"
            style={{ left: tooltip.x + 60, top: tooltip.y + 80 }}
          >
            {tooltip.text}
          </div>
        )}

        {/* Legend */}
        <div
          className="absolute bottom-6 left-6 card p-4 space-y-2"
          style={{ zIndex: 10 }}
        >
          <p className="text-xs font-semibold mb-2" style={{ color: "var(--text-primary)" }}>CLASSES</p>
          {LEGEND.map((l) => (
            <div key={l.label} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full border-2 border-white" style={{ background: l.color }} />
              <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{l.label}</span>
            </div>
          ))}
          <div className="border-t pt-2 mt-2" style={{ borderColor: "var(--border)" }}>
            <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-primary)" }}>EDGES</p>
            <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
              <span className="w-5 border-t border-dashed" style={{ borderColor: "#94a3b8" }} />
              subClassOf
            </div>
            <div className="flex items-center gap-2 text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
              <span className="w-5 border-t-2" style={{ borderColor: "#475569" }} />
              Object property
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
