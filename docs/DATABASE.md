# Database Setup & Operations

All commands should be run from the project root:
```bash
cd /home/banyan/trade-data/prediction-market-analysis
```

## Connection Details

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5435` |
| Database | `tradedata` |
| Username | `postgres` |
| Password | `postgres` |

**Connection string:**
```
postgresql://postgres:postgres@localhost:5435/tradedata
```

---

## 1. Container Management

```bash
# Start (after first setup or system restart)
docker start trade-data-db

# First-time setup (if container doesn't exist)
docker run -d \
  --name trade-data-db \
  -e POSTGRES_DB=tradedata \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5435:5432 \
  -v trade-data-pgdata:/var/lib/postgresql/data \
  postgres:15

# Check it's ready
docker exec trade-data-db pg_isready -U postgres

# Stop
docker stop trade-data-db
```

---

## 2. Populate the Database

```bash
uv run ingest_postgres.py
```

Reads all parquet files from `data/` and loads them into Postgres. Skips tables that already exist — safe to re-run after collecting new data.

---

## 3. Other DB Commands

```bash
# Connect via psql
psql -h localhost -p 5435 -U postgres -d tradedata

# Table sizes
docker exec trade-data-db psql -U postgres -d tradedata -c "
  SELECT tablename,
         pg_size_pretty(pg_total_relation_size(tablename::text)) AS size
  FROM pg_tables WHERE schemaname='public';
"

# Row counts
docker exec trade-data-db psql -U postgres -d tradedata -c "
  SELECT 'kalshi_markets'     AS table, COUNT(*) FROM kalshi_markets
  UNION ALL
  SELECT 'polymarket_markets', COUNT(*) FROM polymarket_markets
  UNION ALL
  SELECT 'kalshi_trades',      COUNT(*) FROM kalshi_trades
  UNION ALL
  SELECT 'polymarket_trades',  COUNT(*) FROM polymarket_trades;
"

# Wipe and re-ingest everything from scratch
docker exec trade-data-db psql -U postgres -d tradedata -c "
  DROP TABLE IF EXISTS kalshi_markets, kalshi_trades, polymarket_markets, polymarket_trades;
"
uv run ingest_postgres.py
```

---

## 4. Collect More Data

```bash
# Kalshi markets + trades (last 3 months)
uv run run_kalshi.py

# Polymarket markets + trades (last ~90 days)
uv run run_indexers.py
```

After any indexing run, re-run `ingest_postgres.py` to load the new parquet files into Postgres.

---

## Tables

| Table | Description |
|---|---|
| `kalshi_markets` | Kalshi market metadata (title, status, prices, volume) |
| `kalshi_trades` | Kalshi individual trades (price, count, side, timestamp) |
| `polymarket_markets` | Polymarket market metadata (question, volume, liquidity) |
| `polymarket_trades` | Polymarket trades from Polygon blockchain (OrderFilled events) |

See [SCHEMAS.md](SCHEMAS.md) for full column-level documentation.
