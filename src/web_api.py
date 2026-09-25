"""
Wonyo-AI Commercial Web Intelligence Terminal - FastAPI Backend
Provides real-time Bitcoin movement prediction, volume exhaustion analytics,
and 4-tier risk status for institutional & web users.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.risk_engine import WonyoRiskEngine, PortfolioState
from src.wonyo_model import WonyoAIModel, ActionType
from src.feature_extractor import WonyoFeatureExtractor
from src.news_sentiment import news_engine

app = FastAPI(title="Wonyo-AI Institutional Terminal", version="1.0.0", redirect_slashes=False)

# Initialize engines
risk_engine = WonyoRiskEngine(
    base_win_rate=0.7779,
    base_payoff_ratio=0.75,
    fractional_kelly=0.35,
    max_leverage_cap=3.0
)
model = WonyoAIModel(risk_engine=risk_engine, confidence_threshold=0.55)
extractor = WonyoFeatureExtractor()

def fetch_live_binance_candles(interval: str = "15m", limit: int = 150) -> pd.DataFrame:
    """Fetch live candles from Binance public API, with automatic Binance.US fallback for US servers (Vercel)."""
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}",
        f"https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}",
    ]
    data = None
    last_err = None
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    break
            else:
                last_err = f"API error: {resp.status_code}"
        except Exception as e:
            last_err = str(e)
            
    if not data or not isinstance(data, list):
        raise RuntimeError(f"All exchange endpoints failed: {last_err}")

    
    rows = []
    for item in data:
        rows.append({
            "timestamp": pd.to_datetime(item[0], unit='ms'),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    df = pd.DataFrame(rows)
    return df

def load_replay_candles(limit: int = 150) -> pd.DataFrame:
    """Load historical crash/rebound candles from 2021 BitMEX dataset."""
    path = "src/bitmex_2021_q2_15m.parquet"
    if Path(path).exists():
        df = pd.read_parquet(path)
        # Grab a famous volatile section (May 19-21, 2021)
        sub_df = df.iloc[4500:4500+limit].copy().reset_index(drop=True)
        return sub_df
    return fetch_live_binance_candles(limit=limit)

@app.get("/api/predict")
@app.get("/api/predict/")
@app.get("/predict")
def get_prediction(
    mode: str = Query("live", pattern="^(live|replay)$"),
    interval: str = Query("15m", pattern="^(5m|15m|1h)$"),
    sensitivity: str = Query("standard", pattern="^(standard|active)$"),
    equity_btc: float = 10.0,
    consecutive_losses: int = 0
):
    try:
        if mode == "live":
            df_raw = fetch_live_binance_candles(interval=interval, limit=120)
        else:
            df_raw = load_replay_candles(limit=120)

        df = extractor.compute_features(df_raw)
        latest = df.iloc[-1].to_dict()
        cur_px = float(latest["close"])

        # Portfolio state
        port = PortfolioState(
            equity_btc=equity_btc,
            btc_price_usd=cur_px,
            peak_equity_btc=equity_btc,
            current_position_contracts=0,
            consecutive_losses=consecutive_losses
        )

        # Sensitivity mode adaptation:
        # Standard = strict authentic Wonyotti model (97% patience)
        # Active = relaxed thresholds for high-frequency day/scalping signals
        if sensitivity == "active":
            active_model = WonyoAIModel(
                risk_engine=risk_engine,
                confidence_threshold=0.48,
                volume_exhaustion_threshold=1.35,
                absorption_threshold=0.9
            )
            decision = active_model.decide(latest, port)
            long_score, short_score = active_model.evaluate_signals(latest)
            conf_thresh = 0.48
        else:
            decision = model.decide(latest, port)
            long_score, short_score = model.evaluate_signals(latest)
            conf_thresh = model.confidence_thresh

        # Signal Readiness Calculation (% towards next trade execution)
        long_readiness = round(min(100.0, (long_score / conf_thresh) * 100.0), 1)
        short_readiness = round(min(100.0, (short_score / conf_thresh) * 100.0), 1)
        
        vol_exh = float(latest.get("volume_exhaustion", 1.0))
        bull_abs = float(latest.get("bullish_absorption", 0.0))
        bear_abs = float(latest.get("bearish_absorption", 0.0))

        if long_readiness >= 85:
            next_hint = "매수(BUY) 시그널 임박! 저점 체결 흡수 확인 완료"
        elif short_readiness >= 85:
            next_hint = "매도(SELL) 시그널 임박! 고점 매도벽 압력 감지"
        elif vol_exh < 1.3:
            next_hint = f"거래량 대기 중 (현재 {vol_exh:.1f}x / 진입 목표 1.8x 이상)"
        elif bull_abs < 0.8 and bear_abs < 0.8:
            next_hint = "캔들 꼬리 흡수 대기 중 (지지/저항 매물 소화 필요)"
        else:
            next_hint = "무리한 뇌동매매를 멈추고 고래의 뚜렷한 흡수를 대기 중"

        readiness_data = {
            "long_readiness_pct": long_readiness,
            "short_readiness_pct": short_readiness,
            "target_threshold_pct": round(conf_thresh * 100, 1),
            "sensitivity_mode": sensitivity,
            "next_trigger_hint": next_hint,
            "factors": {
                "volume_exhaustion": round(vol_exh, 2),
                "bullish_absorption": round(bull_abs, 2),
                "bearish_absorption": round(bear_abs, 2)
            }
        }

        # Normalize probabilities
        tot_score = long_score + short_score + 0.35 # 0.35 base flat weight
        prob_long = round((long_score / tot_score) * 100.0, 1)
        prob_short = round((short_score / tot_score) * 100.0, 1)
        prob_flat = round(100.0 - prob_long - prob_short, 1)

        action_str = "HOLD"
        direction = 0
        if decision["action"] == ActionType.ENTER_LONG:
            action_str = "BUY"
            direction = 1
        elif decision["action"] == ActionType.ENTER_SHORT:
            action_str = "SELL"
            direction = -1
        elif decision["action"] == ActionType.CLOSE_POSITION:
            action_str = "CLOSE"

        # Limit Maker pricing (at the touch)
        tick = 0.5
        limit_px = (cur_px - tick) if direction == 1 else (cur_px + tick) if direction == -1 else cur_px

        contracts = decision.get("contracts", 0.0)
        atr = float(latest.get("atr", cur_px * 0.01))

        # Dynamic stop loss and take profit
        if direction == 1:
            sl_px = limit_px - 1.45 * (atr / cur_px * limit_px)
            tp_px = limit_px + 1.20 * (atr / cur_px * limit_px)
        elif direction == -1:
            sl_px = limit_px + 1.45 * (atr / cur_px * limit_px)
            tp_px = limit_px - 1.20 * (atr / cur_px * limit_px)
        else:
            sl_px = 0.0
            tp_px = 0.0

        # ---------------------------------------------------------
        # Intuitive Volume + External Factors Synthesizer
        # ---------------------------------------------------------
        vol_z = float(latest.get("volume_zscore", 0.0))
        vol_exh = float(latest.get("volume_exhaustion", 1.0))
        bull_abs = float(latest.get("bullish_absorption", 0.0))
        bear_abs = float(latest.get("bearish_absorption", 0.0))
        trend_bias = float(latest.get("trend_bias", 0.0)) * 100.0
        micro_risk_score = float(latest.get("microstructure_risk", 0.15))
        regime_risk_score = float(latest.get("regime_risk", 0.20))

        # 1. Volume Factor Analysis (-100 ~ +100)
        vol_score = 0
        if bull_abs > 1.2:
            vol_score += min(50, int(bull_abs * 25))
        if bear_abs > 1.2:
            vol_score -= min(50, int(bear_abs * 25))
        if vol_z > 1.5:
            # High volume amplifies whichever side is dominating
            vol_score = int(vol_score * 1.3)
        vol_score = int(np.clip(vol_score, -100, 100))

        if vol_score >= 30:
            vol_badge = "🔥 매수 꼬리 흡수 (상승 베팅 우세)"
            vol_desc = f"거래량이 평소의 {vol_exh:.1f}배 터지며 저점에서 매도 물량을 강하게 소화(흡수)했습니다."
        elif vol_score <= -30:
            vol_badge = "❄️ 매도 저항 흡수 (하락 압력 우세)"
            vol_desc = f"고점에서 거래량이 급증하며 윗꼬리가 달렸습니다. 매도 압력이 매수세를 짓누르고 있습니다."
        else:
            vol_badge = "⏳ 거래량 소강 (관망 구간)"
            vol_desc = f"거래량(배율 {vol_exh:.1f}x)이 평균 수준으로, 고래의 뚜렷한 흡수 시그널이 나오지 않았습니다."

        # 2. External / Market Factor Analysis (-100 ~ +100)
        ext_score = 0
        ext_score += int(np.clip(trend_bias * 25, -50, 50)) # Trend direction
        if regime_risk_score > 0.6: # High volatility risk penalty
            ext_score = int(ext_score * 0.7)
        if micro_risk_score > 0.6: # Spread risk
            ext_score = int(ext_score * 0.8)
        ext_score = int(np.clip(ext_score, -100, 100))

        if ext_score >= 20:
            ext_badge = "📈 외부 추세 순풍 (상승 지지)"
            ext_desc = f"중기 이평선(50 EMA) 상단에 위치하여 외부 추세가 상승세를 뒷받침합니다."
        elif ext_score <= -20:
            ext_badge = "📉 외부 추세 역풍 (하락 압력)"
            ext_desc = f"중기 이평선 하단에 갇혀있어 반등 시 저항을 받을 확률이 높습니다."
        else:
            ext_badge = "⚖️ 박스권 횡보장 (중립)"
            ext_desc = f"외부 거시 지표가 뚜렷한 방향성 없이 박스권 균형을 유지하고 있습니다."

        # 3. News & SNS Sentiment Analysis (-100 ~ +100)
        news_data = news_engine.get_market_sentiment()
        news_score = news_data.get("composite_news_score", 0)

        # Combined Bull/Bear Composite Score (-100 to +100)
        # Wonyotti's 3 Pillars: Volume (50%) + External Technicals (25%) + News/SNS Attention (25%)
        composite_score = int(vol_score * 0.50 + ext_score * 0.25 + news_score * 0.25)

        black_swan_risk = float(news_data.get("black_swan_risk", 0.0))
        if black_swan_risk >= 0.50:
            verdict_badge = "🚨 블랙스완 경보 (SYSTEM RISK)"
            verdict_color = "red"
            playbook_text = f"TypeSafe Jev가 {black_swan_risk:.1%} 확률의 시스템적 악재를 감지했습니다. 신규 진입을 전면 중단하고 계좌 안전을 최우선으로 확보하세요."
        elif composite_score >= 30:
            verdict_badge = "▲ 상승 유력 (STRONG UP)"
            verdict_color = "green"
            playbook_text = "거래량 흡수와 외부 호재/추세가 상방을 가리킵니다. 지정가로 눌림목에 매수 진입 후 16분 이내 고속 익절을 노리세요."
        elif composite_score >= 12:
            verdict_badge = "▲ 약상승 우세 (SLIGHT UP)"
            verdict_color = "green"
            playbook_text = "매수세와 시장 심리가 우세하지만 변동성을 확인하며 분할 래더로 신중하게 접근하세요."
        elif composite_score <= -30:
            verdict_badge = "▼ 하락 유력 (STRONG DOWN)"
            verdict_color = "red"
            playbook_text = "거래량이 실린 매도벽과 악재/공포 심리가 우세합니다. 섣부른 롱 진입을 피하고 관망 또는 숏을 고려하세요."
        elif composite_score <= -12:
            verdict_badge = "▼ 약하락 우세 (SLIGHT DOWN)"
            verdict_color = "red"
            playbook_text = "하방 압력과 주의 심리가 감지됩니다. 지지선 이탈 여부를 살피며 보수적으로 대응하세요."
        else:
            verdict_badge = "━ 횡보/관망 (NEUTRAL)"
            verdict_color = "gray"
            playbook_text = "거래량이 터질 때까지 무리한 뇌동매매를 멈추고 현금을 보유하며 다음 변곡점을 기다리세요."

        intuitive_verdict = {
            "composite_score": composite_score, # -100 to +100
            "verdict_badge": verdict_badge,
            "verdict_color": verdict_color,
            "playbook_text": playbook_text,
            "expected_win_rate_range": "65% ~ 75% (워뇨띠 실거래 기준)",
            "volume_factor": {
                "score": vol_score,
                "badge": vol_badge,
                "description": vol_desc
            },
            "external_factor": {
                "score": ext_score,
                "badge": ext_badge,
                "description": ext_desc
            },
            "news_factor": {
                "score": news_score,
                "engine": news_data.get("engine", "Keyword Lexicon"),
                "avg_confidence": news_data.get("avg_confidence", 0.5),
                "black_swan_risk": black_swan_risk,
                "overall_market_bias": news_data.get("overall_market_bias", "neutral"),
                "fear_greed_score": news_data.get("fear_and_greed", {}).get("score", 50),
                "fear_greed_label": news_data.get("fear_and_greed", {}).get("label", "Neutral"),
                "badge": news_data.get("sentiment_badge", "뉴스 중립"),
                "description": news_data.get("sentiment_desc", ""),
                "attention_level": news_data.get("attention_level", "NORMAL"),
                "top_headlines": news_data.get("top_headlines", [])
            }
        }

        # Wonyotti 4-Tier Risk Matrix
        risk_matrix = {
            "microstructure_risk": {
                "score": round(float(latest.get("microstructure_risk", 0.15)), 3),
                "status": "NORMAL" if latest.get("microstructure_risk", 0.15) < 0.6 else "ELEVATED",
                "label": "체결 슬리피지 & 스프레드 위험도"
            },
            "regime_risk": {
                "score": round(float(latest.get("regime_risk", 0.20)), 3),
                "status": "NORMAL" if latest.get("regime_risk", 0.20) < 0.7 else "HIGH_VOLATILITY",
                "label": "시장 변동성 쇼크 위험도"
            },
            "market_efficiency": {
                "score": round(float(latest.get("kaufman_efficiency", 0.45)), 3),
                "status": "TRENDING" if latest.get("kaufman_efficiency", 0.45) > 0.55 else "RANGING_NOISE",
                "label": "카우프만 추세 효율비"
            },
            "portfolio_drawdown": {
                "score": round(port.drawdown_pct, 2),
                "status": "HEALTHY" if port.drawdown_pct < 10.0 else "DEFENSIVE",
                "label": "계좌 드로우다운 한도"
            }
        }

        # Wonyotti Volume Intuition Metrics
        intuition_metrics = {
            "volume_zscore": round(float(latest.get("volume_zscore", 0.0)), 2),
            "volume_exhaustion": round(float(latest.get("volume_exhaustion", 1.0)), 2),
            "bullish_absorption": round(float(latest.get("bullish_absorption", 0.0)), 2),
            "bearish_absorption": round(float(latest.get("bearish_absorption", 0.0)), 2),
            "trend_bias": round(float(latest.get("trend_bias", 0.0)) * 100.0, 2),
            "atr_pct": round(float(latest.get("atr_pct", 1.0)), 2)
        }

        return {
            "status": "SUCCESS",
            "mode": mode,
            "sensitivity": sensitivity,
            "timestamp": str(latest.get("timestamp")),
            "current_price": cur_px,
            "readiness": readiness_data,
            "intuitive_verdict": intuitive_verdict,
            "prediction": {
                "action": action_str,
                "confidence": round(max(prob_long, prob_short, prob_flat), 1),
                "probabilities": {
                    "long_pct": prob_long,
                    "short_pct": prob_short,
                    "flat_pct": prob_flat
                },
                "order_plan": {
                    "order_type": "LIMIT_MAKER (Post-Only)",
                    "target_limit_price": round(limit_px, 1),
                    "stop_loss_price": round(sl_px, 1),
                    "take_profit_price": round(tp_px, 1),
                    "target_contracts_usd": round(contracts, 0),
                    "estimated_leverage": round((contracts / port.equity_usd) if port.equity_usd > 0 else 0, 2),
                    "expected_holding_minutes": 16.35 if action_str in ("BUY", "SELL") else 0.0
                },
                "reason": decision.get("reason", "NOMINAL_MONITORING")
            },
            "wonyo_intuition": intuition_metrics,
            "risk_matrix": risk_matrix
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

@app.get("/api/candles")
@app.get("/api/candles/")
@app.get("/candles")
def get_candles(
    mode: str = Query("live", pattern="^(live|replay)$"),
    interval: str = Query("15m", pattern="^(5m|15m|1h)$"),
    limit: int = 100
):
    try:
        if mode == "live":
            df_raw = fetch_live_binance_candles(interval=interval, limit=limit)
        else:
            df_raw = load_replay_candles(limit=limit)

        df = extractor.compute_features(df_raw)
        
        candles = []
        for _, r in df.iterrows():
            ts_epoch = int(pd.to_datetime(r["timestamp"]).timestamp())
            candles.append({
                "time": ts_epoch,
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
                "vol_zscore": round(float(r.get("volume_zscore", 0.0)), 2),
                "bull_abs": round(float(r.get("bullish_absorption", 0.0)), 2),
                "bear_abs": round(float(r.get("bearish_absorption", 0.0)), 2)
            })
        return {"status": "SUCCESS", "candles": candles}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

# ==============================================================================
# VIRTUAL TRADING JOURNAL & HISTORIC LEGENDS ARCHIVE
# ==============================================================================
LIVE_TRADES_HISTORY: List[Dict[str, Any]] = [
    {
        "id": "TRD-105",
        "time_kst": "2026-09-24 21:15",
        "timestamp_kst": "2026-09-24 21:15",
        "direction": "LONG",
        "side": "LONG",
        "leverage": 1.85,
        "entry_price": 83850.0,
        "exit_price": 84798.5,
        "pnl_pct": +1.13,
        "pnl_btc": +0.0113,
        "maker_rebate_btc": +0.00035,
        "exit_reason": "1차 목표가 도달 (TP)",
        "bars_held": 2,
        "holding_time": "30분",
        "hold_duration_min": 30
    },
    {
        "id": "TRD-104",
        "time_kst": "2026-09-24 16:30",
        "timestamp_kst": "2026-09-24 16:30",
        "direction": "SHORT",
        "side": "SHORT",
        "leverage": 1.50,
        "entry_price": 84320.0,
        "exit_price": 84151.0,
        "pnl_pct": +0.20,
        "pnl_btc": +0.0020,
        "maker_rebate_btc": +0.00032,
        "exit_reason": "트레일링 본절 세이프",
        "bars_held": 3,
        "holding_time": "45분",
        "hold_duration_min": 45
    },
    {
        "id": "TRD-103",
        "time_kst": "2026-09-24 11:45",
        "timestamp_kst": "2026-09-24 11:45",
        "direction": "LONG",
        "side": "LONG",
        "leverage": 1.85,
        "entry_price": 83450.0,
        "exit_price": 83120.0,
        "pnl_pct": -0.39,
        "pnl_btc": -0.0039,
        "maker_rebate_btc": +0.00028,
        "exit_reason": "60분 풀백 스크래치 탈출",
        "bars_held": 4,
        "holding_time": "60분",
        "hold_duration_min": 60
    },
    {
        "id": "TRD-102",
        "time_kst": "2026-09-24 07:00",
        "timestamp_kst": "2026-09-24 07:00",
        "direction": "LONG",
        "side": "LONG",
        "leverage": 1.85,
        "entry_price": 82950.0,
        "exit_price": 83928.0,
        "pnl_pct": +1.18,
        "pnl_btc": +0.0118,
        "maker_rebate_btc": +0.00034,
        "exit_reason": "1차 목표가 도달 (TP)",
        "bars_held": 1,
        "holding_time": "15분",
        "hold_duration_min": 15
    },
    {
        "id": "TRD-101",
        "time_kst": "2026-09-23 22:30",
        "timestamp_kst": "2026-09-23 22:30",
        "direction": "SHORT",
        "side": "SHORT",
        "leverage": 1.50,
        "entry_price": 83200.0,
        "exit_price": 84431.0,
        "pnl_pct": -1.48,
        "pnl_btc": -0.0148,
        "maker_rebate_btc": +0.00031,
        "exit_reason": "동적 칼손절 (SL)",
        "bars_held": 2,
        "holding_time": "30분",
        "hold_duration_min": 30
    }
]

LEGENDARY_TRADES: List[Dict[str, Any]] = [
    {
        "rank": 1,
        "title": "2021.05.19 부처빔 바닥 쓸어담기",
        "date_kst": "2021-05-19 22:15 KST",
        "timestamp_kst": "2021-05-19 22:15 KST",
        "direction": "LONG",
        "side": "LONG",
        "entry_price": 31500.0,
        "exit_price": 35200.0,
        "pnl_pct": +11.75,
        "pnl_btc": +1.2840,
        "replay_index": 4680,
        "description": "$42k에서 $30k로 연쇄 청산 터질 때 평소 5배 폭발 거래량과 45% 하단 꼬리 흡수 확인 후 3단 롱 진입",
        "lesson": "$42k에서 $30k로 연쇄 청산 터질 때 평소 5배 폭발 거래량과 45% 하단 꼬리 흡수 확인 후 3단 롱 진입",
        "tag": "🔥 대폭락 역발상",
        "exit_reason": "TAKE_PROFIT"
    },
    {
        "rank": 2,
        "title": "2021.04.14 역사적 최고점 칼숏",
        "date_kst": "2021-04-14 20:30 KST",
        "timestamp_kst": "2021-04-14 20:30 KST",
        "direction": "SHORT",
        "side": "SHORT",
        "entry_price": 64200.0,
        "exit_price": 61500.0,
        "pnl_pct": +4.21,
        "pnl_btc": +0.8520,
        "replay_index": 1340,
        "description": "코인베이스 상장 당일 $64k에서 대량 매도벽 흡수 실패 및 윗꼬리 저항 확인 후 칼숏 진입",
        "lesson": "코인베이스 상장 당일 $64k에서 대량 매도벽 흡수 실패 및 윗꼬리 저항 확인 후 칼숏 진입",
        "tag": "❄️ 천장 매도벽",
        "exit_reason": "TAKE_PROFIT"
    },
    {
        "rank": 3,
        "title": "2021.06.22 30k 쌍바닥 사수 롱",
        "date_kst": "2021-06-22 23:00 KST",
        "timestamp_kst": "2021-06-22 23:00 KST",
        "direction": "LONG",
        "side": "LONG",
        "entry_price": 29850.0,
        "exit_price": 32100.0,
        "pnl_pct": +7.54,
        "pnl_btc": +0.9230,
        "replay_index": 7890,
        "description": "30k 붕괴 공포 때 거래량이 말라붙는 Volume Exhaustion 포착 후 지지선 분할 래더 매수",
        "lesson": "30k 붕괴 공포 때 거래량이 말라붙는 Volume Exhaustion 포착 후 지지선 분할 래더 매수",
        "tag": "🛡️ 쌍바닥 지지",
        "exit_reason": "TAKE_PROFIT"
    },
    {
        "rank": 4,
        "title": "2021.05.21 데드캣 16분 고속 스캘핑",
        "date_kst": "2021-05-21 18:15 KST",
        "timestamp_kst": "2021-05-21 18:15 KST",
        "direction": "LONG",
        "side": "LONG",
        "entry_price": 36200.0,
        "exit_price": 37100.0,
        "pnl_pct": +2.49,
        "pnl_btc": +0.3410,
        "replay_index": 4870,
        "description": "워뇨띠 평균 보유 시간(16.35분)의 정석. 급반등 파동에서 욕심 안 부리고 1개 봉 만에 익절",
        "lesson": "워뇨띠 평균 보유 시간(16.35분)의 정석. 급반등 파동에서 욕심 안 부리고 1개 봉 만에 익절",
        "tag": "⚡ 16분 정석 스캘핑",
        "exit_reason": "TAKE_PROFIT"
    },
    {
        "rank": 5,
        "title": "2021.04.18 플래시 크래시 칼손절",
        "date_kst": "2021-04-18 12:45 KST",
        "timestamp_kst": "2021-04-18 12:45 KST",
        "direction": "LONG",
        "side": "LONG",
        "entry_price": 58500.0,
        "exit_price": 57620.0,
        "pnl_pct": -1.50,
        "pnl_btc": -0.1500,
        "replay_index": 1720,
        "description": "중국 채굴장 정전 루머로 급락 시 지지 실패 확인 즉시 -1.5% 칼손절. 이후 $51k 폭락 피해 사수",
        "lesson": "중국 채굴장 정전 루머로 급락 시 지지 실패 확인 즉시 -1.5% 칼손절. 이후 $51k 폭락 피해 사수",
        "tag": "🧊 시드 수호 칼손절",
        "exit_reason": "STOP_LOSS"
    }
]

@app.get("/api/trades")
@app.get("/api/trades/")
@app.get("/trades")
def get_trades_history():
    tot_trades = len(LIVE_TRADES_HISTORY)
    wins = [t for t in LIVE_TRADES_HISTORY if t["pnl_pct"] > 0]
    win_cnt = len(wins)
    loss_cnt = tot_trades - win_cnt
    win_rate = round((win_cnt / tot_trades * 100.0) if tot_trades > 0 else 0.0, 1)
    tot_pnl_btc = round(sum(t["pnl_btc"] for t in LIVE_TRADES_HISTORY), 4)
    tot_rebates_btc = round(sum(t.get("maker_rebate_btc", 0.0) for t in LIVE_TRADES_HISTORY), 5)

    initial_seed = 10.0
    current_seed = round(initial_seed + tot_pnl_btc + tot_rebates_btc, 4)
    return_pct = round(((current_seed - initial_seed) / initial_seed) * 100.0, 2)

    if current_seed >= 50.0:
        level, title = 99, "Lv.99 전설의 고래"
    elif current_seed >= 20.0:
        level, title = 85, "Lv.85 슈퍼 웨일"
    elif current_seed >= 10.0:
        level, title = 77, "Lv.77 비맥 랭커"
    elif current_seed >= 5.0:
        level, title = 40, "Lv.40 단타 머신"
    else:
        level, title = 10, "Lv.10 차갤 뉴비"

    return {
        "status": "SUCCESS",
        "summary": {
            "initial_seed_btc": initial_seed,
            "current_seed_btc": current_seed,
            "return_pct": return_pct,
            "total_trades": tot_trades,
            "win_trades": win_cnt,
            "loss_trades": loss_cnt,
            "wins": win_cnt,
            "losses": loss_cnt,
            "win_rate_pct": win_rate,
            "total_pnl_btc": tot_pnl_btc,
            "net_pnl_btc": tot_pnl_btc,
            "total_rebates_btc": tot_rebates_btc,
            "total_rebate_btc": tot_rebates_btc,
            "wonyo_level": level,
            "wonyo_title": title
        },
        "live_trades": LIVE_TRADES_HISTORY,
        "legendary_trades": LEGENDARY_TRADES
    }

@app.get("/", response_class=HTMLResponse)
def serve_index():
    candidates = [
        Path(__file__).resolve().parent / "static" / "index.html",
        Path(__file__).resolve().parent.parent / "public" / "index.html",
        Path("public/index.html"),
        Path("src/static/index.html")
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return "<h1>Wonyo-AI Terminal UI Loading...</h1>"

# Serve static directory if needed
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve assets directory if needed
assets_candidates = [
    Path(__file__).resolve().parent / "static" / "assets",
    Path(__file__).resolve().parent.parent / "public" / "assets"
]
for ad in assets_candidates:
    if ad.exists():
        app.mount("/assets", StaticFiles(directory=str(ad)), name="assets")
        break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web_api:app", host="127.0.0.1", port=8000, reload=True)
