#!/usr/bin/env python3
# ────────────────────────────────────────────────────────────────
#  main.py  –  “one‑shot” runner for the full KnightShift pipeline
#
#  Flow:  Ingest  →  Clean  →  Enrich
#
#  NB: In production we schedule these tasks with Airflow; this file
#      remains handy for ad‑hoc local runs or unit‑test orchestration.
# ────────────────────────────────────────────────────────────────
from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import FunctionType
from typing import Final

# ── Repo‑relative imports ───────────────────────────────────────
SRC_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = SRC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))  # make src.* importable before pylint/mypy

from src.pipeline.run_cleaning import validate_and_clean  # noqa: E402
from src.pipeline.run_enrichment import main as run_enrichment  # noqa: E402
from src.pipeline.run_ingestion import run_tv_ingestion  # noqa: E402

# ── Logging setup (shared file across stages) ───────────────────
LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE: Final[Path] = LOG_DIR / "pipeline.log"

# Pipe *everything* (print + traceback) to the same log file
sys.stdout = sys.stderr = open(
    LOG_FILE, "a", buffering=1, encoding="utf-8"
)  # noqa: P201

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,  # override any previous basicConfig
)
logger = logging.getLogger("main")


# ── Small helper to reduce boilerplate ──────────────────────────
def _stage(title: str, fn: FunctionType) -> None:
    """
    Wrapper that logs **start → finish** around a pipeline stage.
    """
    logger.info("%s – started", title)
    try:
        fn()
        logger.info("%s – finished", title)
    except Exception:  # pragma: no cover  (we want full stacktrace in log)
        logger.exception("%s – failed", title)
        raise


# ── Entry‑point ─────────────────────────────────────────────────
if __name__ == "__main__":
    _stage("TV Game Ingestion", run_tv_ingestion)
    _stage("Sanitize Game Records", validate_and_clean)
    _stage("Back‑fill User Profiles", run_enrichment)
