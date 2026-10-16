import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from authentication import (
    AppAreaMismatch,
    AuthenticationConfigurationError,
    AuthenticationUnavailable,
    InvalidAccessToken,
    SupabaseTokenAuthenticator,
)
from database import check_database


class HealthHandler(BaseHTTPRequestHandler):
    server_version = "NIKNOLIGBackend"
    sys_version = ""

    def do_GET(self):
        path = self.path.partition("?")[0]
        if path == "/health/live":
            self._send_json(200, {"status": "live"})
        elif path == "/health/ready":
            if self.server.readiness_check():
                self._send_json(200, {"status": "ready"})
            else:
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


def create_server(
    host, port, readiness_check=check_database, authenticator=None
):
    server = ThreadingHTTPServer((host, port), HealthHandler)
    server.daemon_threads = True
    server.readiness_check = readiness_check
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
