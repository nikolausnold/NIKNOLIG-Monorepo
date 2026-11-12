import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import database
from database import check_database


class HealthLoginTests(unittest.TestCase):
    base = {"PGHOST": "db", "PGDATABASE": "nold_staging", "PGUSER": "backend_device_api"}

    def params(self, extra, secrets):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(self.base)
            for name, value in secrets.items():
                path = Path(directory, name)
                path.write_text(value)
                env[name] = str(path)
            env.update(extra)
            with patch.dict("os.environ", env, clear=True):
                return database.health_connection_parameters()

    def test_dedicated_health_login_overrides_api_login(self):
        dsn, kwargs = self.params(
            {"HEALTH_DB_USER": "backend_health"},
            {"PGPASSWORD_FILE": "api-secret", "HEALTH_DB_PASSWORD_FILE": "health-secret"},
        )
        self.assertEqual("", dsn)
        self.assertEqual(("backend_health", "health-secret"), (kwargs["user"], kwargs["password"]))

    def test_normal_connection_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "pw")
            path.write_text("api-secret")
            env = {**self.base, "PGPASSWORD_FILE": str(path), "HEALTH_DB_USER": "backend_health",
                   "HEALTH_DB_PASSWORD_FILE": str(path)}
            with patch.dict("os.environ", env, clear=True):
                _, kwargs = database.connection_parameters()
        self.assertNotIn("user", kwargs)

    def test_incomplete_or_missing_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            self.params({"HEALTH_DB_USER": "backend_health"}, {"PGPASSWORD_FILE": "x"})
        with self.assertRaises(ValueError):
            self.params({}, {"PGPASSWORD_FILE": "x", "HEALTH_DB_PASSWORD_FILE": "y"})
        with self.assertRaises(OSError):
            self.params({"HEALTH_DB_USER": "backend_health",
                         "HEALTH_DB_PASSWORD_FILE": "/nonexistent/secret"}, {"PGPASSWORD_FILE": "x"})
        with self.assertRaises(ValueError):
            self.params({"HEALTH_DB_USER": "backend_health"},
                        {"PGPASSWORD_FILE": "x", "HEALTH_DB_PASSWORD_FILE": ""})

    def test_probe_connects_with_health_login_and_wrong_role_is_rejected(self):
        import asyncio
        import migrate

        class Result:
            def __init__(self, rows): self.rows = rows
            async def fetchall(self): return self.rows

        class Connection:
            async def execute(self, *_): return Result([("backend_device_api", "backend_device_api")])
            async def close(self): pass

        seen = {}

        async def connect(dsn, **kwargs):
            seen.update(kwargs)
            return Connection()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "pw")
            path.write_text("health-secret")
            env = {**self.base, "HEALTH_DB_USER": "backend_health", "HEALTH_DB_PASSWORD_FILE": str(path)}
            with patch.dict("os.environ", env, clear=True), \
                    patch("database.psycopg.AsyncConnection.connect", connect):
                with self.assertRaises(RuntimeError):
                    asyncio.run(database.probe(migrate.check_health_ready_async, health_login=True))
        self.assertEqual("backend_health", seen["user"])
        self.assertTrue(seen["options"].endswith("default_transaction_read_only=on"))

    def test_database_outage_propagates_for_503(self):
        import asyncio

        async def down(*_, **__): raise OSError("down")

        with patch.dict("os.environ", self.base, clear=True), \
                patch("database.psycopg.AsyncConnection.connect", down):
            with self.assertRaises(OSError):
                asyncio.run(database.probe(AsyncMock(), health_login=True))


class DatabaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "BACKEND_DB_HOST": "postgres",
            "BACKEND_DB_PORT": "5432",
            "BACKEND_DB_NAME": "niknolig_local",
            "BACKEND_DB_USER": "local_user",
            "BACKEND_DB_PASSWORD": "local-only-test",
        }

    def test_missing_or_invalid_database_configuration_fails_closed(self):
        for key in self.environment:
            with self.subTest(key=key):
                environment = dict(self.environment)
                environment.pop(key)
                self.assertFalse(check_database(environment, connector=Mock()))
        invalid_port = dict(self.environment, BACKEND_DB_PORT="70000")
        self.assertFalse(check_database(invalid_port, connector=Mock()))

    def test_probe_uses_short_timeout_and_only_select_one(self):
        cursor = Mock()
        cursor.fetchone.return_value = (1,)
        cursor_context = Mock()
        cursor_context.__enter__ = Mock(return_value=cursor)
        cursor_context.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.cursor.return_value = cursor_context
        connection_context = Mock()
        connection_context.__enter__ = Mock(return_value=connection)
        connection_context.__exit__ = Mock(return_value=False)
        connector = Mock(return_value=connection_context)

        self.assertTrue(check_database(self.environment, connector=connector))
        options = connector.call_args.kwargs
        self.assertEqual("postgres", options["host"])
        self.assertEqual(5432, options["port"])
        self.assertEqual("niknolig_local", options["dbname"])
        self.assertEqual("local_user", options["user"])
        self.assertEqual(self.environment["BACKEND_DB_PASSWORD"], options["password"])
        self.assertEqual(2, options["connect_timeout"])
        cursor.execute.assert_called_once_with("SELECT 1")

    def test_probe_failure_returns_false_without_leaking_details(self):
        connector = Mock(side_effect=RuntimeError("private database detail"))
        self.assertFalse(check_database(self.environment, connector=connector))

    def test_probe_deadline_covers_stalls_after_connection_and_caps_workers(self):
        entered_query = threading.Event()
        release_query = threading.Event()
        query_finished = threading.Event()
        cursor = Mock()

        def stall_query(_statement):
            entered_query.set()
            release_query.wait(timeout=2)
            query_finished.set()

        cursor.execute.side_effect = stall_query
        cursor_context = Mock()
        cursor_context.__enter__ = Mock(return_value=cursor)
        cursor_context.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.cursor.return_value = cursor_context
        connection_context = Mock()
        connection_context.__enter__ = Mock(return_value=connection)
        connection_context.__exit__ = Mock(return_value=False)
        connector = Mock(return_value=connection_context)

        try:
            with patch("database.PROBE_DEADLINE_SECONDS", 0.05):
                started = time.monotonic()
                self.assertFalse(
                    check_database(self.environment, connector=connector)
                )
                self.assertLess(time.monotonic() - started, 0.5)
                self.assertTrue(entered_query.is_set())
                self.assertFalse(
                    check_database(self.environment, connector=Mock())
                )
                connector.assert_called_once()
        finally:
            release_query.set()
        self.assertTrue(query_finished.wait(timeout=1))
        self.assertTrue(database._PROBE_SLOT.acquire(timeout=1))
        database._PROBE_SLOT.release()


if __name__ == "__main__":
    unittest.main()
