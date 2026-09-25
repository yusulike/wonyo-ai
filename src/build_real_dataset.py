"""
Wonyo-AI: Build Full Real Trade Dataset from 600MB BitMEX Execution Logs
Extracts 12-factor Alpha & Risk Matrix, matches Wonyotti's real trade actions,
and exports compressed (X, y_action, y_size) for Neural Network training.
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import numpy as np
import pandas as pd
from src.feature_extractor import WonyoFeatureExtractor

def build_dataset(data_dir: str = "aoa_public_2021-12-31_with_letter", out_npz: str = "src/wonyo_dataset_real.npz"):
    print("=== [1/4] Loading 600MB Execution Tape with DuckDB ===")
    con = duckdb.connect()
    
    # 1. Load 15m candle aggregation and execution actions in unified query
    print("Aggregating 15-minute candles and Wonyotti trade actions...")
    query = f"""
    WITH raw_trades AS (
        SELECT 
            time_bucket(INTERVAL '15 Minutes', CAST(transacttime AS TIMESTAMP)) as candle_time,
            CAST(transacttime AS TIMESTAMP) as ts,
            lastpx as price,
            lastqty as qty,
            side,
            ordtype,
            lastliquidityind
        FROM '{data_dir}/aoa-execution-*.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND transacttime IS NOT NULL
    ),
    candles AS (
        SELECT 
            candle_time as timestamp,
            first(price ORDER BY ts ASC) as open,
            max(price) as high,
            min(price) as low,
            last(price ORDER BY ts ASC) as close,
            sum(qty) as volume,
            sum(CASE WHEN side = 'Buy' THEN qty ELSE 0 END) as buy_volume,
            sum(CASE WHEN side = 'Sell' THEN qty ELSE 0 END) as sell_volume,
            count(*) as trade_count
        FROM raw_trades
        GROUP BY candle_time
        ORDER BY candle_time ASC
    )
    SELECT * FROM candles
    """
    df_candles = con.sql(query).df()
    print(f"Loaded {len(df_candles):,} 15-minute candles with authentic trade actions!")
    
    # 2. Extract 12 Risk & Alpha Features
    print("\n=== [2/4] Computing 12 Institutional Risk & Alpha Features ===")
    extractor = WonyoFeatureExtractor()
    df_feat = extractor.compute_features(df_candles)
    
    feature_cols = [
        'volume_zscore',
        'volume_exhaustion',
        'body_ratio',
        'upper_wick_ratio',
        'lower_wick_ratio',
        'bullish_absorption',
        'bearish_absorption',
        'ret_1',
        'ret_5',
        'trend_bias',
        'microstructure_risk',
        'kaufman_efficiency'
    ]
    
    # Replace NaN / Inf
    df_feat[feature_cols] = df_feat[feature_cols].fillna(0.0).replace([np.inf, -np.inf], 0.0)
    
    # 3. Labeling Wonyotti's Authentic Actions & Position Sizing
    print("\n=== [3/4] Reconstructing Real Wonyotti Actions & Sizing ===")
    # Action labels:
    # 0: HOLD / PASS
    # 1: BUY_LONG
    # 2: SELL_SHORT
    # 3: CLOSE / SCRATCH
    actions = []
    sizes = []
    
    buy_vol = df_candles['buy_volume'].to_numpy()
    sell_vol = df_candles['sell_volume'].to_numpy()
    total_vol = df_candles['volume'].to_numpy()
    prices = df_candles['close'].to_numpy()
    
    # Rolling 90th percentile volume for size normalization
    vol_90 = np.percentile(total_vol, 90) if len(total_vol) > 0 else 1.0
    
    # Cumulative net position tracker
    net_position = 0.0
    
    for i in range(len(df_candles)):
        b = buy_vol[i]
        s = sell_vol[i]
        tot = total_vol[i]
        
        # Normalized size (0.1 to 3.0 scale)
        norm_size = float(np.clip(tot / (vol_90 + 1e-4), 0.1, 5.0))
        
        net_delta = b - s
        prev_pos = net_position
        net_position += net_delta
        
        if prev_pos == 0:
            if net_delta > 0:
                action = 1 # BUY_LONG
            elif net_delta < 0:
                action = 2 # SELL_SHORT
            else:
                action = 0 # HOLD
        else:
            # Check if position flipped or flattened
            if (prev_pos > 0 and net_position <= 0) or (prev_pos < 0 and net_position >= 0):
                action = 3 # CLOSE_POSITION
            elif (prev_pos > 0 and net_delta > 0):
                action = 1 # ADD LONG
            elif (prev_pos < 0 and net_delta < 0):
                action = 2 # ADD SHORT
            else:
                action = 0 # HOLD
                
        actions.append(action)
        sizes.append(norm_size)
        
    df_feat['action'] = actions
    df_feat['size'] = sizes
    
    action_counts = pd.Series(actions).value_counts()
    print("Action distribution:")
    labels_map = {0: "HOLD", 1: "BUY_LONG", 2: "SELL_SHORT", 3: "CLOSE"}
    for k, v in action_counts.items():
        print(f"  {labels_map.get(k, k)} ({k}): {v:,} ({v/len(actions)*100:.2f}%)")
        
    # 4. Construct 32-step sliding window tensors
    print("\n=== [4/4] Generating 32-step Sliding Window Tensors ===")
    seq_len = 32
    feat_matrix = df_feat[feature_cols].to_numpy().astype(np.float32)
    action_array = np.array(actions, dtype=np.int64)
    size_array = np.array(sizes, dtype=np.float32)
    
    X_list = []
    y_action_list = []
    y_size_list = []
    
    for t in range(seq_len, len(feat_matrix)):
        X_list.append(feat_matrix[t-seq_len:t])
        y_action_list.append(action_array[t])
        y_size_list.append(size_array[t])
        
    X = np.stack(X_list, axis=0)
    y_act = np.array(y_action_list)
    y_sz = np.array(y_size_list)
    
    print(f"Final Tensor Dimensions:")
    print(f"  X shape:      {X.shape} (dtype: {X.dtype})")
    print(f"  y_act shape:  {y_act.shape} (dtype: {y_act.dtype})")
    print(f"  y_sz shape:   {y_sz.shape} (dtype: {y_sz.dtype})")
    
    np.savez_compressed(
        out_npz,
        X=X,
        y_action=y_act,
        y_size=y_sz,
        feature_cols=np.array(feature_cols)
    )
    print(f"\nSuccessfully generated and compressed: {out_npz}")
    file_size_mb = os.path.getsize(out_npz) / (1024 * 1024)
    print(f"Output File Size: {file_size_mb:.2f} MB")
    return out_npz

if __name__ == "__main__":
    build_dataset()
