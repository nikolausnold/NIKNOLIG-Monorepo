"""Transactional, checksummed migrations; the proposed product schema stays opt-in."""

import argparse
import hashlib
import os
from pathlib import Path

from psycopg import sql

import database


MIGRATIONS = Path(__file__).resolve().parent / "migrations"
BASELINE = "000_health_runtime"
CONTRACT = "001_initial_contract"
LOCK_ID = 723046110

# PostgreSQL's canonical deparser output, not constraint names alone. Relation
# identity, type, validation and deferrability are checked separately below.
LEDGER_CONSTRAINTS = {
    ("backend_schema_migrations", "backend_schema_migrations_pkey"):
        ("p", "PRIMARY KEY (version)"),
    ("backend_schema_migrations", "backend_schema_migrations_checksum_check"):
        ("c", "CHECK (checksum ~ '^[0-9a-f]{64}$'::text)"),
}
CONTRACT_CONSTRAINTS = {
    ("device_installations", "device_installations_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_installations", "device_installations_area_installation_unique"):
        ("u", "UNIQUE (app_area, installation_reference)"),
    ("device_installations", "device_installations_id_area_unique"):
        ("u", "UNIQUE (id, app_area)"),
    ("device_installations", "device_installations_principal_not_empty"):
        ("c", "CHECK (length(btrim(principal_reference)) > 0)"),
    ("device_installations", "device_installations_fingerprint_format"):
        ("c", "CHECK (public_key_fingerprint IS NULL OR public_key_fingerprint ~ '^[0-9a-f]{64}$'::text)"),
    ("device_installations", "device_installations_verified_requires_key"):
        ("c", "CHECK (identity_state <> 'verified'::device_identity_state OR public_key_fingerprint IS NOT NULL)"),
    ("device_installations", "device_installations_verified_timestamp"):
        ("c", "CHECK ((identity_state <> 'verified'::device_identity_state OR verified_at IS NOT NULL) AND (identity_state <> 'pending'::device_identity_state OR verified_at IS NULL))"),
    ("device_installations", "device_installations_revoked_timestamp"):
        ("c", "CHECK ((identity_state = 'revoked'::device_identity_state) = (revoked_at IS NOT NULL))"),
    ("device_links", "device_links_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_links", "device_links_distinct_devices"):
        ("c", "CHECK (first_device_id <> second_device_id)"),
    ("device_links", "device_links_distinct_app_areas"):
        ("c", "CHECK (first_app_area <> second_app_area)"),
    ("device_links", "device_links_first_device_area"):
        ("f", "FOREIGN KEY (first_device_id, first_app_area) REFERENCES device_installations(id, app_area) ON DELETE RESTRICT"),
    ("device_links", "device_links_second_device_area"):
        ("f", "FOREIGN KEY (second_device_id, second_app_area) REFERENCES device_installations(id, app_area) ON DELETE RESTRICT"),
    ("device_links", "device_links_expiry_after_creation"):
        ("c", "CHECK (expires_at > created_at)"),
    ("device_links", "device_links_activation_timestamp"):
        ("c", "CHECK (state <> 'active'::device_link_state OR activated_at IS NOT NULL)"),
    ("device_links", "device_links_revocation_timestamp"):
        ("c", "CHECK (state <> 'revoked'::device_link_state OR revoked_at IS NOT NULL)"),
}
CONTRACT_INDEXES = {
    "device_installations_area_fingerprint_unique":
        ("device_installations", True, ["app_area", "public_key_fingerprint"],
         "(public_key_fingerprint IS NOT NULL)"),
    "device_links_first_device_idx": ("device_links", False, ["first_device_id"], None),
    "device_links_second_device_idx": ("device_links", False, ["second_device_id"], None),
}
INDEX_SEMANTICS = """
    AND NOT i.indnullsnotdistinct
    AND NOT EXISTS (
        SELECT 1 FROM unnest(
            i.indkey::smallint[], i.indcollation::oid[],
            i.indclass::oid[], i.indoption::smallint[]
        ) AS key(attnum, coll_oid, opclass_oid, options)
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = key.attnum
        JOIN pg_opclass op ON op.oid = key.opclass_oid
        WHERE key.coll_oid <> a.attcollation OR NOT op.opcdefault OR key.options <> 0
    )
"""


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


def _constraint_checks(expected, message):
    rows = yield (
        "SELECT r.relname, c.conname, c.contype, pg_get_constraintdef(c.oid, true) "
        "FROM pg_constraint c JOIN pg_class r ON r.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = r.relnamespace "
        "LEFT JOIN pg_index i ON i.indexrelid = c.conindid "
        "WHERE n.nspname = 'public' AND c.convalidated "
        "AND NOT c.condeferrable AND NOT c.condeferred "
        "AND (c.contype <> 'c' OR NOT c.connoinherit) "
        "AND r.relkind = 'r' AND "
        "(c.contype NOT IN ('p', 'u') OR "
        "(i.indrelid = r.oid AND i.indisunique AND i.indisvalid AND i.indisready "
        "AND i.indimmediate AND i.indpred IS NULL AND i.indexprs IS NULL "
        + INDEX_SEMANTICS + "))"
    )
    actual = {(table, name): (kind, definition) for table, name, kind, definition in rows}
    if any(actual.get(key) != value for key, value in expected.items()):
        raise RuntimeError(message)


def _contract_checks(applied):
    rows = yield (
        "SELECT name, to_regclass('public.' || name) IS NOT NULL FROM "
        "(VALUES ('device_installations'), ('device_links')) AS objects(name)"
    )
    if [exists for _, exists in rows] != [applied, applied]:
        raise RuntimeError("Product schema does not match migration history")
    enums = yield (
        "SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) "
        "FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "JOIN pg_enum e ON e.enumtypid = t.oid WHERE n.nspname = 'public' "
        "AND t.typname IN ('app_area', 'device_identity_state', 'device_link_state') "
        "GROUP BY t.typname ORDER BY t.typname"
    )
    expected_enums = [
        ("app_area", ["niknolig", "niknolig-defense"]),
        ("device_identity_state", ["pending", "verified", "revoked"]),
        ("device_link_state", ["pending", "active", "revoked", "expired"]),
    ]
    if enums != (expected_enums if applied else []):
        raise RuntimeError("Product enum invariants do not match migration history")
    if not applied:
        return
    yield from _constraint_checks(CONTRACT_CONSTRAINTS, "Required contract constraints have drifted")
    indexes = yield (
        "SELECT idx.relname, tab.relname, i.indisunique, "
        "ARRAY(SELECT pg_get_indexdef(i.indexrelid, k, true) "
        "FROM generate_series(1, i.indnkeyatts) k ORDER BY k), "
        "pg_get_expr(i.indpred, i.indrelid) "
        "FROM pg_index i JOIN pg_class idx ON idx.oid = i.indexrelid "
        "JOIN pg_class tab ON tab.oid = i.indrelid "
        "JOIN pg_namespace n ON n.oid = idx.relnamespace "
        "JOIN pg_namespace tn ON tn.oid = tab.relnamespace "
        "JOIN pg_am am ON am.oid = idx.relam "
        "WHERE n.nspname = 'public' AND tn.nspname = 'public' "
        "AND tab.relkind = 'r' AND am.amname = 'btree' "
        "AND i.indisvalid AND i.indisready AND i.indimmediate "
        "AND i.indnatts = i.indnkeyatts AND i.indexprs IS NULL"
        + INDEX_SEMANTICS
    )
    actual = {name: (table, unique, columns, predicate)
              for name, table, unique, columns, predicate in indexes}
    if any(actual.get(name) != value for name, value in CONTRACT_INDEXES.items()):
        raise RuntimeError("Required contract indexes have drifted")


def _readiness_checks():
    if (yield "SELECT 1") != [(1,)]:
        raise RuntimeError("Database probe failed")
    records = yield "SELECT version, checksum FROM public.backend_schema_migrations ORDER BY version"
    _check_records(records)
    yield from _constraint_checks(LEDGER_CONSTRAINTS, "Migration ledger invariants have drifted")
    yield from _contract_checks(len(records) == 2)


def _run_checks(connection, checks):
    rows = None
    while True:
        try:
            query = checks.send(rows)
        except StopIteration:
            return
        rows = connection.execute(query).fetchall()


def _check_contract_invariants(connection, applied):
    _run_checks(connection, _contract_checks(applied))


def check_ready(connection):
    _run_checks(connection, _readiness_checks())


async def check_ready_async(connection):
    await _run_checks_async(connection, _readiness_checks())


async def _run_checks_async(connection, checks):
    rows = None
    while True:
        try:
            query = checks.send(rows)
        except StopIteration:
            return
        cursor = await connection.execute(query)
        rows = await cursor.fetchall()


def _health_role_checks():
    rows = yield """
        SELECT EXISTS (
            SELECT 1 FROM pg_roles r WHERE r.rolname = 'backend_health' AND (
                r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
                OR r.rolbypassrls
                OR EXISTS (SELECT 1 FROM pg_auth_members m
                           WHERE m.member = r.oid OR m.roleid = r.oid)
                OR EXISTS (SELECT 1 FROM pg_db_role_setting s WHERE s.setrole = r.oid)
                OR EXISTS (
                    SELECT 1 FROM pg_shdepend d
                    WHERE d.refclassid = 'pg_authid'::regclass AND d.refobjid = r.oid
                    AND NOT (
                        d.deptype = 'a' AND d.objsubid = 0 AND (
                            (d.classid = 'pg_database'::regclass
                             AND d.objid = (SELECT oid FROM pg_database
                                           WHERE datname = current_database()))
                            OR (d.dbid = (SELECT oid FROM pg_database
                                          WHERE datname = current_database()) AND (
                                (d.classid = 'pg_class'::regclass
                                 AND d.objid = 'public.backend_schema_migrations'::regclass)
                                OR (d.classid = 'pg_namespace'::regclass
                                    AND d.objid = 'public'::regnamespace)
                            ))
                        )
                    )
                )
            )
        ) OR EXISTS (
            SELECT 1 FROM (
                SELECT 'SELECT' AS allowed, relacl AS acl FROM pg_class
                WHERE oid = 'public.backend_schema_migrations'::regclass
                UNION ALL
                SELECT 'USAGE', nspacl FROM pg_namespace WHERE nspname = 'public'
                UNION ALL
                SELECT 'CONNECT', datacl FROM pg_database WHERE datname = current_database()
            ) objects CROSS JOIN LATERAL aclexplode(objects.acl) a
            JOIN pg_roles r ON r.oid = a.grantee
            WHERE r.rolname = 'backend_health'
              AND (a.privilege_type <> objects.allowed OR a.is_grantable)
        )
    """
    if rows != [(False,)]:
        raise RuntimeError("Existing health role has unexpected privileges, ownership or memberships")
    # PUBLIC grants are inherited even by NOINHERIT roles.
    rows = yield """
        SELECT has_schema_privilege('backend_health', 'public', 'CREATE')
        OR EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
            AND (
                has_table_privilege('backend_health', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                OR has_any_column_privilege('backend_health', c.oid, 'INSERT,UPDATE,REFERENCES')
                OR (c.oid <> 'public.backend_schema_migrations'::regclass
                    AND has_any_column_privilege('backend_health', c.oid, 'SELECT'))
            )
        )
    """
    if rows != [(False,)]:
        raise RuntimeError("Health role has unexpected effective schema or table privileges")


def _check_health_role(connection):
    _run_checks(connection, _health_role_checks())


async def check_health_ready_async(connection):
    cursor = await connection.execute("SELECT current_user, session_user")
    if await cursor.fetchall() != [("backend_health", "backend_health")]:
        raise RuntimeError("Health runtime requires the dedicated health login")
    await _run_checks_async(connection, _health_role_checks())
    await check_ready_async(connection)


def _configure_health_role(connection, secret_path):
    if not secret_path:
        return
    password = database.read_secret(secret_path)
    # libpq has already resolved keyword overrides, URL, environment and passfile.
    admin_password = connection.info.password
    if not admin_password:
        raise ValueError("Effective migration database password is unavailable")
    if password == admin_password:
        raise ValueError("Health and migration database credentials must differ")
    role = sql.Identifier("backend_health")
    if not connection.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = 'backend_health'"
    ).fetchone():
        connection.execute(sql.SQL("CREATE ROLE {}").format(role))
    _check_health_role(connection)
    connection.execute(
        sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}").format(
                    role, sql.Literal(password)
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
