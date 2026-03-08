"""ForecastIndexer — runs the LLM agent over resolved markets and persists signals.

Extends the Indexer base class so it is auto-discovered by ``make index``.

Behaviour:
- Loads resolved markets from Parquet (result IN ('yes','no'), volume > 500)
- Stratified sample of up to N markets per domain per run
- Runs LLMForecaster in both "raw" and "news" conditions
- Writes ForecastSignal dicts to data/forecasts/<run_id>.parquet
- Supports resume via cursor file (data/forecasts/.cursor)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from src.agent.forecaster import LLMForecaster
from src.agent.llm import LLMClient
from src.agent.news import NewsRetriever
from src.common.indexer import Indexer

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent.parent
_FORECASTS_DIR = _BASE_DIR / "data" / "forecasts"
_CURSOR_FILE = _FORECASTS_DIR / ".cursor"

MARKETS_PER_DOMAIN = int(os.getenv("FORECAST_MARKETS_PER_DOMAIN", "50"))
MIN_VOLUME = float(os.getenv("FORECAST_MIN_VOLUME", "500"))


class ForecastIndexer(Indexer):
    """Run LLM forecasts over a stratified sample of resolved markets."""

    def __init__(self):
        super().__init__(
            name="forecast_indexer",
            description="Run LLM agent over resolved markets and save forecast signals",
        )
        self.kalshi_dir = _BASE_DIR / "data" / "kalshi" / "markets"
        self.poly_dir = _BASE_DIR / "data" / "polymarket" / "markets"
        self.output_dir = _FORECASTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        forecaster = LLMForecaster(
            llm_client=LLMClient(),
            news_retriever=NewsRetriever(),
        )

        already_done = self._load_cursor()
        markets = self._load_markets(already_done)

        if not markets:
            logger.info("No markets to process (all done or no data found).")
            print("No markets to process.")
            return

        print(f"Processing {len(markets)} markets across domains...")
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        records: list[dict] = []

        for i, row in enumerate(markets):
            market_id = row["market_id"]
            print(f"[{i+1}/{len(markets)}] {market_id} ({row['domain']})")
            try:
                signals = forecaster.forecast(
                    market_id=market_id,
                    platform=row["platform"],
                    question=row["question"],
                    market_price=row.get("market_price", 0.5),
                    created_at=row.get("created_at"),
                    event_ticker=row.get("event_ticker"),
                )
                for sig in signals:
                    d = sig.to_dict()
                    d["true_result"] = row.get("result", "")
                    # Compute Brier score immediately
                    if d["true_result"] in ("yes", "no"):
                        actual = 1.0 if d["true_result"] == "yes" else 0.0
                        d["brier_score"] = (sig.calibrated_probability - actual) ** 2
                    records.append(d)

                already_done.add(market_id)
                self._save_cursor(already_done)
            except Exception as exc:
                logger.error("Failed on %s: %s", market_id, exc)

        if records:
            df = pd.DataFrame(records)
            out_path = self.output_dir / f"forecasts_{run_id}.parquet"
            df.to_parquet(out_path, index=False)
            print(f"\nSaved {len(records)} forecast records to {out_path}")
        else:
            print("No forecasts generated in this run.")

    # ── Market loading ────────────────────────────────────────────────────────

    def _load_markets(self, skip_ids: set[str]) -> list[dict]:
        """Load a stratified sample of resolved markets from Parquet."""
        con = duckdb.connect()
        markets: list[dict] = []

        # Kalshi
        if self.kalshi_dir.exists():
            markets += self._sample_kalshi(con, skip_ids)

        # Polymarket
        if self.poly_dir.exists():
            markets += self._sample_polymarket(con, skip_ids)

        con.close()
        return markets

    def _sample_kalshi(self, con, skip_ids: set) -> list[dict]:
        from src.analysis.kalshi.util.categories import get_hierarchy
        from src.kg.etl.kalshi_etl import KALSHI_GROUP_TO_PAPER_DOMAIN

        glob = str(self.kalshi_dir / "*.parquet")
        try:
            rows = con.execute(f"""
                SELECT ticker, event_ticker, title, result, volume, last_price,
                       created_time, close_time
                FROM read_parquet('{glob}')
                WHERE result IN ('yes', 'no')
                  AND volume >= {MIN_VOLUME}
                ORDER BY RANDOM()
                LIMIT {MARKETS_PER_DOMAIN * 10}
            """).fetchall()
        except Exception as e:
            logger.warning("Kalshi load failed: %s", e)
            return []

        domain_counts: dict[str, int] = {}
        result = []
        for r in rows:
            ticker, event_ticker, title, result_val, volume, last_price, created, close = r
            if ticker in skip_ids:
                continue
            group, _cat, subcat = get_hierarchy(event_ticker or ticker)
            domain = KALSHI_GROUP_TO_PAPER_DOMAIN.get(group, "Politics")
            if domain_counts.get(domain, 0) >= MARKETS_PER_DOMAIN:
                continue
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            result.append({
                "market_id": ticker,
                "platform": "kalshi",
                "question": title or ticker,
                "result": result_val,
                "domain": domain,
                "subcategory": subcat,
                "volume": volume,
                "market_price": (last_price or 50) / 100.0,
                "created_at": created,
                "event_ticker": event_ticker,
            })
        return result

    def _sample_polymarket(self, con, skip_ids: set) -> list[dict]:
        from src.kg.etl.polymarket_etl import _classify_question, _infer_result

        glob = str(self.poly_dir / "*.parquet")
        try:
            rows = con.execute(f"""
                SELECT condition_id, question, volume, outcome_prices, outcomes,
                       created_at, end_date
                FROM read_parquet('{glob}')
                WHERE closed = true
                  AND condition_id IS NOT NULL
                  AND volume >= {MIN_VOLUME}
                ORDER BY RANDOM()
                LIMIT {MARKETS_PER_DOMAIN * 10}
            """).fetchall()
        except Exception as e:
            logger.warning("Polymarket load failed: %s", e)
            return []

        domain_counts: dict[str, int] = {}
        result = []
        for r in rows:
            cid, question, volume, outcome_prices, outcomes, created, close = r
            if cid in skip_ids:
                continue
            inferred = _infer_result(outcome_prices, outcomes)
            if not inferred:
                continue
            domain = _classify_question(question)
            if domain_counts.get(domain, 0) >= MARKETS_PER_DOMAIN:
                continue
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            result.append({
                "market_id": cid,
                "platform": "polymarket",
                "question": question or "",
                "result": inferred,
                "domain": domain,
                "subcategory": "",
                "volume": volume,
                "market_price": 0.5,
                "created_at": created,
                "event_ticker": None,
            })
        return result

    # ── Cursor (resume support) ───────────────────────────────────────────────

    def _load_cursor(self) -> set[str]:
        if _CURSOR_FILE.exists():
            try:
                return set(json.loads(_CURSOR_FILE.read_text()))
            except Exception:
                pass
        return set()

    def _save_cursor(self, done: set[str]) -> None:
        _CURSOR_FILE.write_text(json.dumps(list(done)))
