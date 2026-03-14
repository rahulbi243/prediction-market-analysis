"""SQLite-backed pipeline run tracking.

Stores ETL run history so the dashboard can display Pipeline Runs.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "pipeline_runs.db"


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    p = db_path or _DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            file TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            entities INTEGER DEFAULT 0,
            triples INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            violations INTEGER DEFAULT 0,
            error TEXT
        )
    """)
    conn.commit()
    return conn


def start_run(source: str, file: str, db_path: Path | None = None) -> str:
    """Record a new pipeline run starting. Returns the run ID."""
    run_id = uuid.uuid4().hex[:12]
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO runs (id, source, file, started_at, status) VALUES (?, ?, ?, ?, 'running')",
            (run_id, source, file, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return run_id


def finish_run(
    run_id: str,
    *,
    entities: int = 0,
    triples: int = 0,
    status: str = "success",
    violations: int = 0,
    error: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Mark a pipeline run as finished."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """UPDATE runs
               SET finished_at = ?, entities = ?, triples = ?,
                   status = ?, violations = ?, error = ?
               WHERE id = ?""",
            (
                datetime.now(timezone.utc).isoformat(),
                entities,
                triples,
                status,
                violations,
                error,
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_runs(limit: int = 50, db_path: Path | None = None) -> list[dict]:
    """Return recent pipeline runs, newest first."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_run(run_id: str, db_path: Path | None = None) -> dict | None:
    """Return a single run by ID."""
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def last_ingestion_time(db_path: Path | None = None) -> str | None:
    """Return the ISO timestamp of the most recent successful run."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT finished_at FROM runs WHERE status = 'success' ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
        return row["finished_at"] if row else None
    finally:
        conn.close()
