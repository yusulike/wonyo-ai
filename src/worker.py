"""
Wonyo-AI Always-On Trading Worker (hybrid architecture, personal Linux server)
==============================================================================
The browser dashboard is the only "heartbeat" on Vercel - when nobody has the
page open, nothing runs. This worker runs 24/7 on a personal server as that
heartbeat:

  every 10s tick:
    1. Manage any open virtual position against the live BTC price
       (stop loss -> take profit -> 60-min scratch -> 120-min hard timeout)
    2. On each closed 15m candle, evaluate the wonyo model for a new entry
    3. Record finished trades to the same Postgres ledger (POSTGRES_URL / Neon)
       the Vercel dashboard reads - SQLite fallback is automatic.

Run:  uv run python -m src.worker
Env:  POSTGRES_URL (Neon connection string; omit for local SQLite)
      WONYO_WORKER_MAX_TICKS=N  (smoke test: stop after N ticks)
State: data/worker_state.json (equity, loss streak, open position)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.risk_engine import PortfolioState
from src.wonyo_model import ActionType
from src.web_api import model, extractor, fetch_live_binance_candles
from src.db import WonyoDBManager

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "worker_state.json"

TICK_SECONDS = 10
KST = timezone(timedelta(hours=9))

# Wonyotti commercial exit rules (see AGENTS.md)
SCRATCH_MINUTES = 60        # losing but recovered to within -0.4% -> scratch exit
SCRATCH_PNL_PCT = -0.4
TIMEOUT_MINUTES = 120       # hard timeout (loser median 88min + buffer)
MAKER_REBATE_RATE = 0.00025 # BitMEX maker rebate, both entry and exit fills


def now_kst() -> datetime:
    return datetime.now(KST)


def fetch_live_price() -> float:
    """Current BTC price with Binance.US fallback (mirrors web_api pattern)."""
    for host in ("api.binance.com", "api.binance.us"):
        try:
            r = requests.get(f"https://{host}/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
            if r.status_code == 200:
                return float(r.json()["price"])
        except Exception:
            continue
    raise RuntimeError("All price endpoints failed")


# ---------------------------------------------------------------------------
# Position lifecycle - pure logic, unit-tested in tests/test_worker.py
# ---------------------------------------------------------------------------

def open_position(decision: Dict[str, Any], price: float, equity_btc: float) -> Dict[str, Any]:
    side = "LONG" if decision["direction"] == 1 else "SHORT"
    contracts = float(decision["contracts"])
    return {
        "id": "WYC-" + now_kst().strftime("%Y%m%d-%H%M%S"),
        "side": side,
        "direction": side,
        "entry_price": float(decision["limit_price"]),
        "contracts": contracts,
        "leverage": round(contracts / (equity_btc * price), 2) if equity_btc * price > 0 else 0.0,
        "stop_loss": float(decision["stop_loss"]),
        "take_profit": float(decision["take_profit"]),
        "entry_time": now_kst().isoformat(),
        "entry_epoch": time.time(),
    }


def unrealized_pnl_pct(position: Dict[str, Any], price: float) -> float:
    move_pct = (price - position["entry_price"]) / position["entry_price"] * 100.0
    return move_pct if position["side"] == "LONG" else -move_pct


def check_exit(position: Dict[str, Any], price: float, now_epoch: float) -> Optional[Dict[str, Any]]:
    """Priority: stop loss -> take profit -> 60-min scratch -> hard timeout."""
    held_min = (now_epoch - position["entry_epoch"]) / 60.0
    pnl_pct = unrealized_pnl_pct(position, price)
    long = position["side"] == "LONG"

    if (long and price <= position["stop_loss"]) or (not long and price >= position["stop_loss"]):
        return {"reason": "STOP_LOSS", "exit_price": position["stop_loss"]}
    if (long and price >= position["take_profit"]) or (not long and price <= position["take_profit"]):
        return {"reason": "TAKE_PROFIT", "exit_price": position["take_profit"]}
    if held_min >= SCRATCH_MINUTES and SCRATCH_PNL_PCT <= pnl_pct < 0.0:
        return {"reason": "SCRATCH_EXIT", "exit_price": price}
    if held_min >= TIMEOUT_MINUTES:
        return {"reason": "TIMEOUT_CLOSE", "exit_price": price}
    return None


def compute_trade(position: Dict[str, Any], exit_price: float, exit_reason: str) -> Dict[str, Any]:
    """Builds the ledger record (and BTC PnL) for a finished position.
    Uses inverse-contract BTC PnL: dir * contracts * (1/entry - 1/exit)."""
    entry = position["entry_price"]
    direction = 1 if position["side"] == "LONG" else -1
    pnl_btc = direction * position["contracts"] * (1.0 / entry - 1.0 / exit_price)
    rebate_btc = position["contracts"] * MAKER_REBATE_RATE * 2.0 / exit_price
    pnl_pct = unrealized_pnl_pct(position, exit_price)
    held_min = (time.time() - position["entry_epoch"]) / 60.0

    return {
        "id": position["id"],
        "timestamp_kst": datetime.fromtimestamp(position["entry_epoch"], KST).strftime("%Y-%m-%d %H:%M"),
        "side": position["side"],
        "direction": position["side"],
        "leverage": position["leverage"],
        "entry_price": entry,
        "exit_price": exit_price,
        "pnl_pct": round(pnl_pct, 3),
        "pnl_btc": round(pnl_btc, 6),
        "maker_rebate_btc": round(rebate_btc, 6),
        "net_pnl_btc": round(pnl_btc + rebate_btc, 6),
        "exit_reason": exit_reason,
        "holding_time": f"{int(held_min // 60):02d}:{int(held_min % 60):02d}",
        "bars_held": max(1, int(held_min / 15) + 1),
    }


# ---------------------------------------------------------------------------
# Worker state persistence
# ---------------------------------------------------------------------------

def default_state() -> Dict[str, Any]:
    return {"equity_btc": 10.0, "peak_equity_btc": 10.0, "consecutive_losses": 0,
            "position": None, "last_closed_ts": None}


def load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return {**default_state(), **json.loads(STATE_PATH.read_text(encoding="utf-8"))}
        except Exception:
            print("[worker] state file corrupted, starting fresh", flush=True)
    return default_state()


def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run() -> None:
    max_ticks = int(os.environ.get("WONYO_WORKER_MAX_TICKS", "0"))
    (ROOT / "data").mkdir(parents=True, exist_ok=True)  # state file + local SQLite ledger home
    db = WonyoDBManager(sqlite_path=str(ROOT / "data" / "worker_trades.db"))
    db.init_db()
    state = load_state()
    storage = "Postgres(Neon)" if db.use_postgres else "SQLite(local)"
    print(f"[worker] started | equity={state['equity_btc']:.4f} BTC | ledger={storage} "
          f"| open={'yes' if state['position'] else 'no'}", flush=True)

    ticks = 0
    while max_ticks == 0 or ticks < max_ticks:
        ticks += 1
        try:
            price = fetch_live_price()

            # 1. Manage the open position against the live price
            if state["position"]:
                exit_info = check_exit(state["position"], price, time.time())
                if exit_info:
                    trade = compute_trade(state["position"], exit_info["exit_price"], exit_info["reason"])
                    db.record_trade(trade)
                    state["equity_btc"] += trade["net_pnl_btc"]
                    state["peak_equity_btc"] = max(state["peak_equity_btc"], state["equity_btc"])
                    state["consecutive_losses"] = state["consecutive_losses"] + 1 if trade["net_pnl_btc"] < 0 else 0
                    state["position"] = None
                    print(f"[worker] CLOSED {trade['id']} {trade['side']} {trade['exit_reason']} "
                          f"{trade['pnl_pct']:+.2f}% ({trade['net_pnl_btc']:+.6f} BTC) "
                          f"| equity={state['equity_btc']:.4f} BTC", flush=True)

            # 2. Entry evaluation on each newly closed 15m candle
            df = fetch_live_binance_candles(interval="15m", limit=150)
            feats = extractor.compute_features(df)
            closed = feats.iloc[-2].to_dict()  # iloc[-1] is still forming
            if str(closed["timestamp"]) != state["last_closed_ts"]:
                state["last_closed_ts"] = str(closed["timestamp"])
                if state["position"] is None:
                    port = PortfolioState(
                        equity_btc=state["equity_btc"],
                        btc_price_usd=price,
                        peak_equity_btc=state["peak_equity_btc"],
                        current_position_contracts=0,
                        consecutive_losses=state["consecutive_losses"],
                    )
                    decision = model.decide(closed, port)
                    if decision["action"] in (ActionType.ENTER_LONG, ActionType.ENTER_SHORT):
                        state["position"] = open_position(decision, price, state["equity_btc"])
                        p = state["position"]
                        print(f"[worker] OPENED {p['id']} {p['side']} {p['leverage']}x "
                              f"@ {p['entry_price']:.1f} | SL {p['stop_loss']:.1f} TP {p['take_profit']:.1f} "
                              f"| reason={decision['reason']}", flush=True)

            save_state(state)
        except Exception as e:
            print(f"[worker] tick error: {e}", flush=True)
        time.sleep(TICK_SECONDS)

    print(f"[worker] stopped after {ticks} ticks (smoke mode)", flush=True)


if __name__ == "__main__":
    run()
