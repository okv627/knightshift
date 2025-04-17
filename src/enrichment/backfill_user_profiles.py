#!/usr/bin/env python3
"""
backfill_user_profiles.py
─────────────────────────
Fetch public profiles from **Lichess** for any player that appears in
`tv_channel_games` but has not yet been enriched.
The script

1. collects unique user‑names whose `profile_updated` flag is **False**;
2. pulls their profile JSON from the Lichess REST API;
3. inserts the data into `lichess_users` (or skips if it already exists);
4. flips `profile_updated = TRUE` for every processed game row.

Runtime limits, throttling, and batch pauses are controlled via the
constants in **Config**.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Set

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# ──────────────────────────────────────────────────────────────────────────
#   Local imports  (add project root to PYTHONPATH first)
# ──────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]  # project root (knightshift/)
sys.path.insert(0, str(ROOT))

from src.utils.db_utils import get_database_url, get_lichess_token, load_db_credentials
from src.utils.logging_utils import setup_logger

# ──────────────────────────────────────────────────────────────────────────
#   Env & DB initialisation
# ──────────────────────────────────────────────────────────────────────────
load_dotenv(ROOT / "config" / ".env.local")

LOGGER = setup_logger("backfill_user_profiles", level=logging.INFO)

ENGINE = create_engine(
    get_database_url(load_db_credentials()),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
SESSION: Session = sessionmaker(bind=ENGINE)()
METADATA = MetaData()

# ──────────────────────────────────────────────────────────────────────────
#   Table models  (minimal columns only)
# ──────────────────────────────────────────────────────────────────────────
TV_GAMES = Table(
    "tv_channel_games",
    METADATA,
    Column("id", String, primary_key=True),
    Column("white", String),
    Column("black", String),
    Column("profile_updated", Boolean, default=False),
)

LICHESS_USERS = Table(
    "lichess_users",
    METADATA,
    Column("id", String(50), primary_key=True),
    Column("username", String(50)),
    Column("title", String(10)),
    Column("url", Text),
    Column("real_name", Text),
    Column("location", Text),
    Column("bio", Text),
    Column("fide_rating", Integer),
    Column("uscf_rating", Integer),
    Column("bullet_rating", Integer),
    Column("blitz_rating", Integer),
    Column("classical_rating", Integer),
    Column("rapid_rating", Integer),
    Column("chess960_rating", Integer),
    Column("ultra_bullet_rating", Integer),
    Column("country_code", String(5)),
    Column("created_at", BigInteger),
    Column("seen_at", BigInteger),
    Column("playtime_total", Integer),
    Column("playtime_tv", Integer),
    Column("games_all", Integer),
    Column("games_rated", Integer),
    Column("games_win", Integer),
    Column("games_loss", Integer),
    Column("games_draw", Integer),
    Column("patron", Boolean),
    Column("streaming", Boolean),
)

# ──────────────────────────────────────────────────────────────────────────
#   Config
# ──────────────────────────────────────────────────────────────────────────
TIME_PER_USER = 0.5  # seconds between individual API calls
BATCH_SIZE = 3_000  # users processed before a long pause
BATCH_PAUSE = 15 * 60  # seconds to pause after each big batch
PROGRESS_INTERVAL = 30  # seconds between progress log lines
SCRIPT_TIME_LIMIT = 3  # hard stop (seconds) – keeps CI tests fast

# ──────────────────────────────────────────────────────────────────────────
#   Shared HTTP session
# ──────────────────────────────────────────────────────────────────────────
HTTP = requests.Session()
HTTP.headers.update(
    {
        "Authorization": f"Bearer {get_lichess_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
)

# ═════════════════════════════════════════════════════════════════════════
# Helper functions
# ═════════════════════════════════════════════════════════════════════════


def _collect_unprofiled_users() -> Set[str]:
    """Return all distinct white/black players whose profile is not updated."""
    rows = SESSION.execute(
        select(TV_GAMES.c.white, TV_GAMES.c.black).where(
            TV_GAMES.c.profile_updated.is_(False)
        )
    ).fetchall()

    users: set[str] = set()
    for w, b in rows:
        if w:
            users.add(w)
        if b:
            users.add(b)
    return users


def _fetch_profile(username: str) -> Optional[dict]:
    """Fetch player JSON; handle 429 / network errors gracefully."""
    url = f"https://lichess.org/api/user/{username}"
    try:
        resp = HTTP.get(url, params={"trophies": "false"})
        if resp.status_code == 429:
            LOGGER.error("Rate‑limit hit on '%s'; stopping backfill.", username)
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()
    except HTTPError as e:  # 4xx/5xx
        LOGGER.warning("HTTP %s for user '%s': %s", resp.status_code, username, e)
    except Exception as e:
        LOGGER.warning("Error fetching '%s': %s", username, e)
    return None


def _profile_exists(user_id: str) -> bool:
    return (
        SESSION.execute(
            select(LICHESS_USERS.c.id).where(LICHESS_USERS.c.id == user_id)
        ).first()
        is not None
    )


def _insert_profile(data: dict) -> None:
    """Insert a new row into `lichess_users` (rollback on failure)."""
    profile = data.get("profile", {})
    perfs = data.get("perfs", {})
    play_time = data.get("playTime", {})
    cnt = data.get("count", {})

    row = {
        # identifiers
        "id": data.get("id"),
        "username": data.get("username"),
        "title": data.get("title"),
        "url": data.get("url"),
        # free‑text
        "real_name": profile.get("realName"),
        "location": profile.get("location"),
        "bio": profile.get("bio"),
        # ratings
        "fide_rating": profile.get("fideRating"),
        "uscf_rating": profile.get("uscfRating"),
        "bullet_rating": perfs.get("bullet", {}).get("rating"),
        "blitz_rating": perfs.get("blitz", {}).get("rating"),
        "classical_rating": perfs.get("classical", {}).get("rating"),
        "rapid_rating": perfs.get("rapid", {}).get("rating"),
        "chess960_rating": perfs.get("chess960", {}).get("rating"),
        "ultra_bullet_rating": perfs.get("ultraBullet", {}).get("rating"),
        # misc
        "country_code": profile.get("flag"),
        "created_at": data.get("createdAt"),
        "seen_at": data.get("seenAt"),
        "playtime_total": play_time.get("total"),
        "playtime_tv": play_time.get("tv"),
        "games_all": cnt.get("all"),
        "games_rated": cnt.get("rated"),
        "games_win": cnt.get("win"),
        "games_loss": cnt.get("loss"),
        "games_draw": cnt.get("draw"),
        "patron": data.get("patron"),
        "streaming": data.get("streaming"),
    }

    SESSION.execute(LICHESS_USERS.insert().values(**row))
    SESSION.commit()


def _mark_profile_done(username: str) -> None:
    """Set profile_updated=TRUE for all games where the user appears."""
    SESSION.execute(
        update(TV_GAMES)
        .where((TV_GAMES.c.white == username) | (TV_GAMES.c.black == username))
        .values(profile_updated=True)
    )
    SESSION.commit()


def _handle_user(username: str) -> bool:
    """Fetch, insert (if new), and flag games; return True on any success."""
    data = _fetch_profile(username)
    if not data or not (user_id := data.get("id")):
        return False

    if _profile_exists(user_id):
        LOGGER.info("User '%s' already present – skipping insert.", username)
    else:
        try:
            _insert_profile(data)
            LOGGER.info("Inserted profile for '%s' (id=%s).", username, user_id)
        except Exception as e:
            LOGGER.error("Insert failed for '%s': %s – rolling back", username, e)
            SESSION.rollback()
            return False

    _mark_profile_done(username)
    return True


def _eta(total: int, seconds_per_user: float) -> str:
    minutes, seconds = divmod(int(total * seconds_per_user), 60)
    return f"~{minutes} min {seconds} s" if minutes else f"~{seconds} s"


# ═════════════════════════════════════════════════════════════════════════
# Main processing loop
# ═════════════════════════════════════════════════════════════════════════


def _process(users: Set[str]) -> None:
    total = len(users)
    LOGGER.info(
        "Need to enrich %d unique users (ETA %s).", total, _eta(total, TIME_PER_USER)
    )

    start = last_log = time.time()
    processed = 0

    for username in users:
        # hard stop for CI / unit‑tests
        if time.time() - start > SCRIPT_TIME_LIMIT:
            LOGGER.warning(
                "Time‑limit (%s s) reached – stopping early.", SCRIPT_TIME_LIMIT
            )
            break

        if _handle_user(username):
            processed += 1

        # periodic status report
        if time.time() - last_log > PROGRESS_INTERVAL:
            LOGGER.info(
                "Progress %d/%d (remaining %d)…", processed, total, total - processed
            )
            last_log = time.time()

        # rate‑limit protection
        time.sleep(TIME_PER_USER)

        # long cool‑down after big batch
        if processed and processed % BATCH_SIZE == 0:
            LOGGER.info(
                "Processed %d users – cooling‑off %d min.", processed, BATCH_PAUSE // 60
            )
            time.sleep(BATCH_PAUSE)

    LOGGER.info("Finished: %d user profiles processed.", processed)


# ═════════════════════════════════════════════════════════════════════════
# Entry‑point
# ═════════════════════════════════════════════════════════════════════════
def main() -> None:
    users = _collect_unprofiled_users()
    if not users:
        LOGGER.info("All profiles up‑to‑date – nothing to do.")
        return
    _process(users)


if __name__ == "__main__":
    main()
