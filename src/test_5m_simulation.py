"""
Test Wonyo-AI on 5-Minute Candles (Closer to Wonyotti's 25.8m Median Holding Time)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.test_improved_simulation import run_improved_backtest

if __name__ == "__main__":
    print("Loading 5-minute dataset...")
    df_5m = pd.read_parquet("src/bitmex_2021_q2_5m.parquet")
    print(f"Loaded {len(df_5m):,} 5-minute candles.")
    # On 5m, 1.0% arm trailing might be too wide or suitable; let's test arm 0.8%, lock 0.25%
    run_improved_backtest(df_5m, arm_trailing_pct=0.8, lock_profit_pct=0.25)
