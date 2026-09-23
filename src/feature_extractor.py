"""
Wonyo-Quant Feature Extractor
Generates 4-Tier Risk-Conditioned Feature Tensors:
1. Volume Alpha & Price Action
2. Microstructure & Liquidity Risk
3. Market Regime Shift Risk
4. Portfolio & Capital State
"""

import numpy as np
import pandas as pd
from typing import Dict, Any

class WonyoFeatureExtractor:
    def __init__(
        self,
        volume_window: int = 20,
        volatility_window: int = 20,
        kaufman_window: int = 14
    ):
        self.vol_window = volume_window
        self.volatility_window = volatility_window
        self.kaufman_window = kaufman_window

    def compute_features(self, df_candles: pd.DataFrame, portfolio_state: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Input: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        Output: Feature engineered DataFrame with all 4 risk/alpha tiers.
        """
        df = df_candles.copy()

        # ----------------------------------------------------
        # 1. ALPHA TIER: Volume Profile & Price Action
        # ----------------------------------------------------
        # Volume EMA & Z-Score
        df['vol_ema'] = df['volume'].ewm(span=self.vol_window, adjust=False).mean()
        df['vol_std'] = df['volume'].rolling(self.vol_window).std()
        df['volume_zscore'] = np.where(df['vol_std'] > 0, (df['volume'] - df['vol_ema']) / df['vol_std'], 0.0)
        df['volume_exhaustion'] = df['volume'] / (df['vol_ema'] + 1e-6)

        # Candle Micro-geometry (Wicks & Body)
        candle_range = np.maximum(df['high'] - df['low'], 1e-6)
        body = np.abs(df['close'] - df['open'])
        upper_wick = df['high'] - np.maximum(df['open'], df['close'])
        lower_wick = np.minimum(df['open'], df['close']) - df['low']

        df['body_ratio'] = body / candle_range
        df['upper_wick_ratio'] = upper_wick / candle_range
        df['lower_wick_ratio'] = lower_wick / candle_range

        # Absorption Pattern: High volume + Long wick (Order absorption at support/resistance)
        # Bullish absorption: heavy volume hitting lower wick (buyers soaking sellers)
        # Bearish absorption: heavy volume hitting upper wick (sellers soaking buyers)
        df['bullish_absorption'] = df['lower_wick_ratio'] * np.clip(df['volume_exhaustion'], 0, 5)
        df['bearish_absorption'] = df['upper_wick_ratio'] * np.clip(df['volume_exhaustion'], 0, 5)

        # Returns & Momentum
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_5'] = df['close'].pct_change(5)
        df['ret_15'] = df['close'].pct_change(15)

        # Multi-timeframe Moving Averages
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['trend_bias'] = (df['close'] - df['ema_50']) / df['ema_50'] # Positive in uptrend, negative in downtrend

        # True Range & ATR
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = df['true_range'].rolling(self.volatility_window).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100.0

        # ----------------------------------------------------
        # 2. MICROSTRUCTURE & LIQUIDITY RISK TIER
        # ----------------------------------------------------
        # Amihud Illiquidity Ratio: |ret| / (Price * Volume)
        # Measures price impact per unit of dollar volume
        dollar_vol = df['close'] * df['volume']
        df['amihud_illiquidity'] = (df['ret_1'].abs() / (dollar_vol + 1e-6)) * 1e8
        df['microstructure_risk'] = (
            (df['amihud_illiquidity'] - df['amihud_illiquidity'].rolling(self.vol_window).mean()) /
            (df['amihud_illiquidity'].rolling(self.vol_window).std() + 1e-6)
        )
        df['microstructure_risk'] = 1.0 / (1.0 + np.exp(-df['microstructure_risk'])) # Sigmoid mapped to [0, 1]

        # ----------------------------------------------------
        # 3. MARKET REGIME SHIFT RISK TIER
        # ----------------------------------------------------
        # Kaufman Efficiency Ratio (KER): Net Directional Movement / Gross Price Path
        direction = (df['close'] - df['close'].shift(self.kaufman_window)).abs()
        volatility = df['close'].diff().abs().rolling(self.kaufman_window).sum()
        df['kaufman_efficiency'] = np.where(volatility > 0, direction / volatility, 0.0)

        # Realized Volatility Regime (Annualized std of 15m returns)
        roll_vol = df['ret_1'].rolling(self.volatility_window).std()
        mean_vol = roll_vol.rolling(100).mean()
        std_vol = roll_vol.rolling(100).std()
        df['regime_risk'] = np.where(std_vol > 0, (roll_vol - mean_vol) / std_vol, 0.0)
        df['regime_risk'] = np.clip(1.0 / (1.0 + np.exp(-df['regime_risk'])), 0.0, 1.0) # [0, 1]

        # ----------------------------------------------------
        # 4. PORTFOLIO & CAPITAL RISK TIER
        # ----------------------------------------------------
        if portfolio_state is not None:
            df['portfolio_drawdown'] = portfolio_state.get('drawdown_pct', 0.0)
            df['consecutive_losses'] = portfolio_state.get('consecutive_losses', 0)
            df['current_leverage'] = portfolio_state.get('current_leverage', 0.0)
        else:
            df['portfolio_drawdown'] = 0.0
            df['consecutive_losses'] = 0
            df['current_leverage'] = 0.0

        return df
