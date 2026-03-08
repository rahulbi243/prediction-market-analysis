"""News retriever.

Primary: DuckDuckGo search (no key required).
Fallback: Exa API when EXA_API_KEY is set in the environment.

Snippets are filtered to only include results published before the
market's ``created_at`` timestamp (temporal purity, per paper §3.2).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    snippet: str
    url: str
    published_at: datetime | None = None
    source: str = "duckduckgo"


class NewsRetriever:
    """Fetch news snippets for a prediction market question.

    Args:
        n: Number of snippets to return per query.
        use_exa: Override to force/disable Exa (auto-detected via env otherwise).
    """

    def __init__(self, n: int = 10, use_exa: bool | None = None):
        self.n = n
        self._exa_key = os.getenv("EXA_API_KEY", "")
        self._use_exa = use_exa if use_exa is not None else bool(self._exa_key)

    def fetch(self, question: str, created_at: datetime | None = None) -> list[NewsItem]:
        """Return up to ``self.n`` news snippets relevant to ``question``.

        Items published after ``created_at`` are filtered out (temporal purity).
        """
        if self._use_exa:
            items = self._fetch_exa(question)
        else:
            items = self._fetch_ddg(question)

        # Temporal filter
        if created_at:
            cutoff = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
            items = [i for i in items if i.published_at is None or i.published_at <= cutoff]

        return items[: self.n]

    # ── DuckDuckGo ────────────────────────────────────────────────────────────

    def _fetch_ddg(self, question: str) -> list[NewsItem]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("duckduckgo-search not installed; returning empty news list")
            return []

        items: list[NewsItem] = []
        try:
            with DDGS() as ddgs:
                for result in ddgs.news(question, max_results=self.n * 2):
                    pub = _parse_date(result.get("date"))
                    items.append(
                        NewsItem(
                            title=result.get("title", ""),
                            snippet=result.get("body", ""),
                            url=result.get("url", ""),
                            published_at=pub,
                            source="duckduckgo",
                        )
                    )
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)

        return items

    # ── Exa ───────────────────────────────────────────────────────────────────

    def _fetch_exa(self, question: str) -> list[NewsItem]:
        try:
            from exa_py import Exa  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("exa-py not installed; falling back to DuckDuckGo")
            return self._fetch_ddg(question)

        try:
            exa = Exa(api_key=self._exa_key)
            results = exa.search_and_contents(
                question,
                num_results=self.n * 2,
                text={"max_characters": 500},
                type="neural",
            )
            items: list[NewsItem] = []
            for r in results.results:
                pub = _parse_date(getattr(r, "published_date", None))
                items.append(
                    NewsItem(
                        title=getattr(r, "title", ""),
                        snippet=getattr(r, "text", ""),
                        url=getattr(r, "url", ""),
                        published_at=pub,
                        source="exa",
                    )
                )
            return items
        except Exception as exc:
            logger.warning("Exa search failed (%s); falling back to DuckDuckGo", exc)
            return self._fetch_ddg(question)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(str(value)[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
