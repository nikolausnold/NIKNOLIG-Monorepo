import json
import os
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import AsyncMock, Mock, patch


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import _check_readiness, create_server, main
from migrate import check_health_ready_async


class BackendHealthServerTests(unittest.TestCase):
    def setUp(self):
        self.readiness_probe = Mock()
        self.server = create_server("127.0.0.1", 0, readiness_probe=self.readiness_probe)
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
        self.readiness_probe.assert_called_once_with()

    def test_readiness_failure_returns_generic_service_unavailable(self):
        self.readiness_probe.side_effect = RuntimeError("secret database address")

        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/health/ready", timeout=2)

        self.assertEqual(503, raised.exception.code)
        body = json.load(raised.exception)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
        self.assertEqual(
            "Service is temporarily unavailable.", body["error"]["message"]
        )
        self.assertNotIn("secret database address", json.dumps(body))
        self.assertIn("requestId", body["error"])

    def test_default_readiness_probe_checks_postgres_and_migrations(self):
        with patch("app.database.probe", new_callable=AsyncMock) as probe:
            _check_readiness()

        probe.assert_awaited_once_with(check_health_ready_async)

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

    def test_invalid_port_fails_without_starting_server(self):
        with patch.dict(os.environ, {"BACKEND_HOST": "127.0.0.1", "BACKEND_PORT": "70000"}):
            with self.assertRaisesRegex(SystemExit, "BACKEND_PORT"):
                main()


if __name__ == "__main__":
    unittest.main()
