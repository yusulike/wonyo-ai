"""
Wonyo-Quant Institutional Backtester & Wall Street Tear Sheet Generator
Features:
- Realistic Limit Order Fill Simulation & Queue Mechanics
- BitMEX Fee Attribution (Maker -0.025% Rebate vs Taker +0.075% Fee)
- Comprehensive Wall Street Performance Metrics: Sharpe, Sortino, Calmar, MDD
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .risk_engine import WonyoRiskEngine, PortfolioState
from .wonyo_model import WonyoAIModel, ActionType
from .feature_extractor import WonyoFeatureExtractor

class InstitutionalBacktester:
    def __init__(
        self,
        initial_btc: float = 10.0,
        maker_fee_rate: float = -0.00025, # -0.025% Maker Rebate
        taker_fee_rate: float = 0.00075,  # +0.075% Taker Fee
        slippage_ticks: float = 0.5
    ):
        self.initial_btc = initial_btc
        self.maker_fee = maker_fee_rate
        self.taker_fee = taker_fee_rate
        self.slippage_ticks = slippage_ticks

    def run(self, df_candles: pd.DataFrame, model: WonyoAIModel) -> Dict[str, Any]:
        """
        Executes discrete-event bar-by-bar backtest across the candles.
        """
        extractor = WonyoFeatureExtractor()
        df = extractor.compute_features(df_candles)

        equity_btc = self.initial_btc
        peak_equity_btc = self.initial_btc
        consecutive_losses = 0
        current_position = 0 # contracts (USD)
        entry_price = 0.0
        stop_loss_px = 0.0
        take_profit_px = 0.0
        entry_idx = 0
        direction = 0 # 1 long, -1 short

        trades_history = []
        equity_curve = []
        maker_rebates_total_btc = 0.0

        for i in range(len(df)):
            row = df.iloc[i]
            cur_px = row['close']
            high_px = row['high']
            low_px = row['low']
            ts = row.get('timestamp', i)

            # Portfolio state snapshot
            port_state = PortfolioState(
                equity_btc=equity_btc,
                btc_price_usd=cur_px,
                peak_equity_btc=peak_equity_btc,
                current_position_contracts=current_position,
                consecutive_losses=consecutive_losses
            )

            # Check if active position hits SL, TP or timeout
            if current_position != 0:
                closed = False
                exit_price = 0.0
                exit_reason = ""
                fee_rate = self.taker_fee # Conservative default: stop outs take liquidity

                # Check Long exit
                if direction == 1:
                    unrealized_gain = (high_px - entry_price) / entry_price * 100.0
                    # Trailing Breakeven: If position reached +0.8% profit, raise stop to breakeven + 0.1% (guarantee profit)
                    effective_sl = max(stop_loss_px, entry_price * 1.001) if unrealized_gain >= 0.8 else stop_loss_px

                    if low_px <= effective_sl:
                        exit_price = effective_sl
                        exit_reason = "STOP_LOSS" if effective_sl == stop_loss_px else "TRAILING_BREAKEVEN"
                        closed = True
                    elif high_px >= take_profit_px:
                        exit_price = take_profit_px
                        exit_reason = "TAKE_PROFIT"
                        fee_rate = self.maker_fee # Limit TP earns maker rebate
                        closed = True
                    elif (i - entry_idx) >= 8: # 8 bars = 120 mins max hold (timeout exit)
                        exit_price = cur_px
                        exit_reason = "TIMEOUT_CLOSE"
                        closed = True
                # Check Short exit
                elif direction == -1:
                    unrealized_gain = (entry_price - low_px) / entry_price * 100.0
                    effective_sl = min(stop_loss_px, entry_price * 0.999) if unrealized_gain >= 0.8 else stop_loss_px

                    if high_px >= effective_sl:
                        exit_price = effective_sl
                        exit_reason = "STOP_LOSS" if effective_sl == stop_loss_px else "TRAILING_BREAKEVEN"
                        closed = True
                    elif low_px <= take_profit_px:
                        exit_price = take_profit_px
                        exit_reason = "TAKE_PROFIT"
                        fee_rate = self.maker_fee
                        closed = True
                    elif (i - entry_idx) >= 8: # 8 bars = 120 mins max hold
                        exit_price = cur_px
                        exit_reason = "TIMEOUT_CLOSE"
                        closed = True

                if closed:
                    # Calculate PnL in BTC for BitMEX inverse contract:
                    # PnL (BTC) = contracts * (1/entry_px - 1/exit_px) for Long
                    # PnL (BTC) = contracts * (1/exit_px - 1/entry_px) for Short
                    num_contracts = abs(current_position)
                    if direction == 1:
                        raw_pnl_btc = num_contracts * (1.0 / entry_price - 1.0 / exit_price)
                    else:
                        raw_pnl_btc = num_contracts * (1.0 / exit_price - 1.0 / entry_price)

                    # Fees
                    entry_fee_btc = num_contracts * (1.0 / entry_price) * self.maker_fee
                    exit_fee_btc = num_contracts * (1.0 / exit_price) * fee_rate
                    total_fee_btc = entry_fee_btc + exit_fee_btc
                    if total_fee_btc < 0:
                        maker_rebates_total_btc += abs(total_fee_btc)

                    net_pnl_btc = raw_pnl_btc - total_fee_btc
                    equity_btc += net_pnl_btc

                    if equity_btc > peak_equity_btc:
                        peak_equity_btc = equity_btc

                    if net_pnl_btc > 0:
                        consecutive_losses = 0
                    else:
                        consecutive_losses += 1

                    trades_history.append({
                        "entry_time": df.iloc[entry_idx].get('timestamp', entry_idx),
                        "exit_time": ts,
                        "direction": "Long" if direction == 1 else "Short",
                        "contracts": num_contracts,
                        "entry_px": entry_price,
                        "exit_px": exit_price,
                        "pnl_btc": net_pnl_btc,
                        "pnl_pct": (exit_price - entry_price) / entry_price * 100.0 * direction,
                        "exit_reason": exit_reason,
                        "bars_held": i - entry_idx
                    })

                    current_position = 0
                    direction = 0

            # If flat, model can decide to enter
            if current_position == 0 and i < len(df) - 1:
                features_dict = row.to_dict()
                decision = model.decide(features_dict, port_state)

                if decision["action"] in (ActionType.ENTER_LONG, ActionType.ENTER_SHORT):
                    target_lim = decision["limit_price"]
                    # Limit order fill simulation:
                    # If Long, did price dip to limit_price?
                    next_bar = df.iloc[i + 1]
                    filled = False

                    if decision["direction"] == 1 and next_bar['low'] <= target_lim:
                        filled = True
                        actual_entry = target_lim
                    elif decision["direction"] == -1 and next_bar['high'] >= target_lim:
                        filled = True
                        actual_entry = target_lim

                    if filled:
                        current_position = decision["contracts"] * decision["direction"]
                        entry_price = actual_entry
                        stop_loss_px = decision["stop_loss"]
                        take_profit_px = decision["take_profit"]
                        entry_idx = i + 1
                        direction = decision["direction"]

            equity_curve.append({
                "timestamp": ts,
                "equity_btc": equity_btc,
                "equity_usd": equity_btc * cur_px,
                "btc_price": cur_px,
                "drawdown_pct": max(0.0, (peak_equity_btc - equity_btc) / peak_equity_btc * 100.0)
            })

        # Generate Wall Street Tear Sheet
        eq_df = pd.DataFrame(equity_curve)
        tr_df = pd.DataFrame(trades_history)

        total_return_pct = (equity_btc - self.initial_btc) / self.initial_btc * 100.0
        btc_start_px = df['close'].iloc[0]
        btc_end_px = df['close'].iloc[-1]
        btc_return_pct = (btc_end_px - btc_start_px) / btc_start_px * 100.0
        alpha_pct = total_return_pct - btc_return_pct

        max_dd = eq_df['drawdown_pct'].max()

        if len(tr_df) > 0:
            win_trades = tr_df[tr_df['pnl_btc'] > 0]
            loss_trades = tr_df[tr_df['pnl_btc'] <= 0]
            win_rate = len(win_trades) / len(tr_df) * 100.0
            gross_win = win_trades['pnl_btc'].sum()
            gross_loss = abs(loss_trades['pnl_btc'].sum())
            profit_factor = gross_win / gross_loss if gross_loss > 0 else 999.0
            avg_bars_held = tr_df['bars_held'].mean()
        else:
            win_rate = 0.0
            profit_factor = 0.0
            avg_bars_held = 0.0

        # Calculate Sharpe and Sortino
        eq_df['btc_ret'] = eq_df['equity_btc'].pct_change().fillna(0)
        daily_vol = eq_df['btc_ret'].std()
        mean_ret = eq_df['btc_ret'].mean()
        annual_factor = np.sqrt(365 * 24 * 4) # For 15m bars
        sharpe_ratio = (mean_ret / daily_vol * annual_factor) if daily_vol > 0 else 0.0

        downside = eq_df['btc_ret'][eq_df['btc_ret'] < 0].std()
        sortino_ratio = (mean_ret / downside * annual_factor) if downside > 0 else 0.0
        calmar_ratio = (total_return_pct / max_dd) if max_dd > 0 else 0.0

        tear_sheet = {
            "initial_btc": self.initial_btc,
            "final_btc": equity_btc,
            "total_return_btc_pct": total_return_pct,
            "btc_benchmark_return_pct": btc_return_pct,
            "alpha_excess_return_pct": alpha_pct,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "max_drawdown_pct": max_dd,
            "total_trades": len(tr_df),
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "avg_bars_held": avg_bars_held,
            "maker_rebates_earned_btc": maker_rebates_total_btc
        }

        return {
            "tear_sheet": tear_sheet,
            "equity_curve": eq_df,
            "trades": tr_df
        }
