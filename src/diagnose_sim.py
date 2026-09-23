import duckdb
import pandas as pd

con = duckdb.connect()

print("=== Simulated Trades Breakdown ===")
summary = con.sql("""
    SELECT 
        exit_reason,
        count(*) as count,
        round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct,
        avg(pnl_pct) as avg_pnl_pct,
        sum(pnl_btc) as sum_pnl_btc,
        avg(bars_held) as avg_bars_held
    FROM 'src/simulated_trades_15m.csv'
    GROUP BY exit_reason
    ORDER BY count DESC
""").df()
print(summary)

print("\n=== Long vs Short Performance in Simulation ===")
side_perf = con.sql("""
    SELECT 
        direction,
        count(*) as count,
        round(count(CASE WHEN pnl_pct > 0 THEN 1 END) * 100.0 / count(*), 2) as win_rate_pct,
        avg(pnl_pct) as avg_pnl_pct,
        sum(pnl_btc) as sum_pnl_btc
    FROM 'src/simulated_trades_15m.csv'
    GROUP BY direction
""").df()
print(side_perf)
