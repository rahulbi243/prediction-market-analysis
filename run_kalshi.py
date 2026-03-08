"""Run Kalshi markets + trades indexers (last 3 months)."""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from src.indexers.kalshi.markets import KalshiMarketsIndexer
from src.indexers.kalshi.trades import KalshiTradesIndexer

# Nov 28, 2025 – Feb 28, 2026
MIN_TS = 1764288000
MAX_TS = 1772236800

print("=" * 60)
print("Step 1/2: Kalshi Markets (Nov 28, 2025 – Feb 28, 2026)")
print("=" * 60)
KalshiMarketsIndexer(min_close_ts=MIN_TS, max_close_ts=MAX_TS).run()

print()
print("=" * 60)
print("Step 2/2: Kalshi Trades (Nov 28, 2025 – Feb 28, 2026)")
print("=" * 60)
KalshiTradesIndexer(min_ts=MIN_TS, max_ts=MAX_TS).run()

print()
print("Kalshi indexing complete.")
