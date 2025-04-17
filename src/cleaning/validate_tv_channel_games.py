#!/usr/bin/env python3
"""
validate_tv_channel_games.py
────────────────────────────
• Marks every row in **tv_channel_games** as *valid* or deletes / updates it
  according to simple business rules:

    ─ required columns present
    ─ `result` in {"1‑0", "0‑1", "1/2‑1/2"}
    ─ cast `white_elo` / `black_elo` to INT (set NULL if malformed)
    ─ replace ECO value “?” with NULL

The script is intentionally simple and **side‑effectful**:
it mutates / deletes rows directly and writes a short `validation_notes`
string so downstream tasks can see what happened.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from sqlalchemy import (
    BOOLEAN,
    INTEGER,
    Column,
    Date,
    DateTime,
    MetaData,
    String,
    Table,
    Time,
    create_engine,
    delete,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker

# ──────────────────────────────────────────────────────────────────────────
#   Project imports
# ──────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]  # knightshift/
sys.path.insert(0, str(ROOT))

from src.utils.db_utils import get_database_url, load_db_credentials
from src.utils.logging_utils import setup_logger

# ──────────────────────────────────────────────────────────────────────────
#   Env / DB initialisation
# ──────────────────────────────────────────────────────────────────────────
load_dotenv(ROOT / "config" / ".env.local")

LOGGER = setup_logger("validate_tv_channel_games")

ENGINE = create_engine(get_database_url(load_db_credentials()))
META = MetaData()

TV_GAMES = Table("tv_channel_games", META, autoload_with=ENGINE)
SessionLocal = sessionmaker(bind=ENGINE)

# ──────────────────────────────────────────────────────────────────────────
#   Config
# ──────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS = ("white", "black", "moves", "result")
VALID_RESULTS = {"1-0", "0-1", "1/2-1/2"}
THROTTLE_DELAY = 0  # seconds; keep 0 for now

# ═════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═════════════════════════════════════════════════════════════════════════


def _to_int(value) -> int | None:
    """Return int(value) or None if cast fails / value is None."""
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _validate_required(row) -> Tuple[bool, str]:
    """Check presence of mandatory columns."""
    missing = next((f for f in REQUIRED_FIELDS if not getattr(row, f, None)), None)
    return (False, f"Missing field: {missing}") if missing else (True, "")


def _validate_result(row) -> Tuple[bool, str]:
    """Ensure the 'result' is one of the allowed strings."""
    if row.result not in VALID_RESULTS:
        return False, f"Invalid result: {row.result}"
    return True, ""


# ═════════════════════════════════════════════════════════════════════════
# Core processing
# ═════════════════════════════════════════════════════════════════════════


def _process_row(session: Session, row) -> Tuple[bool, bool]:
    """
    Validate / clean a single DB row.

    Returns: (row_processed, was_deleted)
    """
    notes: list[str] = []

    # ⇢ mandatory columns & result value
    for check in (_validate_required, _validate_result):
        ok, msg = check(row)
        if not ok:
            notes.append(msg)
            session.execute(delete(TV_GAMES).where(TV_GAMES.c.id == row.id))
            return True, True  # processed + deleted

    # ⇢ ELO cast
    white_elo = _to_int(row.white_elo)
    black_elo = _to_int(row.black_elo)
    if row.white_elo is not None and white_elo is None:
        notes.append("Invalid white_elo")
    if row.black_elo is not None and black_elo is None:
        notes.append("Invalid black_elo")

    # ⇢ ECO fix
    eco_value = None if getattr(row, "eco", None) == "?" else row.eco
    if row.eco == "?":
        notes.append("Set ECO to NULL")

    session.execute(
        update(TV_GAMES)
        .where(TV_GAMES.c.id == row.id)
        .values(
            white_elo=white_elo,
            black_elo=black_elo,
            eco=eco_value,
            is_validated=True,
            validation_notes=", ".join(notes) if notes else "Valid",
        )
    )
    return True, False  # processed, not deleted


def _validate_all() -> None:
    session = SessionLocal()
    rows = session.execute(
        select(TV_GAMES).where(TV_GAMES.c.is_validated.is_(False))
    ).fetchall()

    LOGGER.info("Starting validation on %d row(s)…", len(rows))
    updated = deleted = 0

    for i, row in enumerate(rows, start=1):
        try:
            processed, was_deleted = _process_row(session, row)
            if processed:
                if was_deleted:
                    deleted += 1
                else:
                    updated += 1
        except Exception as exc:
            LOGGER.error("Error processing %s: %s – rolling back", row.id, exc)
            session.rollback()

        if i % 30 == 0:
            LOGGER.info("Processed %d/%d …", i, len(rows))
        time.sleep(THROTTLE_DELAY)

    session.commit()
    LOGGER.info("Validation done. Updated=%d  Deleted=%d", updated, deleted)


# ═════════════════════════════════════════════════════════════════════════
# Entrypoint
# ═════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    _validate_all()
