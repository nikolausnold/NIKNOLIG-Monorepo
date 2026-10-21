"""Bounded PostgreSQL connections; no credentials or database details in responses."""

import asyncio
from contextlib import suppress
import os
from pathlib import Path

import psycopg


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


def connect():
    dsn, kwargs = connection_parameters()
    return psycopg.connect(dsn, **kwargs)


async def probe(check):
    connection = None

    async def run():
        nonlocal connection
        dsn, kwargs = connection_parameters()
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
