"""Knowledge Graph Explorer — FastAPI backend.

Serves:
  GET /          → D3.js frontend (static/index.html)
  GET /api/graph → node/edge JSON for the force-directed graph
  GET /api/stats → triple counts per named graph

Run with:
    uv run src/kg/explorer/app.py
or:
    uvicorn src.kg.explorer.app:app --reload --port 8765
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.kg.client import FusekiClient
from src.kg.explorer.graph_builder import build_graph

_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="PMO Knowledge Graph Explorer", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# ── Client factory: Fuseki (local) or Oxigraph (Render/static deployment) ─────
_oxigraph_client = None

def _client():
    global _oxigraph_client
    kg_data = os.getenv("KG_DATA_PATH")
    if kg_data:
        if _oxigraph_client is None:
            from src.kg.client_oxigraph import OxigraphClient  # noqa: PLC0415
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


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EXPLORER_PORT", "8765"))
    print(f"\nKG Explorer → http://localhost:{port}\n")
    uvicorn.run("src.kg.explorer.app:app", host="0.0.0.0", port=port, reload=True)
