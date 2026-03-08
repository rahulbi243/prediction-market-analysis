"""Fuseki SPARQL client wrapping SPARQLWrapper."""

from __future__ import annotations

import logging
import os

import httpx
from SPARQLWrapper import JSON, POST, SPARQLWrapper

logger = logging.getLogger(__name__)

PMO_NS = "http://pmo.research/ontology#"
PMIR_NS = "http://pmo.research/instance/"


class FusekiClient:
    """Thin wrapper around a Fuseki TDB2 dataset.

    Supports:
    - SELECT queries  → list of binding dicts
    - UPDATE queries  → INSERT/DELETE
    - GSP uploads     → Turtle graph upload
    - ping            → liveness check
    """

    def __init__(
        self,
        base_url: str | None = None,
        dataset: str | None = None,
        password: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("FUSEKI_URL", "http://localhost:3030")).rstrip("/")
        self.dataset = dataset or os.getenv("FUSEKI_DATASET", "pmo")
        self._password = password or os.getenv("FUSEKI_PASSWORD", "fuseki-dev")
        self._auth = ("admin", self._password)
        self._query_ep = f"{self.base_url}/{self.dataset}/sparql"
        self._update_ep = f"{self.base_url}/{self.dataset}/update"
        self._gsp_ep = f"{self.base_url}/{self.dataset}/data"

    # ── Public API ────────────────────────────────────────────────────────────

    def query(self, sparql: str) -> list[dict]:
        """Execute a SELECT query; return list of binding dicts."""
        sw = SPARQLWrapper(self._query_ep)
        sw.setHTTPAuth("BASIC")
        sw.setCredentials(*self._auth)
        sw.setQuery(sparql)
        sw.setReturnFormat(JSON)
        results = sw.query().convert()
        bindings = results.get("results", {}).get("bindings", [])
        return [
            {k: v.get("value") for k, v in row.items()}
            for row in bindings
        ]

    def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE (INSERT/DELETE)."""
        sw = SPARQLWrapper(self._update_ep)
        sw.setHTTPAuth("BASIC")
        sw.setCredentials(*self._auth)
        sw.setMethod(POST)
        sw.setQuery(sparql)
        sw.query()

    def upload_turtle(self, turtle: str, graph_uri: str) -> None:
        """Upload a Turtle document via Graph Store Protocol (GSP).

        The triples are merged (POST) into the named graph.
        """
        resp = httpx.post(
            self._gsp_ep,
            params={"graph": graph_uri},
            content=turtle.encode("utf-8"),
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=self._auth,
            timeout=60,
        )
        resp.raise_for_status()
        logger.debug("Uploaded %d bytes to graph %s", len(turtle), graph_uri)

    def ping(self) -> bool:
        """Return True if Fuseki is reachable and the dataset exists."""
        try:
            resp = httpx.get(f"{self.base_url}/$/ping", auth=self._auth, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Prefixes helper ───────────────────────────────────────────────────────

    @staticmethod
    def prefixes() -> str:
        return (
            f"PREFIX pmo:  <{PMO_NS}>\n"
            f"PREFIX pmir: <{PMIR_NS}>\n"
            "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
            "PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        )
