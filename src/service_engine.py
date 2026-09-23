"""
Wonyo-Quant Commercial Service Engine
Institutional Real-time Signal & Execution API Core
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.risk_engine import WonyoRiskEngine, PortfolioState
from src.wonyo_model import WonyoAIModel, ActionType
from src.feature_extractor import WonyoFeatureExtractor

@dataclass
class CommercialSignalResponse:
    timestamp: str
    action: str            # 'BUY', 'SELL', 'CLOSE', 'HOLD'
    order_type: str        # 'LIMIT_MAKER'
    symbol: str
    limit_price: float
    size_usd_contracts: float
    estimated_leverage: float
    stop_loss_price: float
    take_profit_price: float
    expected_holding_minutes: float
    signal_confidence: float
    risk_state: Dict[str, Any]
    status: str            # 'EXECUTABLE' or 'SAFE_MODE_BLOCKED'
    reason: str

class WonyoSignalService:
    """
    Production-grade Engine for Commercial Signal Services & Automated Execution.
    Maintains a rolling candle buffer, evaluates 4-tier risk tensors in real-time,
    and returns institutional-grade trading directives.
    """
    def __init__(
        self,
        symbol: str = "XBTUSD",
        buffer_size: int = 150,
        fractional_kelly: float = 0.35,
        max_leverage: float = 3.0
    ):
        self.symbol = symbol
        self.buffer_size = buffer_size
        self.risk_engine = WonyoRiskEngine(
            fractional_kelly=fractional_kelly,
            max_leverage_cap=max_leverage
        )
        self.model = WonyoAIModel(risk_engine=self.risk_engine)
        self.extractor = WonyoFeatureExtractor()
        self.candle_buffer: List[Dict[str, Any]] = []

    def push_candle(self, candle: Dict[str, Any]):
        """
        Pushes a new candle: {'timestamp': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}
        """
        self.candle_buffer.append(candle)
        if len(self.candle_buffer) > self.buffer_size:
            self.candle_buffer.pop(0)

    def evaluate_live(self, portfolio_dict: Dict[str, Any]) -> CommercialSignalResponse:
        """
        Evaluates current market state and portfolio health to generate a production signal.
        """
        if len(self.candle_buffer) < 30:
            return CommercialSignalResponse(
                timestamp=str(pd.Timestamp.now()),
                action="HOLD",
                order_type="NONE",
                symbol=self.symbol,
                limit_price=0.0,
                size_usd_contracts=0.0,
                estimated_leverage=0.0,
                stop_loss_price=0.0,
                take_profit_price=0.0,
                expected_holding_minutes=0.0,
                signal_confidence=0.0,
                risk_state={"buffer_status": f"{len(self.candle_buffer)}/30 candles"},
                status="WARMING_UP",
                reason="INSUFFICIENT_HISTORY_BUFFER"
            )

        df_candles = pd.DataFrame(self.candle_buffer)
        df_features = self.extractor.compute_features(df_candles)
        latest_row = df_features.iloc[-1].to_dict()

        port = PortfolioState(
            equity_btc=float(portfolio_dict.get("equity_btc", 1.0)),
            btc_price_usd=float(latest_row["close"]),
            peak_equity_btc=float(portfolio_dict.get("peak_equity_btc", portfolio_dict.get("equity_btc", 1.0))),
            current_position_contracts=float(portfolio_dict.get("current_position_contracts", 0.0)),
            consecutive_losses=int(portfolio_dict.get("consecutive_losses", 0))
        )

        decision = self.model.decide(latest_row, port)

        action_str = "HOLD"
        if decision["action"] == ActionType.ENTER_LONG:
            action_str = "BUY"
        elif decision["action"] == ActionType.ENTER_SHORT:
            action_str = "SELL"
        elif decision["action"] == ActionType.CLOSE_POSITION:
            action_str = "CLOSE"

        # Determine expected holding time based on Wonyotti's profile
        # Winners: 16.35 mins median, Losers: 88.46 mins
        expected_hold = 16.35 if action_str in ("BUY", "SELL") else 0.0

        is_executable = action_str in ("BUY", "SELL", "CLOSE")
        contracts = decision.get("contracts", 0.0)
        lev = (contracts / port.equity_usd) if port.equity_usd > 0 else 0.0

        risk_state = {
            "microstructure_risk": round(float(latest_row.get("microstructure_risk", 0.0)), 4),
            "regime_risk": round(float(latest_row.get("regime_risk", 0.0)), 4),
            "portfolio_drawdown_pct": round(port.drawdown_pct, 2),
            "consecutive_losses": port.consecutive_losses,
            "volume_zscore": round(float(latest_row.get("volume_zscore", 0.0)), 2),
            "bullish_absorption": round(float(latest_row.get("bullish_absorption", 0.0)), 2),
            "bearish_absorption": round(float(latest_row.get("bearish_absorption", 0.0)), 2)
        }

        return CommercialSignalResponse(
            timestamp=str(latest_row.get("timestamp", pd.Timestamp.now())),
            action=action_str,
            order_type="LIMIT_MAKER" if is_executable else "NONE",
            symbol=self.symbol,
            limit_price=float(decision.get("limit_price", latest_row["close"])),
            size_usd_contracts=round(contracts, 2),
            estimated_leverage=round(lev, 2),
            stop_loss_price=float(decision.get("stop_loss", 0.0)),
            take_profit_price=float(decision.get("take_profit", 0.0)),
            expected_holding_minutes=expected_hold,
            signal_confidence=round(float(decision.get("confidence", 0.0)), 3),
            risk_state=risk_state,
            status="EXECUTABLE" if is_executable else "SAFE_MODE_BLOCKED",
            reason=decision.get("reason", "NOMINAL")
        )
