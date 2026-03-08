"""Forecast Parquet → RDF ETL.

Reads data/forecasts/*.parquet and emits pmo:LLMForecast triples
linked to their market URIs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.kg.etl.base import BaseETL

logger = logging.getLogger(__name__)


class ForecastETL(BaseETL):
    """Load LLM forecast Parquet files into the KG."""

    @property
    def graph_uri(self) -> str:
        return "http://pmo.research/graph/forecasts"

    def build_query(self, data_dir: Path) -> str:
        glob = str(data_dir / "*.parquet")
        return f"""
            SELECT *
            FROM read_parquet('{glob}')
        """

    def rows_to_turtle(self, rows: list[dict]) -> str:
        lines = [self.turtle_header()]
        for row in rows:
            market_id = row.get("market_id", "")
            platform = row.get("platform", "")
            condition = row.get("condition", "raw")
            model = row.get("model", "")
            if not market_id:
                continue

            forecast_id = f"{market_id}_{condition}_{model}".replace("/", "_").replace(" ", "_")
            forecast_uri = f"<http://pmo.research/instance/forecast/{forecast_id}>"

            if platform == "kalshi":
                market_uri = f"<http://pmo.research/instance/kalshi/{market_id.replace('/', '_')}>"
            else:
                market_uri = f"<http://pmo.research/instance/polymarket/{market_id.replace('/', '_')}>"

            raw_prob = row.get("raw_probability") or 0.0
            cal_prob = row.get("calibrated_probability") or raw_prob
            conf_low = row.get("confidence_low") or 0.0
            conf_high = row.get("confidence_high") or 1.0
            forecasted_at = row.get("forecasted_at")
            reasoning = self.escape_str(row.get("reasoning") or "")[:2000]
            edge = row.get("edge") or 0.0

            # Brier score (computed post-resolution; may be None)
            brier = row.get("brier_score")

            # Failure modes stored as comma-separated string or list
            failure_modes = row.get("failure_modes") or []
            if isinstance(failure_modes, str):
                failure_modes = [f.strip() for f in failure_modes.split(",") if f.strip()]

            triples = [
                f"{forecast_uri} a pmo:LLMForecast ;",
                f"    pmo:forecastsMarket {market_uri} ;",
                f'    pmo:model "{self.escape_str(model)}" ;',
                f'    pmo:condition "{self.escape_str(condition)}" ;',
                f'    pmo:rawProbability "{float(raw_prob)}"^^xsd:double ;',
                f'    pmo:calibratedProbability "{float(cal_prob)}"^^xsd:double ;',
                f'    pmo:confidenceLow "{float(conf_low)}"^^xsd:double ;',
                f'    pmo:confidenceHigh "{float(conf_high)}"^^xsd:double ;',
                f'    pmo:edge "{float(edge)}"^^xsd:double ;',
                f'    pmo:reasoning "{reasoning}" ;',
            ]

            if forecasted_at:
                dt = str(forecasted_at)[:19].replace(" ", "T")
                triples.append(f'    pmo:forecasted_at "{dt}"^^xsd:dateTime ;')

            if brier is not None:
                triples.append(f'    pmo:brierScore "{float(brier)}"^^xsd:double ;')

            for fm in failure_modes:
                fm_clean = fm.strip().replace(" ", "")
                if fm_clean:
                    triples.append(f"    pmo:exhibitsFailureMode pmo:{fm_clean} ;")

            triples[-1] = triples[-1].rstrip(" ;") + " ."
            lines.append("\n".join(triples))
            lines.append("")

        return "\n".join(lines)
