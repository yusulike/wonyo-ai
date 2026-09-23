import duckdb
import pandas as pd
import numpy as np

con = duckdb.connect()

print("Analyzing Wonyotti's exact entry and exit dynamics from 2021 execution logs...")

# 1. Analyze Order Placement Offset (Limit Price vs Previous Trade Price)
# Did he place inside the spread, at the touch, or deep in the orderbook?
offset_df = con.sql("""
    WITH xbt_trades AS (
        SELECT 
            CAST(transacttime AS TIMESTAMP) as ts,
            orderid,
            side,
            ordtype,
            lastqty,
            lastpx,
            price as order_limit_px,
            LAG(lastpx) OVER (ORDER BY CAST(transacttime AS TIMESTAMP)) as prev_px
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2021-01-01-2021-06-30.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND ordtype = 'Limit'
    )
    SELECT 
        side,
        avg(abs(order_limit_px - prev_px)) as avg_offset_usd,
        median(abs(order_limit_px - prev_px)) as median_offset_usd,
        quantile_cont(abs(order_limit_px - prev_px), 0.25) as p25_offset_usd,
        quantile_cont(abs(order_limit_px - prev_px), 0.75) as p75_offset_usd
    FROM xbt_trades
    WHERE prev_px IS NOT NULL AND order_limit_px IS NOT NULL AND abs(order_limit_px - prev_px) < 500
    GROUP BY side
""").df()
print("\n=== Limit Order Price Placement Offset vs Current Market Price ===")
print(offset_df)

# 2. Analyze Execution Spikes: Volume clustering within 1 minute of his orders
print("\n=== Clustering of Wonyotti's order fills per minute ===")
fill_cluster = con.sql("""
    WITH minute_fills AS (
        SELECT 
            time_bucket(INTERVAL '1 Minute', CAST(transacttime AS TIMESTAMP)) as min_bucket,
            count(*) as num_fills,
            sum(lastqty) as total_volume_usd,
            count(distinct orderid) as num_orders
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2021-01-01-2021-06-30.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade'
        GROUP BY min_bucket
    )
    SELECT 
        avg(num_fills) as avg_fills_per_active_min,
        median(num_fills) as median_fills,
        quantile_cont(num_fills, 0.90) as p90_fills,
        avg(total_volume_usd) as avg_volume_usd,
        median(total_volume_usd) as median_volume_usd
    FROM minute_fills
""").df()
print(fill_cluster)

# 3. Analyze Trade Cycle PnL Distribution:
# How long do losing trades stay open vs winning trades?
print("\n=== Duration: Winners vs Losers ===")
# Let's inspect the reconstructed trade cycles from reconstruct_trades.py
cycles = con.sql("""
    WITH trades AS (
        SELECT 
            CAST(transacttime AS TIMESTAMP) as ts,
            CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty,
            lastpx,
            lastqty
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2021-01-01-2021-06-30.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade'
    )
    SELECT count(*) as total_trades FROM trades
""").fetchone()[0]
print(f"2021 H1 XBTUSD trades count: {cycles:,}")
