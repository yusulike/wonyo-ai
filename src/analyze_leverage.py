import duckdb
import polars as pl
import numpy as np
import pandas as pd

con = duckdb.connect()

print("Analyzing Leverage and Position Sizing over time...")

# 1. Daily max position notional in USD
daily_pos = con.sql("""
    WITH trades AS (
        SELECT 
            CAST(date AS DATE) as trade_date,
            CAST(transacttime AS TIMESTAMP) as ts,
            lastpx,
            CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade'
    ),
    cum_trades AS (
        SELECT 
            trade_date,
            ts,
            lastpx,
            abs(sum(signed_qty) OVER (ORDER BY ts)) as abs_position_usd
        FROM trades
    ),
    daily_max_pos AS (
        SELECT 
            trade_date,
            max(abs_position_usd) as max_position_usd,
            avg(lastpx) as avg_btc_price
        FROM cum_trades
        GROUP BY trade_date
    ),
    daily_wallet AS (
        SELECT 
            CAST(date AS DATE) as wallet_date,
            walletbalance / 1e8 as balance_btc
        FROM 'aoa_public_2021-12-31_with_letter/aoa-wallet-2018-03-01-2021-12-31.csv'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY date ORDER BY transacttime DESC) = 1
    )
    SELECT 
        p.trade_date,
        p.max_position_usd,
        p.avg_btc_price,
        w.balance_btc,
        (w.balance_btc * p.avg_btc_price) as wallet_usd,
        (p.max_position_usd / (w.balance_btc * p.avg_btc_price)) as estimated_leverage
    FROM daily_max_pos p
    JOIN daily_wallet w ON p.trade_date = w.wallet_date
    WHERE w.balance_btc > 0
    ORDER BY p.trade_date ASC
""").df()

print(f"Total days analyzed: {len(daily_pos):,}")
print("\n--- Estimated Daily Peak Leverage Distribution ---")
lev = daily_pos["estimated_leverage"].dropna()
print(lev.describe(percentiles=[0.10, 0.25, 0.50, 0.75, 0.90, 0.95]))

print("\n--- Leverage Usage Bracket ---")
print(f"Under 1.0x (Cash equivalent / partial bet): {(lev < 1.0).mean()*100:.2f}%")
print(f"1.0x - 2.5x (Safe leverage):               {((lev >= 1.0) & (lev < 2.5)).mean()*100:.2f}%")
print(f"2.5x - 5.0x (Moderate leverage):           {((lev >= 2.5) & (lev < 5.0)).mean()*100:.2f}%")
print(f"5.0x - 10.0x (Aggressive):                 {((lev >= 5.0) & (lev < 10.0)).mean()*100:.2f}%")
print(f"Over 10.0x (High Risk):                    {(lev >= 10.0).mean()*100:.2f}%")

# Yearly median leverage
daily_pos["year"] = pd.to_datetime(daily_pos["trade_date"]).dt.year
print("\n--- Median Leverage by Year (Seed Growth Effect) ---")
print(daily_pos.groupby("year")["estimated_leverage"].median())
