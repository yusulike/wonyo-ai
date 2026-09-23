"""
Fetch 15-minute BitMEX Candles for 2021
"""

import time
import requests
import pandas as pd
from datetime import datetime, timezone

def fetch_15m_candles():
    base_url = "https://www.bitmex.com/api/v1/trade/bucketed"
    symbol = "XBTUSD"
    bin_size = "15m"
    start_date = "2021-01-01"
    end_date = "2021-07-01" # 6 months of intense 2021 volatility (bull market + May 19 crash)
    
    current_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    
    all_rows = []
    print(f"Fetching {symbol} ({bin_size}) from {start_date} to {end_date}...")
    
    while current_start < end_dt:
        params = {
            "binSize": bin_size,
            "partial": "false",
            "symbol": symbol,
            "count": 1000,
            "startTime": current_start.isoformat(),
            "reverse": "false"
        }
        
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            if resp.status_code == 429:
                time.sleep(2)
                continue
            if resp.status_code != 200:
                print(f"Error {resp.status_code}")
                break
                
            data = resp.json()
            if not data:
                break
                
            for item in data:
                all_rows.append({
                    "timestamp": pd.to_datetime(item["timestamp"]),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(item["volume"]) if item.get("volume") is not None else 0.0,
                    "vwap": float(item.get("vwap", item["close"]))
                })
                
            last_ts = pd.to_datetime(data[-1]["timestamp"])
            current_start = last_ts + pd.Timedelta(seconds=1)
            time.sleep(0.2)
            
            if len(all_rows) % 3000 == 0:
                print(f"Fetched {len(all_rows):,} candles (up to {last_ts})...")
                
        except Exception as e:
            print(f"Fetch error: {e}")
            break

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    out_file = "src/bitmex_2021_h1_15m.parquet"
    df.to_parquet(out_file)
    print(f"Saved {len(df):,} 15-minute candles to {out_file}")

if __name__ == "__main__":
    fetch_15m_candles()
