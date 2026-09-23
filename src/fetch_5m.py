"""
Fetch 5-minute BitMEX Candles and resample to 15m
"""

import time
import requests
import pandas as pd
from datetime import datetime, timezone

def fetch_5m_candles(
    start_date: str = "2021-04-01",
    end_date: str = "2021-06-30"
):
    base_url = "https://www.bitmex.com/api/v1/trade/bucketed"
    symbol = "XBTUSD"
    bin_size = "5m"
    
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
                print(f"Error {resp.status_code}: {resp.text}")
                break
                
            data = resp.json()
            if not data:
                break
                
            for item in data:
                if item.get("open") is not None:
                    all_rows.append({
                        "timestamp": pd.to_datetime(item["timestamp"]),
                        "open": float(item["open"]),
                        "high": float(item["high"]),
                        "low": float(item["low"]),
                        "close": float(item["close"]),
                        "volume": float(item["volume"]) if item.get("volume") is not None else 0.0,
                    })
                
            last_ts = pd.to_datetime(data[-1]["timestamp"])
            current_start = last_ts + pd.Timedelta(seconds=1)
            time.sleep(0.15)
            
            if len(all_rows) % 5000 == 0:
                print(f"Fetched {len(all_rows):,} 5m candles (up to {last_ts})...")
                
        except Exception as e:
            print(f"Fetch error: {e}")
            break

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    out_5m = "src/bitmex_2021_q2_5m.parquet"
    df.to_parquet(out_5m)
    print(f"Saved {len(df):,} 5-minute candles to {out_5m}")

    # Resample to 15m
    df.set_index("timestamp", inplace=True)
    df_15m = df.resample("15min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna().reset_index()
    
    out_15m = "src/bitmex_2021_q2_15m.parquet"
    df_15m.to_parquet(out_15m)
    print(f"Resampled and saved {len(df_15m):,} 15-minute candles to {out_15m}")

if __name__ == "__main__":
    fetch_5m_candles()
