"""Minimal PostgreSQL connectivity probe for readiness checks."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any


def check_database(
    environ: Mapping[str, str] | None = None,
    connector: Callable[..., Any] | None = None,
) -> bool:
    """Return whether PostgreSQL accepts a bounded SELECT 1 probe."""
    settings = os.environ if environ is None else environ
    host = settings.get("BACKEND_DB_HOST", "").strip()
    database = settings.get("BACKEND_DB_NAME", "").strip()
    user = settings.get("BACKEND_DB_USER", "").strip()
    password = settings.get("BACKEND_DB_PASSWORD", "")
    try:
        port = int(settings.get("BACKEND_DB_PORT", "5432"))
    except (TypeError, ValueError):
        return False
    if not host or not database or not user or not password or not 1 <= port <= 65535:
        return False

    if connector is None:
        try:
            import psycopg
        except ImportError:
            return False
        connector = psycopg.connect

    connection_options = {
        "host": host,
        "port": port,
        "dbname": database,
        "user": user,
        "password": password,
        "connect_timeout": 2,
    }
    try:
        with connector(**connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except Exception:
        return False
