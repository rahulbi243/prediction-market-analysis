"""Benchmark 3: Failure Mode Prevalence.

Novel contribution: Quantitative failure mode × domain table;
detector validity cross-check via Brier score delta.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.loader import load_forecasts
from src.common.analysis import Analysis, AnalysisOutput

_FAILURE_MODES = ["RecencyBias", "RumourOverweighting", "DefinitionDrift"]
_DOMAIN_ORDER = ["Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"]


class FailureModePrevalence(Analysis):
    """Failure mode × domain prevalence table and Brier score impact."""

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="failure_mode_prevalence",
            description="Failure mode rate by domain and Brier score impact",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        df = load_forecasts(self.forecasts_dir)
        if df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "no forecast data"})

        df = df[df["true_result"].isin(["yes", "no"])].copy()
        probs = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
        actuals = (df["true_result"] == "yes").astype(float)
        df["brier"] = (probs - actuals) ** 2

        # Explode failure_modes string column into individual flags
        for mode in _FAILURE_MODES:
            df[mode] = df["failure_modes"].astype(str).str.contains(mode, na=False)

        # Prevalence table: domain × failure_mode → rate
        prev_rows = []
        for domain in df["domain"].unique():
            sub = df[df["domain"] == domain]
            row = {"domain": domain, "n": len(sub)}
            for mode in _FAILURE_MODES:
                row[f"{mode}_rate"] = float(sub[mode].mean()) if len(sub) > 0 else float("nan")
            prev_rows.append(row)
        prev_df = pd.DataFrame(prev_rows)

        # Brier delta: forecasts with failure mode vs without
        impact_rows = []
        for mode in _FAILURE_MODES:
            with_mode = df[df[mode]]["brier"].mean()
            without_mode = df[~df[mode]]["brier"].mean()
            impact_rows.append({
                "failure_mode": mode,
                "brier_with": with_mode,
                "brier_without": without_mode,
                "brier_delta": with_mode - without_mode,
            })
        impact_df = pd.DataFrame(impact_rows)

        fig = self._create_figure(prev_df, impact_df)
        combined = pd.concat([prev_df, impact_df], ignore_index=True, sort=False)
        return AnalysisOutput(figure=fig, data=combined)

    def _create_figure(self, prev_df: pd.DataFrame, impact_df: pd.DataFrame) -> plt.Figure:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Heatmap: domain × mode
        ax1 = axes[0]
        domains = [d for d in _DOMAIN_ORDER if d in prev_df["domain"].values]
        prev_df_idx = prev_df.set_index("domain")
        matrix = np.array([
            [prev_df_idx.loc[d, f"{m}_rate"] if d in prev_df_idx.index else 0.0 for m in _FAILURE_MODES]
            for d in domains
        ])
        im = ax1.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=0.5)
        ax1.set_xticks(range(len(_FAILURE_MODES)))
        ax1.set_xticklabels([m.replace("Overweighting", "\nOverweighting") for m in _FAILURE_MODES], fontsize=9)
        ax1.set_yticks(range(len(domains)))
        ax1.set_yticklabels(domains, fontsize=9)
        ax1.set_title("Failure Mode Prevalence by Domain")
        plt.colorbar(im, ax=ax1, fraction=0.03, label="Rate")
        for i, _domain in enumerate(domains):
            for j, _mode in enumerate(_FAILURE_MODES):
                val = matrix[i, j]
                ax1.text(j, i, f"{val:.0%}", ha="center", va="center", fontsize=8,
                         color="white" if val > 0.3 else "black")

        # Bar chart: Brier delta per mode
        ax2 = axes[1]
        modes = impact_df["failure_mode"].tolist()
        deltas = impact_df["brier_delta"].tolist()
        colors = ["#d62728" if d > 0 else "#2ca02c" for d in deltas]
        ax2.bar(modes, deltas, color=colors)
        ax2.axhline(0, color="grey", linewidth=0.8)
        ax2.set_title("Brier Score Delta\n(with failure mode − without)")
        ax2.set_ylabel("Δ Brier Score")
        ax2.tick_params(axis="x", rotation=15)

        fig.suptitle("Benchmark 3: Failure Mode Prevalence & Impact", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig
