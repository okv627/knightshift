#!/usr/bin/env python3
"""
run_cleaning.py

Entry point for game record cleaning. Runs sanitize_game_records.validate_and_clean.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env vars from .env.local
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "config" / ".env.local")

# Add project root (knightshift/) to sys.path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now import your cleaning logic
from knightshift.cleaning.validate_tv_channel_games import validate_and_clean

if __name__ == "__main__":
    validate_and_clean()
