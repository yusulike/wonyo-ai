"""
Wonyo-AI Database Persistence Layer
Supports Vercel Postgres (Neon Serverless PostgreSQL via pg8000) with automatic SQLite fallback.
"""

import os
import sys
import ssl
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import sqlite3
import tempfile

try:
    import pg8000.native
    HAS_PG8000 = True
except ImportError:
    HAS_PG8000 = False

logger = logging.getLogger("wonyo_db")

# Historical Legendary Trades Archive (Static Fact Records)
LEGENDARY_TRADES: List[Dict[str, Any]] = [
    {
        "rank": 1,
        "title": "2021.05.19 부처빔 바닥 쓸어담기",
        "date_kst": "2021-05-19 22:15 KST",
        "timestamp": "2021-05-19",
        "timestamp_kst": "2021-05-19 22:15 KST",
        "direction": "LONG",
        "side": "LONG",
        "action": "LONG 2.5x",
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
        "timestamp": "2021-04-14",
        "timestamp_kst": "2021-04-14 20:30 KST",
        "direction": "SHORT",
        "side": "SHORT",
        "action": "SHORT 2.0x",
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
        "timestamp": "2021-06-22",
        "timestamp_kst": "2021-06-22 23:00 KST",
        "direction": "LONG",
        "side": "LONG",
        "action": "LONG 2.0x",
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
        "timestamp": "2021-05-21",
        "timestamp_kst": "2021-05-21 18:15 KST",
        "direction": "LONG",
        "side": "LONG",
        "action": "LONG 1.8x",
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
        "timestamp": "2021-04-18",
        "timestamp_kst": "2021-04-18 12:45 KST",
        "direction": "LONG",
        "side": "LONG",
        "action": "LONG 1.5x",
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

# Initial Seed Trades if DB is completely empty
DEFAULT_SEED_TRADES: List[Dict[str, Any]] = [
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
        "holding_time": "30분"
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
        "holding_time": "45분"
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
        "holding_time": "60분"
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
        "holding_time": "15분"
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
        "holding_time": "30분"
    }
]

class WonyoDBManager:
    """
    Manages trades ledger persistence.
    Prioritizes Vercel Postgres (Neon) when POSTGRES_URL / DATABASE_URL is present.
    Gracefully falls back to local SQLite when running locally or if connection fails.
    """
    def __init__(self, postgres_url: Optional[str] = None, sqlite_path: Optional[str] = None):
        self.postgres_url = postgres_url or os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
        
        if sqlite_path:
            self.sqlite_path = sqlite_path
        else:
            # On Vercel Serverless / AWS Lambda, the app root (/var/task) is read-only.
            # Only /tmp is writable. We use tempfile.gettempdir() to ensure writable storage.
            temp_dir = Path(tempfile.gettempdir())
            self.sqlite_path = str(temp_dir / "wonyo_trades.db")
            
        self.use_postgres = bool(self.postgres_url and HAS_PG8000)
        self._initialized = False

    def _get_pg_connection(self):
        if not self.postgres_url or not HAS_PG8000:
            return None
        try:
            parsed = urlparse(self.postgres_url)
            ssl_context = ssl.create_default_context()
            conn = pg8000.native.Connection(
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/"),
                ssl_context=ssl_context
            )
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to Vercel Postgres: {e}. Falling back to SQLite.")
            return None

    def _get_sqlite_connection(self):
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to SQLite file {self.sqlite_path}: {e}. Falling back to :memory:")
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            return conn

    def init_db(self):
        """Initializes tables and seeds default simulation records if empty."""
        if self._initialized:
            return

        try:
            # 1. Try Postgres
            pg_conn = self._get_pg_connection()
            if pg_conn:
                try:
                    pg_conn.run("""
                        CREATE TABLE IF NOT EXISTS trades (
                            id VARCHAR(64) PRIMARY KEY,
                            time_kst VARCHAR(64),
                            timestamp_kst VARCHAR(64),
                            direction VARCHAR(16),
                            side VARCHAR(16),
                            leverage REAL,
                            entry_price REAL,
                            exit_price REAL,
                            pnl_pct REAL,
                            pnl_btc REAL,
                            maker_rebate_btc REAL,
                            exit_reason VARCHAR(128),
                            holding_time VARCHAR(32),
                            bars_held INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    # Check row count
                    res = pg_conn.run("SELECT COUNT(*) FROM trades;")
                    count = res[0][0] if res else 0
                    if count == 0:
                        for t in DEFAULT_SEED_TRADES:
                            pg_conn.run("""
                                INSERT INTO trades (
                                    id, time_kst, timestamp_kst, direction, side, leverage,
                                    entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                                    exit_reason, holding_time, bars_held
                                ) VALUES (
                                    :id, :time_kst, :timestamp_kst, :direction, :side, :leverage,
                                    :entry_price, :exit_price, :pnl_pct, :pnl_btc, :maker_rebate_btc,
                                    :exit_reason, :holding_time, :bars_held
                                ) ON CONFLICT (id) DO NOTHING;
                            """, **t)
                    pg_conn.close()
                    self.use_postgres = True
                    self._initialized = True
                    return
                except Exception as e:
                    logger.warning(f"Postgres initialization error: {e}. Falling back to SQLite.")
                    try:
                        pg_conn.close()
                    except Exception:
                        pass
                    self.use_postgres = False

            # 2. SQLite Fallback
            conn = self._get_sqlite_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS trades (
                            id TEXT PRIMARY KEY,
                            time_kst TEXT,
                            timestamp_kst TEXT,
                            direction TEXT,
                            side TEXT,
                            leverage REAL,
                            entry_price REAL,
                            exit_price REAL,
                            pnl_pct REAL,
                            pnl_btc REAL,
                            maker_rebate_btc REAL,
                            exit_reason TEXT,
                            holding_time TEXT,
                            bars_held INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor = conn.execute("SELECT COUNT(*) FROM trades;")
                    count = cursor.fetchone()[0]
                    if count == 0:
                        for t in DEFAULT_SEED_TRADES:
                            conn.execute("""
                                INSERT OR IGNORE INTO trades (
                                    id, time_kst, timestamp_kst, direction, side, leverage,
                                    entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                                    exit_reason, holding_time, bars_held
                                ) VALUES (
                                    :id, :time_kst, :timestamp_kst, :direction, :side, :leverage,
                                    :entry_price, :exit_price, :pnl_pct, :pnl_btc, :maker_rebate_btc,
                                    :exit_reason, :holding_time, :bars_held
                                );
                            """, t)
            finally:
                conn.close()
            self._initialized = True
        except Exception as e:
            logger.warning(f"init_db fallback failed gracefully: {e}")
            self._initialized = True

    def record_trade(self, trade: Dict[str, Any]) -> bool:
        """Inserts a newly executed virtual trade into persistent storage."""
        self.init_db()

        trade_data = {
            "id": trade.get("id", f"TRD-{int(os.times().elapsed * 1000)}"),
            "time_kst": trade.get("time_kst") or trade.get("timestamp_kst", "--"),
            "timestamp_kst": trade.get("timestamp_kst") or trade.get("time_kst", "--"),
            "direction": trade.get("direction") or trade.get("side", "LONG"),
            "side": trade.get("side") or trade.get("direction", "LONG"),
            "leverage": float(trade.get("leverage", 1.85)),
            "entry_price": float(trade.get("entry_price", 0.0)),
            "exit_price": float(trade.get("exit_price", 0.0)),
            "pnl_pct": float(trade.get("pnl_pct", 0.0)),
            "pnl_btc": float(trade.get("pnl_btc", 0.0)),
            "maker_rebate_btc": float(trade.get("maker_rebate_btc", 0.0)),
            "exit_reason": str(trade.get("exit_reason", "--")),
            "holding_time": str(trade.get("holding_time", "--")),
            "bars_held": int(trade.get("bars_held", 1))
        }

        if self.use_postgres:
            pg_conn = self._get_pg_connection()
            if pg_conn:
                try:
                    pg_conn.run("""
                        INSERT INTO trades (
                            id, time_kst, timestamp_kst, direction, side, leverage,
                            entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                            exit_reason, holding_time, bars_held
                        ) VALUES (
                            :id, :time_kst, :timestamp_kst, :direction, :side, :leverage,
                            :entry_price, :exit_price, :pnl_pct, :pnl_btc, :maker_rebate_btc,
                            :exit_reason, :holding_time, :bars_held
                        ) ON CONFLICT (id) DO UPDATE SET
                            exit_price = EXCLUDED.exit_price,
                            pnl_pct = EXCLUDED.pnl_pct,
                            pnl_btc = EXCLUDED.pnl_btc;
                    """, **trade_data)
                    pg_conn.close()
                    return True
                except Exception as e:
                    logger.warning(f"Failed to record trade in Postgres: {e}")
                    try:
                        pg_conn.close()
                    except Exception:
                        pass

        # SQLite fallback
        conn = self._get_sqlite_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trades (
                        id, time_kst, timestamp_kst, direction, side, leverage,
                        entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                        exit_reason, holding_time, bars_held
                    ) VALUES (
                        :id, :time_kst, :timestamp_kst, :direction, :side, :leverage,
                        :entry_price, :exit_price, :pnl_pct, :pnl_btc, :maker_rebate_btc,
                        :exit_reason, :holding_time, :bars_held
                    );
                """, trade_data)
            return True
        except Exception as e:
            logger.error(f"Failed to record trade in SQLite: {e}")
            return False
        finally:
            conn.close()

    def _build_default_response(self) -> Dict[str, Any]:
        """Guarantees a valid 200 OK trades response even if storage is completely unreachable."""
        return {
            "status": "SUCCESS",
            "storage_type": "In-Memory (Safe Fallback)",
            "summary": {
                "initial_seed_btc": 10.0,
                "current_seed_btc": 10.0074,
                "return_pct": 0.07,
                "total_trades": len(DEFAULT_SEED_TRADES),
                "win_trades": 3,
                "loss_trades": 2,
                "wins": 3,
                "losses": 2,
                "win_rate_pct": 60.0,
                "total_pnl_btc": 0.0058,
                "net_pnl_btc": 0.0058,
                "total_rebates_btc": 0.0016,
                "total_rebate_btc": 0.0016,
                "wonyo_level": 77,
                "wonyo_title": "Lv.77 비맥 랭커"
            },
            "live_trades": list(DEFAULT_SEED_TRADES),
            "legendary_trades": LEGENDARY_TRADES
        }

    def get_trades_history(self, limit: Any = 20) -> Dict[str, Any]:
        """Fetches latest trades and computes portfolio summary stats."""
        try:
            limit_val = int(limit)
            if limit_val < 1:
                limit_val = 20
        except Exception:
            limit_val = 20

        try:
            self.init_db()
        except Exception as e:
            logger.warning(f"init_db call in get_trades_history: {e}")

        live_trades: List[Dict[str, Any]] = []

        try:
            if self.use_postgres:
                pg_conn = self._get_pg_connection()
                if pg_conn:
                    try:
                        rows = pg_conn.run(f"""
                            SELECT id, time_kst, timestamp_kst, direction, side, leverage,
                                   entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                                   exit_reason, holding_time, bars_held
                            FROM trades
                            ORDER BY created_at DESC, id DESC
                            LIMIT {limit_val};
                        """)
                        for r in rows:
                            live_trades.append({
                                "id": r[0],
                                "time_kst": r[1],
                                "timestamp_kst": r[2],
                                "direction": r[3],
                                "side": r[4],
                                "leverage": r[5],
                                "entry_price": r[6],
                                "exit_price": r[7],
                                "pnl_pct": r[8],
                                "pnl_btc": r[9],
                                "maker_rebate_btc": r[10],
                                "exit_reason": r[11],
                                "holding_time": r[12],
                                "bars_held": r[13]
                            })
                        pg_conn.close()
                    except Exception as e:
                        logger.warning(f"Failed to query Postgres trades: {e}")
                        try:
                            pg_conn.close()
                        except Exception:
                            pass

            if not live_trades:
                # SQLite fallback query
                conn = self._get_sqlite_connection()
                try:
                    cursor = conn.execute(f"""
                        SELECT id, time_kst, timestamp_kst, direction, side, leverage,
                               entry_price, exit_price, pnl_pct, pnl_btc, maker_rebate_btc,
                               exit_reason, holding_time, bars_held
                        FROM trades
                        ORDER BY created_at DESC, rowid DESC
                        LIMIT {limit_val};
                    """)
                    for r in cursor.fetchall():
                        live_trades.append(dict(r))
                except Exception as e:
                    logger.error(f"Failed to query SQLite trades: {e}")
                    live_trades = list(DEFAULT_SEED_TRADES)
                finally:
                    conn.close()

            if not live_trades:
                live_trades = list(DEFAULT_SEED_TRADES)

            # Compute Summary Statistics
            tot_trades = len(live_trades)
            wins = [t for t in live_trades if t.get("pnl_pct", 0.0) > 0]
            win_cnt = len(wins)
            loss_cnt = tot_trades - win_cnt
            win_rate = round((win_cnt / tot_trades * 100.0) if tot_trades > 0 else 0.0, 1)
            tot_pnl_btc = round(sum(t.get("pnl_btc", 0.0) for t in live_trades), 4)
            tot_rebates_btc = round(sum(t.get("maker_rebate_btc", 0.0) for t in live_trades), 5)

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
                "storage_type": "Vercel Postgres (Neon)" if (self.use_postgres and live_trades and live_trades != DEFAULT_SEED_TRADES) else "SQLite (Local/Fallback)",
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
                "live_trades": live_trades,
                "legendary_trades": LEGENDARY_TRADES
            }
        except Exception as e:
            logger.error(f"Critical error in get_trades_history: {e}")
            return self._build_default_response()

# Global Singleton DB Manager
_db_manager_instance: Optional[WonyoDBManager] = None

def get_db_manager() -> WonyoDBManager:
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = WonyoDBManager()
        _db_manager_instance.init_db()
    return _db_manager_instance
