# src/utils/db_utils.py
"""
Tiny helper module for **all** DB / secret look‑ups.

Keeps PG connection info in one place and hides the AWS Secrets Manager
plumbing from the rest of the code‑base.
─────────────────────────────────────────────────────────────────────────
Public helpers
──────────────
load_db_credentials()   -> Dict[str, str]
get_database_url(creds) -> str
get_lichess_token()     -> Optional[str]
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load .env.* as early as possible so every import sees the variables
load_dotenv()

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
_SECRET_NAME: str = os.getenv("DB_SECRET_NAME", "LichessDBCreds")
_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
_DOCKER_MODE: bool = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────
def _bool_env(var_name: str, default: str = "false") -> bool:
    """Convert `TRUE / true / 1`‑like strings to bool."""
    return os.getenv(var_name, default).strip().lower() in {"1", "true", "yes"}


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────
def load_db_credentials(
    secret_name: str = _SECRET_NAME,
    region_name: str = _REGION,
) -> Dict[str, str]:
    """
    Fetch the Postgres credentials JSON from **AWS Secrets Manager**.

    If the code is running inside Docker Compose (detected via
    *RUNNING_IN_DOCKER=true*), we **override** ``PGHOST`` with *db* so it
    points at the Postgres service on the internal compose network.
    """
    client = boto3.session.Session().client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        creds: Dict[str, str] = json.loads(response["SecretString"])
    except ClientError as exc:
        # Fail fast – the caller can decide how to recover / exit
        raise RuntimeError(f"Failed to load secret `{secret_name}`") from exc

    if _DOCKER_MODE:
        # Must match the service name in docker‑compose.yml
        creds["PGHOST"] = "db"

    return creds


def get_database_url(creds: Dict[str, str]) -> str:
    """
    Build a SQLAlchemy URL **pg8000 driver** string from the creds dict.
    Example:
       postgresql+pg8000://postgres:postgres@localhost:5432/knightshift
    """
    return (
        "postgresql+pg8000://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
    ).format(
        PGUSER=creds["PGUSER"],
        PGPASSWORD=creds["PGPASSWORD"],
        PGHOST=creds.get("PGHOST", "localhost"),
        PGPORT=creds.get("PGPORT", "5432"),
        PGDATABASE=creds["PGDATABASE"],
    )


def get_lichess_token() -> Optional[str]:
    """Return the bearer token used for Lichess API calls (or *None*)."""
    return os.getenv("LICHESS_TOKEN")
