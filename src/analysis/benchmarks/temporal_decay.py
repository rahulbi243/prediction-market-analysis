"""Benchmark 5: Temporal Decay.

Novel contribution: LLM accuracy vs days-to-close,
with breakeven horizon per domain.

The "breakeven horizon" is the days-to-close threshold below which
LLM accuracy falls to ≤50% (i.e., worse than chance), suggesting that
very short-horizon markets are not worth forecasting.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.loader import load_forecasts
from src.common.analysis import Analysis, AnalysisOutput

_DOMAIN_ORDER = ["Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"]
_COLORS = [
    "#1f77b4", "#d62728", "#2ca02c", "#9467bd",
    "#e377c2", "#ff7f0e", "#8c564b",
]


class TemporalDecay(Analysis):
    """LLM accuracy as a function of days-to-close, by domain."""

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="temporal_decay",
            description="LLM accuracy vs days-to-close and breakeven horizon per domain",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        df = load_forecasts(self.forecasts_dir, condition="raw")
        if df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "no forecast data"})

        df = df[df["true_result"].isin(["yes", "no"])].copy()

        # Compute days_to_close from forecasted_at and market close_time
        # If close_time not available, use a placeholder
        if "close_time" in df.columns and "forecasted_at" in df.columns:
            df["forecasted_at"] = pd.to_datetime(df["forecasted_at"], errors="coerce", utc=True)
            df["close_time"] = pd.to_datetime(df["close_time"], errors="coerce", utc=True)
            df["days_to_close"] = (df["close_time"] - df["forecasted_at"]).dt.total_seconds() / 86400
        else:
            # Cannot compute without timestamps — return empty
            return AnalysisOutput(
                data=pd.DataFrame(),
                metadata={"error": "close_time or forecasted_at column missing"},
            )

        df = df[df["days_to_close"].notna() & (df["days_to_close"] > 0)]
        if df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "no valid days_to_close"})

        probs = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
        df["correct"] = ((probs >= 0.5) == (df["true_result"] == "yes")).astype(float)

        # Bin into log-spaced windows
        bins = [0, 1, 3, 7, 14, 30, 60, 180, 365, 1e6]
        labels = ["<1d", "1–3d", "3–7d", "1–2w", "2–4w", "1–2m", "2–6m", "6m–1y", ">1y"]
        df["horizon_bin"] = pd.cut(df["days_to_close"], bins=bins, labels=labels)

        rows = []
        for domain in df["domain"].unique():
            sub = df[df["domain"] == domain]
            for bin_label, grp in sub.groupby("horizon_bin", observed=True):
                if len(grp) < 5:
                    continue
                rows.append({
                    "domain": domain,
                    "horizon_bin": str(bin_label),
                    "n": len(grp),
                    "accuracy": float(grp["correct"].mean()),
                    "days_midpoint": float(grp["days_to_close"].median()),
                })
        data = pd.DataFrame(rows)

        breakeven = self._compute_breakeven(data)
        data = data.merge(breakeven, on="domain", how="left")

        fig = self._create_figure(data, breakeven)
        return AnalysisOutput(figure=fig, data=data)

    def _compute_breakeven(self, data: pd.DataFrame) -> pd.DataFrame:
        """Estimate the breakeven horizon for each domain."""
        rows = []
        for domain, grp in data.groupby("domain"):
            grp = grp.sort_values("days_midpoint")
            above = grp[grp["accuracy"] > 0.5]
            if above.empty:
                horizon = float("nan")
            else:
                horizon = float(above["days_midpoint"].min())
            rows.append({"domain": str(domain), "breakeven_days": horizon})
        return pd.DataFrame(rows)

    def _create_figure(self, data: pd.DataFrame, breakeven: pd.DataFrame) -> plt.Figure:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Panel 1: Accuracy vs horizon bin by domain
        ax1 = axes[0]
        domain_list = [d for d in _DOMAIN_ORDER if d in data["domain"].values]
        for domain, color in zip(domain_list, _COLORS):
            sub = data[data["domain"] == domain].sort_values("days_midpoint")
            if sub.empty:
                continue
            ax1.plot(sub["days_midpoint"], sub["accuracy"], "o-", label=domain, color=color, linewidth=1.5, markersize=5)
        ax1.axhline(0.5, linestyle="--", color="grey", linewidth=0.8, label="Chance")
        ax1.set_xscale("log")
        ax1.set_xlabel("Days to Close (log scale)")
        ax1.set_ylabel("Accuracy")
        ax1.set_title("Accuracy vs Days to Close")
        ax1.legend(fontsize=7, loc="lower right")
        ax1.set_ylim(0, 1)

        # Panel 2: Breakeven horizon bar chart
        ax2 = axes[1]
        be = breakeven.set_index("domain")
        domains = [d for d in _DOMAIN_ORDER if d in be.index]
        vals = [be.loc[d, "breakeven_days"] for d in domains]
        colors = [c for d, c in zip(_DOMAIN_ORDER, _COLORS) if d in be.index]
        ax2.barh(domains, vals, color=colors[:len(domains)])
        ax2.set_xlabel("Breakeven Horizon (days)")
        ax2.set_title("Breakeven Days-to-Close by Domain\n(min. days for accuracy > 50%)")
        ax2.axvline(7, linestyle="--", color="grey", linewidth=0.8, label="7 days")
        ax2.legend(fontsize=8)

        fig.suptitle("Benchmark 5: Temporal Decay of LLM Forecasting Accuracy", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig
