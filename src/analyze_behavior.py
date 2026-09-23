import duckdb
import pandas as pd

con = duckdb.connect()

print("=== [1] Executions per Distinct Order (Ladder / Iceberg behavior) ===")
# Let's see how many fills per orderid and time span per order
order_cluster = con.sql("""
    WITH order_summary AS (
        SELECT 
            orderid,
            count(*) as fills_per_order,
            sum(lastqty) as total_qty,
            avg(lastpx) as avg_price,
            min(transacttime) as order_start,
            max(transacttime) as order_end
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
        WHERE orderid IS NOT NULL AND orderid != ''
        GROUP BY orderid
    )
    SELECT 
        count(*) as total_unique_orders,
        avg(fills_per_order) as avg_fills_per_order,
        median(fills_per_order) as median_fills_per_order,
        quantile_cont(fills_per_order, 0.90) as p90_fills_per_order,
        avg(total_qty) as avg_order_qty
    FROM order_summary
""").df()
print(order_cluster)

print("\n=== [2] Hourly Distribution (UTC & KST) ===")
hourly_df = con.sql("""
    SELECT 
        extract(hour from CAST(transacttime AS TIMESTAMP)) as hour_utc,
        (extract(hour from CAST(transacttime AS TIMESTAMP)) + 9) % 24 as hour_kst,
        count(*) as execution_count,
        round(count(*) * 100.0 / sum(count(*)) over(), 2) as pct
    FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
    WHERE transacttime IS NOT NULL
    GROUP BY hour_utc, hour_kst
    ORDER BY hour_kst ASC
""").df()
print(hourly_df.to_string())

print("\n=== [3] Time Interval between consecutive orders (Manual vs Bot behavior) ===")
intervals_df = con.sql("""
    WITH order_times AS (
        SELECT 
            DISTINCT orderid,
            min(CAST(transacttime AS TIMESTAMP)) as order_time
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-2018-03-01-2018-12-31.csv'
        WHERE orderid IS NOT NULL AND orderid != ''
        GROUP BY orderid
    ),
    diffs AS (
        SELECT 
            order_time,
            epoch(order_time - lag(order_time) OVER (ORDER BY order_time)) as diff_seconds
        FROM order_times
    )
    SELECT 
        avg(diff_seconds) as avg_interval_sec,
        median(diff_seconds) as median_interval_sec,
        quantile_cont(diff_seconds, 0.25) as p25_interval_sec,
        quantile_cont(diff_seconds, 0.75) as p75_interval_sec,
        quantile_cont(diff_seconds, 0.95) as p95_interval_sec
    FROM diffs
    WHERE diff_seconds IS NOT NULL AND diff_seconds > 0
""").df()
print(intervals_df)
