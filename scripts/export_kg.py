"""Export Fuseki KG to N-Quads for static / Render deployment.

Run from project root:
    uv run python scripts/export_kg.py

Outputs:
  src/kg/explorer/static/graph.nq   — full named-graph dump for Oxigraph
  src/kg/explorer/static/data.json  — pre-baked graph JSON for Vercel static
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kg.client import FusekiClient
from src.kg.client_oxigraph import export_kg_to_nquads
from src.kg.explorer.graph_builder import build_graph


def main():
    client = FusekiClient()
    if not client.ping():
        logger.error("Fuseki not reachable. Start with: cd infra && docker compose up -d")
        sys.exit(1)

    # ── 1. N-Quads dump for Oxigraph / Render ─────────────────────────────────
    nq_path = Path("src/kg/explorer/static/graph.nq")
    n = export_kg_to_nquads(client, nq_path)
    logger.info("N-Quads export: %d triples → %s (%.1f MB)",
                n, nq_path, nq_path.stat().st_size / 1e6)

    # ── 2. JSON snapshot for Vercel static ────────────────────────────────────
    graph = build_graph(
        client,
        include_markets=True,
        include_forecasts=True,
        include_news=False,
        market_limit=500,
        forecast_limit=650,
    )
    json_path = Path("src/kg/explorer/static/data.json")
    with open(json_path, "w") as f:
        json.dump(graph, f, separators=(",", ":"))
    logger.info("JSON snapshot: %d nodes, %d links → %s (%.0f KB)",
                graph["stats"]["node_count"],
                graph["stats"]["link_count"],
                json_path,
                json_path.stat().st_size / 1024)

    print("\nExport complete:")
    print(f"  N-Quads  → {nq_path}")
    print(f"  JSON     → {json_path}")
    print("\nNext steps:")
    print("  Vercel:  push repo → Vercel auto-deploys src/kg/explorer/static/")
    print("  Render:  docker build -f Dockerfile.explorer . && render deploy")


if __name__ == "__main__":
    main()
