"""Transactional, checksummed migrations; the proposed product schema stays opt-in."""

import argparse
import hashlib
import os
from pathlib import Path
import re

from psycopg import sql

import database


MIGRATIONS = Path(__file__).resolve().parent / "migrations"
BASELINE = "000_health_runtime"
CONTRACT = "001_initial_contract"
LOCK_ID = 723046110


def migration_text(version):
    return (MIGRATIONS / f"{version}.sql").read_text(encoding="utf-8")


def checksum(version):
    return hashlib.sha256(migration_text(version).encode("utf-8")).hexdigest()


def _records(connection):
    return connection.execute(
        "SELECT version, checksum FROM public.backend_schema_migrations ORDER BY version"
    ).fetchall()


def _check_records(records):
    baseline = [(BASELINE, checksum(BASELINE))]
    if records not in (baseline, baseline + [(CONTRACT, checksum(CONTRACT))]):
        raise RuntimeError("Unknown, incomplete or changed migration history")


def _check_contract_invariants(connection, applied):
    rows = connection.execute(
        "SELECT name, to_regclass('public.' || name) IS NOT NULL FROM "
        "(VALUES ('device_installations'), ('device_links')) AS objects(name)"
    ).fetchall()
    if [exists for _, exists in rows] != [applied, applied]:
        raise RuntimeError("Product schema does not match migration history")
    enums = connection.execute(
        "SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) "
        "FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "JOIN pg_enum e ON e.enumtypid = t.oid WHERE n.nspname = 'public' "
        "AND t.typname IN ('app_area', 'device_identity_state', 'device_link_state') "
        "GROUP BY t.typname ORDER BY t.typname"
    ).fetchall()
    expected_enums = [
        ("app_area", ["niknolig", "niknolig-defense"]),
        ("device_identity_state", ["pending", "verified", "revoked"]),
        ("device_link_state", ["pending", "active", "revoked", "expired"]),
    ]
    if enums != (expected_enums if applied else []):
        raise RuntimeError("Product enum invariants do not match migration history")
    if not applied:
        return
    required = set(re.findall(r"\bCONSTRAINT\s+(\w+)", migration_text(CONTRACT)))
    constraints = connection.execute(
        "SELECT c.conname FROM pg_constraint c JOIN pg_class r ON r.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = r.relnamespace WHERE n.nspname = 'public' "
        "AND r.relname IN ('device_installations', 'device_links') AND c.convalidated"
    ).fetchall()
    if not required.issubset({name for name, in constraints}):
        raise RuntimeError("Required contract constraints are missing or unvalidated")
    indexes = connection.execute(
        "SELECT r.relname FROM pg_index i JOIN pg_class r ON r.oid = i.indexrelid "
        "JOIN pg_namespace n ON n.oid = r.relnamespace "
        "WHERE n.nspname = 'public' AND i.indisvalid AND i.indisready"
    ).fetchall()
    required_indexes = set(re.findall(r"\bCREATE (?:UNIQUE )?INDEX\s+(\w+)", migration_text(CONTRACT)))
    if not required_indexes.issubset({name for name, in indexes}):
        raise RuntimeError("Required contract indexes are missing or invalid")


def check_ready(connection):
    if connection.execute("SELECT 1").fetchone() != (1,):
        raise RuntimeError("Database probe failed")
    records = _records(connection)
    _check_records(records)
    _check_contract_invariants(connection, len(records) == 2)


def _configure_health_role(connection, secret_path):
    if not secret_path:
        return
    role = sql.Identifier("backend_health")
    if not connection.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = 'backend_health'"
    ).fetchone():
        connection.execute(sql.SQL("CREATE ROLE {}").format(role))
    connection.execute(
        sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOINHERIT PASSWORD {}").format(
                    role, sql.Literal(database.read_secret(secret_path))
                )
    )
    name = connection.execute("SELECT current_database()").fetchone()[0]
    connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
        sql.Identifier(name), role
    ))
    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    connection.execute(sql.SQL(
        "GRANT SELECT ON public.backend_schema_migrations TO {}"
    ).format(role))


def migrate(connection, *, approve_contract=False, health_secret_path=None):
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        connection.execute(migration_text(BASELINE))
        records = _records(connection)
        if not records:
            _check_contract_invariants(connection, False)
            connection.execute(
                "INSERT INTO public.backend_schema_migrations(version, checksum) VALUES (%s, %s)",
                (BASELINE, checksum(BASELINE)),
            )
            records = _records(connection)
        _check_records(records)
        _check_contract_invariants(connection, len(records) == 2)
        if approve_contract and len(records) == 1:
            # Keep the original SQL unchanged but let the outer transaction own atomicity.
            text = migration_text(CONTRACT)
            before, separator, body = text.partition("BEGIN;")
            body, end, after = body.rpartition("COMMIT;")
            if not separator or not end or after.strip():
                raise RuntimeError("Migration transaction envelope changed")
            connection.execute(body)
            connection.execute(
                "INSERT INTO public.backend_schema_migrations(version, checksum) VALUES (%s, %s)",
                (CONTRACT, checksum(CONTRACT)),
            )
        check_ready(connection)
        _configure_health_role(connection, health_secret_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approve-contract-schema", action="store_true",
        help="Apply 001 only AFTER actual architecture/security/data-model approval; not a P0 approval",
    )
    args = parser.parse_args()
    try:
        with database.connect() as connection:
            migrate(
                connection,
                approve_contract=args.approve_contract_schema,
                health_secret_path=os.environ.get("HEALTH_DB_PASSWORD_FILE"),
            )
    except Exception:
        raise SystemExit("Migration failed; database unavailable, unapproved drift, or invalid history.") from None
    print("Health runtime migration complete. No product or SecurityChain-P0 approval is implied.")


if __name__ == "__main__":
    main()
