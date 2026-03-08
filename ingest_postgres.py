"""
Ingest parquet data into PostgreSQL using DuckDB's postgres extension.
Target: localhost:5434, database: tradedata
"""
import os
import sys
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import duckdb

PG_CONN = "host=localhost port=5434 dbname=tradedata user=postgres password=postgres"

con = duckdb.connect()
con.execute("INSTALL postgres; LOAD postgres;")
con.execute(f"ATTACH '{PG_CONN}' AS pg (TYPE POSTGRES)")

# ── Helpers ───────────────────────────────────────────────────────────────────

def table_exists(name: str) -> bool:
    result = con.execute(
        f"SELECT count(*) FROM pg.information_schema.tables "
        f"WHERE table_schema='public' AND table_name='{name}'"
    ).fetchone()
    return result[0] > 0

def load_table(name: str, glob: str, create_sql: str) -> None:
    files = list(Path(".").glob(glob))
    if not files:
        print(f"  [skip] No files found for {name}")
        return

    if table_exists(name):
        count = con.execute(f"SELECT count(*) FROM pg.{name}").fetchone()[0]
        print(f"  [skip] {name} already exists ({count:,} rows)")
        return

    print(f"  Creating table {name}...")
    con.execute(create_sql)
    print(f"  Loading {len(files)} parquet file(s) into {name}...")
    con.execute(f"INSERT INTO pg.{name} SELECT * FROM read_parquet('{glob}')")
    count = con.execute(f"SELECT count(*) FROM pg.{name}").fetchone()[0]
    print(f"  Done — {count:,} rows loaded")

# ── Kalshi Markets ────────────────────────────────────────────────────────────

print("\n=== Kalshi Markets ===")
load_table(
    name="kalshi_markets",
    glob="data/kalshi/markets/markets_*.parquet",
    create_sql="""
        CREATE TABLE pg.kalshi_markets (
            ticker          TEXT,
            event_ticker    TEXT,
            market_type     TEXT,
            title           TEXT,
            yes_sub_title   TEXT,
            no_sub_title    TEXT,
            status          TEXT,
            yes_bid         BIGINT,
            yes_ask         BIGINT,
            no_bid          BIGINT,
            no_ask          BIGINT,
            last_price      BIGINT,
            volume          BIGINT,
            volume_24h      BIGINT,
            open_interest   BIGINT,
            result          TEXT,
            created_time    TIMESTAMPTZ,
            open_time       TIMESTAMPTZ,
            close_time      TIMESTAMPTZ,
            _fetched_at     TIMESTAMPTZ
        )
    """,
)

# ── Kalshi Trades ─────────────────────────────────────────────────────────────

print("\n=== Kalshi Trades ===")
load_table(
    name="kalshi_trades",
    glob="data/kalshi/trades/trades_*.parquet",
    create_sql="""
        CREATE TABLE pg.kalshi_trades (
            trade_id        TEXT,
            ticker          TEXT,
            count           BIGINT,
            yes_price       BIGINT,
            no_price        BIGINT,
            taker_side      TEXT,
            created_time    TIMESTAMPTZ,
            _fetched_at     TIMESTAMPTZ
        )
    """,
)

# ── Polymarket Markets ────────────────────────────────────────────────────────

print("\n=== Polymarket Markets ===")
load_table(
    name="polymarket_markets",
    glob="data/polymarket/markets/markets_*.parquet",
    create_sql="""
        CREATE TABLE pg.polymarket_markets (
            id                   TEXT,
            condition_id         TEXT,
            question             TEXT,
            slug                 TEXT,
            outcomes             TEXT,
            outcome_prices       TEXT,
            clob_token_ids       TEXT,
            volume               DOUBLE PRECISION,
            liquidity            DOUBLE PRECISION,
            active               BOOLEAN,
            closed               BOOLEAN,
            end_date             TIMESTAMPTZ,
            created_at           TIMESTAMPTZ,
            market_maker_address TEXT,
            _fetched_at          TIMESTAMPTZ
        )
    """,
)

# ── Polymarket Trades ─────────────────────────────────────────────────────────

print("\n=== Polymarket Trades ===")
load_table(
    name="polymarket_trades",
    glob="data/polymarket/trades/trades_*.parquet",
    create_sql="""
        CREATE TABLE pg.polymarket_trades (
            block_number        BIGINT,
            transaction_hash    TEXT,
            log_index           BIGINT,
            order_hash          TEXT,
            maker               TEXT,
            taker               TEXT,
            maker_asset_id      TEXT,
            taker_asset_id      TEXT,
            maker_amount        BIGINT,
            taker_amount        BIGINT,
            fee                 BIGINT,
            _fetched_at         TIMESTAMPTZ,
            _contract           TEXT
        )
    """,
)

print("\nIngestion complete.")
print(f"\nConnect with:")
print(f"  psql -h localhost -p 5434 -U postgres -d tradedata")
