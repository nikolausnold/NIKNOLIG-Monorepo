import json
import os
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from uuid import UUID


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_server, main


class BackendHealthServerTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
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
            ("/health/live?probe=1", {"status": "live"}),
        ):
            with self.subTest(path=path):
                with urlopen(self.base_url + path, timeout=2) as response:
                    self.assertEqual(200, response.status)
                    self.assertEqual("application/json; charset=utf-8", response.headers["Content-Type"])
                    self.assertEqual("no-store", response.headers["Cache-Control"])
                    self.assertEqual(expected, json.load(response))

    def test_readiness_fails_closed_with_generic_contract_error(self):
        request_ids = set()
        for path in ("/health/ready", "/health/ready?probe=1"):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(self.base_url + path, timeout=2)
                with raised.exception as response:
                    self.assertEqual(503, response.code)
                    self.assertEqual("application/json; charset=utf-8", response.headers["Content-Type"])
                    self.assertEqual("no-store", response.headers["Cache-Control"])
                    self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
                    encoded = response.read()
                    self.assertEqual(len(encoded), int(response.headers["Content-Length"]))
                    body = json.loads(encoded)
                self.assertEqual({"error"}, set(body))
                error = body["error"]
                self.assertEqual({"code", "message", "requestId"}, set(error))
                self.assertEqual("SERVICE_UNAVAILABLE", error["code"])
                self.assertEqual("Service is temporarily unavailable.", error["message"])
                self.assertEqual(4, UUID(error["requestId"]).version)
                request_ids.add(error["requestId"])
        self.assertEqual(2, len(request_ids))

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

    def test_unimplemented_product_routes_stay_unavailable_for_any_auth_context(self):
        contexts = (
            {},
            {"Authorization": ""},
            {"Authorization": "Bearer"},
            {"Authorization": "Basic invalid"},
            {"Authorization": " ".join(("Bearer", "invalid-local-test"))},
            {
                "Authorization": " ".join(("Bearer", "unverified-niknolig-test")),
                "X-App-Area": "niknolig-defense",
                "X-Role": "Founder Owner",
            },
            {
                "Authorization": " ".join(("Bearer", "unverified-defense-test")),
                "X-App-Area": "niknolig",
                "X-Role": "App Administrator",
            },
        )
        for path in ("/v1/devices", "/v1/niknolig/profile", "/v1/niknolig-defense/profile"):
            for headers in contexts:
                with self.subTest(path=path, headers=headers):
                    request = Request(self.base_url + path, headers=headers)
                    with self.assertRaises(HTTPError) as raised:
                        urlopen(request, timeout=2)
                    with raised.exception as response:
                        self.assertEqual(404, response.code)
                        self.assertEqual("no-store", response.headers["Cache-Control"])
                        body = json.load(response)
                    self.assertEqual({"error"}, set(body))
                    self.assertEqual({"code", "message", "requestId"}, set(body["error"]))
                    self.assertEqual("NOT_FOUND", body["error"]["code"])
                    self.assertEqual("Resource was not found.", body["error"]["message"])
                    self.assertEqual(4, UUID(body["error"]["requestId"]).version)

    def test_invalid_auth_headers_do_not_enable_readiness_or_protect_public_liveness(self):
        headers = {
            "Authorization": " ".join(("Bearer", "invalid-local-test")),
            "X-Role": "Founder Owner",
        }
        with urlopen(Request(self.base_url + "/health/live", headers=headers), timeout=2) as response:
            self.assertEqual(200, response.status)
            self.assertEqual({"status": "live"}, json.load(response))
        with self.assertRaises(HTTPError) as raised:
            urlopen(Request(self.base_url + "/health/ready", headers=headers), timeout=2)
        with raised.exception as response:
            self.assertEqual(503, response.code)
            self.assertEqual("SERVICE_UNAVAILABLE", json.load(response)["error"]["code"])


if __name__ == "__main__":
    unittest.main()
