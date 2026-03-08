"""Oxigraph-backed SPARQL client — same interface as FusekiClient.

Used when Fuseki is not available (e.g. Render/Vercel deployments).
Loads RDF from a .nq (N-Quads) or .ttl (Turtle) file at startup.

Usage:
    from src.kg.client_oxigraph import OxigraphClient
    client = OxigraphClient("src/kg/explorer/static/graph.nq")
    rows = client.query("SELECT ...")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PREFIXES = """
PREFIX pmo:  <http://pmo.research/ontology#>
PREFIX pmir: <http://pmo.research/instance/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


class OxigraphClient:
    """In-process SPARQL store backed by pyoxigraph."""

    def __init__(self, data_path: str | Path):
        import pyoxigraph  # noqa: PLC0415

        self._store = pyoxigraph.Store()
        data_path = Path(data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"RDF data file not found: {data_path}")

        ext = data_path.suffix.lower()
        fmt_map = {
            ".nq":  "application/n-quads",
            ".nt":  "application/n-triples",
            ".ttl": "text/turtle",
            ".trig":"application/trig",
        }
        mime = fmt_map.get(ext, "application/n-quads")

        logger.info("Loading RDF from %s ...", data_path)
        with open(data_path, "rb") as f:
            self._store.load(f, mime)
        logger.info("Oxigraph store ready")

    def query(self, sparql: str) -> list[dict]:
        """Run a SELECT query, return list of binding dicts."""
        full = _PREFIXES + sparql
        results = self._store.query(full)
        variables = list(results.variables)  # consume before iterating bindings
        rows = []
        for binding in results:
            row = {}
            for var in variables:
                val = binding[var]
                if val is None:
                    continue
                # pyoxigraph Variable str is "?name" — strip leading "?"
                key = str(var).lstrip("?")
                # NamedNode and Literal both have .value; BlankNode has .value too
                row[key] = val.value if hasattr(val, "value") else str(val)
            rows.append(row)
        return rows

    def update(self, sparql: str) -> None:
        """Run an UPDATE (INSERT/DELETE) query."""
        self._store.update(_PREFIXES + sparql)

    def ping(self) -> bool:
        return True

    def prefixes(self) -> str:
        return _PREFIXES

    def upload_turtle(self, turtle: str, graph_uri: str) -> None:
        """Load Turtle data into a named graph."""
        import pyoxigraph  # noqa: PLC0415
        named_graph = pyoxigraph.NamedNode(graph_uri)
        self._store.load(turtle.encode(), "text/turtle", base_iri=None, to_graph=named_graph)


# ── Export helper ─────────────────────────────────────────────────────────────

def export_kg_to_nquads(fuseki_client, output_path: str | Path) -> int:
    """Dump all named-graph triples from Fuseki to an N-Quads file.

    Returns triple count.
    """
    rows = fuseki_client.query("""
        SELECT ?g ?s ?p ?o WHERE {
            GRAPH ?g { ?s ?p ?o }
        }
    """)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for r in rows:
            s = _nq_term(r["s"])
            p = _nq_term(r["p"])
            o = _nq_term(r["o"])
            g = _nq_term(r["g"])
            if s and p and o and g:
                f.write(f"{s} {p} {o} {g} .\n")
                count += 1

    logger.info("Exported %d triples to %s", count, output_path)
    return count


def _nq_term(val: Optional[str]) -> Optional[str]:
    """Format a SPARQL binding value as an N-Quads term."""
    if not val:
        return None
    if val.startswith("http://") or val.startswith("https://"):
        return f"<{val}>"
    # Literal — already a plain string value from SPARQLWrapper
    escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
