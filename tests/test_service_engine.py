"""
Unit Tests for WonyoSignalService
Following Superpowers TDD Standards
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.service_engine import WonyoSignalService, CommercialSignalResponse

def test_signal_service_warming_up():
    service = WonyoSignalService()
    # Push fewer than 30 candles
    for i in range(10):
        service.push_candle({
            "timestamp": f"2021-05-01 12:{i:02d}:00",
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 100000.0
        })
    res = service.evaluate_live({"equity_btc": 5.0})
    assert res.status == "WARMING_UP"
    assert res.action == "HOLD"
    assert res.order_type == "NONE"

def test_signal_service_live_response_structure():
    service = WonyoSignalService()
    # Push 40 normal candles
    for i in range(40):
        service.push_candle({
            "timestamp": f"2021-05-01 12:{i:02d}:00",
            "open": 50000.0 + i * 5,
            "high": 50100.0 + i * 5,
            "low": 49900.0 + i * 5,
            "close": 50050.0 + i * 5,
            "volume": 100000.0 + i * 100
        })
    res = service.evaluate_live({
        "equity_btc": 10.0,
        "current_position_contracts": 0,
        "consecutive_losses": 0
    })
    assert isinstance(res, CommercialSignalResponse)
    assert res.symbol == "XBTUSD"
    assert "microstructure_risk" in res.risk_state
    assert "regime_risk" in res.risk_state
    assert "portfolio_drawdown_pct" in res.risk_state
