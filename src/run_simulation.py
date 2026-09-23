"""
Project AOA - Wall Street Simulation & Quantitative Tear Sheet Runner
Evaluates Wonyo-AI on continuous BitMEX market data across 2021.
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.risk_engine import WonyoRiskEngine
from src.wonyo_model import WonyoAIModel
from src.backtester import InstitutionalBacktester

def main():
    print("=================================================================")
    print(" PROJECT AOA: WALL STREET INSTITUTIONAL QUANTITATIVE SIMULATION  ")
    print("=================================================================")

    # 1. Load continuous market dataset
    data_path = "src/bitmex_2021_1h.parquet"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Missing {data_path}")

    df_candles = pd.read_parquet(data_path)
    print(f"Loaded {len(df_candles):,} hourly candles ({df_candles['timestamp'].min()} to {df_candles['timestamp'].max()})")

    # 2. Configure Institutional Engines
    risk_engine = WonyoRiskEngine(
        base_win_rate=0.7779,
        base_payoff_ratio=0.75,
        fractional_kelly=0.35, # Conservative fractional Kelly
        max_leverage_cap=3.0,  # Strict institutional leverage cap
        min_stop_loss_pct=1.0,
        max_stop_loss_pct=2.5
    )

    model = WonyoAIModel(
        risk_engine=risk_engine,
        confidence_threshold=0.60,
        volume_exhaustion_threshold=2.0,
        absorption_threshold=1.2
    )

    backtester = InstitutionalBacktester(
        initial_btc=10.0,
        maker_fee_rate=-0.00025, # -0.025% Maker Rebate
        taker_fee_rate=0.00075   # +0.075% Taker Fee
    )

    print("\nRunning Institutional Execution Simulation with Risk Gating & Maker Rebates...")
    results = backtester.run(df_candles, model)

    ts = results["tear_sheet"]
    eq = results["equity_curve"]
    tr = results["trades"]

    print("\n=================================================================")
    print("                    WALL STREET TEAR SHEET                       ")
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
    print(f" Average Bars Held:             {ts['avg_bars_held']:.1f} hours")
    print(f" Total Maker Rebates Earned:    {ts['maker_rebates_earned_btc']:.6f} BTC")
    print("=================================================================")

    # Save Tear Sheet to JSON
    with open("src/wonyo_tear_sheet.json", "w") as f:
        json.dump(ts, f, indent=2)

    # Plot Equity Curve & Drawdown
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    ax1.plot(pd.to_datetime(eq['timestamp']), eq['equity_btc'], label='Wonyo-AI Equity (BTC)', color='#00ff88', linewidth=2)
    ax1.set_ylabel('Portfolio Equity (BTC)', fontsize=12, fontweight='bold')
    ax1.set_title('Wonyo-AI (Project AOA) Institutional Performance vs Benchmark (2021)', fontsize=14, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper left')

    # Drawdown plot
    ax2.fill_between(pd.to_datetime(eq['timestamp']), -eq['drawdown_pct'], 0, color='#ff3366', alpha=0.4, label='Drawdown (%)')
    ax2.set_ylabel('Drawdown (%)', fontsize=11)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower left')

    plt.tight_layout()
    chart_path = "src/wonyo_performance_chart.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()
    print(f"\nSaved institutional performance chart to {chart_path}")

    # Also save trades summary
    if len(tr) > 0:
        print("\nSample Trades:")
        print(tr.head(10)[["direction", "contracts", "entry_px", "exit_px", "pnl_btc", "pnl_pct", "exit_reason"]])
        tr.to_csv("src/simulated_trades.csv", index=False)

if __name__ == "__main__":
    main()
