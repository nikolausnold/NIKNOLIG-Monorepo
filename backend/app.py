import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4


def database_is_ready():
    names = (
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    )
    values = {name: os.environ.get(name) for name in names}
    if not any(values.values()):
        return True
    if not all(values.values()):
        return False

    try:
        port = int(values["DATABASE_PORT"])
        if not 1 <= port <= 65535:
            return False
        import psycopg

        connection_options = {
            "host": values["DATABASE_HOST"],
            "port": port,
            "dbname": values["DATABASE_NAME"],
            "user": values["DATABASE_USER"],
            "connect_timeout": 2,
        }
        connection_options["password"] = values["DATABASE_PASSWORD"]
        with psycopg.connect(**connection_options) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except Exception:
        return False


class HealthHandler(BaseHTTPRequestHandler):
    server_version = "NIKNOLIGBackend"
    sys_version = ""

    def do_GET(self):
        path = self.path.partition("?")[0]
        if path == "/health/live":
            self._send_json(200, {"status": "live"})
        elif path == "/health/ready":
            try:
                ready = self.server.readiness_check()
            except Exception:
                ready = False
            if ready:
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


def create_server(host, port, readiness_check=None):
    server = ThreadingHTTPServer((host, port), HealthHandler)
    server.daemon_threads = True
    server.readiness_check = (
        database_is_ready if readiness_check is None else readiness_check
    )
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

    server = create_server(host, port)
    print(f"Health-only backend listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
