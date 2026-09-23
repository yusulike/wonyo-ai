import duckdb
import pandas as pd

con = duckdb.connect()

print("Aggregating BitMEX trade executions into 15-minute OHLCV candles...")

# We aggregate 2018-2021 executions into 15-minute candles
# Note: time_bucket creates clean 15-min intervals
candles_df = con.sql("""
    WITH raw_trades AS (
        SELECT 
            time_bucket(INTERVAL '15 Minutes', CAST(transacttime AS TIMESTAMP)) as candle_time,
            CAST(transacttime AS TIMESTAMP) as ts,
            lastpx as price,
            lastqty as qty
        FROM 'aoa_public_2021-12-31_with_letter/aoa-execution-*.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND transacttime IS NOT NULL
    )
    SELECT 
        candle_time as timestamp,
        first(price ORDER BY ts ASC) as open,
        max(price) as high,
        min(price) as low,
        last(price ORDER BY ts ASC) as close,
        sum(qty) as volume
    FROM raw_trades
    GROUP BY candle_time
    ORDER BY candle_time ASC
""").df()

print(f"Constructed {len(candles_df):,} 15-minute candles from authentic BitMEX trades!")
print(candles_df.head())
print(candles_df.tail())

candles_df.to_parquet("src/bitmex_15m_candles.parquet")
print("Saved to src/bitmex_15m_candles.parquet")
