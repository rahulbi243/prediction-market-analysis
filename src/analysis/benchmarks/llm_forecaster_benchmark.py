"""Benchmark 1: LLM Forecaster Benchmark.

Novel contribution vs paper:
- Kalshi + Polymarket (vs Metaculus/Manifold in original paper)
- 1000+ questions from live dataset
- Crypto as 7th domain (not in original paper)
- Accuracy × Brier × ECE per domain and per condition (raw vs news)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.loader import load_forecasts
from src.backtest.metrics import ForecastingMetrics
from src.common.analysis import Analysis, AnalysisOutput

_DOMAIN_ORDER = ["Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"]
_COLORS = {"raw": "#4C72B0", "news": "#DD8452"}


class LLMForecasterBenchmark(Analysis):
    """Accuracy × calibration breakdown by domain and news condition."""

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="llm_forecaster_benchmark",
            description="LLM accuracy, Brier score and ECE by domain and news condition",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        rows = []
        for condition in ("raw", "news"):
            df = load_forecasts(self.forecasts_dir, condition=condition)
            if df.empty:
                continue
            for domain in df["domain"].unique():
                sub = df[df["domain"] == domain]
                m = ForecastingMetrics.compute(sub)
                rows.append({
                    "condition": condition,
                    "domain": domain,
                    "n": m.n,
                    "accuracy": m.accuracy,
                    "brier_score": m.brier_score,
                    "ece": m.ece,
                    "log_loss": m.log_loss,
                })

        data = pd.DataFrame(rows)
        if data.empty:
            return AnalysisOutput(data=data, metadata={"error": "no forecast data"})

        fig = self._create_figure(data)
        return AnalysisOutput(figure=fig, data=data)

    def _create_figure(self, data: pd.DataFrame) -> plt.Figure:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        metrics = ["accuracy", "brier_score", "ece"]
        titles = ["Accuracy (↑ better)", "Brier Score (↓ better)", "ECE (↓ better)"]

        domains = [d for d in _DOMAIN_ORDER if d in data["domain"].values]
        x = np.arange(len(domains))
        width = 0.35

        for ax, metric, title in zip(axes, metrics, titles):
            for i, condition in enumerate(("raw", "news")):
                sub = data[data["condition"] == condition].set_index("domain")
                vals = [sub.loc[d, metric] if d in sub.index else float("nan") for d in domains]
                offset = (i - 0.5) * width
                ax.bar(x + offset, vals, width, label=condition, color=_COLORS[condition], alpha=0.85)

            ax.set_title(title, fontsize=11)
            ax.set_xticks(x)
            ax.set_xticklabels(domains, rotation=30, ha="right", fontsize=8)
            ax.legend(fontsize=8)
            if metric == "accuracy":
                ax.axhline(0.5, linestyle="--", color="grey", linewidth=0.8)
                ax.set_ylim(0, 1)

        fig.suptitle("Benchmark 1: LLM Forecaster — Accuracy by Domain & Condition", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig
