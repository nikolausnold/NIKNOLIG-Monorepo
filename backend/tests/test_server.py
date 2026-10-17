import json
import os
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_server, main


class BackendHealthServerTests(unittest.TestCase):
    def setUp(self):
        self.readiness = False
        self.server = create_server("127.0.0.1", 0, lambda: self.readiness)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_liveness_does_not_depend_on_database_readiness(self):
        with urlopen(self.base_url + "/health/live", timeout=2) as response:
            self.assertEqual(200, response.status)
            self.assertEqual({"status": "live"}, json.load(response))

    def test_readiness_fails_closed_when_database_is_unavailable(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/health/ready", timeout=2)

        self.assertEqual(503, raised.exception.code)
        self.assertEqual("no-store", raised.exception.headers["Cache-Control"])
        body = json.load(raised.exception)
        self.assertEqual("SERVICE_UNAVAILABLE", body["error"]["code"])
        self.assertRegex(
            body["error"]["requestId"],
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )

    def test_readiness_returns_200_only_after_dependency_probe_succeeds(self):
        self.readiness = True
        with urlopen(self.base_url + "/health/ready", timeout=2) as response:
            self.assertEqual(200, response.status)
            self.assertEqual({"status": "ready"}, json.load(response))

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
