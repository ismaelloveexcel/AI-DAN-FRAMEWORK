"""AIDAN-OS API entry point — imports and runs the lean server."""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.server import app  # noqa: F401 — re-export for uvicorn

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
