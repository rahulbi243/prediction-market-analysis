"""Polymarket Parquet → RDF ETL.

Uses keyword-based domain mapping on the question field.
URI pattern: pmir:polymarket/{condition_id}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.kg.etl.base import BaseETL

logger = logging.getLogger(__name__)

# Keyword → paper domain mapping (order matters — more specific first)
_DOMAIN_KEYWORDS: list[tuple[str, str]] = [
    # Crypto
    (r"\b(bitcoin|btc|ethereum|eth|crypto|sol|xrp|doge|nft|blockchain|defi)\b", "Crypto"),
    # Finance
    (r"\b(fed|federal reserve|interest rate|s&p|nasdaq|dow|gdp|cpi|inflation|recession|stock|market cap|ipo|tariff|oil|gas price)\b", "Finance"),
    # Sports
    (r"\b(nfl|nba|mlb|nhl|mls|ufc|f1|formula 1|soccer|football|basketball|baseball|hockey|golf|tennis|championship|super bowl|world cup|playoffs)\b", "Sports"),
    # Entertainment
    (r"\b(oscar|grammy|emmy|bafta|movie|film|song|album|spotify|netflix|youtube|celebrity|award|box office)\b", "Entertainment"),
    # Geopolitics
    (r"\b(war|ceasefire|nato|un|united nations|peace|treaty|invasion|conflict|ukraine|russia|china|taiwan|iran|israel|gaza|sanctions)\b", "Geopolitics"),
    # Politics
    (r"\b(president|election|senate|house|congress|democrat|republican|vote|ballot|governor|minister|parliament|prime minister|poll)\b", "Politics"),
    # Technology
    (r"\b(ai|gpt|openai|llm|spacex|nasa|apple|google|microsoft|meta|tesla|tech|robot|launch|starship)\b", "Technology"),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), domain) for pattern, domain in _DOMAIN_KEYWORDS]


def _classify_question(question: str | None) -> str:
    """Map a Polymarket question to one of the 7 paper domains via keyword matching."""
    if not question:
        return "Politics"
    for pattern, domain in _COMPILED:
        if pattern.search(question):
            return domain
    return "Politics"  # default


class PolymarketETL(BaseETL):
    """Load Polymarket markets Parquet files into the KG."""

    def __init__(self, client=None, limit: int = 10000):
        super().__init__(client)
        self.limit = limit

    @property
    def graph_uri(self) -> str:
        return "http://pmo.research/graph/polymarket"

    def build_query(self, data_dir: Path) -> str:
        glob = str(data_dir / "*.parquet")
        return f"""
            SELECT
                condition_id,
                question,
                volume,
                active,
                closed,
                end_date,
                created_at,
                outcome_prices,
                outcomes
            FROM read_parquet('{glob}')
            WHERE closed = true
              AND condition_id IS NOT NULL
            ORDER BY volume DESC
            LIMIT {self.limit}
        """

    def rows_to_turtle(self, rows: list[dict]) -> str:
        lines = [self.turtle_header()]
        for row in rows:
            cid = row.get("condition_id", "")
            if not cid:
                continue

            safe_cid = str(cid).replace("/", "_").replace(" ", "_")
            uri = f"<http://pmo.research/instance/polymarket/{safe_cid}>"

            question = row.get("question") or ""
            domain = _classify_question(question)
            volume = row.get("volume") or 0
            created = row.get("created_at")
            close = row.get("end_date")

            # Determine result from outcome_prices (price closest to 1.0 wins)
            result = _infer_result(row.get("outcome_prices"), row.get("outcomes"))

            triples = [
                f"{uri} a pmo:PolymarketMarket, pmo:Market ;",
                f'    pmo:marketId "{self.escape_str(cid)}" ;',
                '    pmo:platform "polymarket" ;',
                f'    pmo:question "{self.escape_str(question)}" ;',
                f'    pmo:volume "{float(volume)}"^^xsd:double ;',
                f"    pmo:belongsToDomain pmo:{domain} ;",
            ]

            if result:
                triples.append(f'    pmo:result "{result}" ;')
            if created:
                dt = str(created)[:19].replace(" ", "T")
                triples.append(f'    pmo:createdAt "{dt}"^^xsd:dateTime ;')
            if close:
                dt = str(close)[:19].replace(" ", "T")
                triples.append(f'    pmo:closeTime "{dt}"^^xsd:dateTime ;')

            triples[-1] = triples[-1].rstrip(" ;") + " ."
            lines.append("\n".join(triples))
            lines.append("")

        return "\n".join(lines)


def _infer_result(outcome_prices: str | None, outcomes: str | None) -> str | None:
    """Infer yes/no from serialised outcome_prices and outcomes fields."""
    if not outcome_prices or not outcomes:
        return None
    try:
        import json
        prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
        outs = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
        if not prices or not outs:
            return None
        # Find the outcome with price closest to 1.0
        prices_f = [float(p) for p in prices]
        max_idx = prices_f.index(max(prices_f))
        winning = str(outs[max_idx]).strip().lower()
        if winning in ("yes", "no"):
            return winning
        # Binary Yes/No market: prices[0] = Yes probability
        if len(prices_f) == 2 and prices_f[0] > 0.5:
            return "yes"
        elif len(prices_f) == 2:
            return "no"
    except Exception:
        pass
    return None
