#!/usr/bin/env python3
"""
run_ingestion.py

Entry point for game ingestion. Imports and runs run_tv_ingestion from get_games_from_tv.py.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("CWD:", os.getcwd())
print("Files in CWD:", os.listdir())
print("ENV:", dict(os.environ))  # Optional, or log just PG vars

print("Loaded .env.local")

# Load env vars from .env.local
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")

print("Loaded .env.local")

# --- Add project root (knightshift/) to sys.path ---
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]  # Goes up to knightshift/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Now import your ingestion logic ---
from src.ingestion.get_games_from_tv import run_tv_ingestion

if __name__ == "__main__":
    run_tv_ingestion()
