# src/utils/logging_utils.py
"""
Minimal helper for **consistent, dual‑destination logging** across every
script in KnightShift.

───────────────────────────────────────────────────────────────────────────
Features
────────
✔  Console **and** rotating file output
✔  Auto‑detects Airflow vs. local path for log directory
✔  Clears old handlers so `setup_logger()` is *idempotent*
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────
_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DEFAULT_LEVEL = logging.INFO


def _detect_logs_dir() -> Path:
    """
    If we are running **inside the Airflow container**, log to the shared
    ``/opt/airflow/logs/pipeline_logs`` folder so logs appear in the UI.
    Otherwise log to `<project‑root>/logs`.
    """
    airflow_home = Path("/opt/airflow")
    if airflow_home.exists():
        return airflow_home / "logs" / "pipeline_logs"

    # project_root/../.. → <repo>/logs
    return Path(__file__).resolve().parents[2] / "logs"


def _init_file_handler(
    logs_dir: Path, logger_name: str, fmt: logging.Formatter
) -> Optional[logging.Handler]:
    """
    Create a time‑stamped FileHandler *if* the directory is writable.
    Any permission error is swallowed – we keep console logging alive.
    """
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = logs_dir / f"{logger_name}_{timestamp}.log"
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(fmt)
        return fh
    except PermissionError:
        # Failsafe: still emit a warning on the root logger
        logging.getLogger().warning("⚠️  Cannot write logs to %s", logs_dir)
        return None


# ──────────────────────────────────────────────────────────────────────
# Public factory
# ──────────────────────────────────────────────────────────────────────
def setup_logger(
    name: str,
    level: int = _DEFAULT_LEVEL,
    logs_dir: Union[str, Path, None] = None,
) -> logging.Logger:
    """
    Return a **fresh** `logging.Logger`.

    Parameters
    ----------
    name
        The logger name – also used in the file name.
    level
        Logging level (INFO by default).
    logs_dir
        Override log directory (rarely needed). ``None`` ⇒ auto detect.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Idempotent: clear handlers added by previous calls in long‑running procs
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(_FMT)

    # ── Console handler ───────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # ── File handler (optional) ───────────────────────────────────────
    target_dir: Path = Path(logs_dir) if logs_dir else _detect_logs_dir()
    file_handler = _init_file_handler(target_dir, name, formatter)
    if file_handler:
        logger.addHandler(file_handler)

    return logger
