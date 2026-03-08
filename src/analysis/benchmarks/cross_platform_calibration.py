"""Benchmark 2: Cross-Platform Calibration.

Novel contribution: First matched-pairs Kalshi vs Polymarket
Brier / ECE comparison on the same question types.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.loader import load_forecasts
from src.backtest.metrics import ForecastingMetrics
from src.common.analysis import Analysis, AnalysisOutput

_PLATFORMS = ["kalshi", "polymarket"]
_COLORS = {"kalshi": "#1f77b4", "polymarket": "#ff7f0e"}


class CrossPlatformCalibration(Analysis):
    """Brier score and ECE comparison between Kalshi and Polymarket."""

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="cross_platform_calibration",
            description="Matched Kalshi vs Polymarket Brier/ECE calibration comparison",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        df = load_forecasts(self.forecasts_dir, condition="raw")
        if df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "no forecast data"})

        rows = []
        for platform in _PLATFORMS:
            sub = df[df["platform"] == platform]
            overall = ForecastingMetrics.compute(sub)
            rows.append({
                "platform": platform,
                "domain": "Overall",
                "n": overall.n,
                "brier_score": overall.brier_score,
                "ece": overall.ece,
                "accuracy": overall.accuracy,
            })
            for domain, grp in sub.groupby("domain"):
                m = ForecastingMetrics.compute(grp)
                rows.append({
                    "platform": platform,
                    "domain": str(domain),
                    "n": m.n,
                    "brier_score": m.brier_score,
                    "ece": m.ece,
                    "accuracy": m.accuracy,
                })

        data = pd.DataFrame(rows)
        fig = self._create_figure(data)
        return AnalysisOutput(figure=fig, data=data)

    def _create_figure(self, data: pd.DataFrame) -> plt.Figure:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        domains = data["domain"].unique()
        x = np.arange(len(domains))
        width = 0.35

        for ax, metric, title in zip(axes, ["brier_score", "ece"],
                                     ["Brier Score (↓ better)", "ECE (↓ better)"]):
            for i, platform in enumerate(_PLATFORMS):
                sub = data[data["platform"] == platform].set_index("domain")
                vals = [sub.loc[d, metric] if d in sub.index else float("nan") for d in domains]
                offset = (i - 0.5) * width
                ax.bar(x + offset, vals, width, label=platform, color=_COLORS[platform], alpha=0.85)
            ax.set_title(title, fontsize=11)
            ax.set_xticks(x)
            ax.set_xticklabels(domains, rotation=30, ha="right", fontsize=8)
            ax.legend()

        fig.suptitle("Benchmark 2: Cross-Platform Calibration (Kalshi vs Polymarket)", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig
