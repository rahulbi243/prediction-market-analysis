"""Forecasting and trading metrics dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ForecastingMetrics:
    """Accuracy and calibration metrics for a set of forecasts."""

    n: int = 0
    accuracy: float = float("nan")
    brier_score: float = float("nan")
    log_loss: float = float("nan")
    ece: float = float("nan")           # Expected Calibration Error (15 bins)

    @classmethod
    def compute(cls, df: pd.DataFrame) -> ForecastingMetrics:
        """Compute from a DataFrame with columns:
        calibrated_probability, true_result (yes/no).
        """
        df = df[df["true_result"].isin(["yes", "no"])].copy()
        if df.empty:
            return cls()

        n = len(df)
        probs = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
        actuals = (df["true_result"] == "yes").astype(float)

        predicted = (probs >= 0.5).astype(float)
        accuracy = (predicted == actuals).mean()

        brier = ((probs - actuals) ** 2).mean()

        log_loss = -np.mean(
            actuals * np.log(probs) + (1 - actuals) * np.log(1 - probs)
        )

        ece = _compute_ece(probs.values, actuals.values)

        return cls(n=n, accuracy=float(accuracy), brier_score=float(brier),
                   log_loss=float(log_loss), ece=ece)


@dataclass
class TradingMetrics:
    """P&L and risk metrics for a backtest run."""

    n_trades: int = 0
    roi: float = float("nan")
    sharpe: float = float("nan")
    max_drawdown: float = float("nan")
    win_rate: float = float("nan")
    profit_factor: float = float("nan")

    @classmethod
    def compute(cls, returns: list[float]) -> TradingMetrics:
        """Compute from a list of per-trade P&L returns (fraction of bankroll)."""
        if not returns:
            return cls()

        arr = np.array(returns, dtype=float)
        n = len(arr)
        roi = float(arr.mean())
        sharpe = float(arr.mean() / arr.std()) if arr.std() > 0 else 0.0

        cumulative = np.cumprod(1 + arr)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_dd = float(drawdowns.min())

        wins = arr[arr > 0]
        losses = arr[arr < 0]
        win_rate = float(len(wins) / n) if n > 0 else 0.0
        profit_factor = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")

        return cls(
            n_trades=n,
            roi=roi,
            sharpe=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )


@dataclass
class StratifiedMetrics:
    """Metrics broken down by domain and platform."""

    overall_forecasting: ForecastingMetrics = field(default_factory=ForecastingMetrics)
    overall_trading: TradingMetrics = field(default_factory=TradingMetrics)
    by_domain: dict[str, ForecastingMetrics] = field(default_factory=dict)
    by_platform: dict[str, ForecastingMetrics] = field(default_factory=dict)


def _compute_ece(probs: np.ndarray, actuals: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error via equal-width binning."""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(probs)
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (probs >= lo) & (probs < hi)
        if not mask.any():
            continue
        bin_conf = probs[mask].mean()
        bin_acc = actuals[mask].mean()
        ece += (mask.sum() / n) * abs(bin_conf - bin_acc)
    return float(ece)
