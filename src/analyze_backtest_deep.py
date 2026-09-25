import pandas as pd
import numpy as np

def analyze():
    df = pd.read_csv("src/ladder_trades.csv")
    print("=== LADDER TRADES DEEP ANALYSIS ===")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(df['pnl_btc'] > 0).mean() * 100:.2f}%")
    print(f"Total PnL (BTC): {df['pnl_btc'].sum():.4f}")
    
    print("\n--- Breakdown by Exit Reason ---")
    grp = df.groupby('exit_reason').agg(
        count=('pnl_btc', 'count'),
        win_rate=('pnl_btc', lambda x: (x > 0).mean() * 100),
        sum_pnl=('pnl_btc', 'sum'),
        mean_pnl=('pnl_btc', 'mean'),
        avg_bars=('bars_held', 'mean')
    )
    print(grp.to_string())

    print("\n--- Breakdown by Direction ---")
    grp_dir = df.groupby('direction').agg(
        count=('pnl_btc', 'count'),
        win_rate=('pnl_btc', lambda x: (x > 0).mean() * 100),
        sum_pnl=('pnl_btc', 'sum'),
        mean_pnl=('pnl_btc', 'mean')
    )
    print(grp_dir.to_string())

    print("\n--- Loss Analysis ---")
    losses = df[df['pnl_btc'] < 0]
    print(f"Avg Loss (BTC): {losses['pnl_btc'].mean():.6f}")
    print(f"Max Loss (BTC): {losses['pnl_btc'].min():.6f}")
    
    wins = df[df['pnl_btc'] > 0]
    print(f"Avg Win (BTC):  {wins['pnl_btc'].mean():.6f}")
    print(f"Max Win (BTC):  {wins['pnl_btc'].max():.6f}")

    print("\n--- Trailing Breakeven Detail ---")
    tb = df[df['exit_reason'] == 'TRAILING_BREAKEVEN']
    print(f"Trailing Breakeven count: {len(tb)}, PnL sum: {tb['pnl_btc'].sum():.6f}, Avg PnL: {tb['pnl_btc'].mean():.6f}")
    print(f"Why Trailing Breakeven PnL is negative/positive? Sample:")
    print(tb[['entry_time', 'direction', 'tot_contracts', 'avg_entry_px', 'exit_px', 'pnl_btc', 'pnl_pct', 'bars_held']].head(5))

    print("\n--- Stop Loss Detail ---")
    sl = df[df['exit_reason'] == 'STOP_LOSS']
    print(f"Stop Loss count: {len(sl)}, PnL sum: {sl['pnl_btc'].sum():.6f}, Avg PnL: {sl['pnl_btc'].mean():.6f}")
    print(f"Avg Stop Loss Pct: {sl['pnl_pct'].mean():.2f}%")

if __name__ == "__main__":
    analyze()
