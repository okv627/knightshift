# src/db/game_upsert.py
"""
Idempotent “upsert” helper for tv_channel_games
───────────────────────────────────────────────
* Normalises raw PGN metadata → dictionary ready for SQLAlchemy
* INSERTs a new row if `id` not present, otherwise UPDATEs it
* Returns **True** when an *existing* row was updated, **False** on insert / failure
"""

from __future__ import annotations

from datetime import datetime, date, time
from typing import Any, Dict, Optional

from sqlalchemy import Table, select, update
from sqlalchemy.orm import Session

from src.utils.logging_utils import setup_logger

LOGGER = setup_logger("game_upsert")


# ═══════════════════════════════════════════════
# Parsing helpers
# ═══════════════════════════════════════════════


def _parse_int(value: Any) -> Optional[int]:
    """Cast to `int`, returning *None* if the cast fails / value is falsy."""
    try:
        return int(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _parse_date(value: str | None, fmt: str = "%Y.%m.%d") -> Optional[date]:
    """Cast a *YYYY.MM.DD* string to `date`, else *None*."""
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        LOGGER.debug("Bad date %s – stored NULL", value)
        return None


def _parse_time(value: str | None, fmt: str = "%H:%M:%S") -> Optional[time]:
    """Cast an *HH:MM:SS* string to `time`, else *None*."""
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).time()
    except ValueError:
        LOGGER.debug("Bad time %s – stored NULL", value)
        return None


# ═══════════════════════════════════════════════
# Public helpers
# ═══════════════════════════════════════════════


def build_game_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise the raw PGN dict into DB‑ready column → value mapping."""
    return {
        "id": raw.get("site", "").split("/")[-1],
        "event": raw.get("event", ""),
        "site": raw.get("site", ""),
        "date": _parse_date(raw.get("date")),
        "white": raw.get("white", ""),
        "black": raw.get("black", ""),
        "result": raw.get("result", ""),
        "utc_date": _parse_date(raw.get("utcdate")),
        "utc_time": _parse_time(raw.get("utctime")),
        "white_elo": _parse_int(raw.get("whiteelo")),
        "black_elo": _parse_int(raw.get("blackelo")),
        "white_title": raw.get("whitetitle", ""),
        "black_title": raw.get("blacktitle", ""),
        "variant": raw.get("variant", ""),
        "time_control": raw.get("timecontrol", ""),
        "eco": raw.get("eco", ""),
        "termination": raw.get("termination", ""),
        "moves": raw.get("moves", ""),
        "opening": raw.get("opening", ""),
        "ingested_at": datetime.utcnow(),
    }


def upsert_game(session: Session, table: Table, game: Dict[str, Any]) -> bool:
    """
    Insert or update a single game row.

    Returns **True** if an existing row was updated, **False** on insert or error.
    """
    game_id = game.get("id")
    if not game_id:
        LOGGER.warning("Missing game ID – skipping row.")
        return False

    try:
        with session.begin():
            exists = session.execute(
                select(table.c.id).where(table.c.id == game_id)
            ).first()

            if exists:
                session.execute(update(table).where(table.c.id == game_id).values(game))
                LOGGER.info("Updated game %s", game_id)
                return True
            else:
                session.execute(table.insert().values(game))
                LOGGER.info("Inserted new game %s", game_id)
                return False

    except Exception as exc:  # pragma: no cover
        LOGGER.error("Error upserting game %s – %s", game_id, exc)
        session.rollback()
        return False
