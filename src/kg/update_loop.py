"""Phase 6: KG Update Loop.

After each benchmark run this module writes learnings back into Fuseki as RDF.
Can be called standalone or imported by benchmark scripts.

Writes:
  pmo:domainAccuracy         per domain per model/condition
  pmo:failureModeRate        per domain
  pmo:newsSensitivityIndex   per domain/subcategory
  pmo:breakEvenHorizon       per domain

These become queryable context for the agent in subsequent runs
(see src/kg/queries/benchmark_queries.py).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.backtest.loader import load_forecasts
from src.backtest.metrics import ForecastingMetrics
from src.kg.client import FusekiClient
from src.kg.queries.benchmark_queries import write_domain_learnings

logger = logging.getLogger(__name__)

_FAILURE_MODES = ["RecencyBias", "RumourOverweighting", "DefinitionDrift"]


def run_kg_update(
    forecasts_dir: Path | str | None = None,
    client: FusekiClient | None = None,
) -> None:
    """Compute benchmark learnings from forecast data and write to Fuseki KG."""
    client = client or FusekiClient()

    if not client.ping():
        logger.warning("Fuseki not reachable — skipping KG update loop.")
        return

    raw_df = load_forecasts(forecasts_dir, condition="raw")
    news_df = load_forecasts(forecasts_dir, condition="news")

    if raw_df.empty:
        logger.warning("No raw forecast data found — nothing to write.")
        return

    df = raw_df.copy()
    df = df[df["true_result"].isin(["yes", "no"])]
    probs = df["calibrated_probability"].astype(float).clip(0.01, 0.99)
    actuals = (df["true_result"] == "yes").astype(float)
    df["brier"] = (probs - actuals) ** 2

    for mode in _FAILURE_MODES:
        df[mode] = df["failure_modes"].astype(str).str.contains(mode, na=False)

    domains = df["domain"].unique()

    for domain in domains:
        sub = df[df["domain"] == domain]
        metrics = ForecastingMetrics.compute(sub)

        # Failure mode rate (any mode)
        failure_rate = float(sub[_FAILURE_MODES].any(axis=1).mean()) if not sub.empty else None

        # NSI
        nsi = None
        if not news_df.empty:
            news_sub = news_df[
                (news_df["domain"] == domain) & news_df["true_result"].isin(["yes", "no"])
            ]
            if not news_sub.empty:
                np_prob = news_sub["calibrated_probability"].astype(float).clip(0.01, 0.99)
                na = (news_sub["true_result"] == "yes").astype(float)
                news_brier = float(((np_prob - na) ** 2).mean())
                nsi = float(metrics.brier_score - news_brier) if not pd.isna(metrics.brier_score) else None

        # Breakeven horizon (days)
        breakeven = None
        if "days_to_close" in sub.columns:
            sub2 = sub[sub["days_to_close"].notna() & (sub["days_to_close"] > 0)].copy()
            probs2 = sub2["calibrated_probability"].astype(float).clip(0.01, 0.99)
            sub2["correct"] = ((probs2 >= 0.5) == (sub2["true_result"] == "yes"))
            sub2 = sub2.sort_values("days_to_close")
            above = sub2[sub2["correct"]]
            if not above.empty:
                breakeven = float(above["days_to_close"].min())

        logger.info(
            "Writing KG for domain=%s acc=%.3f nsi=%s be=%s",
            domain, metrics.accuracy, nsi, breakeven,
        )

        write_domain_learnings(
            client=client,
            domain=domain,
            accuracy=metrics.accuracy if not pd.isna(metrics.accuracy) else None,
            failure_mode_rate=failure_rate,
            nsi=nsi,
            breakeven_horizon=breakeven,
        )

    logger.info("KG update loop complete — wrote learnings for %d domains.", len(domains))
    print(f"KG update loop complete. Wrote learnings for domains: {list(domains)}")
