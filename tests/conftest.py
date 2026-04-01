"""Pytest configuration — ensure project root is on sys.path."""
import sys
import os

# Add project root to path so 'api', 'core', 'agents' are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
