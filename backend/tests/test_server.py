import json
import os
import sys
import threading
from types import SimpleNamespace
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import MagicMock, patch


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_server, database_is_ready, main


class BackendHealthServerTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(
            "127.0.0.1", 0, readiness_check=lambda: True
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_health_routes_match_the_openapi_status_contract(self):
        for path, expected in (
            ("/health/live", {"status": "live"}),
            ("/health/ready", {"status": "ready"}),
        ):
            with self.subTest(path=path):
                with urlopen(self.base_url + path, timeout=2) as response:
                    self.assertEqual(200, response.status)
                    self.assertEqual("application/json; charset=utf-8", response.headers["Content-Type"])
                    self.assertEqual("no-store", response.headers["Cache-Control"])
                    self.assertEqual(expected, json.load(response))

    def test_unsupported_path_returns_generic_not_found_error(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/v1/devices", timeout=2)

        self.assertEqual(404, raised.exception.code)
        body = json.load(raised.exception)
        self.assertEqual("NOT_FOUND", body["error"]["code"])
        self.assertEqual("Resource was not found.", body["error"]["message"])
        self.assertRegex(
            body["error"]["requestId"],
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )

    def test_readiness_returns_generic_503_when_dependency_is_unavailable(self):
        self.server.readiness_check = lambda: False

        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/health/ready", timeout=2)

        self.assertEqual(503, raised.exception.code)
        body = json.load(raised.exception)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
        self.assertEqual(
            "Service is temporarily unavailable.",
            body["error"]["message"],
        )
        self.assertIn("requestId", body["error"])

    def test_readiness_fails_closed_when_dependency_check_raises(self):
        def failed_check():
            raise RuntimeError("internal connection details")

        self.server.readiness_check = failed_check

        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/health/ready", timeout=2)

        self.assertEqual(503, raised.exception.code)
        self.assertNotIn("internal connection details", raised.exception.read().decode())

    def test_database_readiness_checks_authenticated_postgres_connection(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        driver = SimpleNamespace(connect=MagicMock(return_value=connection))
        config = {
            "DATABASE_HOST": "postgres",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "niknolig_local",
            "DATABASE_USER": "niknolig_local",
            "DATABASE_PASSWORD": "local-test-password",
        }

        with patch.dict(os.environ, config), patch.dict(sys.modules, {"psycopg": driver}):
            self.assertTrue(database_is_ready())

        expected_options = {
            "host": "postgres",
            "port": 5432,
            "dbname": "niknolig_local",
            "user": "niknolig_local",
            "connect_timeout": 2,
        }
        expected_options["password"] = "local-test-password"
        driver.connect.assert_called_once_with(**expected_options)
        connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1"
        )

    def test_database_readiness_fails_closed_for_incomplete_configuration(self):
        config = {
            "DATABASE_HOST": "postgres",
            "DATABASE_PORT": "",
            "DATABASE_NAME": "",
            "DATABASE_USER": "",
            "DATABASE_PASSWORD": "",
        }

        with patch.dict(os.environ, config):
            self.assertFalse(database_is_ready())

    def test_database_readiness_fails_closed_when_postgres_is_unavailable(self):
        driver = SimpleNamespace(connect=MagicMock(side_effect=OSError("offline")))
        config = {
            "DATABASE_HOST": "postgres",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "niknolig_local",
            "DATABASE_USER": "niknolig_local",
            "DATABASE_PASSWORD": "local-test-password",
        }

        with patch.dict(os.environ, config), patch.dict(sys.modules, {"psycopg": driver}):
            self.assertFalse(database_is_ready())

        driver.connect.assert_called_once()

    def test_invalid_port_fails_without_starting_server(self):
        with patch.dict(os.environ, {"BACKEND_HOST": "127.0.0.1", "BACKEND_PORT": "70000"}):
            with self.assertRaisesRegex(SystemExit, "BACKEND_PORT"):
                main()


if __name__ == "__main__":
    unittest.main()
