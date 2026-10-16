import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from database import check_database


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


if __name__ == "__main__":
    unittest.main()
