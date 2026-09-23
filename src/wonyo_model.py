"""
Wonyo-AI Core Policy Model
Risk-Conditioned Behavioral Decision Engine
Combines Machine Learning Probability Calibration with Wonyotti's Empirical Rules:
- Volume Exhaustion & Candle Absorption Detection
- 99.38% Limit Order Maker Strategy
- Bidirectional Symmetry (Long & Short Parity)
- Multi-tier Risk Gating
"""

import numpy as np
from enum import Enum
from typing import Dict, Any, Tuple
from .risk_engine import WonyoRiskEngine, PortfolioState

class ActionType(Enum):
    FLAT = 0
    ENTER_LONG = 1
    ENTER_SHORT = 2
    CLOSE_POSITION = 3

class WonyoAIModel:
    def __init__(
        self,
        risk_engine: WonyoRiskEngine = None,
        confidence_threshold: float = 0.62,
        volume_exhaustion_threshold: float = 2.2,
        absorption_threshold: float = 1.3
    ):
        self.risk_engine = risk_engine or WonyoRiskEngine()
        self.confidence_thresh = confidence_threshold
        self.vol_exhaustion_thresh = volume_exhaustion_threshold
        self.absorption_thresh = absorption_threshold

    def evaluate_signals(self, row: Dict[str, Any]) -> Tuple[float, float]:
        """
        Computes calibrated Long and Short score in [0, 1] based on:
        - Volume Exhaustion + Absorption
        - Momentum & Kaufman Efficiency
        - Overextension vs Mean
        """
        vol_z = row.get('volume_zscore', 0.0)
        vol_exh = row.get('volume_exhaustion', 1.0)
        bull_abs = row.get('bullish_absorption', 0.0)
        bear_abs = row.get('bearish_absorption', 0.0)
        upper_wick_ratio = row.get('upper_wick_ratio', 0.0)
        lower_wick_ratio = row.get('lower_wick_ratio', 0.0)
        body_ratio = row.get('body_ratio', 0.5)
        ret_1 = row.get('ret_1', 0.0)
        ret_5 = row.get('ret_5', 0.0)
        kaufman = row.get('kaufman_efficiency', 0.5)

        long_score = 0.0
        short_score = 0.0

        # Pattern 1: Bullish Orderflow Absorption (Liquidity soak at lows)
        if (bull_abs >= self.absorption_thresh and vol_exh >= self.vol_exhaustion_thresh) or \
           ((vol_z > 1.5 or vol_exh > 1.8) and lower_wick_ratio > 0.35 and ret_1 < 0.005):
            absorption_power = max(bull_abs, lower_wick_ratio / (body_ratio + 1e-4))
            long_score += 0.50 + min(0.35, absorption_power * 0.1)

        # Pattern 2: Bearish Orderflow Absorption (Liquidity soak at highs)
        if (bear_abs >= self.absorption_thresh and vol_exh >= self.vol_exhaustion_thresh) or \
           ((vol_z > 1.5 or vol_exh > 1.8) and upper_wick_ratio > 0.35 and ret_1 > -0.005):
            absorption_power = max(bear_abs, upper_wick_ratio / (body_ratio + 1e-4))
            short_score += 0.50 + min(0.35, absorption_power * 0.1)

        # Pattern 3: Mean Reversion on Extreme Volatility Exhaustion
        if vol_z > 2.0 and abs(ret_1) > 0.02:
            if ret_1 < -0.02: # Oversold panic flush
                long_score += 0.45
            elif ret_1 > 0.02: # Overbought climax
                short_score += 0.45

        # Pattern 4: Trend Bias Alignment (Wonyotti's trend continuation filter)
        trend_bias = row.get('trend_bias', 0.0)
        if trend_bias > 0.01:
            long_score += 0.15   # Tailwind for Longs
            short_score -= 0.15  # Penalty for counter-trend Shorts
        elif trend_bias < -0.01:
            short_score += 0.15  # Tailwind for Shorts
            long_score -= 0.15   # Penalty for counter-trend Longs

        return np.clip(long_score, 0.0, 1.0), np.clip(short_score, 0.0, 1.0)

    def decide(
        self,
        features: Dict[str, Any],
        portfolio: PortfolioState
    ) -> Dict[str, Any]:
        """
        End-to-End Decision:
        Takes state + risk inputs -> Action, Limit Price, Contracts, StopLoss, TakeProfit
        """
        current_price = features.get('close', 0.0)
        current_atr = features.get('atr', current_price * 0.01)
        micro_risk = features.get('microstructure_risk', 0.0)
        regime_risk = features.get('regime_risk', 0.0)

        # 1. RISK GATING: Check if conditions are too hostile for new risk
        if micro_risk >= 0.80:
            return {
                "action": ActionType.FLAT,
                "confidence": 0.0,
                "reason": "RISK_GATE_MICROSTRUCTURE_ILLIQUID",
                "contracts": 0
            }
        if regime_risk >= 0.85:
            return {
                "action": ActionType.FLAT,
                "confidence": 0.0,
                "reason": "RISK_GATE_REGIME_VOLATILITY_SHOCK",
                "contracts": 0
            }
        if portfolio.drawdown_pct >= 20.0:
            return {
                "action": ActionType.FLAT,
                "confidence": 0.0,
                "reason": "RISK_GATE_PORTFOLIO_DRAWDOWN_LIMIT",
                "contracts": 0
            }

        # 2. Check if existing position needs to be managed
        has_long = portfolio.current_position_contracts > 0
        has_short = portfolio.current_position_contracts < 0

        long_score, short_score = self.evaluate_signals(features)

        # If holding long and strong short signal arrives -> close
        if has_long and short_score >= self.confidence_thresh:
            return {
                "action": ActionType.CLOSE_POSITION,
                "confidence": short_score,
                "reason": "REVERSAL_SIGNAL_SHORT",
                "limit_price": current_price,
                "contracts": abs(portfolio.current_position_contracts)
            }
        # If holding short and strong long signal arrives -> close
        if has_short and long_score >= self.confidence_thresh:
            return {
                "action": ActionType.CLOSE_POSITION,
                "confidence": long_score,
                "reason": "REVERSAL_SIGNAL_LONG",
                "limit_price": current_price,
                "contracts": abs(portfolio.current_position_contracts)
            }

        # 3. New Entry Decision
        selected_action = ActionType.FLAT
        confidence = 0.0
        direction = 0

        if not (has_long or has_short):
            if long_score >= self.confidence_thresh and long_score > short_score:
                selected_action = ActionType.ENTER_LONG
                confidence = long_score
                direction = 1
            elif short_score >= self.confidence_thresh and short_score > long_score:
                selected_action = ActionType.ENTER_SHORT
                confidence = short_score
                direction = -1

        if selected_action == ActionType.FLAT:
            return {
                "action": ActionType.FLAT,
                "confidence": max(long_score, short_score),
                "reason": "NO_HIGH_CONVICTION_SETUP",
                "contracts": 0
            }

        # 4. Position Sizing via Wall St Risk Engine
        contracts, sizing_meta = self.risk_engine.calculate_position_size(
            portfolio=portfolio,
            signal_confidence=confidence,
            microstructure_risk=micro_risk,
            regime_risk=regime_risk
        )

        if not sizing_meta.get("allowed", False) or contracts <= 0:
            return {
                "action": ActionType.FLAT,
                "confidence": confidence,
                "reason": sizing_meta.get("reason", "RISK_SIZING_ZERO"),
                "contracts": 0
            }

        # 5. Order Placement: Limit Order (Maker)
        # Wonyotti uses 99.38% Limit orders.
        # For Long: placed at current_price - 0.5 * tick (passive bid)
        # For Short: placed at current_price + 0.5 * tick (passive ask)
        tick_size = 0.5
        if direction == 1:
            limit_price = current_price - tick_size
        else:
            limit_price = current_price + tick_size

        # 6. Dynamic Stops
        stop_loss, take_profit = self.risk_engine.calculate_dynamic_stops(
            entry_price=limit_price,
            direction=direction,
            current_atr=current_atr,
            regime_risk=regime_risk
        )

        return {
            "action": selected_action,
            "direction": direction,
            "confidence": confidence,
            "limit_price": limit_price,
            "contracts": contracts,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "sizing_meta": sizing_meta,
            "reason": "EXECUTE_RISK_CONDITIONED_LIMIT_ENTRY"
        }
