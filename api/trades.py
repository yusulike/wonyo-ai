import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, Request
from src.web_api import get_trades_history

app = FastAPI()

@app.api_route("/", methods=["GET"])
@app.api_route("/{full_path:path}", methods=["GET"])
def handle_trades(request: Request, full_path: str = ""):
    return get_trades_history()
