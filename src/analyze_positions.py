import duckdb
import polars as pl
import numpy as np

con = duckdb.connect()

print("Reconstructing XBTUSD position for 2018...")

# We calculate cumulative position on XBTUSD
# In BitMEX inverse contract: 1 contract = 1 USD.
# Buy increases position by lastqty, Sell decreases position by lastqty.
df = con.sql("""
    SELECT 
        CAST(transacttime AS TIMESTAMP) as ts,
        side,
        lastqty,
        lastpx,
        CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2018-03-01-2018-12-31.csv'
    WHERE symbol = 'XBTUSD' AND transacttime IS NOT NULL
    ORDER BY ts ASC
""").pl()

print(f"Loaded {len(df):,} executions for 2018 XBTUSD")

# Compute cumulative position
df = df.with_columns([
    pl.col("signed_qty").cum_sum().alias("position")
])

print("Position min, max, median:")
print(f"Max Long: {df['position'].max():,} contracts ($)")
print(f"Max Short: {df['position'].min():,} contracts ($)")

# Find zero-crossings or flats (when position hits 0 or changes sign)
# Let's identify trade cycles: an entry from 0 (or sign flip) until back to 0 or sign flip
positions = df["position"].to_numpy()
timestamps = df["ts"].to_numpy()

cycles = []
in_position = False
start_idx = 0
current_dir = 0 # 1 for long, -1 for short

for i in range(len(positions)):
    pos = positions[i]
    if not in_position:
        if pos != 0:
            in_position = True
            start_idx = i
            current_dir = 1 if pos > 0 else -1
    else:
        # Check if closed or flipped
        if (current_dir == 1 and pos <= 0) or (current_dir == -1 and pos >= 0):
            # cycle ended
            duration_sec = (timestamps[i] - timestamps[start_idx]) / np.timedelta64(1, 's')
            cycles.append({
                "direction": "Long" if current_dir == 1 else "Short",
                "start_time": timestamps[start_idx],
                "end_time": timestamps[i],
                "duration_min": duration_sec / 60.0,
                "duration_hours": duration_sec / 3600.0,
            })
            if pos == 0:
                in_position = False
            else:
                start_idx = i
                current_dir = 1 if pos > 0 else -1

import pandas as pd
cycles_df = pd.DataFrame(cycles)
print(f"\nTotal trade cycles identified in 2018: {len(cycles_df):,}")
print("\nHolding Duration Statistics (Minutes):")
print(cycles_df["duration_min"].describe(percentiles=[0.25, 0.5, 0.75, 0.90, 0.95]))

print("\nHolding Duration Breakdown:")
print(f"Under 15 mins (Scalping): {(cycles_df['duration_min'] < 15).mean()*100:.1f}%")
print(f"15 mins - 1 hour (Short Day): {((cycles_df['duration_min'] >= 15) & (cycles_df['duration_min'] < 60)).mean()*100:.1f}%")
print(f"1 hour - 4 hours (Day Trading): {((cycles_df['duration_min'] >= 60) & (cycles_df['duration_min'] < 240)).mean()*100:.1f}%")
print(f"4 hours - 24 hours (Swing): {((cycles_df['duration_min'] >= 240) & (cycles_df['duration_min'] < 1440)).mean()*100:.1f}%")
print(f"Over 24 hours (Position Trading): {(cycles_df['duration_min'] >= 1440).mean()*100:.1f}%")
