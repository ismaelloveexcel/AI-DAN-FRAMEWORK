#!/usr/bin/env python3
"""AIDAN-OS — API entry point. Runs the lean AIDAN server."""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.server import app  # noqa: F401 — re-export for Dockerfile CMD

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
