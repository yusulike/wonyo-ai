import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from src.web_api import app

client = TestClient(app)

print("=== [1] Testing /api/predict (LIVE BTC) ===")
r_pred = client.get("/api/predict?mode=live")
print("Status code:", r_pred.status_code)
d = r_pred.json()
print("Live Price: $", d.get("current_price"))
print("Action:", d.get("prediction", {}).get("action"))
print("Confidence:", d.get("prediction", {}).get("confidence"))
print("Probabilities:", d.get("prediction", {}).get("probabilities"))
print("Intuition:", d.get("wonyo_intuition"))
print("Risk Matrix:", d.get("risk_matrix"))

print("\n=== [2] Testing /api/candles ===")
r_candles = client.get("/api/candles?mode=live&limit=10")
print("Status code:", r_candles.status_code)
candles = r_candles.json().get("candles", [])
print(f"Returned {len(candles)} candles. Latest candle:", candles[-1])

print("\n=== [3] Testing / (HTML UI) ===")
r_ui = client.get("/")
print("UI status code:", r_ui.status_code, "HTML length:", len(r_ui.text))
