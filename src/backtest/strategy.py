"""Betting strategy interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.agent.signal import ForecastSignal


class Strategy(ABC):
    """Abstract betting strategy.

    ``bet_size`` returns a fraction of bankroll to bet (0.0 = pass).
    Positive return → bet YES; negative → bet NO (callers use abs value +
    ``signal.bet_direction`` to determine side).
    """

    @abstractmethod
    def bet_size(self, signal: ForecastSignal, market_price: float) -> float:
        """Return signed bankroll fraction. 0.0 means do not bet."""


class FlatBetStrategy(Strategy):
    """Flat bet of fixed size when |edge| exceeds threshold."""

    def __init__(self, fraction: float = 0.02, edge_threshold: float = 0.05):
        self.fraction = fraction
        self.threshold = edge_threshold

    def bet_size(self, signal: ForecastSignal, market_price: float) -> float:
        edge = signal.calibrated_probability - market_price
        if abs(edge) < self.threshold:
            return 0.0
        return self.fraction * (1 if edge > 0 else -1)


class KellyCriterionStrategy(Strategy):
    """Fractional Kelly, capped at max_fraction of bankroll."""

    def __init__(self, kelly_fraction: float = 0.5, max_fraction: float = 0.20):
        self.kelly_multiplier = kelly_fraction
        self.max_fraction = max_fraction

    def bet_size(self, signal: ForecastSignal, market_price: float) -> float:
        if signal.kelly_fraction == 0.0:
            return 0.0
        sized = signal.kelly_fraction * self.kelly_multiplier
        capped = min(sized, self.max_fraction)
        return capped * (1 if signal.bet_direction == "yes" else -1)


class ConfidenceScaledStrategy(Strategy):
    """Kelly × (1 − CI_width) — shrinks bet when confidence interval is wide."""

    def __init__(self, kelly_fraction: float = 0.5, max_fraction: float = 0.20):
        self.kelly_multiplier = kelly_fraction
        self.max_fraction = max_fraction

    def bet_size(self, signal: ForecastSignal, market_price: float) -> float:
        if signal.kelly_fraction == 0.0:
            return 0.0
        ci_width = max(0.0, signal.confidence_high - signal.confidence_low)
        confidence_scalar = max(0.0, 1.0 - ci_width)
        sized = signal.kelly_fraction * self.kelly_multiplier * confidence_scalar
        capped = min(sized, self.max_fraction)
        return capped * (1 if signal.bet_direction == "yes" else -1)
