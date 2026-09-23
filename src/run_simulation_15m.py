"""
Project AOA - Wall Street Simulation on High-Resolution (15-Minute) Market Data
Evaluates Wonyo-AI on 2021 Q2 (High Volatility Crash & Recovery Regime)
"""

import os
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt

from src.risk_engine import WonyoRiskEngine
from src.wonyo_model import WonyoAIModel
from src.backtester import InstitutionalBacktester

def main():
    print("=================================================================")
    print(" PROJECT AOA: HIGH-RESOLUTION (15m) INSTITUTIONAL SIMULATION    ")
    print("=================================================================")

    data_path = "src/bitmex_2021_q2_15m.parquet"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Missing {data_path}")

    df_candles = pd.read_parquet(data_path)
    print(f"Loaded {len(df_candles):,} 15m candles ({df_candles['timestamp'].min()} to {df_candles['timestamp'].max()})")

    # Configure Institutional Engines calibrated to Wonyotti's exact profile
    risk_engine = WonyoRiskEngine(
        base_win_rate=0.7779,
        base_payoff_ratio=0.75,
        fractional_kelly=0.35, # Conservative fractional Kelly
        max_leverage_cap=3.0,  # 3.0x institutional cap
        min_stop_loss_pct=1.0,
        max_stop_loss_pct=2.0
    )

    model = WonyoAIModel(
        risk_engine=risk_engine,
        confidence_threshold=0.60,
        volume_exhaustion_threshold=2.2,
        absorption_threshold=1.3
    )

    backtester = InstitutionalBacktester(
        initial_btc=10.0,
        maker_fee_rate=-0.00025, # -0.025% Maker Rebate
        taker_fee_rate=0.00075   # +0.075% Taker Fee
    )

    print("\nRunning Discrete-Event Simulation with Maker Rebates & Realistic Risk Inputs...")
    results = backtester.run(df_candles, model)

    ts = results["tear_sheet"]
    eq = results["equity_curve"]
    tr = results["trades"]

    print("\n=================================================================")
    print("             WALL STREET TEAR SHEET (2021 Q2 CRASH & RECOVERY)   ")
    print("=================================================================")
    print(f" Initial Capital (BTC):         {ts['initial_btc']:.4f} BTC")
    print(f" Final Capital (BTC):           {ts['final_btc']:.4f} BTC")
    print(f" Total Return (BTC):            {ts['total_return_btc_pct']:+.2f}%")
    print(f" Benchmark BTC Return (Hold):   {ts['btc_benchmark_return_pct']:+.2f}%")
    print(f" Alpha (Excess Return vs BTC):  {ts['alpha_excess_return_pct']:+.2f}%")
    print(f" Annualized Sharpe Ratio:       {ts['sharpe_ratio']:.2f}")
    print(f" Annualized Sortino Ratio:      {ts['sortino_ratio']:.2f}")
    print(f" Calmar Ratio:                  {ts['calmar_ratio']:.2f}")
    print(f" Maximum Drawdown (MDD):        {ts['max_drawdown_pct']:.2f}%")
    print(f" Total Executed Trades:         {ts['total_trades']:,}")
    print(f" Win Rate:                      {ts['win_rate_pct']:.2f}%")
    print(f" Profit Factor:                 {ts['profit_factor']:.2f}")
    print(f" Average Bars Held (15m bars):  {ts['avg_bars_held']:.1f} bars (~{ts['avg_bars_held']*15:.0f} mins)")
    print(f" Total Maker Rebates Earned:    {ts['maker_rebates_earned_btc']:.6f} BTC")
    print("=================================================================")

    # Save Tear Sheet to JSON
    with open("src/wonyo_tear_sheet_15m.json", "w") as f:
        json.dump(ts, f, indent=2)

    # Plot Equity Curve & Benchmark
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    ax1.plot(pd.to_datetime(eq['timestamp']), eq['equity_btc'], label='Wonyo-AI Equity (BTC)', color='#00ff88', linewidth=2)
    ax1.set_ylabel('Portfolio Equity (BTC)', fontsize=12, fontweight='bold')
    ax1.set_title('Wonyo-AI (Project AOA) Institutional 15m Simulation (Q2 2021)', fontsize=14, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper left')

    ax2.fill_between(pd.to_datetime(eq['timestamp']), -eq['drawdown_pct'], 0, color='#ff3366', alpha=0.4, label='Drawdown (%)')
    ax2.set_ylabel('Drawdown (%)', fontsize=11)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower left')

    plt.tight_layout()
    chart_path = "src/wonyo_performance_15m.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()
    print(f"\nSaved performance chart to {chart_path}")

    if len(tr) > 0:
        print("\nLast 5 Executed Trades:")
        print(tr.tail(5)[["direction", "contracts", "entry_px", "exit_px", "pnl_btc", "pnl_pct", "exit_reason", "bars_held"]])
        tr.to_csv("src/simulated_trades_15m.csv", index=False)

if __name__ == "__main__":
    main()
