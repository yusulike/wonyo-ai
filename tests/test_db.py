import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import sqlite3
from src.db import WonyoDBManager, get_db_manager

def test_db_manager_sqlite_fallback(tmp_path):
    """Test that WonyoDBManager gracefully initializes and seeds SQLite when POSTGRES_URL is not set."""
    db_file = tmp_path / "test_trades.db"
    mgr = WonyoDBManager(postgres_url=None, sqlite_path=str(db_file))
    mgr.init_db()

    # Verify table creation & initial seeding
    result = mgr.get_trades_history()
    assert result["status"] == "SUCCESS"
    assert len(result["live_trades"]) >= 5
    assert result["summary"]["total_trades"] >= 5
    assert "win_rate_pct" in result["summary"]
    assert "net_pnl_btc" in result["summary"]
    assert "wonyo_level" in result["summary"]

def test_db_manager_record_trade(tmp_path):
    """Test recording a new trade and ensuring summary metrics update correctly."""
    db_file = tmp_path / "test_trades_record.db"
    mgr = WonyoDBManager(postgres_url=None, sqlite_path=str(db_file))
    mgr.init_db()

    initial_count = len(mgr.get_trades_history()["live_trades"])

    # Record a new profitable trade
    new_trade = {
        "id": "TRD-TEST-999",
        "direction": "LONG",
        "side": "LONG",
        "leverage": 2.0,
        "entry_price": 85000.0,
        "exit_price": 86000.0,
        "pnl_pct": 1.18,
        "pnl_btc": 0.0118,
        "maker_rebate_btc": 0.00035,
        "exit_reason": "1차 목표가 도달 (TP)",
        "holding_time": "15분",
        "bars_held": 1
    }
    mgr.record_trade(new_trade)

    updated = mgr.get_trades_history()
    assert len(updated["live_trades"]) == initial_count + 1
    latest = updated["live_trades"][0]
    assert latest["id"] == "TRD-TEST-999"
    assert latest["direction"] == "LONG"
    assert latest["pnl_pct"] == 1.18

def test_legendary_trades_included():
    """Verify that legendary historical archive trades are always returned."""
    mgr = WonyoDBManager(postgres_url=None, sqlite_path=":memory:")
    mgr.init_db()
    data = mgr.get_trades_history()
    assert "legendary_trades" in data
    assert len(data["legendary_trades"]) >= 3
    assert data["legendary_trades"][0]["title"] == "2021.05.19 부처빔 바닥 쓸어담기"

def test_trades_sorted_descending_by_timestamp(tmp_path):
    """Verify trades are strictly returned in descending order of trade transaction timestamp."""
    db_file = tmp_path / "test_sort_trades.db"
    mgr = WonyoDBManager(postgres_url=None, sqlite_path=str(db_file))
    mgr.init_db()

    # Record out-of-order trades
    mgr.record_trade({
        "id": "TRD-EARLY",
        "timestamp_kst": "2026-09-20 10:00",
        "direction": "LONG",
        "entry_price": 80000.0,
        "exit_price": 81000.0,
        "pnl_pct": 1.25
    })
    mgr.record_trade({
        "id": "TRD-LATEST",
        "timestamp_kst": "2026-09-25 18:30",
        "direction": "SHORT",
        "entry_price": 85000.0,
        "exit_price": 84000.0,
        "pnl_pct": 1.18
    })

    data = mgr.get_trades_history(limit=50)
    trades = data["live_trades"]
    timestamps = [t.get("timestamp_kst") or t.get("time_kst") or "" for t in trades]
    # Check that timestamps list is strictly monotonically non-increasing (descending)
    for i in range(len(timestamps) - 1):
        assert timestamps[i] >= timestamps[i + 1], f"Trade at {i} ({timestamps[i]}) is older than {i+1} ({timestamps[i+1]})"
    assert trades[0]["id"] == "TRD-LATEST"

