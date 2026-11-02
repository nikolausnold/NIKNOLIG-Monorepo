import asyncio
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from authentication import (
    AppAreaMismatch,
    AuthenticationConfigurationError,
    AuthenticationUnavailable,
    InvalidAccessToken,
    SupabaseTokenAuthenticator,
)
from ai_support import SupportService, error_response
import database
from migrate import check_health_ready_async
from support_http import (
    MAX_SUPPORT_BODY_BYTES, SUPPORT_READ_TIMEOUT_SECONDS,
    _is_supported_content_type, _normalize_common_support_payload,
    _reject_json_constant, _unique_json_object,
)


def _check_readiness():
    asyncio.run(database.probe(check_health_ready_async))


class HealthHandler(BaseHTTPRequestHandler):
    server_version = "NIKNOLIGBackend"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(SUPPORT_READ_TIMEOUT_SECONDS)

    def do_GET(self):
        path = self.path.partition("?")[0]
        if path == "/health/live":
            self._send_json(200, {"status": "live"})
        elif path == "/health/ready":
            try:
                self.server.readiness_probe()
            except Exception:
                self._send_json(
                    503,
                    {
                        "error": {
                            "code": "SERVICE_UNAVAILABLE",
                            "message": "Service is temporarily unavailable.",
                            "requestId": str(uuid4()),
                        }
                    },
                )
            else:
                self._send_json(200, {"status": "ready"})
        elif path == "/v1/session":
            self._get_session()
        else:
            self._send_json(
                404,
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Resource was not found.",
                        "requestId": str(uuid4()),
                    }
                },
            )

    def _get_session(self):
        authorization = self.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if (
            scheme.lower() != "bearer"
            or not separator
            or not token
            or " " in token
            or len(token) > 16_384
        ):
            self._send_error(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
            return

        if self.server.authenticator is None:
            self._send_error(
                503,
                "SERVICE_UNAVAILABLE",
                "Authentication is temporarily unavailable.",
            )
            return
        try:
            _, app_area = self.server.authenticator.authenticate(token)
        except AppAreaMismatch:
            self._send_error(
                403,
                "APP_AREA_MISMATCH",
                "The token is not valid for this app area.",
            )
        except AuthenticationUnavailable:
            self._send_error(
                503,
                "SERVICE_UNAVAILABLE",
                "Authentication is temporarily unavailable.",
            )
        except InvalidAccessToken:
            self._send_error(401, "AUTHENTICATION_INVALID", "The access token is invalid.")
        except AuthenticationConfigurationError:
            self._send_error(
                503,
                "SERVICE_UNAVAILABLE",
                "Authentication is temporarily unavailable.",
            )
        else:
            self._send_json(200, {"authenticated": True, "appArea": app_area})

    def _send_error(self, status, code, message):
        self._send_json(
            status,
            {
                "error": {
                    "code": code,
                    "message": message,
                    "requestId": str(uuid4()),
                }
            },
        )

    def do_POST(self):
        self.close_connection = True
        if self.path not in ("/support", "/v1/ai/support"):
            self._send_json(*error_response(404, "NOT_FOUND"))
            return
        common_support_route = self.path == "/support"
        lengths = self.headers.get_all("Content-Length", [])
        if (self.headers.get_all("Transfer-Encoding") or len(lengths) != 1 or
                not lengths[0].isascii() or not lengths[0].isdigit() or
                len(lengths[0]) > 8 or
                len(self.headers.get_all("Authorization", [])) > 1 or
                len(self.headers.get_all("Content-Type", [])) != 1 or
                not _is_supported_content_type(self.headers["Content-Type"]) or
                self.headers.get_all("Content-Encoding")):
            self._send_json(*error_response(400, "VALIDATION_FAILED"))
            return
        length = int(lengths[0])
        if length > MAX_SUPPORT_BODY_BYTES:
            self._send_json(*error_response(413, "PAYLOAD_TOO_LARGE"))
            return
        try:
            deadline = time.monotonic() + SUPPORT_READ_TIMEOUT_SECONDS
            chunks, remaining = [], length
            while remaining:
                timeout = deadline - time.monotonic()
                if timeout <= 0:
                    raise TimeoutError("Body deadline expired")
                self.connection.settimeout(timeout)
                chunk = self.rfile.read1(remaining)
                if not chunk:
                    raise ValueError("Incomplete body")
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            payload = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
            if type(payload) is not dict:
                raise ValueError("JSON object required")
        except TimeoutError:
            self._send_json(*error_response(408, "REQUEST_TIMEOUT"))
            return
        except (ValueError, UnicodeError, RecursionError):
            self._send_json(*error_response(400, "VALIDATION_FAILED"))
            return
        finally:
            self.connection.settimeout(SUPPORT_READ_TIMEOUT_SECONDS)
        if common_support_route:
            payload = _normalize_common_support_payload(payload)
            if payload is None:
                self._send_json(*error_response(400, "VALIDATION_FAILED"))
                return
        try:
            response = self.server.support_service.handle(
                self.headers.get("Authorization"), payload
            )
        except Exception:
            response = error_response(503, "SERVICE_UNAVAILABLE", escalate=True)
        self._send_json(*response)

    def _send_json(self, status, body):
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format_string, *args):
        return


def create_server(host, port, *, support_service=None, readiness_probe=None, authenticator=None):
    server = ThreadingHTTPServer((host, port), HealthHandler)
    # Injection is for local preparation tests; main has no enabling path.
    server.support_service = support_service or SupportService()
    server.readiness_probe = (
        _check_readiness if readiness_probe is None else readiness_probe
    )
    server.daemon_threads = True
    server.authenticator = authenticator
    return server


def main():
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    raw_port = os.environ.get("BACKEND_PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise SystemExit("BACKEND_PORT must be an integer between 1 and 65535.") from error
    if not 1 <= port <= 65535:
        raise SystemExit("BACKEND_PORT must be an integer between 1 and 65535.")

    try:
        authenticator = SupabaseTokenAuthenticator(os.environ)
    except AuthenticationConfigurationError:
        authenticator = None
    server = create_server(host, port, authenticator=authenticator)
    print(f"Local backend listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
