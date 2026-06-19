"""Shared pytest fixtures."""
import sys
import os

# Ensure the project root is on sys.path so imports like `from scrapers import …` work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
