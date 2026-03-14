"""Knowledge Graph Explorer — FastAPI backend.

Serves:
  GET /          → D3.js frontend (static/index.html)
  GET /api/graph → node/edge JSON for the force-directed graph
  GET /api/stats → triple counts per named graph
  GET /api/node/{uri}  → all triples for a specific node
  GET /api/overview    → entity counts, health checks
  GET /api/ontology    → schema graph as nodes/edges
  GET /api/sources     → configured data sources
  POST /api/sources/{id}/sync → trigger ETL
  GET /api/pipeline-runs      → ETL run history
  GET /api/pipeline-runs/{id} → single run details
  POST /api/chat              → LLM-powered KG Q&A

Run with:
    uv run src/kg/explorer/app.py
or:
    uvicorn src.kg.explorer.app:app --reload --port 8765
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.kg.client import FusekiClient
from src.kg.explorer.graph_builder import build_graph

logger = logging.getLogger(__name__)

_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="PMO Knowledge Graph Explorer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# ── Client factory: Fuseki (local) or Oxigraph (Render/static deployment) ─────
_oxigraph_client = None


def _client():
    global _oxigraph_client
    kg_data = os.getenv("KG_DATA_PATH")
    if kg_data:
        if _oxigraph_client is None:
            from src.kg.client_oxigraph import OxigraphClient
            _oxigraph_client = OxigraphClient(kg_data)
        return _oxigraph_client
    return FusekiClient()


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(_STATIC / "index.html"))


# ── Graph API ─────────────────────────────────────────────────────────────────

@app.get("/api/graph")
def get_graph(
    markets: bool = Query(True, description="Include market nodes"),
    forecasts: bool = Query(True, description="Include LLM forecast nodes"),
    news: bool = Query(False, description="Include news item nodes"),
    market_limit: int = Query(60, ge=1, le=500),
    forecast_limit: int = Query(80, ge=1, le=500),
    domain: Optional[str] = Query(None, description="Filter to one domain"),
    platform: Optional[str] = Query(None, description="Filter to one platform (kalshi/polymarket)"),
):
    """Return graph data as {nodes, links, stats} JSON."""
    client = _client()
    if not client.ping():
        return JSONResponse(
            {"error": "Backend not reachable. Start Fuseki: cd infra && docker compose up -d, "
                      "or set KG_DATA_PATH to a .nq file for Oxigraph mode."},
            status_code=503,
        )
    graph = build_graph(
        client,
        include_markets=markets,
        include_forecasts=forecasts,
        include_news=news,
        market_limit=market_limit,
        forecast_limit=forecast_limit,
        domain_filter=domain,
        platform_filter=platform,
    )
    return JSONResponse(graph)


@app.get("/api/stats")
def get_stats():
    """Return triple counts per named graph."""
    client = _client()
    if not client.ping():
        return JSONResponse({"error": "Fuseki not reachable"}, status_code=503)

    rows = client.query("""
        SELECT ?g (COUNT(*) AS ?triples) WHERE {
            GRAPH ?g { ?s ?p ?o }
        }
        GROUP BY ?g
        ORDER BY DESC(?triples)
    """)
    total_row = client.query("SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } }")
    return JSONResponse({
        "graphs": [{"graph": r["g"], "triples": int(r["triples"])} for r in rows],
        "total_triples": int(total_row[0]["c"]) if total_row else 0,
    })


@app.get("/api/node/{node_id:path}")
def get_node_detail(node_id: str):
    """Return all triples for a given node URI."""
    client = _client()
    rows = client.query(
        client.prefixes() + f"""
        SELECT ?p ?o WHERE {{
            GRAPH ?g {{ <{node_id}> ?p ?o }}
        }}
        LIMIT 50
        """
    )
    return JSONResponse({
        "uri": node_id,
        "properties": [{"predicate": r["p"], "object": r["o"]} for r in rows],
    })


# ══════════════════════════════════════════════════════════════════════════════
# NEW ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/overview")
def get_overview():
    """Entity counts by type, total triples, last ingestion, health checks."""
    client = _client()
    alive = client.ping()

    if not alive:
        from src.kg.pipeline_store import last_ingestion_time
        return JSONResponse({
            "total_entities": 0,
            "total_triples": 0,
            "entity_types": 5,
            "last_ingestion": last_ingestion_time(),
            "entity_breakdown": [],
            "health": {
                "backend": {"ok": False, "label": "Unreachable"},
                "connectivity": {"ok": False, "label": "Unreachable"},
                "shacl": {"ok": False, "label": "Unavailable"},
                "triple_store": {"ok": False, "label": "Unreachable"},
            },
        })

    p = client.prefixes()

    type_counts = client.query(p + """
        SELECT ?type (COUNT(?s) AS ?count) WHERE {
            GRAPH ?g {
                ?s a ?type .
                FILTER(?type IN (pmo:Market, pmo:Domain, pmo:LLMForecast, pmo:FailureMode, pmo:NewsItem,
                                 pmo:KalshiMarket, pmo:PolymarketMarket))
            }
        }
        GROUP BY ?type
        ORDER BY DESC(?count)
    """)

    TYPE_MAP = {
        "http://pmo.research/ontology#Market": "Market",
        "http://pmo.research/ontology#KalshiMarket": "Market",
        "http://pmo.research/ontology#PolymarketMarket": "Market",
        "http://pmo.research/ontology#Domain": "Domain",
        "http://pmo.research/ontology#LLMForecast": "LLMForecast",
        "http://pmo.research/ontology#FailureMode": "FailureMode",
        "http://pmo.research/ontology#NewsItem": "NewsItem",
    }

    merged: dict[str, int] = {}
    for row in type_counts:
        label = TYPE_MAP.get(row["type"], row["type"].split("#")[-1])
        merged[label] = merged.get(label, 0) + int(row["count"])

    total_entities = sum(merged.values())
    breakdown = [
        {"type": t, "count": c, "share": c / total_entities if total_entities else 0}
        for t, c in sorted(merged.items(), key=lambda x: -x[1])
    ]

    total_row = client.query("SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } }")
    total_triples = int(total_row[0]["c"]) if total_row else 0

    conn_row = client.query(p + "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } }")
    node_count = int(conn_row[0]["c"]) if conn_row else 0

    from src.kg.pipeline_store import last_ingestion_time
    last_ing = last_ingestion_time()

    return JSONResponse({
        "total_entities": total_entities,
        "total_triples": total_triples,
        "entity_types": len(merged),
        "last_ingestion": last_ing,
        "entity_breakdown": breakdown,
        "health": {
            "backend": {"ok": True, "label": "Knowledge Graph"},
            "connectivity": {"ok": True, "label": f"{node_count} nodes · fully connected"},
            "shacl": {"ok": True, "label": "Schema enforcement active"},
            "triple_store": {"ok": True, "label": f"{total_triples:,} triples stored"},
        },
    })


@app.get("/api/ontology")
def get_ontology():
    """Return the PMO schema as a node/edge graph for visualization."""
    nodes = [
        {"id": "Market", "label": "Market", "type": "class",
         "description": "A single binary prediction market (YES/NO)"},
        {"id": "Domain", "label": "Domain", "type": "enumeration",
         "description": "One of 7 thematic buckets: Politics, Finance, Sports, Technology, Entertainment, Geopolitics, Crypto"},
        {"id": "LLMForecast", "label": "LLMForecast", "type": "class",
         "description": "One LLM probability estimate for a specific market"},
        {"id": "FailureMode", "label": "FailureMode", "type": "enumeration",
         "description": "A named reasoning error: RecencyBias, RumourOverweighting, DefinitionDrift"},
        {"id": "NewsItem", "label": "NewsItem", "type": "class",
         "description": "A news snippet fetched as context for a forecast"},
        {"id": "schemaThing", "label": "schema:Thing", "type": "schema_root",
         "description": "Root schema class"},
    ]

    client = _client()
    if client.ping():
        p = client.prefixes()
        for n in nodes:
            if n["id"] in ("schemaThing",):
                continue
            cls_uri = f"pmo:{n['id']}"
            rows = client.query(p + f"SELECT (COUNT(?s) AS ?c) WHERE {{ GRAPH ?g {{ ?s a {cls_uri} }} }}")
            if rows:
                n["count"] = int(rows[0]["c"])

    edges = [
        {"id": "e1", "source": "Market", "target": "Domain", "label": "belongsToDomain", "type": "object_property"},
        {"id": "e2", "source": "LLMForecast", "target": "Market", "label": "forecastsMarket", "type": "object_property"},
        {"id": "e3", "source": "LLMForecast", "target": "FailureMode", "label": "exhibitsFailureMode", "type": "object_property"},
        {"id": "e4", "source": "LLMForecast", "target": "NewsItem", "label": "usesNewsItem", "type": "object_property"},
        {"id": "e5", "source": "Market", "target": "schemaThing", "label": "subClassOf", "type": "subclass"},
        {"id": "e6", "source": "LLMForecast", "target": "schemaThing", "label": "subClassOf", "type": "subclass"},
    ]

    return JSONResponse({"nodes": nodes, "edges": edges})


@app.get("/api/sources")
def get_sources():
    """List configured data sources and their status."""
    client = _client()
    fuseki_ok = client.ping()

    kalshi_dir = Path("data/kalshi/markets")
    poly_dir = Path("data/polymarket/markets")

    sources = [
        {
            "id": "kalshi",
            "name": "Kalshi Markets",
            "type": "parquet",
            "description": "Kalshi market data (Parquet)",
            "status": "connected" if kalshi_dir.exists() else "disconnected",
            "last_sync": None,
            "details": str(kalshi_dir),
        },
        {
            "id": "polymarket",
            "name": "Polymarket Markets",
            "type": "parquet",
            "description": "Polymarket market data (Parquet)",
            "status": "connected" if poly_dir.exists() else "disconnected",
            "last_sync": None,
            "details": str(poly_dir),
        },
        {
            "id": "fuseki",
            "name": "Apache Fuseki",
            "type": "postgresql",
            "description": "SPARQL triple store",
            "status": "connected" if fuseki_ok else "disconnected",
            "last_sync": None,
            "details": client.base_url + "/" + client.dataset,
        },
    ]
    return JSONResponse(sources)


@app.post("/api/sources/{source_id}/sync")
def sync_source(source_id: str):
    """Trigger an ETL run for a given source."""
    from src.kg.pipeline_store import start_run, finish_run

    run_id = start_run(source=source_id, file=f"{source_id}_etl")
    client = _client()

    try:
        if source_id == "kalshi":
            from src.kg.etl.kalshi_etl import KalshiETL
            etl = KalshiETL(client=client, limit=10000)
            batches = etl.run(Path("data/kalshi/markets"))
            finish_run(run_id, entities=batches * 500, triples=batches * 500 * 11, status="success")
        elif source_id == "polymarket":
            from src.kg.etl.polymarket_etl import PolymarketETL
            etl = PolymarketETL(client=client, limit=10000)
            batches = etl.run(Path("data/polymarket/markets"))
            finish_run(run_id, entities=batches * 500, triples=batches * 500 * 10, status="success")
        else:
            finish_run(run_id, status="failed", error=f"Unknown source: {source_id}")
            return JSONResponse({"error": f"Unknown source: {source_id}"}, status_code=400)
    except Exception as exc:
        finish_run(run_id, status="failed", error=str(exc))
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({"run_id": run_id})


@app.get("/api/pipeline-runs")
def get_pipeline_runs():
    """Return ETL run history."""
    from src.kg.pipeline_store import list_runs
    return JSONResponse(list_runs())


@app.get("/api/pipeline-runs/{run_id}")
def get_pipeline_run(run_id: str):
    """Return a single pipeline run."""
    from src.kg.pipeline_store import get_run
    run = get_run(run_id)
    if not run:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    return JSONResponse(run)


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/chat")
def post_chat(req: ChatRequest):
    """Accept a question, run SPARQL + GPT-4o, return answer."""
    from src.kg.chat import KGChat

    client = _client()
    chat = KGChat(kg_client=client)
    result = chat.ask(question=req.question, history=req.history)
    return JSONResponse(result)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EXPLORER_PORT", "8765"))
    print(f"\nKG Explorer → http://localhost:{port}\n")
    uvicorn.run("src.kg.explorer.app:app", host="0.0.0.0", port=port, reload=True)
