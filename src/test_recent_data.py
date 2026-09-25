"""
Fetch 1000 recent candles from Binance and run backtest to verify performance in modern markets
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import pandas as pd
from src.test_improved_simulation import run_improved_backtest

def fetch_binance_candles(interval="15m", limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
    fallback = f"https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
    
    data = None
    for ep in [url, fallback]:
        try:
            r = requests.get(ep, timeout=10)
            if r.status_code == 200:
                data = r.json()
                break
        except Exception as e:
            pass
            
    if not data:
        raise RuntimeError("Failed to fetch Binance data")
        
    rows = []
    for item in data:
        rows.append({
            "timestamp": pd.to_datetime(item[0], unit='ms'),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    print("Fetching recent 1,000 15m candles from Binance...")
    df = fetch_binance_candles(interval="15m", limit=1000)
    print(f"Fetched {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    btc_start = df['close'].iloc[0]
    btc_end = df['close'].iloc[-1]
    print(f"BTC Price: ${btc_start:,.2f} -> ${btc_end:,.2f} ({((btc_end - btc_start)/btc_start)*100:+.2f}%)")
    
    run_improved_backtest(df, arm_trailing_pct=1.0, lock_profit_pct=0.3)
