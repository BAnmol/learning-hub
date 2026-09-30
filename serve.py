"""
Production entry point — serves the Flask app with waitress instead of the
Werkzeug development server used by `python app.py`. The dev server is not
designed for production traffic (single-threaded by default, no protection
against slow clients, verbose debug output); waitress is a pure-Python WSGI
server that works the same way on Windows as it does on Linux/macOS.

Usage:
    python serve.py
"""
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for _candidate_path in [
    _PROJECT_ROOT,
    os.path.join(_PROJECT_ROOT, "src"),
    "/home/site/wwwroot",
    "/home/site/wwwroot/src",
    os.getcwd(),
    os.path.join(os.getcwd(), "src"),
]:
    if os.path.exists(_candidate_path) and _candidate_path not in sys.path:
        sys.path.insert(0, _candidate_path)

from dotenv import load_dotenv
from waitress import serve

from app import app

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    threads = int(os.getenv("WEB_CONCURRENCY", 8))
    print(f"Serving Brainfreeze Algos (production/waitress) on http://{host}:{port} with {threads} threads")
    serve(app, host=host, port=port, threads=threads)
