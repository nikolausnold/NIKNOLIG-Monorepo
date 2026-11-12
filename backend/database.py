"""Bounded PostgreSQL connections; no credentials or database details in responses."""

from __future__ import annotations

import os
import asyncio
import threading
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

import psycopg

PROBE_DEADLINE_SECONDS = 2.0
_PROBE_SLOT = threading.BoundedSemaphore(1)


def _run_probe(connection_options, connector) -> bool:
    with connector(**connection_options) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)


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
    if not _PROBE_SLOT.acquire(blocking=False):
        return False

    completed = threading.Event()
    result = []

    def run_probe():
        try:
            result.append(_run_probe(connection_options, connector))
        except Exception:
            result.append(False)
        finally:
            _PROBE_SLOT.release()
            completed.set()

    try:
        worker = threading.Thread(target=run_probe, daemon=True)
        worker.start()
    except Exception:
        _PROBE_SLOT.release()
        return False

    if not completed.wait(PROBE_DEADLINE_SECONDS):
        return False
    return bool(result and result[0])


def read_secret(path):
    value = Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value:
        raise ValueError("A non-empty, single-line secret file is required")
    return value


READINESS_TIMEOUT = 4


def connection_parameters():
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
    return dsn, kwargs


def health_connection_parameters():
    """Readiness login: HEALTH_DB_USER + HEALTH_DB_PASSWORD_FILE override the normal API login.

    Both or neither must be set; with neither, the normal PG* login is used (it must then be the
    health role, which the readiness check enforces). Never falls back to a different secret.
    """
    dsn, kwargs = connection_parameters()
    user = os.environ.get("HEALTH_DB_USER")
    secret_file = os.environ.get("HEALTH_DB_PASSWORD_FILE")
    if bool(user) != bool(secret_file):
        raise ValueError("HEALTH_DB_USER and HEALTH_DB_PASSWORD_FILE must be set together")
    if user:
        host = os.environ.get("PGHOST")
        dbname = os.environ.get("PGDATABASE")
        if dsn or not host or not dbname:
            raise ValueError("Explicit PostgreSQL host and database are required for the health login")
        kwargs.update(host=host, dbname=dbname, user=user, password=read_secret(secret_file))
        return "", kwargs
    return dsn, kwargs


def connect():
    dsn, kwargs = connection_parameters()
    return psycopg.connect(dsn, **kwargs)


async def probe(check, *, health_login=False):
    connection = None

    async def run():
        nonlocal connection
        dsn, kwargs = health_connection_parameters() if health_login else connection_parameters()
        kwargs["options"] = (
            kwargs.get("options", "") + " -c default_transaction_read_only=on"
        ).strip()
        connection = await psycopg.AsyncConnection.connect(dsn, autocommit=True, **kwargs)
        await check(connection)

    task = asyncio.create_task(run())
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=READINESS_TIMEOUT)
    finally:
        if connection is not None:
            # Closing libpq locally never waits for a remote rollback or cancellation.
            await connection.close()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
