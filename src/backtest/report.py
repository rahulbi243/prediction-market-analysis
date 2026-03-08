"""BacktestReportAnalysis — extends Analysis for auto-discovery by make analyze."""

from __future__ import annotations

from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.engine import BacktestEngine
from src.backtest.loader import load_forecasts
from src.backtest.metrics import StratifiedMetrics
from src.backtest.strategy import KellyCriterionStrategy
from src.common.analysis import Analysis, AnalysisOutput


class BacktestReport(Analysis):
    """Multi-panel backtest report: equity curve, calibration, accuracy heatmap,
    failure mode frequency.

    Auto-discovered by ``main.py analyze``.
    """

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="backtest_report",
            description="Backtest equity curve, calibration and domain accuracy heatmap",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        df = load_forecasts(self.forecasts_dir, condition="raw")
        if df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "no forecast data"})

        engine = BacktestEngine(strategy=KellyCriterionStrategy())
        metrics, trades_df = engine.run(df)

        fig = self._create_figure(df, metrics, trades_df)
        summary = self._build_summary(metrics)
        return AnalysisOutput(figure=fig, data=summary)

    # ── Figure ────────────────────────────────────────────────────────────────

    def _create_figure(
        self,
        df: pd.DataFrame,
        metrics: StratifiedMetrics,
        trades_df: pd.DataFrame,
    ) -> plt.Figure:
        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.35)

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        self._plot_equity_curve(ax1, trades_df)
        self._plot_calibration(ax2, df)
        self._plot_domain_accuracy(ax3, metrics)
        self._plot_failure_modes(ax4, df)

        fig.suptitle("Backtest Report — LLM Forecasting Agent", fontsize=14, fontweight="bold")
        return fig

    def _plot_equity_curve(self, ax: plt.Axes, trades_df: pd.DataFrame) -> None:
        ax.set_title("Equity Curve")
        ax.set_xlabel("Trade #")
        ax.set_ylabel("Bankroll")
        if trades_df.empty or "bankroll" not in trades_df.columns:
            ax.text(0.5, 0.5, "No trade data", ha="center", va="center", transform=ax.transAxes)
            return
        traded = trades_df[trades_df["bet_fraction"] != 0].reset_index(drop=True)
        if traded.empty:
            ax.text(0.5, 0.5, "No bets placed", ha="center", va="center", transform=ax.transAxes)
            return
        ax.plot(traded.index, traded["bankroll"], color="#1f77b4", linewidth=1.5)
        ax.axhline(traded["bankroll"].iloc[0], linestyle="--", color="grey", linewidth=0.8)

    def _plot_calibration(self, ax: plt.Axes, df: pd.DataFrame) -> None:
        ax.set_title("Calibration Curve")
        ax.set_xlabel("Predicted Probability")
        ax.set_ylabel("Actual Frequency")
        df2 = df[df["true_result"].isin(["yes", "no"])].copy()
        if df2.empty:
            return
        probs = df2["calibrated_probability"].astype(float).clip(0.01, 0.99)
        actuals = (df2["true_result"] == "yes").astype(float)
        bins = np.linspace(0, 1, 11)
        bin_mid, bin_acc = [], []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (probs >= lo) & (probs < hi)
            if mask.sum() >= 5:
                bin_mid.append((lo + hi) / 2)
                bin_acc.append(actuals[mask].mean())
        ax.plot([0, 1], [0, 1], "--", color="grey", linewidth=0.8, label="Perfect")
        if bin_mid:
            ax.plot(bin_mid, bin_acc, "o-", color="#d62728", linewidth=1.5, label="Actual")
        ax.legend(fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    def _plot_domain_accuracy(self, ax: plt.Axes, metrics: StratifiedMetrics) -> None:
        ax.set_title("Accuracy by Domain")
        if not metrics.by_domain:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            return
        domains = list(metrics.by_domain.keys())
        accs = [metrics.by_domain[d].accuracy for d in domains]
        colors = ["#2ca02c" if a >= 0.6 else "#ff7f0e" if a >= 0.5 else "#d62728" for a in accs]
        bars = ax.barh(domains, accs, color=colors)
        ax.axvline(0.5, linestyle="--", color="grey", linewidth=0.8)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Accuracy")
        for bar, acc in zip(bars, accs):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{acc:.1%}", va="center", fontsize=8)

    def _plot_failure_modes(self, ax: plt.Axes, df: pd.DataFrame) -> None:
        ax.set_title("Failure Mode Frequency")
        if "failure_modes" not in df.columns:
            return
        all_modes: list[str] = []
        for val in df["failure_modes"].dropna():
            all_modes.extend(str(val).split(","))
        all_modes = [m.strip() for m in all_modes if m.strip() and m.strip() != "nan"]
        if not all_modes:
            ax.text(0.5, 0.5, "No failure modes detected", ha="center", va="center", transform=ax.transAxes)
            return
        from collections import Counter
        counts = Counter(all_modes)
        modes = list(counts.keys())
        freqs = [counts[m] for m in modes]
        ax.bar(modes, freqs, color="#9467bd")
        ax.set_ylabel("Count")
        ax.tick_params(axis="x", rotation=15)

    # ── Summary table ─────────────────────────────────────────────────────────

    def _build_summary(self, metrics: StratifiedMetrics) -> pd.DataFrame:
        rows = []
        f = metrics.overall_forecasting
        t = metrics.overall_trading
        rows.append({
            "segment": "overall",
            "n": f.n,
            "accuracy": f.accuracy,
            "brier_score": f.brier_score,
            "ece": f.ece,
            "roi": t.roi,
            "sharpe": t.sharpe,
            "max_drawdown": t.max_drawdown,
            "win_rate": t.win_rate,
        })
        for domain, fm in metrics.by_domain.items():
            rows.append({
                "segment": f"domain:{domain}",
                "n": fm.n,
                "accuracy": fm.accuracy,
                "brier_score": fm.brier_score,
                "ece": fm.ece,
                "roi": float("nan"),
                "sharpe": float("nan"),
                "max_drawdown": float("nan"),
                "win_rate": float("nan"),
            })
        return pd.DataFrame(rows)
