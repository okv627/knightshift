#!/usr/bin/env python3
"""
get_games_from_tv.py
~~~~~~~~~~~~~~~~~~~~
Streams live chess games from **Lichess TV**, parses each PGN with
`parse_pgn_lines`, and **upserts** the results into PostgreSQL.

Execution flow
==============
1. Build a shared SQLAlchemy engine + session (credentials come from
   `config/.env.local` or AWS Secrets Manager via `load_db_credentials`).
2. For each TV channel (bullet, blitz, …) call the Lichess streaming API.
3. Read the PGN stream line‑by‑line, detect game boundaries, and upsert:
      • new games   → INSERT
      • duplicates  → UPDATE (see `upsert_game`)
4. Repeat until the configurable `TIME_LIMIT` or `MAX_GAMES` is reached.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Final, List, Sequence

import requests
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Time,
    create_engine,
)
from sqlalchemy.orm import Session, sessionmaker

# ──────────────────────────────────────────────────────────────────────────
#   Local imports (after adding project root to PYTHONPATH)
# ──────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # idempotent

from src.db.game_upsert import build_game_data, upsert_game
from src.utils.db_utils import get_database_url, get_lichess_token, load_db_credentials
from src.utils.logging_utils import setup_logger
from src.utils.pgn_parser import parse_pgn_lines

# ──────────────────────────────────────────────────────────────────────────
#   Environment & config
# ──────────────────────────────────────────────────────────────────────────
ENV_FILE = PROJECT_ROOT / "config" / ".env.local"
load_dotenv(ENV_FILE)

LOGGER = setup_logger("get_games_from_tv", level=logging.INFO)

# numeric env‑vars with sane fall‑backs
TIME_LIMIT: Final[int] = int(os.getenv("TIME_LIMIT", 30))  # seconds
SLEEP_INTERVAL: Final[int] = int(os.getenv("SLEEP_INTERVAL", 5))  # seconds
RATE_LIMIT_PAUSE: Final[int] = int(os.getenv("RATE_LIMIT_PAUSE", 900))
MAX_GAMES: Final[int] = int(os.getenv("MAX_GAMES", 5000))

CHANNELS: Final[Sequence[str]] = (
    "bullet",
    "blitz",
    "classical",
    "rapid",
    "chess960",
    "antichess",
    "atomic",
    "horde",
    "crazyhouse",
    "bot",
    "computer",
    "kingOfTheHill",
    "threeCheck",
    "ultraBullet",
    "racingKings",
)

# ──────────────────────────────────────────────────────────────────────────
#   Database setup
# ──────────────────────────────────────────────────────────────────────────
CREDS = load_db_credentials()
ENGINE = create_engine(get_database_url(CREDS))
SESSION: Session = sessionmaker(bind=ENGINE)()

METADATA = MetaData()
TV_GAMES_TBL = Table(
    "tv_channel_games",
    METADATA,
    Column("id", String, primary_key=True),
    Column("event", String),
    Column("site", String),
    Column("date", Date),
    Column("white", String),
    Column("black", String),
    Column("result", String),
    Column("utc_date", Date),
    Column("utc_time", Time),
    Column("white_elo", Integer),
    Column("black_elo", Integer),
    Column("white_title", String),
    Column("black_title", String),
    Column("variant", String),
    Column("time_control", String),
    Column("eco", String),
    Column("termination", String),
    Column("moves", String),
    Column("opening", String),
    Column("ingested_at", DateTime),
)

# ──────────────────────────────────────────────────────────────────────────
#   Lichess API session
# ──────────────────────────────────────────────────────────────────────────
HTTP = requests.Session()
HTTP.headers.update(
    {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {get_lichess_token()}",
    }
)


# ──────────────────────────────────────────────────────────────────────────
#   Helper functions
# ──────────────────────────────────────────────────────────────────────────
def _process_game_block(
    pgn_lines: List[bytes], added: List[str], updated: List[str]
) -> None:
    """Parse a single PGN block and upsert it into Postgres."""
    game = parse_pgn_lines(pgn_lines)
    if "site" not in game:  # sanity guard
        return

    db_row = build_game_data(game)
    was_updated = upsert_game(SESSION, TV_GAMES_TBL, db_row)
    (updated if was_updated else added).append(db_row["id"])


def _stream_channel(channel: str, added: List[str], updated: List[str]) -> None:
    """Stream one TV channel, parse games, handle retries & rate‑limits."""
    url = f"https://lichess.org/api/tv/{channel}"
    params = {"clocks": False, "opening": True}

    for attempt in range(1, 4):  # max 3 retries
        resp = HTTP.get(url, params=params, stream=True)
        if resp.status_code == 429:  # too many requests → bail out
            LOGGER.error("Rate‑limit (429) on '%s' – exiting", channel)
            sys.exit(1)
        if resp.ok:
            break

        LOGGER.warning(
            "Channel '%s' returned %s (%s/3) – retrying in 5 s",
            channel,
            resp.status_code,
            attempt,
        )
        time.sleep(5)
    else:
        LOGGER.error("Could not connect to '%s' after retries", channel)
        return

    _parse_stream(resp, added, updated)


def _parse_stream(
    resp: requests.Response, added: List[str], updated: List[str]
) -> None:
    """Detect game boundaries (blank line + move line) and upsert each game."""
    pgn_block: list[bytes] = []

    for raw in resp.iter_lines():
        if not raw:
            continue  # keep buffering until we hit a move line

        line = raw.decode().strip()
        LOGGER.debug("PGN %s", line)
        pgn_block.append(raw)

        # in Lichess streaming API the first move ("1. …") ends the header
        if line.startswith("1. "):
            _process_game_block(pgn_block, added, updated)
            pgn_block.clear()


# ──────────────────────────────────────────────────────────────────────────
#   Main ingestion loop
# ──────────────────────────────────────────────────────────────────────────
def run_tv_ingestion() -> None:
    """Continuously fetch games from all channels until the time/game limit."""
    start = time.time()
    total = 0

    while time.time() - start < TIME_LIMIT:
        added, updated = [], []

        for ch in CHANNELS:
            LOGGER.info("Fetching channel '%s'…", ch)
            _stream_channel(ch, added, updated)

        LOGGER.info("Batch done – %d added, %d updated", len(added), len(updated))
        total += len(added) + len(updated)

        if total >= MAX_GAMES:
            LOGGER.info(
                "Reached %d games → cooling‑off for %d s", MAX_GAMES, RATE_LIMIT_PAUSE
            )
            time.sleep(RATE_LIMIT_PAUSE)
            total = 0

        LOGGER.info("Sleeping %d s before next batch…", SLEEP_INTERVAL)
        time.sleep(SLEEP_INTERVAL)

    LOGGER.info("TIME_LIMIT (%s s) reached – stopping ingestion", TIME_LIMIT)


# ──────────────────────────────────────────────────────────────────────────
# ⏯️  CLI entry‑point
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_tv_ingestion()
