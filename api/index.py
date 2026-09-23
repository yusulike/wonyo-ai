import sys
from pathlib import Path

# Add project root directory to sys.path so 'src' can be imported in Vercel Serverless
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.web_api import app

# Vercel ASGI Handler
app = app
