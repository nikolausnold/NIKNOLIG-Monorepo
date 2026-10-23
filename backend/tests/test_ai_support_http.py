import http.client
import json
from dataclasses import replace
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import SupportService
from app import create_server, MAX_SUPPORT_BODY_BYTES
from test_ai_support import local_service, payload


def support_payload(**changes):
    return {"app": "niknolig", "message": "Local support question.", **changes}


class SupportHTTPTests(unittest.TestCase):
    def setUp(self):
        self.service, self.auth, self.provider, self.audit = local_service()
        self.server = create_server("127.0.0.1", 0, support_service=self.service)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.address = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def post(self, body=None, *, authorization=True, path="/v1/ai/support", extra=None):
        connection = http.client.HTTPConnection(*self.address, timeout=3)
        try:
            headers = {"Content-Type": "application/json", **(extra or {})}
            if authorization:
                headers["Authorization"] = self.auth.authorization
            connection.request("POST", path, json.dumps(payload() if body is None else body),
                               headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
            connection.close()

    def raw(self, request, *, eof=True):
        with socket.create_connection(self.address, timeout=3) as connection:
            connection.sendall(request)
            if eof:
                connection.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        response = b"".join(chunks)
        head, body = response.split(b"\r\n\r\n", 1)
        return int(head.split(b" ", 2)[1]), json.loads(body)

    def test_local_mock_success_and_security_headers(self):
        status, body, headers = self.post()
        self.assertEqual(200, status)
        self.assertTrue(body["untrusted"])
        self.assertEqual("text/plain", body["contentType"])
        self.assertEqual("no-store", headers["Cache-Control"])
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])
        self.assertEqual(1, len(self.provider.calls))

    def test_common_support_route_accepts_both_separately_scoped_apps(self):
        status, body, _ = self.post(
            support_payload(), path="/support")
        self.assertEqual(200, status)
        self.assertEqual("niknolig", body["app"])
        self.assertEqual("support", body["feature"])
        self.assertEqual(["Local support question."], self.provider.calls)

        self.auth.principal = replace(
            self.auth.principal,
            app="niknolig-defense",
            permissions=frozenset({"ai:support"}),
        )
        status, body, _ = self.post(
            support_payload(app="niknolig-defense"), path="/support")
        self.assertEqual(200, status)
        self.assertEqual("niknolig-defense", body["app"])
        self.assertEqual(2, len(self.provider.calls))

    def test_common_support_route_rejects_invalid_input(self):
        invalid_bodies = (
            {},
            {"app": "niknolig"},
            {"message": "A message"},
            support_payload(app="unknown"),
            support_payload(message=""),
            support_payload(message=" \n\t"),
            support_payload(message=123),
            support_payload(message="é" * 1025),
            {**support_payload(), "provider": "caller"},
        )
        for body in invalid_bodies:
            with self.subTest(body=repr(body)[:100]):
                status, result, _ = self.post(body, path="/support")
                self.assertEqual(400, status)
                self.assertEqual(
                    "VALIDATION_FAILED", result["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_common_support_route_keeps_app_scope_authorization(self):
        status, body, _ = self.post(
            support_payload(app="niknolig-defense"), path="/support")
        self.assertEqual(403, status)
        self.assertEqual("APP_AREA_MISMATCH", body["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_common_support_route_validates_before_default_disabled_response(self):
        self.server.support_service = SupportService()
        for body in (
                {}, support_payload(app="unknown"),
                support_payload(message="é" * 1025),
                {**support_payload(), "unexpected": True}):
            with self.subTest(body=repr(body)[:100]):
                status, result, _ = self.post(body, path="/support")
                self.assertEqual(400, status)
                self.assertEqual(
                    "VALIDATION_FAILED", result["error"]["code"])
        status, result, _ = self.post(support_payload(), path="/support")
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", result["error"]["code"])

    def test_default_server_remains_disabled_even_with_environment_flags(self):
        with patch.dict("os.environ", {"AI_ENABLED": "true",
                                      "CLOUDFLARE_API_TOKEN": str(uuid4())}):
            default_server = create_server("127.0.0.1", 0)
        self.server.support_service = default_server.support_service
        default_server.server_close()
        status, body, _ = self.post()
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", body["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_no_auth_body_or_app_header_can_grant_access(self):
        self.assertEqual(401, self.post(authorization=False,
                                       extra={"X-App": "niknolig"})[0])
        self.assertEqual(403, self.post(
            payload(app="niknolig-defense"), extra={"X-App": "niknolig"})[0])
        self.assertEqual(400, self.post({**payload(), "permissions": ["ai:support"]})[0])
        self.assertFalse(self.provider.calls)

    def test_unknown_path_and_query_do_not_dispatch(self):
        self.assertEqual(404, self.post(path="/v1/ai/other")[0])
        self.assertEqual(404, self.post(path="/v1/ai/support?provider=other")[0])
        self.assertFalse(self.provider.calls)

    def test_bad_framing_and_unsupported_encodings_are_rejected(self):
        cases = [
            b"",
            b"Content-Length: -1\r\n",
            b"Content-Length: +2\r\n",
            b"Content-Length: 2,2\r\n",
            b"Content-Length: 2\r\nContent-Length: 2\r\n",
            b"Transfer-Encoding: chunked\r\n",
            b"Content-Length: 2\r\nTransfer-Encoding: chunked\r\n",
            b"Content-Length: 2\r\nContent-Encoding: gzip\r\n",
            b"Content-Length: 2\r\nAuthorization: a\r\nAuthorization: b\r\n",
            b"Content-Length: 9999999999999999999999999999\r\n",
        ]
        for headers in cases:
            with self.subTest(headers=headers):
                status, _ = self.raw(
                    b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
                    b"Content-Type: application/json\r\n" + headers + b"\r\n{}")
                self.assertEqual(400, status)
        self.assertFalse(self.provider.calls)

    def test_content_type_is_required_unambiguous_and_json_only(self):
        for content_type in (b"", b"Content-Type: text/plain\r\n",
                             b"Content-Type: application/json\r\n"
                             b"Content-Type: application/json\r\n"):
            with self.subTest(content_type=content_type):
                status, _ = self.raw(
                    b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
                    b"Content-Length: 2\r\n" + content_type + b"\r\n{}")
                self.assertEqual(400, status)

    def test_equivalent_utf8_json_content_types_are_accepted(self):
        for content_type in ("application/json;charset=utf-8",
                             'application/json; charset="utf-8"'):
            with self.subTest(content_type=content_type):
                status, _, _ = self.post(extra={"Content-Type": content_type})
                self.assertEqual(200, status)
        self.assertEqual(2, len(self.provider.calls))

    def test_duplicate_or_unsupported_content_type_parameters_are_rejected(self):
        for content_type in (
                "application/json; charset=utf-8; charset=utf-8",
                "application/json; charset=latin-1",
                "application/json; profile=other"):
            with self.subTest(content_type=content_type):
                status, _, _ = self.post(extra={"Content-Type": content_type})
                self.assertEqual(400, status)
        self.assertFalse(self.provider.calls)

    def test_oversized_body_is_rejected_before_read(self):
        status, body = self.raw(
            b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Type: application/json\r\nContent-Length: " +
            str(MAX_SUPPORT_BODY_BYTES + 1).encode() + b"\r\n\r\n")
        self.assertEqual(413, status)
        self.assertEqual("PAYLOAD_TOO_LARGE", body["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_malformed_json_duplicate_fields_utf8_and_incomplete_body(self):
        for raw_body in (b"{", b"\xff", b'{"app":"niknolig","app":"niknolig-defense"}',
                         b'{"prompt": NaN}', b'{"prompt": Infinity}', b"",
                         b"[" * 1100 + b"]" * 1100):
            with self.subTest(body=raw_body[:100]):
                status, _ = self.raw(
                    b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
                    b"Content-Type: application/json\r\nContent-Length: " +
                    str(len(raw_body)).encode() + b"\r\n\r\n" + raw_body)
                self.assertEqual(400, status)
        status, _ = self.raw(
            b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Type: application/json\r\nContent-Length: 20\r\n\r\n{}")
        self.assertEqual(400, status)
        self.assertFalse(self.provider.calls)

    def test_body_read_timeout_is_bounded(self):
        with patch("app.SUPPORT_READ_TIMEOUT_SECONDS", 0.1):
            status, body = self.raw(
                b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
                b"Content-Type: application/json\r\nContent-Length: 20\r\n\r\n{}",
                eof=False)
        self.assertEqual(408, status)
        self.assertEqual("REQUEST_TIMEOUT", body["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_slow_drip_cannot_extend_total_body_deadline(self):
        with patch("app.SUPPORT_READ_TIMEOUT_SECONDS", 0.25):
            with socket.create_connection(self.address, timeout=2) as connection:
                connection.sendall(
                    b"POST /v1/ai/support HTTP/1.1\r\nHost: localhost\r\n"
                    b"Content-Type: application/json\r\nContent-Length: 20\r\n\r\n{")
                time.sleep(0.10)
                connection.sendall(b" ")
                time.sleep(0.10)
                connection.sendall(b" ")
                started = time.monotonic()
                response = http.client.HTTPResponse(connection)
                response.begin()
                self.assertEqual(408, response.status)
                self.assertLess(time.monotonic() - started, 0.20)
                self.assertEqual("REQUEST_TIMEOUT",
                                 json.loads(response.read())["error"]["code"])
        self.assertFalse(self.provider.calls)

    def test_provider_timeout_is_generic_over_http(self):
        self.provider.error = TimeoutError(self.auth.authorization)
        status, body, _ = self.post()
        self.assertEqual(503, status)
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertNotIn(self.auth.authorization, json.dumps(body))

    def test_service_exception_does_not_leak_in_http_response(self):
        with patch.object(self.service, "handle", side_effect=RuntimeError("private")):
            status, body, _ = self.post()
        self.assertEqual(503, status)
        self.assertNotIn("private", json.dumps(body))


if __name__ == "__main__":
    unittest.main()
