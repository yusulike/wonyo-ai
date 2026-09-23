"""
BitMEX Continuous OHLCV Fetcher
Fetches authentic BitMEX historical klines with volume.
"""

import time
import requests
import pandas as pd
from datetime import datetime, timezone

def fetch_bitmex_candles(
    symbol: str = "XBTUSD",
    bin_size: str = "1h",
    start_date: str = "2020-01-01",
    end_date: str = "2021-12-31",
    max_records: int = 10000
) -> pd.DataFrame:
    base_url = "https://www.bitmex.com/api/v1/trade/bucketed"
    all_rows = []
    
    current_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)

    print(f"Fetching {symbol} ({bin_size}) from {start_date} to {end_date}...")
    
    while current_start < end_dt and len(all_rows) < max_records:
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
            if resp.status_code == 429: # Rate limit
                time.sleep(3)
                continue
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}")
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
            time.sleep(0.3) # Respect rate limits
            
            if len(all_rows) % 3000 == 0:
                print(f"Fetched {len(all_rows):,} candles so far (up to {last_ts})...")
                
        except Exception as e:
            print(f"Fetch error: {e}")
            break

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    print(f"Successfully fetched {len(df):,} candles.")
    return df

if __name__ == "__main__":
    # Fetch 2021 market data (where Bitcoin had epic volatility from 29k to 64k to 30k to 69k)
    df_2021 = fetch_bitmex_candles(
        symbol="XBTUSD",
        bin_size="1h",
        start_date="2021-01-01",
        end_date="2021-12-31",
        max_records=10000
    )
    df_2021.to_parquet("src/bitmex_2021_1h.parquet")
    print("Saved to src/bitmex_2021_1h.parquet")
