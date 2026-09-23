import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, Request
from src.web_api import get_candles

app = FastAPI()

@app.api_route("/{full_path:path}", methods=["GET"])
def handle_candles(request: Request, full_path: str = ""):
    params = dict(request.query_params)
    mode = params.get("mode", "live")
    interval = params.get("interval", "15m")
    limit = int(params.get("limit", 100))
    return get_candles(mode=mode, interval=interval, limit=limit)
