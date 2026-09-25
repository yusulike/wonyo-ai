import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from src.onnx_predictor import WonyoONNXPredictor, FEATURE_COLS
from src.web_api import app

def test_onnx_predictor_direct():
    predictor = WonyoONNXPredictor()
    assert predictor.is_loaded is True
    
    # Generate mock 32 candles of 12 features
    mock_df = pd.DataFrame(np.random.randn(40, 12), columns=FEATURE_COLS)
    res = predictor.predict(mock_df)
    
    assert res["status"] == "READY"
    assert res["action"] in ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]
    assert "probabilities" in res
    assert res["probabilities"]["hold_pct"] >= 0.0
    assert res["latency_ms"] > 0.0
    assert "size_multiplier" in res

def test_api_nn_prediction():
    client = TestClient(app)
    resp = client.get("/api/nn-prediction?mode=live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "READY"
    assert data["action"] in ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]

def test_api_predict_includes_nn():
    client = TestClient(app)
    resp = client.get("/api/predict?mode=live")
    assert resp.status_code == 200
    data = resp.json()
    assert "nn_prediction" in data
    assert data["nn_prediction"]["status"] == "READY"
