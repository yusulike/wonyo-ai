import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from src.web_api import app

client = TestClient(app)

def test_root_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "panel-wonyo-decision" in response.text
    assert "panel-active-position" in response.text
    assert "sb-news-ticker" in response.text

def test_predict_endpoint_live():
    response = client.get("/api/predict?mode=live&interval=15m")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "readiness" in data
    assert "long_readiness_pct" in data["readiness"]
    assert "short_readiness_pct" in data["readiness"]
    assert "intuitive_verdict" in data
    iv = data["intuitive_verdict"]
    assert "composite_score" in iv
    assert "volume_factor" in iv
    assert "external_factor" in iv
    assert "news_factor" in iv
    assert "top_headlines" in iv["news_factor"]

def test_predict_endpoint_active_sensitivity():
    response = client.get("/api/predict?mode=live&interval=15m&sensitivity=active")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["sensitivity"] == "active"
    assert data["readiness"]["sensitivity_mode"] == "active"

def test_candles_endpoint():
    response = client.get("/api/candles?mode=replay&interval=15m&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(data["candles"]) > 0

def test_vercel_entrypoint():
    from api.index import app as vercel_app
    vercel_client = TestClient(vercel_app)
    resp = vercel_client.get("/")
    assert resp.status_code == 200
    assert "panel-wonyo-decision" in resp.text
    assert "panel-active-position" in resp.text

def test_vercel_path_fix_middleware():
    from api.index import app as vercel_app
    vercel_client = TestClient(vercel_app)
    # Simulate Vercel rewrite where client requested /api/predict but Vercel routes to /api/index.py with header
    resp = vercel_client.get("/api/index.py?mode=live&interval=15m", headers={"x-matched-path": "/api/predict?mode=live&interval=15m"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "intuitive_verdict" in data

def test_standalone_predict_app():
    from api.predict import app as pred_app
    c = TestClient(pred_app)
    resp1 = c.get("/?mode=live&interval=15m")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "SUCCESS"
    resp2 = c.get("/api/predict?mode=live&interval=15m")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "SUCCESS"

def test_standalone_candles_app():
    from api.candles import app as cand_app
    c = TestClient(cand_app)
    resp1 = c.get("/?mode=replay&interval=15m&limit=10")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "SUCCESS"

def test_trades_endpoint():
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "summary" in data
    assert "live_trades" in data
    assert "legendary_trades" in data
    assert len(data["live_trades"]) > 0
    assert len(data["legendary_trades"]) >= 5

def test_standalone_trades_app():
    from api.trades import app as trades_app
    c = TestClient(trades_app)
    resp = c.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "summary" in data

