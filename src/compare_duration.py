import duckdb
import polars as pl
import numpy as np
import pandas as pd

trades_df = duckdb.sql("""
    SELECT 
        CAST(transacttime AS TIMESTAMP) as ts,
        lastpx,
        lastqty,
        CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND transacttime IS NOT NULL
    ORDER BY ts ASC
""").pl()

trades_df = trades_df.with_columns([pl.col("signed_qty").cum_sum().alias("position")])
positions = trades_df["position"].to_numpy()
timestamps = trades_df["ts"].to_numpy()
prices = trades_df["lastpx"].to_numpy()

cycles = []
in_pos = False
start_idx = 0
current_dir = 0
pos_entry_pxs = []

for i in range(len(positions)):
    pos = positions[i]
    if not in_pos:
        if pos != 0:
            in_pos = True
            start_idx = i
            current_dir = 1 if pos > 0 else -1
            pos_entry_pxs = [prices[i]]
    else:
        if (current_dir == 1 and pos <= 0) or (current_dir == -1 and pos >= 0):
            dur = (timestamps[i] - timestamps[start_idx]) / np.timedelta64(1, 's') / 60.0
            pnl = (prices[i] - pos_entry_pxs[0]) / pos_entry_pxs[0] * 100.0 * current_dir
            cycles.append({"duration_min": dur, "pnl": pnl, "win": pnl > 0})
            if pos == 0:
                in_pos = False
                pos_entry_pxs = []
            else:
                start_idx = i
                current_dir = 1 if pos > 0 else -1
                pos_entry_pxs = [prices[i]]

res = pd.DataFrame(cycles)
print("=== WINNERS VS LOSERS HOLDING DURATION ===")
print("Winners count:", res['win'].sum())
print("Losers count:", (~res['win']).sum())
print("Winners Duration median:", f"{res[res['win']]['duration_min'].median():.2f} mins")
print("Losers Duration median:", f"{res[~res['win']]['duration_min'].median():.2f} mins")
print("Winners Duration 75th percentile:", f"{res[res['win']]['duration_min'].quantile(0.75):.2f} mins")
print("Losers Duration 75th percentile:", f"{res[~res['win']]['duration_min'].quantile(0.75):.2f} mins")
