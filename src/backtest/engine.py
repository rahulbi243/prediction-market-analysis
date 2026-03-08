"""BacktestEngine — replays signals against historical market outcomes."""

from __future__ import annotations

import logging

import pandas as pd

from src.backtest.metrics import ForecastingMetrics, StratifiedMetrics, TradingMetrics
from src.backtest.strategy import Strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Replay forecast signals against known outcomes and compute metrics.

    Args:
        strategy: Betting strategy instance.
        initial_bankroll: Starting capital (notional units).
    """

    def __init__(self, strategy: Strategy, initial_bankroll: float = 1000.0):
        self.strategy = strategy
        self.initial_bankroll = initial_bankroll

    def run(self, df: pd.DataFrame) -> tuple[StratifiedMetrics, pd.DataFrame]:
        """Run the backtest.

        Args:
            df: DataFrame from ``loader.load_forecasts()``.  Must contain columns:
                calibrated_probability, market_price, true_result, domain, platform,
                bet_direction, kelly_fraction, confidence_low, confidence_high.

        Returns:
            (StratifiedMetrics, trades_df) — metrics + per-trade ledger.
        """
        df = df[df["true_result"].isin(["yes", "no"])].copy()
        if df.empty:
            return StratifiedMetrics(), pd.DataFrame()

        # Reconstruct ForecastSignal-like objects from DataFrame rows
        records: list[dict] = []
        trade_returns: list[float] = []
        bankroll = self.initial_bankroll

        for _, row in df.iterrows():
            signal = _RowSignal(row)
            market_price = float(row.get("market_price", 0.5))
            frac = self.strategy.bet_size(signal, market_price)

            if frac == 0.0:
                records.append({**row.to_dict(), "bet_fraction": 0.0, "pnl": 0.0, "bankroll": bankroll})
                continue

            bet_yes = frac > 0
            bet_amount = abs(frac) * bankroll
            actual_yes = row["true_result"] == "yes"

            if bet_yes:
                pnl = bet_amount * ((1 - market_price) / market_price) if actual_yes else -bet_amount
            else:
                pnl = bet_amount * (market_price / (1 - market_price)) if not actual_yes else -bet_amount

            bankroll += pnl
            ret = pnl / (abs(frac) * (bankroll - pnl) + 1e-9)
            trade_returns.append(ret)
            records.append({**row.to_dict(), "bet_fraction": frac, "pnl": pnl, "bankroll": bankroll})

        trades_df = pd.DataFrame(records)

        overall_f = ForecastingMetrics.compute(df)
        overall_t = TradingMetrics.compute(trade_returns)

        by_domain: dict[str, ForecastingMetrics] = {}
        for domain, group in df.groupby("domain"):
            by_domain[str(domain)] = ForecastingMetrics.compute(group)

        by_platform: dict[str, ForecastingMetrics] = {}
        for platform, group in df.groupby("platform"):
            by_platform[str(platform)] = ForecastingMetrics.compute(group)

        metrics = StratifiedMetrics(
            overall_forecasting=overall_f,
            overall_trading=overall_t,
            by_domain=by_domain,
            by_platform=by_platform,
        )
        return metrics, trades_df


class _RowSignal:
    """Adapts a DataFrame row to the interface expected by Strategy.bet_size."""

    def __init__(self, row: pd.Series):
        self.calibrated_probability = float(row.get("calibrated_probability", 0.5))
        self.kelly_fraction = float(row.get("kelly_fraction", 0.0))
        self.bet_direction = str(row.get("bet_direction", "pass"))
        self.confidence_low = float(row.get("confidence_low", 0.2))
        self.confidence_high = float(row.get("confidence_high", 0.8))
