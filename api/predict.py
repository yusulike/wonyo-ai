import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, Request
from src.web_api import get_prediction

app = FastAPI()

@app.api_route("/", methods=["GET"])
@app.api_route("/{full_path:path}", methods=["GET"])
def handle_predict(request: Request, full_path: str = ""):
    params = dict(request.query_params)
    mode = params.get("mode", "live")
    interval = params.get("interval", "15m")
    sensitivity = params.get("sensitivity", "standard")
    equity_btc = float(params.get("equity_btc", 10.0))
    consecutive_losses = int(params.get("consecutive_losses", 0))
    return get_prediction(mode=mode, interval=interval, sensitivity=sensitivity, equity_btc=equity_btc, consecutive_losses=consecutive_losses)
