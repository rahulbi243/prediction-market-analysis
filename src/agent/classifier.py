"""Domain classifier.

- Kalshi fast path: get_hierarchy(event_ticker) via KALSHI_GROUP_TO_PAPER_DOMAIN
- Polymarket: keyword trie on question text → LLM fallback for ambiguous cases
"""

from __future__ import annotations

import logging

from src.analysis.kalshi.util.categories import get_hierarchy
from src.kg.etl.kalshi_etl import KALSHI_GROUP_TO_PAPER_DOMAIN
from src.kg.etl.polymarket_etl import _COMPILED as _POLY_COMPILED

logger = logging.getLogger(__name__)

PAPER_DOMAINS = ["Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"]


class DomainClassifier:
    """Classify a market question into one of the 7 paper domains.

    For Kalshi markets the event_ticker prefix is used (fast, deterministic).
    For Polymarket questions a keyword scan is tried first; when no keyword
    matches an LLM call is made as a fallback (pass ``llm_client`` to enable).
    """

    def __init__(self, llm_client=None):
        self._llm = llm_client

    def classify(
        self,
        question: str,
        platform: str = "polymarket",
        event_ticker: str | None = None,
    ) -> tuple[str, str]:
        """Return (domain, subcategory)."""
        if platform == "kalshi" and event_ticker:
            return self._classify_kalshi(event_ticker)
        return self._classify_polymarket(question)

    # ── Kalshi fast path ──────────────────────────────────────────────────────

    def _classify_kalshi(self, event_ticker: str) -> tuple[str, str]:
        group, _cat, subcat = get_hierarchy(event_ticker)
        domain = KALSHI_GROUP_TO_PAPER_DOMAIN.get(group, "Politics")
        return domain, subcat

    # ── Polymarket keyword + LLM ──────────────────────────────────────────────

    def _classify_polymarket(self, question: str) -> tuple[str, str]:
        for pattern, domain in _POLY_COMPILED:
            m = pattern.search(question)
            if m:
                return domain, m.group(0)

        # LLM fallback
        if self._llm:
            domain = self._llm_classify(question)
            return domain, "LLM-classified"

        return "Politics", "unclassified"

    def _llm_classify(self, question: str) -> str:
        domains_list = ", ".join(PAPER_DOMAINS)
        system = (
            "You are a prediction market domain classifier. "
            f"Respond with exactly one domain from: {domains_list}. "
            "Output only the domain name, nothing else."
        )
        result = self._llm.complete(system=system, user=question).strip()
        for d in PAPER_DOMAINS:
            if d.lower() in result.lower():
                return d
        return "Politics"
