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
    assert "WONYO MASTER SCOREBOARD BANNER" in response.text
    assert "sb-verdict" in response.text
    assert "sb-news-ticker" in response.text

def test_predict_endpoint_live():
    response = client.get("/api/predict?mode=live&interval=15m")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "intuitive_verdict" in data
    iv = data["intuitive_verdict"]
    assert "composite_score" in iv
    assert "volume_factor" in iv
    assert "external_factor" in iv
    assert "news_factor" in iv
    assert "top_headlines" in iv["news_factor"]

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
    assert "WONYO MASTER SCOREBOARD BANNER" in resp.text
