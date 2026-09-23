import duckdb
import glob

execution_files = sorted(glob.glob("aoa_public_2021-12-31_with_letter/aoa-execution-*.csv"))
print("Files found:", execution_files)

con = duckdb.connect()

# 1. Total row count and symbols
print("\n=== [1] Overview per file & Total Trades ===")
file_stats = []
for f in execution_files:
    cnt = con.sql(f"SELECT count(*) FROM '{f}'").fetchone()[0]
    file_stats.append((f, cnt))
    print(f"File: {f} -> {cnt:,} rows")

total_rows = sum(s[1] for s in file_stats)
print(f"Total execution rows: {total_rows:,}")

# Let's inspect symbols traded across 2018 file first
print("\n=== [2] Traded Symbols across all files ===")
symbols_df = con.sql("""
    SELECT symbol, count(*) as count, sum(lastqty) as total_contracts
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    GROUP BY symbol
    ORDER BY count DESC
""").df()
print(symbols_df.head(15))

print("\n=== [3] Maker vs Taker (Liquidity Indicator) ===")
liquidity_df = con.sql("""
    SELECT lastliquidityind, count(*) as count, round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    GROUP BY lastliquidityind
""").df()
print(liquidity_df)

print("\n=== [4] Order Type Breakdown ===")
ord_type_df = con.sql("""
    SELECT ordtype, count(*) as count, round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    GROUP BY ordtype
""").df()
print(ord_type_df)

print("\n=== [5] Order Executions per Year ===")
yearly_df = con.sql("""
    SELECT 
        year(CAST(date AS DATE)) as year,
        count(*) as num_executions,
        count(distinct orderid) as num_distinct_orders,
        avg(lastqty) as avg_contract_qty,
        sum(abs(foreignnotional)) as sum_foreignnotional
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    GROUP BY year
    ORDER BY year
""").df()
print(yearly_df)

print("\n=== [6] Trade Side (Buy vs Sell) ===")
side_df = con.sql("""
    SELECT 
        side, 
        count(*) as count,
        round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    GROUP BY side
""").df()
print(side_df)
