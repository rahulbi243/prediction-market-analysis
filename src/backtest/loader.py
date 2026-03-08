"""Load resolved forecast records from data/forecasts/*.parquet."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

_FORECASTS_DIR = Path(__file__).parent.parent.parent / "data" / "forecasts"


def load_forecasts(
    forecasts_dir: Path | str | None = None,
    condition: str | None = None,
    domain: str | None = None,
    platform: str | None = None,
    min_volume: float | None = None,
) -> pd.DataFrame:
    """Load forecast Parquet files into a DataFrame.

    Filters are applied server-side via DuckDB for efficiency.

    Returns an empty DataFrame if no files are found.
    """
    directory = Path(forecasts_dir or _FORECASTS_DIR)
    parquet_files = list(directory.glob("forecasts_*.parquet"))
    if not parquet_files:
        return pd.DataFrame()

    glob = str(directory / "forecasts_*.parquet")
    con = duckdb.connect()

    filters = []
    if condition:
        filters.append(f"condition = '{condition}'")
    if domain:
        filters.append(f"domain = '{domain}'")
    if platform:
        filters.append(f"platform = '{platform}'")
    if min_volume is not None:
        filters.append(f"volume >= {min_volume}")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    df = con.execute(f"SELECT * FROM read_parquet('{glob}') {where}").df()
    con.close()
    return df
