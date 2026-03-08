"""Abstract base class for Parquet → RDF ETL pipelines."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.kg.client import FusekiClient

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # triples per GSP upload


class BaseETL(ABC):
    """Stream Parquet data via DuckDB and upload as RDF batches to Fuseki.

    Subclasses implement :meth:`rows_to_turtle` to convert a batch of rows
    (list of dicts) to a Turtle string.
    """

    def __init__(self, client: FusekiClient | None = None):
        self.client = client or FusekiClient()

    @property
    @abstractmethod
    def graph_uri(self) -> str:
        """Named graph URI for this dataset."""

    @abstractmethod
    def rows_to_turtle(self, rows: list[dict]) -> str:
        """Convert a batch of row dicts to a Turtle string."""

    @abstractmethod
    def build_query(self, data_dir: Path) -> str:
        """Build the DuckDB SQL query that selects the rows to ETL."""

    def run(self, data_dir: Path | str) -> int:
        """Stream Parquet from data_dir and upload triples in batches.

        Returns total number of batches uploaded.
        """
        import duckdb

        data_dir = Path(data_dir)
        if not data_dir.exists():
            logger.warning("data_dir does not exist: %s", data_dir)
            return 0

        sql = self.build_query(data_dir)
        con = duckdb.connect()
        rel = con.execute(sql)

        batch: list[dict] = []
        batches_uploaded = 0
        total_rows = 0

        while True:
            chunk = rel.fetchmany(BATCH_SIZE)
            if not chunk:
                break

            col_names = [desc[0] for desc in rel.description]
            rows = [dict(zip(col_names, row)) for row in chunk]
            batch.extend(rows)
            total_rows += len(rows)

            if len(batch) >= BATCH_SIZE:
                turtle = self.rows_to_turtle(batch)
                self.client.upload_turtle(turtle, self.graph_uri)
                batches_uploaded += 1
                logger.info("Uploaded batch %d (%d rows so far)", batches_uploaded, total_rows)
                batch = []

        # Upload remaining rows
        if batch:
            turtle = self.rows_to_turtle(batch)
            self.client.upload_turtle(turtle, self.graph_uri)
            batches_uploaded += 1

        con.close()
        logger.info("ETL complete: %d rows in %d batches", total_rows, batches_uploaded)
        return batches_uploaded

    # ── Turtle helpers ────────────────────────────────────────────────────────

    @staticmethod
    def turtle_header() -> str:
        return (
            "@prefix pmo:  <http://pmo.research/ontology#> .\n"
            "@prefix pmir: <http://pmo.research/instance/> .\n"
            "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .\n"
            "@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n\n"
        )

    @staticmethod
    def escape_str(value: str | None) -> str:
        if value is None:
            return ""
        return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
