"""Bounded PostgreSQL connections; no credentials or database details in responses."""

import os
from pathlib import Path

import psycopg


def read_secret(path):
    value = Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value:
        raise ValueError("A non-empty, single-line secret file is required")
    return value


def connect():
    kwargs = {
        "connect_timeout": 3,
        "options": "-c statement_timeout=2000 -c lock_timeout=2000",
    }
    if os.environ.get("PGPASSWORD_FILE"):
        kwargs["password"] = read_secret(os.environ["PGPASSWORD_FILE"])
    # No implicit localhost/database fallback: missing operator configuration is unavailable.
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn and not all(os.environ.get(key) for key in ("PGHOST", "PGDATABASE", "PGUSER")):
        raise ValueError("Explicit PostgreSQL connection configuration is required")
    return psycopg.connect(dsn, **kwargs)
