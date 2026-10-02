"""Unit tests for the always-on worker's position lifecycle rules
(stop loss -> take profit -> 60-min scratch -> 120-min hard timeout)
and inverse-contract BTC PnL math. Pure logic - no network."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.worker import (
    check_exit, compute_trade, unrealized_pnl_pct, open_position,
    SCRATCH_MINUTES, TIMEOUT_MINUTES,
)


def make_position(side="LONG", entry=100.0, sl=98.5, tp=101.2, contracts=2000.0,
                  held_minutes=5.0):
    return {
        "id": "WYC-TEST",
        "side": side,
        "direction": side,
        "entry_price": entry,
        "contracts": contracts,
        "leverage": 2.0,
        "stop_loss": sl,
        "take_profit": tp,
        "entry_time": "2026-10-03T00:00:00+09:00",
        "entry_epoch": time.time() - held_minutes * 60,
    }


class TestCheckExit:
    def test_stop_loss_long(self):
        pos = make_position()
        exit_info = check_exit(pos, price=98.4, now_epoch=time.time())
        assert exit_info == {"reason": "STOP_LOSS", "exit_price": 98.5}

    def test_take_profit_long(self):
        pos = make_position()
        exit_info = check_exit(pos, price=101.3, now_epoch=time.time())
        assert exit_info == {"reason": "TAKE_PROFIT", "exit_price": 101.2}

    def test_stop_loss_short(self):
        pos = make_position(side="SHORT", entry=100.0, sl=100.6, tp=98.8)
        exit_info = check_exit(pos, price=100.7, now_epoch=time.time())
        assert exit_info == {"reason": "STOP_LOSS", "exit_price": 100.6}

    def test_take_profit_short(self):
        pos = make_position(side="SHORT", entry=100.0, sl=100.6, tp=98.8)
        exit_info = check_exit(pos, price=98.7, now_epoch=time.time())
        assert exit_info == {"reason": "TAKE_PROFIT", "exit_price": 98.8}

    def test_scratch_exit_mild_loss_after_60min(self):
        # -0.2% loss at 61min -> scratch escape blocks the full stop loss
        pos = make_position(held_minutes=SCRATCH_MINUTES + 1)
        exit_info = check_exit(pos, price=99.8, now_epoch=time.time())
        assert exit_info["reason"] == "SCRATCH_EXIT"
        assert exit_info["exit_price"] == 99.8

    def test_deep_loss_beyond_scratch_window_holds(self):
        # -1.0% loss (not yet at SL) after 61min: no scratch, wait for SL/timeout
        pos = make_position(held_minutes=SCRATCH_MINUTES + 1)
        assert check_exit(pos, price=99.0, now_epoch=time.time()) is None

    def test_hard_timeout_at_120min(self):
        pos = make_position(held_minutes=TIMEOUT_MINUTES + 1)
        exit_info = check_exit(pos, price=100.1, now_epoch=time.time())
        assert exit_info["reason"] == "TIMEOUT_CLOSE"

    def test_no_exit_when_nothing_triggered(self):
        pos = make_position(held_minutes=10)
        assert check_exit(pos, price=100.4, now_epoch=time.time()) is None


class TestPnlMath:
    def test_unrealized_pct_long_and_short(self):
        pos = make_position()
        assert unrealized_pnl_pct(pos, 102.0) == 2.0
        short = make_position(side="SHORT")
        assert unrealized_pnl_pct(short, 99.0) == 1.0

    def test_compute_trade_inverse_contract_btc(self):
        # LONG 100 -> 102 with 2000 USD contracts:
        # pnl_btc = 1 * 2000 * (1/100 - 1/102) = 0.392157 BTC
        # rebate  = 2000 * 0.00025 * 2 / 102   = 0.009804 BTC
        pos = make_position(held_minutes=65)
        trade = compute_trade(pos, exit_price=102.0, exit_reason="TAKE_PROFIT")
        assert trade["pnl_pct"] == 2.0
        assert abs(trade["pnl_btc"] - 0.392157) < 1e-6
        assert abs(trade["maker_rebate_btc"] - 0.009804) < 1e-6
        assert abs(trade["net_pnl_btc"] - 0.401961) < 1e-6
        assert trade["holding_time"] == "01:05"
        assert trade["bars_held"] == 5
        assert trade["exit_reason"] == "TAKE_PROFIT"

    def test_open_position_maps_decision(self):
        decision = {
            "action": "ENTER_LONG", "direction": 1, "contracts": 3000.0,
            "limit_price": 100.0, "stop_loss": 98.5, "take_profit": 101.2,
        }
        pos = open_position(decision, price=100.0, equity_btc=15.0)
        assert pos["side"] == "LONG"
        assert pos["entry_price"] == 100.0
        assert pos["leverage"] == 2.0  # 3000 / (15 * 100)
        assert pos["id"].startswith("WYC-")
