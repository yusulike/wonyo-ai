import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.web_api import app, get_prediction

# Handle both root path when mounted as standalone function, and full path
app.add_api_route("/", get_prediction, methods=["GET"])
app.add_api_route("", get_prediction, methods=["GET"])
