import sys
from pathlib import Path

# Add project root directory to sys.path so 'src' can be imported in Vercel Serverless
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.web_api import app

class VercelPathFixMiddleware:
    """
    On Vercel, requests rewritten via vercel.json arrive at api/index.py with
    scope['path'] set to '/api/index.py' instead of the client's actual path
    (e.g., '/api/predict' or '/api/candles').
    Vercel provides the true client path in the headers:
      - x-matched-path
      - x-invoke-path
      - x-forwarded-uri
    This pure ASGI middleware restores the true path in the ASGI scope BEFORE
    FastAPI evaluates routes.
    """
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            matched = (
                headers.get(b"x-matched-path")
                or headers.get(b"x-invoke-path")
                or headers.get(b"x-forwarded-uri")
            )
            if matched:
                path_str = matched.decode("utf-8").split("?")[0]
                if path_str and path_str not in ("/api/index.py", "/api/index"):
                    scope["path"] = path_str
                    scope["raw_path"] = path_str.encode("utf-8")
        await self.asgi_app(scope, receive, send)

# Wrapped ASGI Handler for Vercel
app = VercelPathFixMiddleware(app)
