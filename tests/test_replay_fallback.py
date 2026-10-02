"""Regression: replay mode must fall back to the embedded dataset when the
parquet is absent (Vercel serverless bundle scenario)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.web_api import load_replay_candles

PARQUET = Path("data/candles/bitmex_2021_q2_15m.parquet")
HIDDEN = Path("data/candles/_hidden_bitmex.parquet")


def test_replay_embedded_fallback_without_parquet():
    assert not HIDDEN.exists(), "leftover hidden parquet from a previous run"
    PARQUET.rename(HIDDEN)
    try:
        df = load_replay_candles(limit=120)
        ts = pd.to_datetime(df["timestamp"])
        assert len(df) == 120
        assert str(ts.iloc[0].date()) == "2021-05-17"
        assert str(ts.iloc[-1].date()) == "2021-05-19"
    finally:
        HIDDEN.rename(PARQUET)


def test_replay_parquet_path_alignment():
    """Embedded window must align with the parquet slice at the same offset."""
    df = load_replay_candles(limit=120)
    ts = pd.to_datetime(df["timestamp"])
    assert str(ts.iloc[0].date()) == "2021-05-17"
