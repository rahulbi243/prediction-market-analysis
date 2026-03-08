"""LLMForecaster — the core forecasting pipeline.

Runs a market through the 7-step prompt in both "raw" and "news" conditions,
extracts the probability, applies calibration, detects failure modes, and
computes trading signal fields.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from src.agent.calibrator import calibrate
from src.agent.classifier import DomainClassifier
from src.agent.failure_detector import detect_failure_modes
from src.agent.llm import LLMClient
from src.agent.news import NewsItem, NewsRetriever
from src.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from src.agent.signal import ForecastSignal

logger = logging.getLogger(__name__)

_PROB_RE = re.compile(r"FINAL_PROB:\s*(\d+)", re.IGNORECASE)
_CI_LOW_RE = re.compile(r"CI_LOW:\s*(\d+)", re.IGNORECASE)
_CI_HIGH_RE = re.compile(r"CI_HIGH:\s*(\d+)", re.IGNORECASE)
_INIT_PROB_RE = re.compile(r"INITIAL_PROB:\s*(\d+)", re.IGNORECASE)


class LLMForecaster:
    """Orchestrates classification → news retrieval → LLM call → signal assembly.

    Args:
        llm_client:     LLMClient instance.
        news_retriever: NewsRetriever instance (optional; skipped if None).
        conditions:     List of conditions to run; default ["raw", "news"].
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        news_retriever: NewsRetriever | None = None,
        conditions: list[str] | None = None,
    ):
        self.llm = llm_client or LLMClient()
        self.news = news_retriever or NewsRetriever()
        self.conditions = conditions or ["raw", "news"]
        self.classifier = DomainClassifier(llm_client=self.llm)

    def forecast(
        self,
        market_id: str,
        platform: str,
        question: str,
        market_price: float = 0.5,
        created_at: datetime | None = None,
        event_ticker: str | None = None,
    ) -> list[ForecastSignal]:
        """Run the full forecasting pipeline for one market.

        Returns one ForecastSignal per condition (raw / news).
        """
        # 1. Classify domain
        domain, subcategory = self.classifier.classify(
            question=question,
            platform=platform,
            event_ticker=event_ticker,
        )

        # 2. Fetch news (shared across conditions)
        news_items: list[NewsItem] = []
        if "news" in self.conditions:
            try:
                news_items = self.news.fetch(question, created_at=created_at)
            except Exception as exc:
                logger.warning("News fetch failed: %s", exc)

        signals: list[ForecastSignal] = []

        for condition in self.conditions:
            snippets = (
                [{"title": n.title, "snippet": n.snippet, "url": n.url} for n in news_items]
                if condition == "news"
                else []
            )

            user_prompt = build_user_prompt(question, condition, snippets)

            try:
                reasoning = self.llm.complete(system=SYSTEM_PROMPT, user=user_prompt)
            except Exception as exc:
                logger.error("LLM call failed for %s/%s: %s", market_id, condition, exc)
                continue

            raw_prob = _extract_prob(reasoning)
            ci_low = _extract_ci_low(reasoning)
            ci_high = _extract_ci_high(reasoning)
            cal_prob = calibrate(raw_prob, domain, condition)
            failure_modes = detect_failure_modes(reasoning)

            edge = cal_prob - market_price
            bet_direction = "pass"
            kelly = 0.0
            if abs(edge) > 0.05:
                bet_direction = "yes" if edge > 0 else "no"
                kelly = _kelly(cal_prob if edge > 0 else 1 - cal_prob, market_price if edge > 0 else 1 - market_price)

            signals.append(
                ForecastSignal(
                    market_id=market_id,
                    platform=platform,
                    domain=domain,
                    subcategory=subcategory,
                    model=self.llm.model,
                    condition=condition,
                    raw_probability=raw_prob,
                    calibrated_probability=cal_prob,
                    confidence_low=ci_low / 100.0,
                    confidence_high=ci_high / 100.0,
                    failure_modes=failure_modes,
                    reasoning=reasoning,
                    news_snippets=snippets,
                    forecasted_at=datetime.utcnow(),
                    market_price=market_price,
                    edge=edge,
                    bet_direction=bet_direction,
                    kelly_fraction=kelly,
                )
            )

        return signals


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _extract_prob(text: str) -> float:
    m = _PROB_RE.search(text) or _INIT_PROB_RE.search(text)
    if m:
        return max(1, min(99, int(m.group(1)))) / 100.0
    return 0.5


def _extract_ci_low(text: str) -> float:
    m = _CI_LOW_RE.search(text)
    return int(m.group(1)) if m else 20.0


def _extract_ci_high(text: str) -> float:
    m = _CI_HIGH_RE.search(text)
    return int(m.group(1)) if m else 80.0


def _kelly(win_prob: float, win_price: float) -> float:
    """Fractional Kelly criterion, capped at 20% of bankroll."""
    if win_price <= 0 or win_price >= 1:
        return 0.0
    b = (1.0 - win_price) / win_price  # odds
    q = 1.0 - win_prob
    kelly = (b * win_prob - q) / b
    return max(0.0, min(0.20, kelly * 0.5))  # half-Kelly, capped at 20%
