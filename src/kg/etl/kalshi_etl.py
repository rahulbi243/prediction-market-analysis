"""Kalshi Parquet → RDF ETL.

Uses get_hierarchy() for domain mapping.
URI pattern: pmir:kalshi/{ticker}
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.analysis.kalshi.util.categories import get_hierarchy
from src.kg.etl.base import BaseETL

logger = logging.getLogger(__name__)

# Map Kalshi groups to the 7 paper domains
KALSHI_GROUP_TO_PAPER_DOMAIN: dict[str, str] = {
    "Politics": "Politics",
    "Finance": "Finance",
    "Sports": "Sports",
    "Science/Tech": "Technology",
    "Entertainment": "Entertainment",
    "World Events": "Geopolitics",
    "Crypto": "Crypto",
    "Weather": "Finance",      # weather → Finance (macro/commodity adjacent)
    "Media": "Entertainment",
    "Esports": "Sports",
    "Other": "Politics",       # fallback
}


def _group_to_domain(group: str) -> str:
    return KALSHI_GROUP_TO_PAPER_DOMAIN.get(group, "Politics")


class KalshiETL(BaseETL):
    """Load Kalshi markets Parquet files into the KG."""

    def __init__(self, client=None, limit: int = 10000):
        super().__init__(client)
        self.limit = limit

    @property
    def graph_uri(self) -> str:
        return "http://pmo.research/graph/kalshi"

    def build_query(self, data_dir: Path) -> str:
        glob = str(data_dir / "*.parquet")
        return f"""
            SELECT
                ticker,
                event_ticker,
                title,
                status,
                result,
                volume,
                last_price,
                created_time,
                close_time
            FROM read_parquet('{glob}')
            WHERE result IN ('yes', 'no')
              AND status = 'finalized'
            ORDER BY volume DESC
            LIMIT {self.limit}
        """

    def rows_to_turtle(self, rows: list[dict]) -> str:
        lines = [self.turtle_header()]
        for row in rows:
            ticker = row.get("ticker", "")
            if not ticker:
                continue

            safe_ticker = ticker.replace("/", "_").replace(" ", "_")
            uri = f"<http://pmo.research/instance/kalshi/{safe_ticker}>"

            event_ticker = row.get("event_ticker") or ticker
            group, _cat, subcat = get_hierarchy(event_ticker)
            domain = _group_to_domain(group)

            title = self.escape_str(row.get("title") or ticker)
            result = self.escape_str(row.get("result") or "")
            volume = row.get("volume") or 0
            created = row.get("created_time")
            close = row.get("close_time")

            triples = [
                f"{uri} a pmo:KalshiMarket, pmo:Market ;",
                f'    pmo:marketId "{self.escape_str(ticker)}" ;',
                '    pmo:platform "kalshi" ;',
                f'    pmo:question "{title}" ;',
                f'    pmo:result "{result}" ;',
                f'    pmo:volume "{float(volume)}"^^xsd:double ;',
                f'    pmo:subcategory "{self.escape_str(subcat)}" ;',
                f"    pmo:belongsToDomain pmo:{domain} ;",
            ]

            if created:
                dt = str(created)[:19].replace(" ", "T")
                triples.append(f'    pmo:createdAt "{dt}"^^xsd:dateTime ;')
            if close:
                dt = str(close)[:19].replace(" ", "T")
                triples.append(f'    pmo:closeTime "{dt}"^^xsd:dateTime ;')

            # close last triple properly
            triples[-1] = triples[-1].rstrip(" ;") + " ."
            lines.append("\n".join(triples))
            lines.append("")

        return "\n".join(lines)
