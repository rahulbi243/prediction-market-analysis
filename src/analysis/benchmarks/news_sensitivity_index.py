"""Benchmark 4: News Sensitivity Index (NSI).

Novel contribution: Continuous NSI score at subcategory granularity
(vs paper's binary helps/hurts classification).

NSI = Brier_raw - Brier_news per domain/subcategory.
  Positive NSI → news helps (lowers Brier score).
  Negative NSI → news hurts.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.backtest.loader import load_forecasts
from src.common.analysis import Analysis, AnalysisOutput

_DOMAIN_ORDER = ["Politics", "Finance", "Sports", "Technology", "Entertainment", "Geopolitics", "Crypto"]


class NewsSensitivityIndex(Analysis):
    """Continuous NSI = Brier(raw) − Brier(news) at domain and subcategory level."""

    def __init__(self, forecasts_dir: Path | str | None = None):
        super().__init__(
            name="news_sensitivity_index",
            description="News Sensitivity Index at domain and subcategory granularity",
        )
        self.forecasts_dir = forecasts_dir

    def run(self) -> AnalysisOutput:
        raw_df = load_forecasts(self.forecasts_dir, condition="raw")
        news_df = load_forecasts(self.forecasts_dir, condition="news")

        if raw_df.empty or news_df.empty:
            return AnalysisOutput(data=pd.DataFrame(), metadata={"error": "need both raw and news forecasts"})

        # Compute Brier scores
        for df in (raw_df, news_df):
            df = df[df["true_result"].isin(["yes", "no"])].copy()
            probs = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
            actuals = (df["true_result"] == "yes").astype(float)
            df["brier"] = (probs - actuals) ** 2

        domain_nsi = _compute_nsi(raw_df, news_df, group_col="domain")
        subcat_nsi = _compute_nsi(raw_df, news_df, group_col="subcategory")

        fig = self._create_figure(domain_nsi, subcat_nsi)
        combined = pd.concat([domain_nsi, subcat_nsi], ignore_index=True, sort=False)
        return AnalysisOutput(figure=fig, data=combined)

    def _create_figure(self, domain_nsi: pd.DataFrame, subcat_nsi: pd.DataFrame) -> plt.Figure:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Domain-level
        ax1 = axes[0]
        d_idx = domain_nsi.set_index("group")
        domains = [d for d in _DOMAIN_ORDER if d in d_idx.index]
        nsi_vals = [d_idx.loc[d, "nsi"] for d in domains]
        colors = ["#2ca02c" if v >= 0 else "#d62728" for v in nsi_vals]
        ax1.barh(domains, nsi_vals, color=colors)
        ax1.axvline(0, color="grey", linewidth=0.8)
        ax1.set_title("NSI by Domain\n(Brier_raw − Brier_news; positive = news helps)")
        ax1.set_xlabel("NSI")

        # Subcategory-level (top 20 by absolute NSI)
        ax2 = axes[1]
        sub = subcat_nsi.dropna(subset=["nsi"]).nlargest(10, "nsi")
        sub_low = subcat_nsi.dropna(subset=["nsi"]).nsmallest(10, "nsi")
        combined = pd.concat([sub, sub_low]).drop_duplicates("group")
        colors2 = ["#2ca02c" if v >= 0 else "#d62728" for v in combined["nsi"]]
        ax2.barh(combined["group"], combined["nsi"], color=colors2)
        ax2.axvline(0, color="grey", linewidth=0.8)
        ax2.set_title("NSI by Subcategory (Top/Bottom 10)")
        ax2.set_xlabel("NSI")
        ax2.tick_params(axis="y", labelsize=7)

        fig.suptitle("Benchmark 4: News Sensitivity Index", fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig


def _compute_nsi(raw_df: pd.DataFrame, news_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Compute NSI = Brier_raw − Brier_news per group."""
    rows = []
    groups = set(raw_df[group_col].dropna().unique()) & set(news_df[group_col].dropna().unique())
    for group in groups:
        r = raw_df[(raw_df[group_col] == group) & raw_df["true_result"].isin(["yes", "no"])]
        n = news_df[(news_df[group_col] == group) & news_df["true_result"].isin(["yes", "no"])]
        if r.empty or n.empty:
            continue

        def brier(df: pd.DataFrame) -> float:
            p = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
            a = (df["true_result"] == "yes").astype(float)
            return float(((p - a) ** 2).mean())

        nsi = brier(r) - brier(n)
        rows.append({"group": group, "group_col": group_col, "n_raw": len(r), "n_news": len(n), "nsi": nsi})
    return pd.DataFrame(rows)
