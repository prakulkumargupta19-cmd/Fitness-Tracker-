"""Vercel serverless entry point for the existing Flask application."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

for directory in (PROJECT_ROOT, BACKEND_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from backend.app import app  # noqa: E402

