"""
Wonyo-Quant Risk Shield Engine
Wall Street Institutional Grade Portfolio & Risk Management Module
Calibrated on Wonyotti's historical 1.44M execution profile.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Tuple

@dataclass
class PortfolioState:
    equity_btc: float
    btc_price_usd: float
    peak_equity_btc: float
    current_position_contracts: float  # In USD contracts (1 contract = $1)
    consecutive_losses: int
    unrealized_pnl_btc: float = 0.0

    @property
    def equity_usd(self) -> float:
        return self.equity_btc * self.btc_price_usd

    @property
    def drawdown_pct(self) -> float:
        if self.peak_equity_btc <= 0:
            return 0.0
        dd = (self.peak_equity_btc - self.equity_btc) / self.peak_equity_btc * 100.0
        return max(0.0, dd)

    @property
    def current_leverage(self) -> float:
        eq_usd = self.equity_usd
        if eq_usd <= 0:
            return 0.0
        return abs(self.current_position_contracts) / eq_usd


class WonyoRiskEngine:
    """
    Implements:
    1. Fractional Kelly Criterion calibrated on observed win rate & payoff ratio.
    2. Dynamic Drawdown & Loss-Streak Penalty (Psychological & Tail-Risk Shield).
    3. Seed-Scale Leverage Decay (Capital preservation scaling).
    4. Volatility-Adjusted Strict Stop Loss & Take Profit limits.
    """
    def __init__(
        self,
        base_win_rate: float = 0.7779,
        base_payoff_ratio: float = 0.75,
        fractional_kelly: float = 0.35, # Conservative fractional Kelly (Wall St standard: 0.2 ~ 0.5)
        max_leverage_cap: float = 5.0,
        min_stop_loss_pct: float = 1.0,
        max_stop_loss_pct: float = 2.5
    ):
        self.p = base_win_rate
        self.b = base_payoff_ratio
        self.fractional_kelly = fractional_kelly
        self.max_leverage_cap = max_leverage_cap
        self.min_stop_loss_pct = min_stop_loss_pct
        self.max_stop_loss_pct = max_stop_loss_pct

        # Full Kelly = (p*(b+1) - 1) / b
        # For p=0.7779, b=0.75: (0.7779*1.75 - 1)/0.75 = (1.3613 - 1)/0.75 = 0.4817 (48.2%)
        self.full_kelly = (self.p * (self.b + 1.0) - 1.0) / self.b

    def compute_seed_leverage_limit(self, equity_btc: float) -> float:
        """
        Wonyotti's empirical leverage decay:
        - 2018 (Seed < 10 BTC): Median leverage ~ 5.38x
        - 2019 (Seed 10-100 BTC): Median leverage ~ 1.78x
        - 2020 (Seed 100-500 BTC): Median leverage ~ 1.45x
        - 2021 (Seed > 500 BTC): Median leverage ~ 1.08x
        """
        if equity_btc <= 1.0:
            return min(self.max_leverage_cap, 5.0)
        elif equity_btc <= 10.0:
            # Linear decay from 5.0x down to 3.0x
            return 5.0 - (equity_btc - 1.0) * (2.0 / 9.0)
        elif equity_btc <= 100.0:
            # Decay from 3.0x down to 1.8x
            return 3.0 - (equity_btc - 10.0) * (1.2 / 90.0)
        elif equity_btc <= 500.0:
            # Decay from 1.8x down to 1.3x
            return 1.8 - (equity_btc - 100.0) * (0.5 / 400.0)
        else:
            # Mega-fund regime: 1.0x ~ 1.2x cash equivalent
            return max(1.0, 1.3 - (equity_btc - 500.0) * (0.3 / 1000.0))

    def evaluate_risk_multipliers(
        self,
        portfolio: PortfolioState,
        microstructure_risk: float, # 0.0 (safe) to 1.0 (extreme risk/spread blown)
        regime_risk: float         # 0.0 (normal) to 1.0 (crisis/extreme volatility)
    ) -> Dict[str, float]:
        """
        Calculates penalty multipliers based on portfolio health and external risks.
        """
        # 1. Drawdown Penalty: As DD approaches 15%, exponentially slash exposure
        dd = portfolio.drawdown_pct
        if dd < 5.0:
            dd_penalty = 1.0
        elif dd < 15.0:
            dd_penalty = 1.0 - (dd - 5.0) * 0.07  # drops to 0.3 at 15% DD
        else:
            # Circuit breaker territory
            dd_penalty = max(0.05, 0.3 - (dd - 15.0) * 0.03)

        # 2. Consecutive Loss Streak Penalty
        # Wonyotti's cooldown habit: after 3+ consecutive losses, reduce size to reset psychology
        streak = portfolio.consecutive_losses
        streak_penalty = max(0.2, 1.0 - (streak * 0.15))

        # 3. Microstructure & Spread Penalty
        micro_penalty = max(0.1, 1.0 - (microstructure_risk * 0.8))

        # 4. Market Regime / Crisis Penalty
        regime_penalty = max(0.2, 1.0 - (regime_risk * 0.7))

        combined_risk_factor = dd_penalty * streak_penalty * micro_penalty * regime_penalty

        return {
            "drawdown_penalty": dd_penalty,
            "streak_penalty": streak_penalty,
            "microstructure_penalty": micro_penalty,
            "regime_penalty": regime_penalty,
            "combined_risk_factor": combined_risk_factor
        }

    def calculate_position_size(
        self,
        portfolio: PortfolioState,
        signal_confidence: float,  # 0.0 to 1.0 from ML model
        microstructure_risk: float = 0.0,
        regime_risk: float = 0.0
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Returns target position size in USD contracts, subject to all institutional risk bounds.
        """
        # Check hard circuit breaker: if DD > 25%, HALT all new entries
        if portfolio.drawdown_pct >= 25.0:
            return 0.0, {"reason": "CIRCUIT_BREAKER_MAX_DRAWDOWN", "allowed": False}

        # Check microstructure risk: if spread is blown out (risk > 0.85), skip entry
        if microstructure_risk >= 0.85:
            return 0.0, {"reason": "CIRCUIT_BREAKER_LIQUIDITY_DRAIN", "allowed": False}

        # 1. Seed leverage cap
        lev_cap = self.compute_seed_leverage_limit(portfolio.equity_btc)

        # 2. Base Kelly allocation
        # Base fraction = Fractional_Kelly * full_kelly * signal_confidence
        base_fraction = self.fractional_kelly * self.full_kelly * signal_confidence

        # 3. Apply risk multipliers
        penalties = self.evaluate_risk_multipliers(portfolio, microstructure_risk, regime_risk)
        effective_fraction = base_fraction * penalties["combined_risk_factor"]

        # Effective leverage = fraction * lev_cap
        target_leverage = min(lev_cap, effective_fraction * lev_cap)

        # Target USD contracts
        target_contracts = portfolio.equity_usd * target_leverage

        meta = {
            "allowed": True,
            "seed_leverage_cap": lev_cap,
            "target_leverage": target_leverage,
            "penalties": penalties,
            "target_contracts": target_contracts
        }
        return target_contracts, meta

    def calculate_dynamic_stops(
        self,
        entry_price: float,
        direction: int, # 1 for Long, -1 for Short
        current_atr: float,
        regime_risk: float
    ) -> Tuple[float, float]:
        """
        Calculates dynamic Stop-Loss and Take-Profit price levels.
        Calibrated to Wonyotti's observed +1.13% target and -1.49% tight loss cut.
        """
        # Volatility scaled SL/TP
        atr_pct = (current_atr / entry_price) * 100.0 if entry_price > 0 else 1.0
        
        # Base stop loss is ~1.5%, adjusted by ATR and regime
        sl_pct = np.clip(1.49 * (1.0 + 0.3 * regime_risk) * (atr_pct / 1.0), self.min_stop_loss_pct, self.max_stop_loss_pct)
        # Base take profit is ~1.13% ~ 1.8%
        tp_pct = sl_pct * self.b * 1.05  # keep favorable expected value

        if direction == 1: # Long
            stop_loss = entry_price * (1.0 - sl_pct / 100.0)
            take_profit = entry_price * (1.0 + tp_pct / 100.0)
        else: # Short
            stop_loss = entry_price * (1.0 + sl_pct / 100.0)
            take_profit = entry_price * (1.0 - tp_pct / 100.0)

        return stop_loss, take_profit
