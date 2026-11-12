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
DEVICE_API = "002_device_api"
DEVICE_API_ROLE = "backend_device_api"
DEVICE_API_TABLES = (
    "device_installations", "device_links", "device_challenges", "device_sessions",
    "device_pairings", "device_grants", "device_status", "device_events",
    "device_refresh_history",
)
# Audit and token history are append-only for the API login; only challenges are pruned.
DEVICE_API_PRIVILEGES = {
    "device_events": "SELECT, INSERT",
    "device_refresh_history": "SELECT, INSERT",
    "device_challenges": "SELECT, INSERT, UPDATE, DELETE",
}
DEVICE_API_COLUMNS = {
    ("device_installations", "public_key"): ("bytea", "YES", "NO"),
    ("device_installations", "display_name"): ("text", "YES", "NO"),
    ("device_challenges", "nonce_hash"): ("bytea", "NO", "NO"),
    ("device_challenges", "device_id"): ("uuid", "NO", "NO"),
    ("device_challenges", "expires_at"): ("timestamptz", "NO", "NO"),
    ("device_challenges", "used_at"): ("timestamptz", "YES", "NO"),
    ("device_challenges", "created_at"): ("timestamptz", "NO", "NO"),
    ("device_sessions", "id"): ("uuid", "NO", "NO"),
    ("device_sessions", "device_id"): ("uuid", "NO", "NO"),
    ("device_sessions", "refresh_hash"): ("bytea", "NO", "NO"),
    ("device_sessions", "expires_at"): ("timestamptz", "NO", "NO"),
    ("device_sessions", "created_at"): ("timestamptz", "NO", "NO"),
    ("device_sessions", "rotated_at"): ("timestamptz", "YES", "NO"),
    ("device_sessions", "revoked_at"): ("timestamptz", "YES", "NO"),
    ("device_sessions", "revoke_reason"): ("text", "YES", "NO"),
    ("device_refresh_history", "refresh_hash"): ("bytea", "NO", "NO"),
    ("device_refresh_history", "session_id"): ("uuid", "NO", "NO"),
    ("device_refresh_history", "consumed_at"): ("timestamptz", "NO", "NO"),
    ("device_pairings", "id"): ("uuid", "NO", "NO"),
    ("device_pairings", "initiator_device_id"): ("uuid", "NO", "NO"),
    ("device_pairings", "claimant_device_id"): ("uuid", "YES", "NO"),
    ("device_pairings", "code_hash"): ("bytea", "NO", "NO"),
    ("device_pairings", "state"): ("text", "NO", "NO"),
    ("device_pairings", "initiator_confirmed_at"): ("timestamptz", "YES", "NO"),
    ("device_pairings", "claimant_confirmed_at"): ("timestamptz", "YES", "NO"),
    ("device_pairings", "link_id"): ("uuid", "YES", "NO"),
    ("device_pairings", "expires_at"): ("timestamptz", "NO", "NO"),
    ("device_pairings", "created_at"): ("timestamptz", "NO", "NO"),
    ("device_grants", "id"): ("uuid", "NO", "NO"),
    ("device_grants", "link_id"): ("uuid", "NO", "NO"),
    ("device_grants", "grantor_device_id"): ("uuid", "NO", "NO"),
    ("device_grants", "grantee_device_id"): ("uuid", "NO", "NO"),
    ("device_grants", "scope"): ("text", "NO", "NO"),
    ("device_grants", "expires_at"): ("timestamptz", "NO", "NO"),
    ("device_grants", "created_at"): ("timestamptz", "NO", "NO"),
    ("device_grants", "revoked_at"): ("timestamptz", "YES", "NO"),
    ("device_status", "device_id"): ("uuid", "NO", "NO"),
    ("device_status", "state"): ("text", "NO", "NO"),
    ("device_status", "detail"): ("text", "YES", "NO"),
    ("device_status", "reported_at"): ("timestamptz", "NO", "NO"),
    ("device_events", "id"): ("int8", "NO", "YES"),
    ("device_events", "device_id"): ("uuid", "NO", "NO"),
    ("device_events", "source_device_id"): ("uuid", "YES", "NO"),
    ("device_events", "link_id"): ("uuid", "YES", "NO"),
    ("device_events", "kind"): ("text", "NO", "NO"),
    ("device_events", "detail"): ("text", "YES", "NO"),
    ("device_events", "created_at"): ("timestamptz", "NO", "NO"),
}
DEVICE_API_DEFAULTS = {
    ("device_challenges", "created_at"): "now()",
    ("device_sessions", "created_at"): "now()",
    ("device_refresh_history", "consumed_at"): "now()",
    ("device_pairings", "state"): "'open'::text",
    ("device_pairings", "created_at"): "now()",
    ("device_grants", "created_at"): "now()",
    ("device_status", "reported_at"): "now()",
    ("device_events", "created_at"): "now()",
}
DEVICE_API_CONSTRAINTS = {
    ("device_installations", "device_installations_public_key_length"):
        ("c", "CHECK (public_key IS NULL OR octet_length(public_key) = 32)"),
    ("device_installations", "device_installations_display_name_length"):
        ("c", "CHECK (display_name IS NULL OR length(display_name) >= 1 AND length(display_name) <= 64)"),
    ("device_challenges", "device_challenges_pkey"): ("p", "PRIMARY KEY (nonce_hash)"),
    ("device_challenges", "device_challenges_device_id_fkey"):
        ("f", "FOREIGN KEY (device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_sessions", "device_sessions_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_sessions", "device_sessions_device_id_fkey"):
        ("f", "FOREIGN KEY (device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_sessions", "device_sessions_refresh_hash_key"): ("u", "UNIQUE (refresh_hash)"),
    ("device_sessions", "device_sessions_reason_requires_revocation"):
        ("c", "CHECK ((revoked_at IS NULL) = (revoke_reason IS NULL))"),
    ("device_refresh_history", "device_refresh_history_pkey"):
        ("p", "PRIMARY KEY (refresh_hash)"),
    ("device_refresh_history", "device_refresh_history_session_id_fkey"):
        ("f", "FOREIGN KEY (session_id) REFERENCES device_sessions(id) ON DELETE RESTRICT"),
    ("device_pairings", "device_pairings_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_pairings", "device_pairings_initiator_device_id_fkey"):
        ("f", "FOREIGN KEY (initiator_device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_pairings", "device_pairings_claimant_device_id_fkey"):
        ("f", "FOREIGN KEY (claimant_device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_pairings", "device_pairings_link_id_fkey"):
        ("f", "FOREIGN KEY (link_id) REFERENCES device_links(id) ON DELETE RESTRICT"),
    ("device_pairings", "device_pairings_state_check"):
        ("c", "CHECK (state = ANY (ARRAY['open'::text, 'claimed'::text, 'confirmed'::text, 'cancelled'::text, 'expired'::text]))"),
    ("device_pairings", "device_pairings_distinct_devices"):
        ("c", "CHECK (claimant_device_id IS NULL OR claimant_device_id <> initiator_device_id)"),
    ("device_grants", "device_grants_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_grants", "device_grants_link_id_fkey"):
        ("f", "FOREIGN KEY (link_id) REFERENCES device_links(id) ON DELETE RESTRICT"),
    ("device_grants", "device_grants_grantor_device_id_fkey"):
        ("f", "FOREIGN KEY (grantor_device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_grants", "device_grants_grantee_device_id_fkey"):
        ("f", "FOREIGN KEY (grantee_device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_grants", "device_grants_scope_check"):
        ("c", "CHECK (scope = ANY (ARRAY['status:read'::text, 'events:read'::text, 'alerts:send'::text]))"),
    ("device_grants", "device_grants_distinct_devices"):
        ("c", "CHECK (grantor_device_id <> grantee_device_id)"),
    ("device_grants", "device_grants_expiry_after_creation"):
        ("c", "CHECK (expires_at > created_at)"),
    ("device_status", "device_status_pkey"): ("p", "PRIMARY KEY (device_id)"),
    ("device_status", "device_status_device_id_fkey"):
        ("f", "FOREIGN KEY (device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_status", "device_status_state_check"):
        ("c", "CHECK (state = ANY (ARRAY['ok'::text, 'warning'::text, 'alert'::text, 'unknown'::text]))"),
    ("device_status", "device_status_detail_check"):
        ("c", "CHECK (detail IS NULL OR length(detail) <= 200)"),
    ("device_events", "device_events_pkey"): ("p", "PRIMARY KEY (id)"),
    ("device_events", "device_events_device_id_fkey"):
        ("f", "FOREIGN KEY (device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_events", "device_events_source_device_id_fkey"):
        ("f", "FOREIGN KEY (source_device_id) REFERENCES device_installations(id) ON DELETE RESTRICT"),
    ("device_events", "device_events_link_id_fkey"):
        ("f", "FOREIGN KEY (link_id) REFERENCES device_links(id) ON DELETE RESTRICT"),
    ("device_events", "device_events_kind_check"):
        ("c", "CHECK (kind ~ '^[a-z_]{1,48}$'::text)"),
    ("device_events", "device_events_detail_check"):
        ("c", "CHECK (detail IS NULL OR length(detail) <= 200)"),
}
DEVICE_API_INDEXES = {
    "device_links_open_pair_unique":
        "CREATE UNIQUE INDEX device_links_open_pair_unique ON public.device_links USING btree "
        "(LEAST(first_device_id, second_device_id), GREATEST(first_device_id, second_device_id)) "
        "WHERE (state = ANY (ARRAY['pending'::device_link_state, 'active'::device_link_state]))",
    "device_challenges_expiry_idx":
        "CREATE INDEX device_challenges_expiry_idx ON public.device_challenges USING btree (expires_at)",
    "device_sessions_device_idx":
        "CREATE INDEX device_sessions_device_idx ON public.device_sessions USING btree (device_id)",
    "device_refresh_history_session_idx":
        "CREATE INDEX device_refresh_history_session_idx ON public.device_refresh_history USING btree (session_id)",
    "device_pairings_live_code_unique":
        "CREATE UNIQUE INDEX device_pairings_live_code_unique ON public.device_pairings USING btree "
        "(code_hash) WHERE (state = ANY (ARRAY['open'::text, 'claimed'::text]))",
    "device_pairings_initiator_idx":
        "CREATE INDEX device_pairings_initiator_idx ON public.device_pairings USING btree (initiator_device_id)",
    "device_grants_link_idx":
        "CREATE INDEX device_grants_link_idx ON public.device_grants USING btree (link_id)",
    "device_events_device_idx":
        "CREATE INDEX device_events_device_idx ON public.device_events USING btree (device_id, id DESC)",
}
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
    contract = baseline + [(CONTRACT, checksum(CONTRACT))]
    if records not in (baseline, contract, contract + [(DEVICE_API, checksum(DEVICE_API))]):
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


def _contract_checks(applied, device_api_applied=False):
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
    if device_api_applied:
        yield from _device_api_schema_checks()


def _device_api_schema_checks():
    tables = yield (
        "SELECT name, to_regclass('public.' || name) IS NOT NULL FROM "
        "(VALUES " + ", ".join(f"('{table}')" for table in DEVICE_API_TABLES) + ") AS objects(name)"
    )
    if any(not exists for _, exists in tables):
        raise RuntimeError("Required device API tables have drifted")
    columns = yield (
        "SELECT c.relname, a.attname, t.typname, "
        "CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END, "
        "CASE WHEN a.attidentity = 'a' THEN 'YES' ELSE 'NO' END, "
        "pg_get_expr(d.adbin, d.adrelid) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = c.oid JOIN pg_type t ON t.oid = a.atttypid "
        "LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum "
        "WHERE n.nspname = 'public' AND c.relname IN ("
        + ", ".join(f"'{table}'" for table in DEVICE_API_TABLES) + ") "
        "AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped"
    )
    actual_columns = {(table, column): (udt, nullable, identity)
                      for table, column, udt, nullable, identity, _ in columns}
    if any(actual_columns.get(key) != value for key, value in DEVICE_API_COLUMNS.items()):
        raise RuntimeError("Required device API columns have drifted")
    actual_defaults = {(table, column): default for table, column, _, _, _, default in columns}
    if any(actual_defaults.get(key) != value for key, value in DEVICE_API_DEFAULTS.items()):
        raise RuntimeError("Required device API column defaults have drifted")
    constraints = yield (
        "SELECT r.relname, c.conname, c.contype, pg_get_constraintdef(c.oid, true) "
        "FROM pg_constraint c "
        "JOIN pg_class r ON r.oid = c.conrelid JOIN pg_namespace n ON n.oid = r.relnamespace "
        "WHERE n.nspname = 'public' AND r.relkind = 'r' AND c.convalidated "
        "AND NOT c.condeferrable AND NOT c.condeferred AND c.conname IN ("
        + ", ".join(f"'{name}'" for _, name in DEVICE_API_CONSTRAINTS) + ")"
    )
    actual_constraints = {(table, name): (kind, definition)
                          for table, name, kind, definition in constraints}
    if any(actual_constraints.get(key) != expected
           for key, expected in DEVICE_API_CONSTRAINTS.items()):
        raise RuntimeError("Required device API constraints have drifted")
    indexes = yield (
        "SELECT idx.relname, pg_get_indexdef(i.indexrelid), i.indisvalid, "
        "i.indisready, i.indimmediate, am.amname "
        "FROM pg_index i JOIN pg_class idx ON idx.oid = i.indexrelid "
        "JOIN pg_namespace n ON n.oid = idx.relnamespace JOIN pg_am am ON am.oid = idx.relam "
        "WHERE n.nspname = 'public' AND idx.relname IN ("
        + ", ".join(f"'{name}'" for name in DEVICE_API_INDEXES) + ")"
    )
    actual_indexes = {
        name: definition
        for name, definition, valid, ready, immediate, method in indexes
        if valid and ready and immediate and method == "btree"
    }
    if any(actual_indexes.get(name) != expected
           for name, expected in DEVICE_API_INDEXES.items()):
        raise RuntimeError("Required device API indexes have drifted")


def _readiness_checks():
    if (yield "SELECT 1") != [(1,)]:
        raise RuntimeError("Database probe failed")
    records = yield "SELECT version, checksum FROM public.backend_schema_migrations ORDER BY version"
    _check_records(records)
    yield from _constraint_checks(LEDGER_CONSTRAINTS, "Migration ledger invariants have drifted")
    yield from _contract_checks(len(records) >= 2, len(records) == 3)


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


def _apply_script(connection, version):
    # Keep the original SQL unchanged but let the outer transaction own atomicity.
    before, separator, body = migration_text(version).partition("BEGIN;")
    body, end, after = body.rpartition("COMMIT;")
    if not separator or not end or after.strip():
        raise RuntimeError("Migration transaction envelope changed")
    connection.execute(body)
    connection.execute(
        "INSERT INTO public.backend_schema_migrations(version, checksum) VALUES (%s, %s)",
        (version, checksum(version)),
    )


def _device_api_role_checks():
    rows = yield (
        "SELECT EXISTS (SELECT 1 FROM pg_roles r WHERE r.rolname = 'backend_device_api' AND ("
        "r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls "
        "OR EXISTS (SELECT 1 FROM pg_auth_members m WHERE m.member = r.oid OR m.roleid = r.oid) "
        "OR EXISTS (SELECT 1 FROM pg_db_role_setting s WHERE s.setrole = r.oid) "
        "OR EXISTS (SELECT 1 FROM pg_shdepend d WHERE d.refclassid = 'pg_authid'::regclass "
        "AND d.refobjid = r.oid AND d.deptype = 'o')))"
    )
    if rows != [(False,)]:
        raise RuntimeError("Existing device API role has unexpected ownership, memberships or attributes")


def _device_api_effective_privilege_checks(*, require_complete=True):
    # Includes privileges inherited from PUBLIC.
    rows = yield (
        "SELECT c.relname, c.relkind, "
        "has_table_privilege('backend_device_api', c.oid, 'SELECT') AS can_select, "
        "has_table_privilege('backend_device_api', c.oid, 'INSERT') AS can_insert, "
        "has_table_privilege('backend_device_api', c.oid, 'UPDATE') AS can_update, "
        "has_table_privilege('backend_device_api', c.oid, 'DELETE') AS can_delete, "
        "has_table_privilege('backend_device_api', c.oid, 'TRUNCATE,REFERENCES,TRIGGER') AS can_admin, "
        "((has_any_column_privilege('backend_device_api', c.oid, 'SELECT') "
        "AND NOT has_table_privilege('backend_device_api', c.oid, 'SELECT')) "
        "OR (has_any_column_privilege('backend_device_api', c.oid, 'INSERT') "
        "AND NOT has_table_privilege('backend_device_api', c.oid, 'INSERT')) "
        "OR (has_any_column_privilege('backend_device_api', c.oid, 'UPDATE') "
        "AND NOT has_table_privilege('backend_device_api', c.oid, 'UPDATE')) "
        "OR (has_any_column_privilege('backend_device_api', c.oid, 'REFERENCES') "
        "AND NOT has_table_privilege('backend_device_api', c.oid, 'REFERENCES'))) AS extra_column_privilege "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')"
    )
    expected = {
        table: {"select", "insert", "update", "delete"} & {
            word.strip().lower() for word in DEVICE_API_PRIVILEGES.get(table, "SELECT, INSERT, UPDATE").split(",")
        }
        for table in DEVICE_API_TABLES
    }
    for (name, kind, can_select, can_insert, can_update, can_delete,
         can_admin, extra_column_privilege) in rows:
        actual = {label for label, flag in (
            ("select", can_select), ("insert", can_insert),
            ("update", can_update), ("delete", can_delete)) if flag}
        expected_privileges = expected.get(name, set())
        if (can_admin or extra_column_privilege or kind != "r"
                or not actual <= expected_privileges
                or (require_complete and actual != expected_privileges)):
            raise RuntimeError("Device API role has unexpected effective table privileges")
    rows = yield "SELECT has_schema_privilege('backend_device_api', 'public', 'CREATE')"
    if rows != [(False,)]:
        raise RuntimeError("Device API role may create objects")


def check_device_api_ready(connection):
    identity = connection.execute("SELECT current_user, session_user").fetchone()
    if identity != (DEVICE_API_ROLE, DEVICE_API_ROLE):
        raise RuntimeError("Device API runtime requires the dedicated device API login")
    _run_checks(connection, _device_api_role_checks())
    _run_checks(connection, _device_api_effective_privilege_checks())
    _run_checks(connection, _device_api_schema_checks())


def _configure_device_api_role(connection, secret_path):
    """Least-privilege login for the device API; refuses pre-existing privileged roles."""
    if not secret_path:
        return
    password = database.read_secret(secret_path)
    if password == connection.info.password:
        raise ValueError("Device API and migration database credentials must differ")
    role = sql.Identifier(DEVICE_API_ROLE)
    if not connection.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s", (DEVICE_API_ROLE,)
    ).fetchone():
        connection.execute(sql.SQL("CREATE ROLE {}").format(role))
    _run_checks(connection, _device_api_role_checks())
    _run_checks(connection, _device_api_effective_privilege_checks(require_complete=False))
    connection.execute(
        sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}").format(
                    role, sql.Literal(password)))
    name = connection.execute("SELECT current_database()").fetchone()[0]
    connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
        sql.Identifier(name), role))
    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    for table in DEVICE_API_TABLES:
        connection.execute(sql.SQL("REVOKE ALL ON public.{} FROM {}").format(
            sql.Identifier(table), role))
        privileges = DEVICE_API_PRIVILEGES.get(table, "SELECT, INSERT, UPDATE")
        connection.execute(sql.SQL("GRANT " + privileges + " ON public.{} TO {}").format(
            sql.Identifier(table), role))
    _run_checks(connection, _device_api_effective_privilege_checks())


def migrate(connection, *, approve_contract=False, health_secret_path=None,
            approve_device_api=False, device_api_secret_path=None):
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
        _check_contract_invariants(connection, len(records) >= 2)
        if approve_contract and len(records) == 1:
            _apply_script(connection, CONTRACT)
            records = _records(connection)
        if approve_device_api:
            if len(records) < 2:
                raise RuntimeError("Device API schema requires the approved contract schema")
            if len(records) == 2:
                _apply_script(connection, DEVICE_API)
                records = _records(connection)
        check_ready(connection)
        _configure_health_role(connection, health_secret_path)
        if len(records) == 3:
            _configure_device_api_role(connection, device_api_secret_path)


def _nonempty_file(path):
    return path if path and os.path.getsize(path) > 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approve-contract-schema", action="store_true",
        help="Apply 001 only AFTER actual architecture/security/data-model approval; not a P0 approval",
    )
    parser.add_argument(
        "--approve-device-api-schema", action="store_true",
        help="Apply 002 (device pairing/session API) after 001; requires release approval",
    )
    args = parser.parse_args()
    try:
        with database.connect() as connection:
            migrate(
                connection,
                approve_contract=args.approve_contract_schema,
                health_secret_path=os.environ.get("HEALTH_DB_PASSWORD_FILE"),
                approve_device_api=args.approve_device_api_schema
                or os.environ.get("APPROVE_DEVICE_API_SCHEMA") == "1",
                device_api_secret_path=_nonempty_file(os.environ.get("DEVICE_API_DB_PASSWORD_FILE")),
            )
    except Exception:
        raise SystemExit("Migration failed; database unavailable, unapproved drift, or invalid history.") from None
    print("Health runtime migration complete. No product or SecurityChain-P0 approval is implied.")


if __name__ == "__main__":
    main()
