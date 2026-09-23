import duckdb
import polars as pl
import datetime

wallet_csv = "aoa_public_2021-12-31_with_letter/aoa-wallet-2018-03-01-2021-12-31.csv"

# 1. Inspect using duckdb
con = duckdb.connect()

print("=== [1] Wallet Summary ===")
summary = con.sql(f"""
    SELECT 
        transacttype,
        count(*) as count,
        sum(amount)/1e8 as total_btc,
        min(amount)/1e8 as min_btc,
        max(amount)/1e8 as max_btc
    FROM '{wallet_csv}'
    GROUP BY transacttype
""").df()
print(summary)

print("\n=== [2] Balance Progression ===")
first_last = con.sql(f"""
    SELECT date, transacttime, transacttype, amount/1e8 as amount_btc, walletbalance/1e8 as balance_btc
    FROM '{wallet_csv}'
    ORDER BY date ASC, transacttime ASC
""").df()
print("First 5 entries:")
print(first_last.head(5))
print("\nLast 5 entries:")
print(first_last.tail(5))

print("\n=== [3] Deposits & Withdrawals ===")
transfers = con.sql(f"""
    SELECT 
        date, 
        transacttype, 
        amount/1e8 as amount_btc, 
        walletbalance/1e8 as balance_btc,
        address
    FROM '{wallet_csv}'
    WHERE transacttype IN ('Deposit', 'Withdrawal')
    ORDER BY date ASC
""").df()
print(transfers.to_string())

print("\n=== [4] Daily PNL Statistics ===")
daily_pnl = con.sql(f"""
    WITH pnl_daily AS (
        SELECT 
            date,
            sum(amount)/1e8 as daily_pnl_btc
        FROM '{wallet_csv}'
        WHERE transacttype = 'RealisedPNL'
        GROUP BY date
    )
    SELECT 
        count(*) as total_trading_days,
        count(CASE WHEN daily_pnl_btc > 0 THEN 1 END) as win_days,
        count(CASE WHEN daily_pnl_btc < 0 THEN 1 END) as loss_days,
        count(CASE WHEN daily_pnl_btc = 0 THEN 1 END) as zero_days,
        sum(daily_pnl_btc) as net_pnl_btc,
        avg(daily_pnl_btc) as avg_daily_pnl_btc,
        max(daily_pnl_btc) as max_day_profit_btc,
        min(daily_pnl_btc) as max_day_loss_btc,
        sum(CASE WHEN daily_pnl_btc > 0 THEN daily_pnl_btc ELSE 0 END) as gross_profit_btc,
        abs(sum(CASE WHEN daily_pnl_btc < 0 THEN daily_pnl_btc ELSE 0 END)) as gross_loss_btc
    FROM pnl_daily
""").df()

daily_pnl["win_rate_pct"] = (daily_pnl["win_days"] / daily_pnl["total_trading_days"]) * 100
daily_pnl["profit_factor"] = daily_pnl["gross_profit_btc"] / daily_pnl["gross_loss_btc"]
print(daily_pnl.T)
