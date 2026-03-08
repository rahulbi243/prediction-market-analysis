"""ForecastSignal dataclass — the output of a single LLM forecast run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ForecastSignal:
    # Market identification
    market_id: str
    platform: str                        # "kalshi" | "polymarket"
    domain: str                          # one of the 7 paper domains
    subcategory: str

    # LLM metadata
    model: str
    condition: str                       # "raw" | "news"

    # Probability outputs
    raw_probability: float               # 0.0 – 1.0
    calibrated_probability: float        # post-calibration
    confidence_low: float                # 90% CI lower bound
    confidence_high: float               # 90% CI upper bound

    # Reasoning + failure modes
    failure_modes: list[str] = field(default_factory=list)
    reasoning: str = ""

    # News context (only populated for "news" condition)
    news_snippets: list[dict] = field(default_factory=list)

    # Temporal
    forecasted_at: datetime = field(default_factory=datetime.utcnow)

    # Trading signal
    market_price: float = 0.5           # last market price at forecast time (0–1)
    edge: float = 0.0                   # calibrated_prob - market_price
    bet_direction: str = "pass"         # "yes" | "no" | "pass"
    kelly_fraction: float = 0.0         # recommended bet size (fraction of bankroll)

    def to_dict(self) -> dict:
        return {
            "market_id": self.market_id,
            "platform": self.platform,
            "domain": self.domain,
            "subcategory": self.subcategory,
            "model": self.model,
            "condition": self.condition,
            "raw_probability": self.raw_probability,
            "calibrated_probability": self.calibrated_probability,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "failure_modes": ",".join(self.failure_modes),
            "reasoning": self.reasoning,
            "news_snippets": str(self.news_snippets),
            "forecasted_at": self.forecasted_at.isoformat(),
            "market_price": self.market_price,
            "edge": self.edge,
            "bet_direction": self.bet_direction,
            "kelly_fraction": self.kelly_fraction,
        }
