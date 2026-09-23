"""
Unit Tests for Wonyo-Quant Risk Shield Engine
Following Superpowers TDD Standards
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.risk_engine import WonyoRiskEngine, PortfolioState

@pytest.fixture
def risk_engine():
    return WonyoRiskEngine(
        base_win_rate=0.7779,
        base_payoff_ratio=0.75,
        fractional_kelly=0.35,
        max_leverage_cap=5.0
    )

def test_full_kelly_calculation(risk_engine):
    # Full Kelly = (p*(b+1) - 1) / b = (0.7779*1.75 - 1)/0.75 = ~0.4817
    assert 0.48 < risk_engine.full_kelly < 0.49

def test_seed_leverage_decay(risk_engine):
    # Seed < 1 BTC
    assert risk_engine.compute_seed_leverage_limit(0.5) == 5.0
    # Seed 10 BTC
    assert pytest.approx(risk_engine.compute_seed_leverage_limit(10.0), rel=1e-2) == 3.0
    # Seed 100 BTC
    assert pytest.approx(risk_engine.compute_seed_leverage_limit(100.0), rel=1e-2) == 1.8
    # Seed 500 BTC
    assert pytest.approx(risk_engine.compute_seed_leverage_limit(500.0), rel=1e-2) == 1.3
    # Seed 1000 BTC
    assert risk_engine.compute_seed_leverage_limit(1500.0) <= 1.1

def test_circuit_breaker_on_extreme_drawdown(risk_engine):
    port = PortfolioState(
        equity_btc=7.0,
        btc_price_usd=50000.0,
        peak_equity_btc=10.0, # 30% Drawdown
        current_position_contracts=0,
        consecutive_losses=3
    )
    contracts, meta = risk_engine.calculate_position_size(
        portfolio=port,
        signal_confidence=0.8,
        microstructure_risk=0.1,
        regime_risk=0.1
    )
    assert contracts == 0.0
    assert meta["reason"] == "CIRCUIT_BREAKER_MAX_DRAWDOWN"
    assert meta["allowed"] is False

def test_circuit_breaker_on_liquidity_drain(risk_engine):
    port = PortfolioState(
        equity_btc=10.0,
        btc_price_usd=50000.0,
        peak_equity_btc=10.0, # 0% DD
        current_position_contracts=0,
        consecutive_losses=0
    )
    # Liquidity risk > 0.85
    contracts, meta = risk_engine.calculate_position_size(
        portfolio=port,
        signal_confidence=0.9,
        microstructure_risk=0.90,
        regime_risk=0.1
    )
    assert contracts == 0.0
    assert meta["reason"] == "CIRCUIT_BREAKER_LIQUIDITY_DRAIN"

def test_dynamic_stop_loss_and_take_profit(risk_engine):
    entry_px = 50000.0
    current_atr = 500.0 # 1% ATR
    regime_risk = 0.2

    # Long stops
    sl_long, tp_long = risk_engine.calculate_dynamic_stops(
        entry_price=entry_px,
        direction=1,
        current_atr=current_atr,
        regime_risk=regime_risk
    )
    assert sl_long < entry_px
    assert tp_long > entry_px
    loss_pct = (entry_px - sl_long) / entry_px * 100.0
    gain_pct = (tp_long - entry_px) / entry_px * 100.0
    assert 1.0 <= loss_pct <= 2.5
    assert gain_pct > 0.8

    # Short stops
    sl_short, tp_short = risk_engine.calculate_dynamic_stops(
        entry_price=entry_px,
        direction=-1,
        current_atr=current_atr,
        regime_risk=regime_risk
    )
    assert sl_short > entry_px
    assert tp_short < entry_px
