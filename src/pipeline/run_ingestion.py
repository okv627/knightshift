#!/usr/bin/env python3
"""
run_ingestion.py

Entry point for game ingestion. Imports and runs run_tv_ingestion from get_games_from_tv.py.
"""

import sys
from pathlib import Path

# --- Add project root (knightshift/) to sys.path ---
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]  # Goes up to knightshift/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Now import your ingestion logic ---
from src.ingestion.get_games_from_tv import run_tv_ingestion

if __name__ == "__main__":
    run_tv_ingestion()
