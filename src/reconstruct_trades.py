import duckdb
import polars as pl
import numpy as np
import pandas as pd

con = duckdb.connect()

print("Loading all trade executions across all files for XBTUSD...")
# We load XBTUSD trades ordered strictly by transacttime
trades_df = con.sql("""
    SELECT 
        CAST(transacttime AS TIMESTAMP) as ts,
        orderid,
        side,
        lastqty,
        lastpx,
        ordtype,
        lastliquidityind,
        CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND transacttime IS NOT NULL
    ORDER BY ts ASC
""").pl()

print(f"Total XBTUSD execution records: {len(trades_df):,}")

# Cumulative position
trades_df = trades_df.with_columns([
    pl.col("signed_qty").cum_sum().alias("position")
])

print("Position min, max:")
print(f"Max Long: {trades_df['position'].max():,} contracts ($)")
print(f"Max Short: {trades_df['position'].min():,} contracts ($)")

# Reconstruct round-trip trade cycles
# A cycle starts when position moves away from 0, and ends when it crosses or touches 0 again.
positions = trades_df["position"].to_numpy()
timestamps = trades_df["ts"].to_numpy()
prices = trades_df["lastpx"].to_numpy()
sides = trades_df["side"].to_numpy()
qtys = trades_df["lastqty"].to_numpy()

cycles = []
in_pos = False
start_idx = 0
current_dir = 0 # +1 Long, -1 Short
pos_entry_qtys = []
pos_entry_pxs = []

for i in range(len(positions)):
    pos = positions[i]
    prev_pos = positions[i-1] if i > 0 else 0
    
    if not in_pos:
        if pos != 0:
            in_pos = True
            start_idx = i
            current_dir = 1 if pos > 0 else -1
            pos_entry_qtys = [qtys[i]]
            pos_entry_pxs = [prices[i]]
    else:
        # Check if still building or closing
        if (current_dir == 1 and pos > prev_pos) or (current_dir == -1 and pos < prev_pos):
            pos_entry_qtys.append(qtys[i])
            pos_entry_pxs.append(prices[i])
            
        # Check if position crossed or touched 0
        if (current_dir == 1 and pos <= 0) or (current_dir == -1 and pos >= 0):
            duration_sec = (timestamps[i] - timestamps[start_idx]) / np.timedelta64(1, 's')
            
            # Avg entry price (weighted)
            tot_entry_qty = sum(pos_entry_qtys)
            avg_entry_px = sum(q * p for q, p in zip(pos_entry_qtys, pos_entry_pxs)) / tot_entry_qty if tot_entry_qty > 0 else prices[start_idx]
            exit_px = prices[i]
            
            # PnL % approx
            if current_dir == 1:
                pnl_pct = (exit_px - avg_entry_px) / avg_entry_px * 100.0
            else:
                pnl_pct = (avg_entry_px - exit_px) / avg_entry_px * 100.0
                
            cycles.append({
                "direction": "Long" if current_dir == 1 else "Short",
                "start_time": timestamps[start_idx],
                "end_time": timestamps[i],
                "duration_min": duration_sec / 60.0,
                "duration_hours": duration_sec / 3600.0,
                "entry_px": avg_entry_px,
                "exit_px": exit_px,
                "pnl_pct": pnl_pct,
                "max_contracts": max(pos_entry_qtys) if pos_entry_qtys else 0
            })
            
            if pos == 0:
                in_pos = False
                pos_entry_qtys = []
                pos_entry_pxs = []
            else:
                start_idx = i
                current_dir = 1 if pos > 0 else -1
                pos_entry_qtys = [abs(pos)]
                pos_entry_pxs = [prices[i]]

res = pd.DataFrame(cycles)
print(f"\n=======================================================")
print(f"Total Completed Trade Cycles: {len(res):,}")
print(f"=======================================================")

print("\n--- [1] Position Duration (Holding Time in Minutes) ---")
print(res["duration_min"].describe(percentiles=[0.10, 0.25, 0.50, 0.75, 0.90, 0.95]))

print("\n--- [2] Holding Time Classification ---")
print(f"Scalping (< 15 min):             {(res['duration_min'] < 15).mean()*100:.2f}%")
print(f"Short Day Trading (15m - 1h):    {((res['duration_min'] >= 15) & (res['duration_min'] < 60)).mean()*100:.2f}%")
print(f"Day Trading (1h - 4h):           {((res['duration_min'] >= 60) & (res['duration_min'] < 240)).mean()*100:.2f}%")
print(f"Short Swing (4h - 24h):          {((res['duration_min'] >= 240) & (res['duration_min'] < 1440)).mean()*100:.2f}%")
print(f"Position/Long Swing (> 24h):     {(res['duration_min'] >= 1440).mean()*100:.2f}%")

print("\n--- [3] Win Rate and Return per Cycle ---")
win_cycles = res[res["pnl_pct"] > 0]
loss_cycles = res[res["pnl_pct"] < 0]
win_rate = len(win_cycles) / len(res) * 100.0
avg_win = win_cycles["pnl_pct"].mean()
avg_loss = loss_cycles["pnl_pct"].mean()
rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

print(f"Win Rate:               {win_rate:.2f}%")
print(f"Average Win:            +{avg_win:.2f}%")
print(f"Average Loss:           {avg_loss:.2f}%")
print(f"Payoff Ratio (Win/Loss):{rr_ratio:.2f}")

print("\n--- [4] Long vs Short Performance ---")
longs = res[res["direction"] == "Long"]
shorts = res[res["direction"] == "Short"]
print(f"Long Count: {len(longs):,} | Win Rate: {(longs['pnl_pct'] > 0).mean()*100:.2f}% | Avg PnL: {longs['pnl_pct'].mean():.2f}%")
print(f"Short Count: {len(shorts):,} | Win Rate: {(shorts['pnl_pct'] > 0).mean()*100:.2f}% | Avg PnL: {shorts['pnl_pct'].mean():.2f}%")

# Save summary metrics to json
summary_out = {
    "total_executions": 1444583,
    "total_trade_cycles": len(res),
    "win_rate_pct": float(win_rate),
    "avg_win_pct": float(avg_win),
    "avg_loss_pct": float(avg_loss),
    "payoff_ratio": float(rr_ratio),
    "median_holding_time_min": float(res["duration_min"].median()),
    "p25_holding_time_min": float(res["duration_min"].quantile(0.25)),
    "p75_holding_time_min": float(res["duration_min"].quantile(0.75)),
    "p90_holding_time_min": float(res["duration_min"].quantile(0.90)),
    "long_ratio_pct": float(len(longs)/len(res)*100),
    "short_ratio_pct": float(len(shorts)/len(res)*100)
}
import json
with open("src/wonyo_stats_summary.json", "w") as f:
    json.dump(summary_out, f, indent=2)
print("\nSaved summary to src/wonyo_stats_summary.json")
