import io
import http.client
import json
from email.message import Message
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import CloudflareWorkersAI, MODEL, ProviderResult, SYSTEM_PROMPT
from workers_ai import MAX_PROVIDER_RESPONSE_BYTES, WorkersAIHTTPTransport


class WorkersAIHTTPTests(unittest.TestCase):
    def setUp(self):
        self.secret = patch("workers_ai.read_secret", return_value="local-test-only")
        self.secret.start()
        self.addCleanup(self.secret.stop)
        self.transport = WorkersAIHTTPTransport(account_id="a" * 32, token_file="/unused")
        self.response = MagicMock()
        self.response.status = 200
        self.response.isclosed.return_value = False
        self.response.headers = Message()
        self.response.headers["Content-Type"] = "application/json"
        self.response.getheader.return_value = None
        self.set_body({
            "success": True, "errors": [],
            "result": {"response": "Help text", "usage": {
                "prompt_tokens": 10, "completion_tokens": 3,
            }},
        })
        self.connection = MagicMock()
        self.connection.getresponse.return_value = self.response
        self.https = patch("workers_ai.http.client.HTTPSConnection", return_value=self.connection)
        self.factory = self.https.start()
        self.addCleanup(self.https.stop)

    def set_body(self, payload):
        stream = io.BytesIO(json.dumps(payload).encode())
        self.response.read1.side_effect = stream.read1

    def invoke(self):
        return CloudflareWorkersAI(self.transport).generate("Help")

    def test_fixed_tls_destination_and_server_side_credentials(self):
        self.assertEqual(ProviderResult("Help text", 10, 3), self.invoke())
        args, kwargs = self.factory.call_args
        self.assertEqual(("api.cloudflare.com",), args)
        self.assertEqual(5.0, kwargs["timeout"])
        self.assertTrue(kwargs["context"].check_hostname)
        args, kwargs = self.connection.request.call_args
        self.assertEqual(("POST", f"/client/v4/accounts/{'a' * 32}/ai/run/{MODEL}"), args)
        payload = json.loads(kwargs["body"])
        self.assertEqual(256, payload["max_tokens"])
        self.assertEqual({"role": "system", "content": SYSTEM_PROMPT}, payload["messages"][0])
        self.assertNotIn("token", payload)
        self.assertEqual("Bearer " + "local-test-only", kwargs["headers"]["Authorization"])
        self.connection.close.assert_called_once()

    def test_invalid_account_and_header_injection_never_connect(self):
        for account in ("", "../other", "a" * 31, "https://example.invalid"):
            with self.assertRaises(ValueError):
                WorkersAIHTTPTransport(account_id=account, token_file="/unused")
        with patch("workers_ai.read_secret", return_value="bad\r\nheader"):
            with self.assertRaises(ValueError):
                WorkersAIHTTPTransport(account_id="a" * 32, token_file="/unused")
        self.factory.assert_not_called()

    def test_redirect_and_errors_are_never_retried_or_followed(self):
        for status in (301, 302, 307, 401, 429, 500):
            self.connection.reset_mock()
            self.response.status = status
            with self.assertRaisesRegex(RuntimeError, "^Provider request failed$"):
                self.invoke()
            self.connection.request.assert_called_once()
            self.connection.close.assert_called_once()

    def test_malformed_or_oversized_provider_output_fails_closed(self):
        invalid = [
            {"success": False, "errors": [{"message": "private"}]},
            {"success": True, "result": {"response": "Hi"}},
            {"success": True, "result": {"response": "x" * 1025, "usage": {
                "prompt_tokens": 1, "completion_tokens": 1,
            }}},
            {"success": True, "result": {"response": "Hi", "usage": {
                "prompt_tokens": True, "completion_tokens": 1,
            }}},
            {"success": True, "result": {"response": "Hi", "usage": {
                "prompt_tokens": 1, "completion_tokens": 257,
            }}},
        ]
        for payload in invalid:
            self.set_body(payload)
            with self.assertRaisesRegex(RuntimeError, "^Provider request failed$"):
                self.invoke()
        self.response.read1.side_effect = io.BytesIO(
            b"x" * (MAX_PROVIDER_RESPONSE_BYTES + 1),
        ).read1
        with self.assertRaises(RuntimeError):
            self.invoke()

    def test_duplicate_keys_non_json_and_network_errors_are_sanitized(self):
        for raw in (b'{"success":true,"success":false}', b'{"result":NaN}', b'not-json'):
            self.response.read1.side_effect = io.BytesIO(raw).read1
            with self.assertRaisesRegex(RuntimeError, "^Provider request failed$"):
                self.invoke()
        self.connection.getresponse.side_effect = TimeoutError("private token and prompt")
        with self.assertRaisesRegex(RuntimeError, "^Provider request failed$"):
            self.invoke()
        self.connection.close.assert_called()

    def test_connection_close_after_complete_body_does_not_touch_closed_socket(self):
        self.response.isclosed.side_effect = [False, True]
        self.assertEqual("Help text", self.invoke().text)
        self.connection.sock.settimeout.assert_called_once()

    def test_real_http_parser_accepts_close_and_chunked_provider_responses(self):
        payload = json.dumps({
            "success": True, "result": {"response": "Help", "usage": {
                "prompt_tokens": 1, "completion_tokens": 1,
            }},
        }).encode()
        responses = (
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload,
            b"Transfer-Encoding: chunked\r\n\r\n" +
            f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\n\r\n",
        )
        for wire_body in responses:
            sock = MagicMock()
            sock.makefile.return_value = io.BytesIO(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"Connection: close\r\n" + wire_body,
            )
            response = http.client.HTTPResponse(sock)
            response.begin()
            self.connection.getresponse.return_value = response
            self.assertEqual("Help", self.invoke().text)
            self.assertTrue(response.isclosed())

    def test_truncated_or_overstated_content_length_is_rejected(self):
        self.response.getheader.side_effect = lambda name: (
            "1000" if name == "Content-Length" else None
        )
        with self.assertRaises(RuntimeError):
            self.invoke()

    def test_deadline_timer_interrupts_socket_and_is_cancelled(self):
        with patch("workers_ai.threading.Timer") as timer_factory:
            timer = timer_factory.return_value
            self.invoke()
            delay, expire = timer_factory.call_args.args
            self.assertGreater(delay, 0)
            self.assertLessEqual(delay, 5)
            expire()
            self.connection.sock.shutdown.assert_called_once()
            timer.start.assert_called_once()
            timer.cancel.assert_called_once()

    def test_connect_time_consumes_budget_and_no_request_after_expiry(self):
        with patch("workers_ai.time.monotonic", side_effect=[0, 6]):
            with self.assertRaises(RuntimeError):
                self.invoke()
        self.connection.request.assert_not_called()
        self.connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
