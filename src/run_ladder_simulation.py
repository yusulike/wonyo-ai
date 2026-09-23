"""
Wonyo-Quant Multi-Leg Split Execution Backtester
Implements Wonyotti's exact laddered limit order entry:
- Leg 1: 40% at current touch
- Leg 2: 30% at -0.4% from touch (scaled dip)
- Leg 3: 30% at -0.8% from touch (deep exhaustion dip)
- Dynamic Take Profit & Breakeven Lock
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import json

from src.risk_engine import WonyoRiskEngine, PortfolioState
from src.wonyo_model import WonyoAIModel, ActionType
from src.feature_extractor import WonyoFeatureExtractor

def run_ladder_backtest(df_candles: pd.DataFrame):
    extractor = WonyoFeatureExtractor()
    df = extractor.compute_features(df_candles)

    risk_engine = WonyoRiskEngine(
        base_win_rate=0.7779,
        base_payoff_ratio=0.75,
        fractional_kelly=0.35,
        max_leverage_cap=2.5,
        min_stop_loss_pct=1.0,
        max_stop_loss_pct=2.0
    )
    model = WonyoAIModel(
        risk_engine=risk_engine,
        confidence_threshold=0.60
    )

    initial_btc = 10.0
    equity_btc = initial_btc
    peak_equity_btc = initial_btc
    consecutive_losses = 0

    maker_fee = -0.00025
    taker_fee = 0.00075

    # Position tracking
    in_position = False
    direction = 0 # +1 Long, -1 Short
    filled_legs = [] # list of (qty, price)
    stop_loss_px = 0.0
    take_profit_px = 0.0
    entry_bar_idx = 0
    active_orders = [] # pending ladder orders: (qty, limit_px)

    trades = []
    equity_curve = []
    maker_rebates_btc = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        cur_px = row['close']
        high_px = row['high']
        low_px = row['low']
        ts = row.get('timestamp', i)

        port = PortfolioState(
            equity_btc=equity_btc,
            btc_price_usd=cur_px,
            peak_equity_btc=peak_equity_btc,
            current_position_contracts=sum(q for q, p in filled_legs) * direction if in_position else 0,
            consecutive_losses=consecutive_losses
        )

        # 1. Manage Active Position
        if in_position:
            # Check if pending ladder legs filled in this bar
            remaining_orders = []
            for qty, lim_px in active_orders:
                leg_filled = False
                if direction == 1 and low_px <= lim_px:
                    leg_filled = True
                elif direction == -1 and high_px >= lim_px:
                    leg_filled = True

                if leg_filled:
                    filled_legs.append((qty, lim_px))
                    # Maker rebate on ladder fill
                    rebate = qty * (1.0 / lim_px) * abs(maker_fee)
                    maker_rebates_btc += rebate
                    equity_btc += rebate
                else:
                    remaining_orders.append((qty, lim_px))
            active_orders = remaining_orders

            # Compute weighted avg entry
            tot_qty = sum(q for q, p in filled_legs)
            avg_entry_px = sum(q * p for q, p in filled_legs) / tot_qty if tot_qty > 0 else cur_px

            # Dynamic SL / TP / Breakeven anchored to weighted average entry price
            closed = False
            exit_px = 0.0
            exit_reason = ""
            exit_fee = taker_fee
            atr = row.get("atr", cur_px * 0.01)

            if direction == 1:
                unrealized_gain = (high_px - avg_entry_px) / avg_entry_px * 100.0
                curr_sl = avg_entry_px - 1.45 * (atr / cur_px * 100.0 / 100.0 * avg_entry_px)
                effective_sl = max(curr_sl, avg_entry_px * 1.002) if unrealized_gain >= 0.75 else curr_sl

                # Scratch exit: If held > 4 bars (60m) and price recovers to within -0.4%, cut early instead of waiting for full stop
                bars_held = i - entry_bar_idx
                if bars_held >= 4 and cur_px > avg_entry_px * 0.996 and cur_px < avg_entry_px:
                    exit_px = cur_px
                    exit_reason = "SCRATCH_PULLBACK_EXIT"
                    closed = True
                elif low_px <= effective_sl:
                    exit_px = effective_sl
                    exit_reason = "STOP_LOSS" if effective_sl == curr_sl else "TRAILING_BREAKEVEN"
                    closed = True
                elif high_px >= take_profit_px:
                    exit_px = take_profit_px
                    exit_reason = "TAKE_PROFIT"
                    exit_fee = maker_fee
                    closed = True
                elif bars_held >= 10:
                    exit_px = cur_px
                    exit_reason = "TIMEOUT_CLOSE"
                    closed = True

            elif direction == -1:
                unrealized_gain = (avg_entry_px - low_px) / avg_entry_px * 100.0
                curr_sl = avg_entry_px + 1.45 * (atr / cur_px * 100.0 / 100.0 * avg_entry_px)
                effective_sl = min(curr_sl, avg_entry_px * 0.998) if unrealized_gain >= 0.75 else curr_sl

                bars_held = i - entry_bar_idx
                if bars_held >= 4 and cur_px < avg_entry_px * 1.004 and cur_px > avg_entry_px:
                    exit_px = cur_px
                    exit_reason = "SCRATCH_PULLBACK_EXIT"
                    closed = True
                elif high_px >= effective_sl:
                    exit_px = effective_sl
                    exit_reason = "STOP_LOSS" if effective_sl == curr_sl else "TRAILING_BREAKEVEN"
                    closed = True
                elif low_px <= take_profit_px:
                    exit_px = take_profit_px
                    exit_reason = "TAKE_PROFIT"
                    exit_fee = maker_fee
                    closed = True
                elif bars_held >= 10:
                    exit_px = cur_px
                    exit_reason = "TIMEOUT_CLOSE"
                    closed = True

            if closed:
                # Calculate PnL across all filled legs
                total_pnl_btc = 0.0
                for q, p in filled_legs:
                    if direction == 1:
                        pnl = q * (1.0 / p - 1.0 / exit_px)
                    else:
                        pnl = q * (1.0 / exit_px - 1.0 / p)
                    total_pnl_btc += pnl

                # Exit fee
                exit_cost_btc = tot_qty * (1.0 / exit_px) * exit_fee
                if exit_cost_btc < 0:
                    maker_rebates_btc += abs(exit_cost_btc)
                net_pnl = total_pnl_btc - exit_cost_btc
                equity_btc += net_pnl

                if equity_btc > peak_equity_btc:
                    peak_equity_btc = equity_btc

                if net_pnl > 0:
                    consecutive_losses = 0
                else:
                    consecutive_losses += 1

                trades.append({
                    "entry_time": df.iloc[entry_bar_idx].get('timestamp', entry_bar_idx),
                    "exit_time": ts,
                    "direction": "Long" if direction == 1 else "Short",
                    "tot_contracts": tot_qty,
                    "avg_entry_px": avg_entry_px,
                    "exit_px": exit_px,
                    "pnl_btc": net_pnl,
                    "pnl_pct": (exit_px - avg_entry_px) / avg_entry_px * 100.0 * direction,
                    "exit_reason": exit_reason,
                    "legs_filled": len(filled_legs),
                    "bars_held": i - entry_bar_idx
                })

                in_position = False
                direction = 0
                filled_legs = []
                active_orders = []

        # 2. Check for New Entry
        if not in_position and i < len(df) - 1:
            feat_dict = row.to_dict()
            dec = model.decide(feat_dict, port)

            if dec["action"] in (ActionType.ENTER_LONG, ActionType.ENTER_SHORT):
                total_contracts = dec["contracts"]
                dir_sign = dec["direction"]
                base_px = dec["limit_price"]
                atr = row.get("atr", base_px * 0.01)

                # Check if Leg 1 (Touch) fills next bar
                next_bar = df.iloc[i + 1]
                leg1_fill = False
                if dir_sign == 1 and next_bar['low'] <= base_px:
                    leg1_fill = True
                elif dir_sign == -1 and next_bar['high'] >= base_px:
                    leg1_fill = True

                if leg1_fill:
                    in_position = True
                    direction = dir_sign
                    entry_bar_idx = i + 1

                    # Leg 1: 40%
                    q1 = total_contracts * 0.40
                    filled_legs = [(q1, base_px)]
                    rebate1 = q1 * (1.0 / base_px) * abs(maker_fee)
                    maker_rebates_btc += rebate1
                    equity_btc += rebate1

                    # Prepare Ladder Legs 2 & 3
                    # Leg 2: 30% at 0.5 * ATR dip
                    # Leg 3: 30% at 1.0 * ATR dip
                    q2 = total_contracts * 0.30
                    q3 = total_contracts * 0.30
                    if dir_sign == 1:
                        lim2 = base_px - 0.5 * atr
                        lim3 = base_px - 1.0 * atr
                        stop_loss_px = base_px - 1.5 * atr
                        take_profit_px = base_px + 1.2 * atr
                    else:
                        lim2 = base_px + 0.5 * atr
                        lim3 = base_px + 1.0 * atr
                        stop_loss_px = base_px + 1.5 * atr
                        take_profit_px = base_px - 1.2 * atr

                    active_orders = [(q2, lim2), (q3, lim3)]

        equity_curve.append({
            "timestamp": ts,
            "equity_btc": equity_btc,
            "equity_usd": equity_btc * cur_px,
            "drawdown_pct": max(0.0, (peak_equity_btc - equity_btc) / peak_equity_btc * 100.0)
        })

    tr_df = pd.DataFrame(trades)
    eq_df = pd.DataFrame(equity_curve)

    print("\n=================================================================")
    print("        WONYOTTI MULTI-LEG LADDER SIMULATION RESULTS (Q2 2021)   ")
    print("=================================================================")
    tot_ret = (equity_btc - initial_btc) / initial_btc * 100.0
    print(f" Initial Equity:        {initial_btc:.4f} BTC")
    print(f" Final Equity:          {equity_btc:.4f} BTC")
    print(f" Total Net Return:      {tot_ret:+.2f}%")
    print(f" Max Drawdown:          {eq_df['drawdown_pct'].max():.2f}%")
    print(f" Total Trades:          {len(tr_df):,}")
    if len(tr_df) > 0:
        win_trades = tr_df[tr_df['pnl_btc'] > 0]
        win_rate = len(win_trades) / len(tr_df) * 100.0
        gross_profit = win_trades['pnl_btc'].sum()
        gross_loss = abs(tr_df[tr_df['pnl_btc'] <= 0]['pnl_btc'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
        print(f" Win Rate:              {win_rate:.2f}%")
        print(f" Profit Factor:         {pf:.2f}")
        print(f" Avg Bars Held:         {tr_df['bars_held'].mean():.1f} bars (~{tr_df['bars_held'].mean()*15:.0f} mins)")
        print(f" Avg Legs Filled:       {tr_df['legs_filled'].mean():.2f} / 3.0")
        print(f" Maker Rebates Earned:  {maker_rebates_btc:.6f} BTC")
        print("\nExit Reasons Breakdown:")
        print(tr_df['exit_reason'].value_counts())
    print("=================================================================")

    tr_df.to_csv("src/ladder_trades.csv", index=False)
    eq_df.to_csv("src/ladder_equity.csv", index=False)

if __name__ == "__main__":
    df = pd.read_parquet("src/bitmex_2021_q2_15m.parquet")
    run_ladder_backtest(df)
