"""
Run selected indexers for the last 3 months of data.
Kalshi: markets + trades (filtered by min_ts = Nov 28, 2025)
Polymarket: markets only (trades require POLYGON_RPC)
"""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from src.indexers.polymarket.markets import PolymarketMarketsIndexer
from src.indexers.polymarket.trades import PolymarketTradesIndexer
from src.indexers.polymarket.blockchain import PolygonClient

# Approximate Polygon block for Nov 28, 2025
# Polygon ~2s/block; current block queried at runtime, minus ~90 days * 43200 blocks/day
import time
client = PolygonClient()
current_block = client.get_block_number()
blocks_per_day = 43200
from_block = current_block - (90 * blocks_per_day)
print(f"Current block: {current_block:,}  |  From block (~Nov 28): {from_block:,}")

print()
print("=" * 60)
print("Step 1/2: Polymarket Markets")
print("=" * 60)
PolymarketMarketsIndexer().run()

print()
print("=" * 60)
print("Step 2/2: Polymarket Trades (last ~90 days of blocks)")
print("=" * 60)
PolymarketTradesIndexer(from_block=from_block).run()

print()
print("All indexers complete.")
