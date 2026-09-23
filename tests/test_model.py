"""
Unit Tests for WonyoAIModel
Following Superpowers TDD Standards
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.risk_engine import WonyoRiskEngine, PortfolioState
from src.wonyo_model import WonyoAIModel, ActionType

@pytest.fixture
def model():
    risk_eng = WonyoRiskEngine()
    return WonyoAIModel(risk_engine=risk_eng)

def test_risk_gating_suppresses_entry(model):
    port = PortfolioState(
        equity_btc=10.0,
        btc_price_usd=50000.0,
        peak_equity_btc=10.0,
        current_position_contracts=0,
        consecutive_losses=0
    )
    # Hostile microstructure
    hostile_features = {
        'close': 50000.0,
        'atr': 500.0,
        'microstructure_risk': 0.85, # Blown spread / drain
        'regime_risk': 0.1,
        'volume_zscore': 3.0,
        'volume_exhaustion': 3.5,
        'bullish_absorption': 2.5
    }
    decision = model.decide(hostile_features, port)
    assert decision["action"] == ActionType.FLAT
    assert "RISK_GATE" in decision["reason"]

def test_bullish_absorption_triggers_long(model):
    port = PortfolioState(
        equity_btc=10.0,
        btc_price_usd=50000.0,
        peak_equity_btc=10.0,
        current_position_contracts=0,
        consecutive_losses=0
    )
    strong_long_features = {
        'close': 50000.0,
        'atr': 400.0,
        'microstructure_risk': 0.1,
        'regime_risk': 0.1,
        'volume_zscore': 2.8,
        'volume_exhaustion': 3.0,
        'bullish_absorption': 2.2, # Strong lower wick + high volume
        'bearish_absorption': 0.1,
        'ret_1': -0.005,
        'ret_5': -0.015,
        'kaufman_efficiency': 0.3
    }
    decision = model.decide(strong_long_features, port)
    assert decision["action"] == ActionType.ENTER_LONG
    assert decision["direction"] == 1
    assert decision["limit_price"] <= 50000.0 # Maker passive order
    assert decision["contracts"] > 0
    assert decision["stop_loss"] < decision["limit_price"] < decision["take_profit"]

def test_bearish_absorption_triggers_short(model):
    port = PortfolioState(
        equity_btc=10.0,
        btc_price_usd=50000.0,
        peak_equity_btc=10.0,
        current_position_contracts=0,
        consecutive_losses=0
    )
    strong_short_features = {
        'close': 50000.0,
        'atr': 400.0,
        'microstructure_risk': 0.1,
        'regime_risk': 0.1,
        'volume_zscore': 2.8,
        'volume_exhaustion': 3.0,
        'bullish_absorption': 0.1,
        'bearish_absorption': 2.2, # Strong upper wick + high volume
        'ret_1': 0.005,
        'ret_5': 0.015,
        'kaufman_efficiency': 0.3
    }
    decision = model.decide(strong_short_features, port)
    assert decision["action"] == ActionType.ENTER_SHORT
    assert decision["direction"] == -1
    assert decision["limit_price"] >= 50000.0 # Maker passive order
    assert decision["contracts"] > 0
    assert decision["take_profit"] < decision["limit_price"] < decision["stop_loss"]
