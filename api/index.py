# Vercel serverless entrypoint for the FastAPI backend.
# The app itself lives in lib/main.py (also run locally via `uvicorn lib.main:app`),
# so there's a single source of truth. We just add the project root to the path
# and re-export `app` — Vercel's Python runtime serves any ASGI `app` it finds here.
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.main import app  # noqa: E402  (path must be set before this import)
