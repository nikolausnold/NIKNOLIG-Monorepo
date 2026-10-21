import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg
import uvicorn


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import database
import deployment
import migrate
from asgi import create_app


class ProductionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = MagicMock()
        cls.application = create_app(connection_factory=cls.factory)
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

    def test_readiness_checks_database_and_migration_invariants(self):
        with patch("asgi.check_ready") as check:
            self.assertEqual((200, {"status": "ready"}), self.request("/health/ready"))
            check.assert_called_once_with(self.factory.return_value.__enter__.return_value)
        self.factory.return_value.__exit__.assert_called()

    def test_unavailable_database_returns_generic_503(self):
        self.factory.side_effect = psycopg.OperationalError("password and internal address")
        status, body = self.request("/health/ready")
        self.assertEqual(503, status)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
        self.assertNotIn("password", json.dumps(body))
        self.assertNotIn("internal address", json.dumps(body))

    def test_missing_or_invalid_migration_returns_generic_503(self):
        for failure in (psycopg.errors.UndefinedTable("ledger"), RuntimeError("schema drift")):
            with self.subTest(failure=type(failure).__name__), patch("asgi.check_ready", side_effect=failure):
                status, body = self.request("/health/ready")
                self.assertEqual(503, status)
                self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
                self.assertNotIn(str(failure), json.dumps(body))

    def test_no_ai_product_or_documentation_routes_even_with_enabling_environment(self):
        with patch.dict(os.environ, {"AI_ENABLED": "true", "SUPPORT_ENABLED": "true"}):
            for path, method in (
                ("/v1/ai/support", "POST"), ("/v1/devices", "GET"),
                ("/v1/pairing", "POST"), ("/docs", "GET"),
                ("/openapi.json", "GET"), ("/health/ready/", "GET"),
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
                cursor.fetchone.return_value = (1,)
            elif "SELECT count(*) FROM pg_constraint" in statement:
                cursor.fetchone.return_value = (2,)
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
        with patch.dict(os.environ, {"PGPASSWORD_FILE": "admin-secret"}), patch(
            "database.read_secret", return_value="same-test-value",
        ), self.assertRaisesRegex(ValueError, "must differ"):
            migrate._configure_health_role(MagicMock(), "health-secret")

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


if __name__ == "__main__":
    unittest.main()
