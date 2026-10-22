import asyncio
from contextlib import redirect_stderr
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import socket
import select
import sys
import threading
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg
import uvicorn


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import database
import deployment
import migrate
from asgi import _check_database, app as production_app, create_app


class ProductionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = AsyncMock()
        cls.application = create_app(readiness_probe=cls.factory)
        cls.socket = socket.socket()
        cls.socket.bind(("127.0.0.1", 0))
        cls.url = f"http://127.0.0.1:{cls.socket.getsockname()[1]}"
        cls.server = uvicorn.Server(uvicorn.Config(
            cls.application, log_level="critical", access_log=False,
        ))
        cls.thread = threading.Thread(
            target=cls.server.run, kwargs={"sockets": [cls.socket]}, daemon=True,
        )
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(0.02)
        if not cls.server.started:
            raise RuntimeError("ASGI test server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.socket.close()
        if cls.thread.is_alive():
            raise RuntimeError("ASGI test server did not stop")

    def setUp(self):
        self.factory.reset_mock(side_effect=True)
        self.factory.return_value = None

    def test_exported_production_entrypoint_registers_contract_health_routes(self):
        health_routes = {
            (route.path, method)
            for route in production_app.routes
            for method in route.methods or ()
            if route.path.startswith("/health/")
        }
        self.assertEqual(
            {("/health/live", "GET"), ("/health/ready", "GET")},
            health_routes,
        )

    def test_production_api_service_builds_and_runs_the_exported_asgi_app(self):
        dockerfile = (BACKEND / "Dockerfile").read_text()
        compose = (BACKEND / "compose.production.yaml").read_text()
        self.assertIn("COPY asgi.py", dockerfile)
        self.assertIn('CMD ["uvicorn", "asgi:app"', dockerfile)
        self.assertIn("api:", compose)
        self.assertIn("build:", compose)
        self.assertIn("context: .", compose)

    def request(self, path, method="GET"):
        try:
            response = urlopen(Request(self.url + path, method=method), timeout=5)
        except HTTPError as response_error:
            response = response_error
        with response:
            self.assertEqual("no-store", response.headers["Cache-Control"])
            self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
            return response.status, json.load(response)

    def test_liveness_never_needs_database(self):
        self.factory.side_effect = RuntimeError("secret database address")
        self.assertEqual((200, {"status": "live"}), self.request("/health/live"))
        self.factory.assert_not_called()

    def test_legacy_health_metadata_matches_production_without_database(self):
        self.factory.side_effect = RuntimeError("unavailable database")
        self.assertEqual(
            (200, {"status": "ok", "service": "NOLD API", "version": "0.2.0"}),
            self.request("/health"),
        )
        self.assertEqual("NOLD API", production_app.title)
        self.assertEqual("0.2.0", production_app.version)
        self.factory.assert_not_called()

    def test_project_catalog_matches_production_without_configuration_or_database(self):
        self.factory.side_effect = RuntimeError("unavailable database")
        self.assertEqual(
            (200, {"projects": ["niknolig", "defense", "monorepo"]}),
            self.request("/projects"),
        )
        self.factory.assert_not_called()

    def test_database_health_checks_connectivity_without_migration_requirement(self):
        self.assertEqual(
            (200, {"status": "ok", "service": "NOLD PostgreSQL"}),
            self.request("/db/health"),
        )
        self.factory.assert_awaited_once_with(_check_database)

    def test_database_connectivity_check_executes_and_fetches_select_one(self):
        connection = AsyncMock()
        cursor = connection.execute.return_value
        asyncio.run(_check_database(connection))
        connection.execute.assert_awaited_once_with("SELECT 1")
        cursor.fetchone.assert_awaited_once_with()

    def test_database_health_failure_is_generic_and_keeps_liveness_available(self):
        for failure in (
            psycopg.OperationalError("private connection details"),
            TimeoutError("private connection details"),
            ValueError("private connection details"),
        ):
            with self.subTest(failure=type(failure).__name__):
                self.factory.side_effect = failure
                self.assertEqual(
                    (503, {"detail": "database_unavailable"}),
                    self.request("/db/health"),
                )
                self.assertEqual(
                    (200, {"status": "live"}), self.request("/health/live"),
                )

    def test_compatibility_routes_do_not_enable_writes_or_project_upstream_access(self):
        for path, method in (
            ("/health", "POST"), ("/projects", "POST"), ("/db/health", "POST"),
            ("/projects/niknolig/health", "GET"),
            ("/projects/unknown/health", "GET"),
        ):
            with self.subTest(path=path, method=method):
                status, body = self.request(path, method)
                self.assertEqual(404, status)
                self.assertEqual("NOT_FOUND", body["error"]["code"])
        self.factory.assert_not_called()

    def test_readiness_checks_database_and_migration_invariants(self):
        self.assertEqual((200, {"status": "ready"}), self.request("/health/ready"))
        self.factory.assert_awaited_once_with(migrate.check_ready_async)

    def test_unavailable_database_returns_generic_503(self):
        self.factory.side_effect = psycopg.OperationalError("password and internal address")
        log = io.StringIO()
        with redirect_stderr(log):
            status, body = self.request("/health/ready")
        self.assertEqual(503, status)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
        self.assertNotIn("password", json.dumps(body))
        self.assertNotIn("internal address", json.dumps(body))
        self.assertEqual(
            {"event": "health_readiness_failed", "status": 503},
            json.loads(log.getvalue()),
        )
        self.assertNotIn("password", log.getvalue())
        self.assertNotIn("internal address", log.getvalue())

    def test_readiness_failure_stays_503_if_stderr_is_unavailable(self):
        self.factory.side_effect = psycopg.OperationalError("private details")
        with patch("asgi.sys.stderr") as stderr:
            stderr.write.side_effect = OSError("closed log stream")
            status, body = self.request("/health/ready")
        self.assertEqual(503, status)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])

    def test_missing_or_invalid_migration_returns_generic_503(self):
        for failure in (psycopg.errors.UndefinedTable("ledger"), RuntimeError("schema drift")):
            with self.subTest(failure=type(failure).__name__):
                self.factory.side_effect = failure
                status, body = self.request("/health/ready")
                self.assertEqual(503, status)
                self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
                self.assertNotIn(str(failure), json.dumps(body))

    def test_liveness_remains_responsive_during_concurrent_readiness_timeouts(self):
        async def stalled(check):
            await asyncio.sleep(0.3)
            raise TimeoutError("private database")

        self.factory.side_effect = stalled
        with ThreadPoolExecutor(max_workers=12) as pool:
            pending = [pool.submit(self.request, "/health/ready") for _ in range(12)]
            time.sleep(0.05)
            started = time.monotonic()
            self.assertEqual((200, {"status": "live"}), self.request("/health/live"))
            self.assertLess(time.monotonic() - started, 0.25)
            for result in pending:
                self.assertEqual(503, result.result()[0])

    def test_automatic_documentation_is_intentionally_disabled(self):
        self.assertIsNone(production_app.docs_url)
        self.assertIsNone(production_app.redoc_url)
        self.assertIsNone(production_app.openapi_url)

        for path in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                status, body = self.request(path)
                self.assertEqual(404, status)
                self.assertEqual("NOT_FOUND", body["error"]["code"])
        self.factory.assert_not_called()

    def test_no_ai_or_product_routes_even_with_enabling_environment(self):
        with patch.dict(os.environ, {"AI_ENABLED": "true", "SUPPORT_ENABLED": "true"}):
            for path, method in (
                ("/v1/ai/support", "POST"), ("/v1/devices", "GET"),
                ("/v1/pairing", "POST"), ("/health/ready/", "GET"),
                ("/health/live", "POST"),
            ):
                with self.subTest(path=path, method=method):
                    status, body = self.request(path, method)
                    self.assertEqual(404, status)
                    self.assertEqual("NOT_FOUND", body["error"]["code"])
        self.factory.assert_not_called()


class MigrationUnitTests(unittest.TestCase):
    def connection(self, records=None, applied=False):
        connection = MagicMock()
        records = records if records is not None else [(migrate.BASELINE, migrate.checksum(migrate.BASELINE))]

        def execute(statement, parameters=None):
            cursor = MagicMock()
            if statement == "SELECT 1":
                cursor.fetchall.return_value = [(1,)]
            elif "pg_get_constraintdef" in statement:
                cursor.fetchall.return_value = [
                    (table, name, kind, definition)
                    for (table, name), (kind, definition) in migrate.LEDGER_CONSTRAINTS.items()
                ]
            elif "SELECT version, checksum" in statement:
                cursor.fetchall.return_value = records
            elif "SELECT name, to_regclass" in statement:
                cursor.fetchall.return_value = [("device_installations", applied), ("device_links", applied)]
            elif "array_agg" in statement:
                cursor.fetchall.return_value = []
            return cursor

        connection.execute.side_effect = execute
        return connection

    def test_readiness_requires_select_and_checked_ledger(self):
        connection = self.connection()
        migrate.check_ready(connection)
        self.assertEqual("SELECT 1", connection.execute.call_args_list[0].args[0])
        self.assertTrue(any("SELECT version, checksum" in call.args[0] for call in connection.execute.call_args_list))

    def test_readiness_rejects_missing_unknown_or_changed_version(self):
        for records in (
            [], [("999_future", "0" * 64)],
            [(migrate.BASELINE, "0" * 64)],
            [(migrate.CONTRACT, migrate.checksum(migrate.CONTRACT))],
        ):
            with self.subTest(records=records), self.assertRaises(RuntimeError):
                migrate.check_ready(self.connection(records))

    def test_readiness_rejects_untracked_product_schema(self):
        with self.assertRaisesRegex(RuntimeError, "schema"):
            migrate.check_ready(self.connection(applied=True))

    def test_health_and_migration_passwords_must_differ(self):
        connection = MagicMock()
        connection.info.password = "same-test-value"
        with patch("database.read_secret", return_value="same-test-value"), self.assertRaisesRegex(
            ValueError, "must differ",
        ):
            migrate._configure_health_role(connection, "health-secret")

    def test_health_provisioning_fails_before_sql_when_effective_password_is_unavailable(self):
        for password in (None, ""):
            with self.subTest(value=password), patch(
                "database.read_secret", return_value="health-test-value",
            ):
                connection = MagicMock()
                connection.info.password = password
                with self.assertRaisesRegex(ValueError, "password is unavailable"):
                    migrate._configure_health_role(connection, "health-secret")
                connection.execute.assert_not_called()

    def test_migrate_defaults_to_baseline_and_takes_transaction_lock(self):
        connection = self.connection()
        migrate.migrate(connection)
        statements = [call.args[0] for call in connection.execute.call_args_list]
        self.assertTrue(any("pg_advisory_xact_lock" in statement for statement in statements))
        self.assertFalse(any("CREATE TYPE app_area" in statement for statement in statements))
        connection.transaction.assert_called_once()

    def test_invalid_history_rolls_back_transaction(self):
        connection = self.connection([("999_future", "0" * 64)])
        with self.assertRaises(RuntimeError):
            migrate.migrate(connection)
        self.assertIs(RuntimeError, connection.transaction.return_value.__exit__.call_args.args[0])

    def test_database_configuration_is_explicit_and_bounded(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            database.connect()
        with patch.dict(os.environ, {
            "PGHOST": "postgres", "PGDATABASE": "health", "PGUSER": "health",
            "PGPASSWORD_FILE": "operator-secret",
        }, clear=True), patch("database.read_secret", return_value="test-only"), patch("database.psycopg.connect") as connect:
            database.connect()
            self.assertEqual(3, connect.call_args.kwargs["connect_timeout"])
            self.assertIn("statement_timeout=2000", connect.call_args.kwargs["options"])
            self.assertEqual("test-only", connect.call_args.kwargs["password"])

    def test_effective_password_uses_url_env_and_file_override(self):
        from urllib.parse import urlencode
        url = "postgresql://admin@localhost/db?" + urlencode({"password": "url-value"})
        cases = [
            ({"DATABASE_URL": url}, "url-value"),
            ({"PGHOST": "localhost", "PGUSER": "admin", "PGDATABASE": "db",
              "PGPASSWORD": "env-value"}, "env-value"),
            ({"DATABASE_URL": url,
              "PGPASSWORD_FILE": "mock-only"}, "file-value"),
        ]
        for environment, expected in cases:
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True), patch(
                "database.read_secret", return_value="file-value",
            ):
                dsn, kwargs = database.connection_parameters()
                from psycopg.conninfo import conninfo_to_dict, make_conninfo
                resolved = conninfo_to_dict(make_conninfo(dsn, **kwargs))
                self.assertEqual(expected, resolved.get("password", os.environ.get("PGPASSWORD")))


class AsyncDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_deadline_closes_connection_before_cancelling_stalled_query(self):
        connection = AsyncMock()
        order = []

        async def close():
            order.append("closed")

        async def stalled(conn):
            try:
                await asyncio.Event().wait()
            finally:
                order.append("cancelled")

        connection.close.side_effect = close
        with patch("database.connection_parameters", return_value=("", {})), patch(
            "database.psycopg.AsyncConnection.connect", return_value=connection,
        ), patch("database.READINESS_TIMEOUT", 0.05):
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                await database.probe(stalled)
            self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(["closed", "cancelled"], order)

    async def test_deadline_also_bounds_connection_establishment(self):
        async def stalled(*args, **kwargs):
            await asyncio.Event().wait()

        with patch("database.connection_parameters", return_value=("", {})), patch(
            "database.psycopg.AsyncConnection.connect", side_effect=stalled,
        ), patch("database.READINESS_TIMEOUT", 0.05):
            with self.assertRaises(TimeoutError):
                await database.probe(migrate.check_ready_async)


class DeploymentTests(unittest.TestCase):
    def test_hostname_requires_exact_operator_confirmation(self):
        # Synthetic test input only: never supplied as a deployment default.
        self.assertEqual("api.real-owned-domain.de", deployment.validate_hostname(
            "api.real-owned-domain.de", "api.real-owned-domain.de",
        ))
        for host, confirmed in (
            ("", ""), ("api.real-owned-domain.de", ""), ("127.0.0.1", "127.0.0.1"),
            ("backend.invalid", "backend.invalid"), ("api.example.com", "api.example.com"),
            ("https://api.real-owned-domain.de", "https://api.real-owned-domain.de"),
            ("api.local", "api.local"), ("a.de\nmalicious", "a.de\nmalicious"),
            ("api.real-owned-domain.de", "different.de"),
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                deployment.validate_hostname(host, confirmed)

    def test_tls_requires_valid_matching_exact_san(self):
        current = time.time()
        cert = {
            "subjectAltName": (("DNS", "api.real-owned-domain.de"),),
            "notBefore": time.strftime("%b %d %H:%M:%S %Y GMT", time.gmtime(current - 60)),
            "notAfter": time.strftime("%b %d %H:%M:%S %Y GMT", time.gmtime(current + 60)),
        }
        with patch("deployment.ssl.SSLContext") as context, patch(
            "deployment.ssl._ssl._test_decode_cert", return_value=cert,
        ):
            deployment.validate_tls("api.real-owned-domain.de", "certificate", "key")
            context.return_value.load_cert_chain.assert_called_once_with("certificate", "key")
            with self.assertRaises(ValueError):
                deployment.validate_tls("different.de", "certificate", "key")
            with patch("deployment.time.time", return_value=current + 120), self.assertRaises(ValueError):
                deployment.validate_tls("api.real-owned-domain.de", "certificate", "key")

    def test_production_database_is_not_exposed_and_schema_opt_in_is_absent(self):
        compose = (BACKEND / "compose.production.yaml").read_text()
        self.assertEqual(1, compose.count("ports:"))
        self.assertIn('ports: ["443:443"]', compose)
        self.assertIn("condition: service_completed_successfully", compose)
        self.assertNotIn("--approve-contract-schema", compose)
        self.assertIn("PGUSER: backend_health", compose)
        self.assertIn("BACKEND_HOSTNAME_CONFIRMED:?", compose)


@unittest.skipUnless(os.environ.get("BACKEND_TEST_DATABASE_URL"), "explicit disposable PostgreSQL test database required")
class PostgreSQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = psycopg.connect(os.environ["BACKEND_TEST_DATABASE_URL"], autocommit=True)
        name = self.connection.execute("SELECT current_database()").fetchone()[0]
        if not name.endswith("_backend_test"):
            self.connection.close()
            raise RuntimeError("Integration tests require a disposable database ending in _backend_test")
        self.connection.execute("DROP SCHEMA public CASCADE")
        self.connection.execute("CREATE SCHEMA public")

    def tearDown(self):
        self.connection.close()

    def test_default_migration_is_repeatable_and_does_not_apply_product_schema(self):
        migrate.migrate(self.connection)
        migrate.migrate(self.connection)
        migrate.check_ready(self.connection)
        self.assertEqual([(migrate.BASELINE, migrate.checksum(migrate.BASELINE))], migrate._records(self.connection))
        self.assertIsNone(self.connection.execute("SELECT to_regclass('public.device_installations')").fetchone()[0])

    def test_unmigrated_database_is_unready(self):
        with self.assertRaises(psycopg.errors.UndefinedTable):
            migrate.check_ready(self.connection)

    def test_explicitly_approved_existing_contract_is_atomic_repeatable_and_checked(self):
        migrate.migrate(self.connection, approve_contract=True)
        migrate.migrate(self.connection, approve_contract=True)
        migrate.check_ready(self.connection)
        self.assertEqual(2, len(migrate._records(self.connection)))
        self.connection.execute("ALTER TABLE device_links DROP CONSTRAINT device_links_distinct_app_areas")
        with self.assertRaisesRegex(RuntimeError, "constraints"):
            migrate.check_ready(self.connection)

    def test_changed_checksum_fails_without_reapplying(self):
        migrate.migrate(self.connection)
        self.connection.execute("UPDATE backend_schema_migrations SET checksum = repeat('0', 64)")
        with self.assertRaises(RuntimeError):
            migrate.migrate(self.connection)
        with self.assertRaises(RuntimeError):
            migrate.check_ready(self.connection)

    def test_missing_ledger_constraint_is_unready(self):
        migrate.migrate(self.connection)
        self.connection.execute(
            "ALTER TABLE backend_schema_migrations DROP CONSTRAINT backend_schema_migrations_checksum_check"
        )
        with self.assertRaisesRegex(RuntimeError, "ledger invariants"):
            migrate.check_ready(self.connection)

    def test_both_inline_product_primary_keys_are_required(self):
        migrate.migrate(self.connection, approve_contract=True)
        for table in ("device_installations", "device_links"):
            with self.subTest(table=table), self.connection.transaction(force_rollback=True):
                self.connection.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_pkey")
                with self.assertRaisesRegex(RuntimeError, "constraints"):
                    migrate.check_ready(self.connection)

    def test_same_named_replacement_constraints_fail_closed(self):
        migrate.migrate(self.connection, approve_contract=True)
        replacements = [
            ("backend_schema_migrations", "backend_schema_migrations_checksum_check", "CHECK (true)"),
            ("backend_schema_migrations", "backend_schema_migrations_pkey", "CHECK (true)"),
            ("backend_schema_migrations", "backend_schema_migrations_pkey", "PRIMARY KEY (checksum)"),
            ("device_installations", "device_installations_pkey", "CHECK (true)"),
            ("device_links", "device_links_pkey", "PRIMARY KEY (first_device_id)"),
            ("device_installations", "device_installations_area_installation_unique",
             "UNIQUE (installation_reference)"),
            ("device_links", "device_links_first_device_area",
             "FOREIGN KEY (first_device_id, first_app_area) REFERENCES device_installations(id, app_area) ON DELETE CASCADE"),
        ]
        replacements += [
            (table, name, "CHECK (true)")
            for (table, name), (kind, _) in migrate.CONTRACT_CONSTRAINTS.items() if kind == "c"
        ]
        for table, name, definition in replacements:
            with self.subTest(constraint=name, replacement=definition), self.connection.transaction(force_rollback=True):
                self.connection.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
                self.connection.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} {definition}")
                with self.assertRaises(RuntimeError):
                    migrate.check_ready(self.connection)
                with self.assertRaises(RuntimeError):
                    migrate.migrate(self.connection)
        migrate.check_ready(self.connection)

    def test_wrong_constraint_owner_and_unvalidated_checks_fail_closed(self):
        migrate.migrate(self.connection, approve_contract=True)
        for replacement in (
            "ALTER TABLE device_installations ADD CONSTRAINT device_links_distinct_devices CHECK (true)",
            "ALTER TABLE device_links ADD CONSTRAINT device_links_distinct_devices CHECK (first_device_id <> second_device_id) NOT VALID",
        ):
            with self.subTest(replacement=replacement), self.connection.transaction(force_rollback=True):
                self.connection.execute("ALTER TABLE device_links DROP CONSTRAINT device_links_distinct_devices")
                self.connection.execute(replacement)
                with self.assertRaisesRegex(RuntimeError, "constraints"):
                    migrate.check_ready(self.connection)

    def test_same_named_replacement_indexes_fail_closed(self):
        migrate.migrate(self.connection, approve_contract=True)
        name = "device_installations_area_fingerprint_unique"
        replacements = [
            f"CREATE INDEX {name} ON device_installations(app_area, public_key_fingerprint) WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(public_key_fingerprint, app_area) WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint)",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint) WHERE public_key_fingerprint IS NULL",
            f"CREATE UNIQUE INDEX {name} ON device_links(first_app_area, first_device_id) WHERE first_device_id IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint) INCLUDE (id) WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint COLLATE \"C\") WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint bpchar_pattern_ops) WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area DESC, public_key_fingerprint) WHERE public_key_fingerprint IS NOT NULL",
            f"CREATE UNIQUE INDEX {name} ON device_installations(app_area, public_key_fingerprint) NULLS NOT DISTINCT WHERE public_key_fingerprint IS NOT NULL",
        ]
        for replacement in replacements:
            with self.subTest(replacement=replacement), self.connection.transaction(force_rollback=True):
                self.connection.execute(f"DROP INDEX {name}")
                self.connection.execute(replacement)
                with self.assertRaisesRegex(RuntimeError, "indexes"):
                    migrate.check_ready(self.connection)
        migrate.check_ready(self.connection)

    def test_contract_failure_rolls_back_sql_and_history(self):
        migrate.migrate(self.connection)
        original = migrate.migration_text

        def broken(version):
            text = original(version)
            return text.replace("COMMIT;", "SELECT 1/0;\nCOMMIT;") if version == migrate.CONTRACT else text

        with patch("migrate.migration_text", side_effect=broken), self.assertRaises(psycopg.errors.DivisionByZero):
            migrate.migrate(self.connection, approve_contract=True)
        self.assertEqual(1, len(migrate._records(self.connection)))
        self.assertIsNone(self.connection.execute("SELECT to_regclass('public.device_installations')").fetchone()[0])
        migrate.check_ready(self.connection)

    def test_health_role_has_only_ledger_read_access(self):
        with patch("database.read_secret", return_value="integration-test-only"):
            migrate.migrate(self.connection, approve_contract=True, health_secret_path="mock-only")
        with self.connection.transaction():
            self.connection.execute("SET LOCAL ROLE backend_health")
            migrate.check_ready(self.connection)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.connection.execute("SELECT * FROM device_installations")
        with self.connection.transaction():
            self.connection.execute("SET LOCAL ROLE backend_health")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.connection.execute("DELETE FROM backend_schema_migrations")

    def test_async_health_role_readiness_accepts_valid_schema_and_rejects_drift(self):
        from psycopg.conninfo import make_conninfo
        with patch("database.read_secret", return_value="integration-test-only"):
            migrate.migrate(self.connection, approve_contract=True, health_secret_path="mock-only")
        dsn = make_conninfo(
            os.environ["BACKEND_TEST_DATABASE_URL"], user="backend_health",
            **{"password": "integration-test-only"},
        )
        with patch.dict(os.environ, {"DATABASE_URL": dsn, "PGPASSWORD_FILE": ""}):
            asyncio.run(database.probe(migrate.check_ready_async))
            self.connection.execute(
                "ALTER TABLE backend_schema_migrations DROP CONSTRAINT backend_schema_migrations_checksum_check, "
                "ADD CONSTRAINT backend_schema_migrations_checksum_check CHECK (true)"
            )
            with self.assertRaisesRegex(RuntimeError, "ledger invariants"):
                asyncio.run(database.probe(migrate.check_ready_async))

    def test_existing_overprivileged_health_role_is_rejected_atomically(self):
        with patch("database.read_secret", return_value="integration-test-only"):
            migrate.migrate(self.connection, approve_contract=True, health_secret_path="mock-only")
        mutations = [
            "GRANT UPDATE ON backend_schema_migrations TO backend_health",
            "GRANT UPDATE (checksum) ON backend_schema_migrations TO backend_health",
            "GRANT SELECT ON device_installations TO backend_health",
            "GRANT SELECT ON backend_schema_migrations TO backend_health WITH GRANT OPTION",
            "ALTER TABLE backend_schema_migrations OWNER TO backend_health",
            "ALTER TABLE device_installations OWNER TO backend_health",
            "GRANT pg_read_all_data TO backend_health",
            "GRANT backend_health TO postgres",
            "ALTER ROLE backend_health BYPASSRLS",
            "ALTER ROLE backend_health SUPERUSER",
            "ALTER ROLE backend_health SET search_path = public",
            "GRANT UPDATE ON backend_schema_migrations TO PUBLIC",
            "GRANT UPDATE (checksum) ON backend_schema_migrations TO PUBLIC",
            "GRANT SELECT (id) ON device_installations TO PUBLIC",
            "GRANT CREATE ON SCHEMA public TO PUBLIC",
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.connection.transaction(force_rollback=True):
                self.connection.execute(mutation)
                with patch("database.read_secret", return_value="integration-test-only"), self.assertRaisesRegex(
                    RuntimeError, "health role|Health role",
                ):
                    migrate.migrate(self.connection, health_secret_path="mock-only")
        with patch("database.read_secret", return_value="integration-test-only"):
            migrate.migrate(self.connection, health_secret_path="mock-only")

    def test_effective_migration_password_cannot_be_reused_for_health(self):
        from psycopg.conninfo import conninfo_to_dict
        from urllib.parse import urlencode
        params = conninfo_to_dict(os.environ["BACKEND_TEST_DATABASE_URL"])
        password = self.connection.info.password
        environments = [
            {"DATABASE_URL": "postgresql:///?" + urlencode({**params, "password": password})},
            {"PGHOST": params["host"], "PGPORT": params.get("port", "5432"),
             "PGDATABASE": params["dbname"], "PGUSER": params["user"], "PGPASSWORD": password},
            {"DATABASE_URL": "postgresql:///?" + urlencode({**params, "password": "not-the-real-password"}),
             "PGPASSWORD_FILE": "mock-only"},
        ]
        for index, environment in enumerate(environments):
            with self.subTest(source=index), patch.dict(os.environ, environment, clear=True), patch(
                "database.read_secret", return_value=password,
            ):
                with database.connect() as connection, self.assertRaisesRegex(ValueError, "must differ"):
                    migrate._configure_health_role(connection, "mock-health-only")

    def test_established_blackholed_query_has_client_deadline_and_live_stays_responsive(self):
        migrate.migrate(self.connection)
        params = self.connection.info.get_parameters()
        upstream = (params["host"], int(params["port"]))
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)
        blackhole = threading.Event()
        stopped = threading.Event()
        failures = []

        def proxy():
            try:
                with listener.accept()[0] as client, socket.create_connection(upstream, timeout=3) as server:
                    while not stopped.is_set():
                        readable, _, _ = select.select([client, server], [], [], 0.05)
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                return
                            if not blackhole.is_set():
                                (server if source is client else client).sendall(data)
            except Exception as failure:
                if not stopped.is_set():
                    failures.append(failure)

        proxy_thread = threading.Thread(target=proxy, daemon=True)
        proxy_thread.start()
        connections = []

        async def probe(check):
            async def drop_then_check(connection):
                connections.append(connection)
                blackhole.set()
                await check(connection)
            await database.probe(drop_then_check)

        app_socket = socket.socket()
        app_socket.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{app_socket.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(create_app(readiness_probe=probe), log_level="critical", access_log=False))
        app_thread = threading.Thread(target=server.run, kwargs={"sockets": [app_socket]}, daemon=True)
        from psycopg.conninfo import make_conninfo
        dsn = make_conninfo(
            os.environ["BACKEND_TEST_DATABASE_URL"], host="127.0.0.1",
            port=listener.getsockname()[1], sslmode="disable",
        )

        def ready():
            try:
                return urlopen(url + "/health/ready", timeout=3).status
            except HTTPError as response:
                with response:
                    self.assertNotIn("database", response.read().decode())
                    return response.code

        try:
            with patch.dict(os.environ, {"DATABASE_URL": dsn, "PGPASSWORD_FILE": ""}), patch(
                "database.READINESS_TIMEOUT", 0.5,
            ):
                app_thread.start()
                for _ in range(100):
                    if server.started:
                        break
                    time.sleep(0.02)
                self.assertTrue(server.started)
                started = time.monotonic()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(ready)
                    self.assertTrue(blackhole.wait(2), "real database connection was not established")
                    live_started = time.monotonic()
                    for _ in range(5):
                        with urlopen(url + "/health/live", timeout=1) as response:
                            self.assertEqual({"status": "live"}, json.load(response))
                    self.assertLess(time.monotonic() - live_started, 0.4)
                    self.assertEqual(503, result.result(timeout=2))
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertTrue(connections[0].closed)
        finally:
            server.should_exit = True
            if app_thread.ident is not None:
                app_thread.join(5)
            app_socket.close()
            stopped.set()
            listener.close()
            proxy_thread.join(5)
        self.assertFalse(app_thread.is_alive())
        self.assertFalse(proxy_thread.is_alive())
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
