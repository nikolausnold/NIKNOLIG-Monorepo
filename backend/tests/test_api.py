"""HTTP unit tests plus opt-in PostgreSQL integration tests.

TEST_DATABASE_DSN must name a disposable local database with CREATE SCHEMA
permission. Integration fixtures use/drop only randomly named private schemas.
No test framework or dependency is needed for legacy test discovery.
"""

import base64
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import mock_open, patch

try:
    import jwt
    import psycopg
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from psycopg import sql
    from psycopg.rows import dict_row
    from backend.api import create_app
    from backend.store import Conflict, Denied, NotFound, PostgresStore, RateLimited, Unavailable
    DEPS = True
except ImportError:
    DEPS = False


if DEPS:
    class MemoryStore:
        """Test double only; production always uses PostgresStore."""

        def __init__(self):
            self.devices = {}
            self.challenges = {}
            self.revoked = set()
            self.available = True
            self.limited = False

        def check(self):
            if not self.available:
                raise Unavailable()

        def ready(self):
            self.check()
            return True

        def authorize(self, token_hash, area, principal):
            self.check()
            if token_hash in self.revoked:
                raise Denied()
            if self.limited:
                raise RateLimited()

        def logout(self, token_hash, expires):
            self.check()
            self.revoked.add(token_hash)

        def register(self, area, principal, installation_id, key, fingerprint):
            self.check()
            if any(d["appArea"] == area and (
                d["installationId"] == str(installation_id) or d["fingerprint"] == fingerprint
            ) for d in self.devices.values()):
                raise Conflict()
            device_id = str(uuid.uuid4())
            self.devices[device_id] = {
                "id": device_id, "installationId": str(installation_id), "appArea": area,
                "principal": principal, "identityState": "pending", "createdAt": "2026-01-01T00:00:00Z",
                "verifiedAt": None, "revokedAt": None, "key": key, "fingerprint": fingerprint,
            }
            return self.public(self.devices[device_id])

        @staticmethod
        def public(device):
            return {k: v for k, v in device.items() if k not in ("principal", "key", "fingerprint")}

        def owned(self, area, principal, device_id):
            self.check()
            device = self.devices.get(str(device_id))
            if not device or device["appArea"] != area or device["principal"] != principal:
                raise NotFound()
            return device

        def get_device(self, area, principal, device_id):
            return self.public(self.owned(area, principal, device_id))

        def list_devices(self, area, principal):
            self.check()
            return [self.public(d) for d in self.devices.values()
                    if d["appArea"] == area and d["principal"] == principal][:100]

        def revoke(self, area, principal, device_id):
            device = self.owned(area, principal, device_id)
            device["identityState"] = "revoked"
            device["revokedAt"] = device["revokedAt"] or "2026-01-01T00:00:01Z"
            return self.public(device)

        def challenge(self, area, principal, device_id):
            device = self.owned(area, principal, device_id)
            if device["identityState"] == "revoked":
                raise Denied()
            challenge_id = str(uuid.uuid4())
            self.challenges[str(device_id)] = {
                "challengeId": challenge_id,
                "message": "\n".join(("NIKNOLIG-DEVICE-POSSESSION", "v1", area,
                                      str(device_id), challenge_id, uuid.uuid4().hex)),
                "expiresAt": "2026-01-01T00:02:00Z", "expired": False,
            }
            return {k: v for k, v in self.challenges[str(device_id)].items() if k != "expired"}

        def verify(self, area, principal, device_id, challenge_id, signature):
            device = self.owned(area, principal, device_id)
            challenge = self.challenges.get(str(device_id))
            if not challenge or challenge["challengeId"] != str(challenge_id):
                raise Denied()
            self.challenges.pop(str(device_id))
            if device["identityState"] == "revoked" or challenge["expired"]:
                raise Denied()
            try:
                key = serialization.load_pem_public_key(device["key"].encode())
                key.verify(signature, challenge["message"].encode(), ec.ECDSA(hashes.SHA256()))
            except InvalidSignature:
                raise Denied() from None
            device["identityState"] = "verified"
            device["verifiedAt"] = device["verifiedAt"] or "2026-01-01T00:00:01Z"
            return self.public(device)


@unittest.skipUnless(DEPS, "optional backend API dependencies are not installed")
class StoreConfigTests(unittest.TestCase):
    def test_explicit_pg_environment_and_connection_limits(self):
        environment = {"PGHOST": "postgres", "PGPORT": "5432", "PGDATABASE": "local_db",
                       "PGUSER": "local_runtime", "PGPASSWORD": "fixture-only"}
        with patch.dict(os.environ, environment, clear=True), patch(
            "backend.store.psycopg.connect",
        ) as connect:
            PostgresStore()._connect()
        options = connect.call_args.kwargs
        self.assertEqual(options["host"], "postgres")
        self.assertEqual(options["port"], "5432")
        self.assertEqual(options["dbname"], "local_db")
        self.assertEqual(options["user"], "local_runtime")
        self.assertEqual(options["password"], "fixture-only")
        self.assertEqual(options["connect_timeout"], 3)
        self.assertIn("statement_timeout=3000", options["options"])

    def test_default_host_port_without_superuser_fallback(self):
        environment = {"PGDATABASE": "local_db", "PGUSER": "local_runtime",
                       "PGPASSWORD": "fixture-only", "POSTGRES_USER": "postgres"}
        with patch.dict(os.environ, environment, clear=True), patch(
            "backend.store.psycopg.connect",
        ) as connect:
            PostgresStore()._connect()
        self.assertEqual(connect.call_args.kwargs["host"], "127.0.0.1")
        self.assertEqual(connect.call_args.kwargs["port"], "54329")
        for missing in ("PGDATABASE", "PGUSER", "PGPASSWORD"):
            with self.subTest(missing=missing), patch.dict(
                os.environ, {k: v for k, v in environment.items() if k != missing}, clear=True,
            ), patch("backend.store.psycopg.connect") as connect:
                with self.assertRaises(Unavailable):
                    PostgresStore()._connect()
                connect.assert_not_called()

    def test_database_dsn_is_explicit_test_injection_only(self):
        with patch.dict(os.environ, {"DATABASE_DSN": "ignored"}, clear=True), patch(
            "backend.api.PostgresStore",
        ) as store:
            create_app()
            store.assert_called_once_with(None)
        with patch("backend.api.PostgresStore") as store:
            create_app({"DATABASE_DSN": "injected-test-dsn"})
            store.assert_called_once_with("injected-test-dsn")

    def test_backend_directory_wsgi_import(self):
        result = subprocess.run(
            [sys.executable, "-c", "import api; assert api.create_app().test_client().get("
             "'/health/live').status_code == 200"],
            cwd=Path(__file__).resolve().parents[1],
            env=dict(os.environ, BACKEND_API_ENABLED="false"),
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(DEPS, "optional backend API dependencies are not installed")
class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_pem = cls.signing_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def new_store(self):
        return MemoryStore()

    def setUp(self):
        self.store = self.new_store()
        self.config = {
            "TESTING": True, "BACKEND_API_ENABLED": True,
            "BACKEND_ALLOW_INSECURE_LOCAL": True, "AUTH_PUBLIC_KEY_FILE": "injected.pem",
            "AUTH_ISSUER": "https://issuer.example", "AUTH_AUDIENCE_NIKNOLIG": "niknolig-api",
            "AUTH_AUDIENCE_DEFENSE": "defense-api",
        }
        self.app = self.make_app()
        self.client = self.app.test_client()
        self.device_key = ec.generate_private_key(ec.SECP256R1())
        self.device_pem = self.device_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def make_app(self, changes=None):
        config = dict(self.config, **(changes or {}))
        with patch("builtins.open", mock_open(read_data=self.public_pem)):
            return create_app(config, self.store)

    def token(self, changes=None, remove=(), algorithm="RS256", headers=None):
        now = int(time.time())
        claims = {
            "iss": "https://issuer.example", "aud": "niknolig-api", "sub": "principal-a",
            "iat": now, "exp": now + 900, "jti": str(uuid.uuid4()), "app_area": "niknolig",
            "scope": "auth:read auth:revoke devices:read devices:write",
        }
        claims.update(changes or {})
        for key in remove:
            claims.pop(key, None)
        key = self.signing_key if algorithm == "RS256" else b"not-a-production-secret-test-only-key"
        return jwt.encode(claims, key, algorithm=algorithm, headers=headers or {"typ": "at+jwt"})

    def headers(self, token=None, area="niknolig"):
        return {"Authorization": " ".join(("Bearer", token or self.token())), "X-App-Area": area}

    def register(self, token=None, area="niknolig", key=None):
        return self.client.post("/v1/devices", headers=self.headers(token, area), json={
            "installationId": str(uuid.uuid4()), "publicKey": key or self.device_pem,
        })

    def new_device(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["id"]

    def new_challenge(self, device_id):
        response = self.client.post(
            f"/v1/devices/{device_id}/challenge", headers=self.headers(), json={},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def signed(self, challenge, key=None):
        signature = (key or self.device_key).sign(
            challenge["message"].encode("utf-8"), ec.ECDSA(hashes.SHA256()),
        )
        return {"challengeId": challenge["challengeId"],
                "signature": base64.b64encode(signature).decode("ascii")}

    def test_health_and_gate(self):
        self.assertEqual(self.client.get("/health/live").status_code, 200)
        self.assertEqual(self.client.get("/health/live").get_json(), {"status": "live"})
        self.assertEqual(self.client.get("/health/ready").status_code, 200)
        client = self.make_app({"BACKEND_API_ENABLED": False}).test_client()
        self.assertEqual(client.get("/health/live").status_code, 200)
        self.assertEqual(client.get("/health/ready").status_code, 503)
        self.assertEqual(client.get("/v1/auth/session", headers=self.headers()).status_code, 503)
        self.assertEqual(client.options("/v1/devices").status_code, 503)
        with patch.dict(os.environ, {}, clear=True):
            default = create_app(store=self.store).test_client()
        self.assertEqual(default.get("/health/ready").status_code, 503)
        self.assertEqual(default.get("/v1/auth/session", headers=self.headers()).status_code, 503)

    def test_auth_config_fail_closed(self):
        for changes in (
            {"AUTH_ISSUER": "http://issuer.example"},
            {"AUTH_AUDIENCE_DEFENSE": "niknolig-api"},
            {"AUTH_AUDIENCE_NIKNOLIG": ""},
        ):
            with self.subTest(changes=changes):
                client = self.make_app(changes).test_client()
                self.assertEqual(client.get("/health/ready").status_code, 503)
                self.assertEqual(client.get("/v1/auth/session", headers=self.headers()).status_code, 503)
        with patch("builtins.open", side_effect=FileNotFoundError("sensitive-path")):
            client = create_app(self.config, self.store).test_client()
        response = client.get("/v1/auth/session", headers=self.headers())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"sensitive-path", response.data)

    def test_https_forwarded_headers_not_trusted(self):
        client = self.make_app({"BACKEND_ALLOW_INSECURE_LOCAL": False}).test_client()
        headers = dict(self.headers(), **{"X-Forwarded-Proto": "https"})
        self.assertEqual(client.get("/v1/auth/session", headers=headers).status_code, 400)
        self.assertEqual(client.get(
            "/v1/auth/session", headers=headers, base_url="https://localhost",
        ).status_code, 200)

    def test_session_minimal_scopes_and_headers(self):
        expires_at = int(time.time()) + 100
        response = self.client.get(
            "/v1/auth/session", headers=self.headers(self.token({"exp": expires_at})),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.get_json()), {"principal", "appArea", "scopes", "expiresAt"})
        self.assertEqual(response.get_json()["principal"], "principal-a")
        self.assertIs(type(response.get_json()["expiresAt"]), int)
        self.assertEqual(response.get_json()["expiresAt"], expires_at)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_jwt_rejections(self):
        now = int(time.time())
        invalid = [
            self.token({"exp": now - 1, "iat": now - 100}),
            self.token({"aud": "defense-api"}), self.token({"aud": ["niknolig-api", "defense-api"]}),
            self.token({"iss": "https://other.example"}), self.token({"app_area": "niknolig-defense"}),
            self.token({"app_area": "unknown"}), self.token({"sub": ""}),
            self.token({"exp": now + 901}), self.token({"iat": now + 10}),
            self.token({"iat": True}), self.token({"exp": float(now + 100)}),
            self.token({"jti": ""}), self.token({"scope": ["auth:read"]}),
            self.token({"scope": "admin"}), self.token({"scope": "auth:read auth:read"}),
            self.token(algorithm="HS256"), self.token(headers={"typ": "JWT"}),
            self.token(headers={"typ": "at+jwt", "crit": ["unknown"]}),
            "malformed", "a" * 8193,
        ] + [self.token(remove=(key,)) for key in (
            "iss", "aud", "sub", "exp", "iat", "jti", "app_area", "scope",
        )]
        for token in invalid:
            with self.subTest(token_case=invalid.index(token)):
                response = self.client.get("/v1/auth/session", headers=self.headers(token))
                self.assertEqual(response.status_code, 401, response.get_json())
                self.assertNotIn(token, response.get_data(as_text=True))
        self.assertEqual(self.client.get("/v1/auth/session").status_code, 401)
        for headers in ({"Authorization": " ".join(("Bearer", self.token()))},
                        self.headers(area="unknown")):
            response = self.client.get("/v1/auth/session", headers=headers)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json()["error"]["code"], "APP_AREA_MISMATCH")

    def test_scope_and_app_isolation(self):
        no_scope = self.token({"scope": "devices:read"})
        self.assertEqual(self.client.get(
            "/v1/auth/session", headers=self.headers(no_scope),
        ).status_code, 403)
        defense = self.token({"aud": "defense-api", "app_area": "niknolig-defense"})
        self.assertEqual(self.client.get(
            "/v1/auth/session", headers=self.headers(defense, "niknolig-defense"),
        ).status_code, 200)
        self.assertEqual(self.client.get(
            "/v1/auth/session", headers=self.headers(defense),
        ).status_code, 403)

    def test_uppercase_error_contract_and_authentication_classification(self):
        cases = (
            ({}, 401, "AUTHENTICATION_REQUIRED"),
            (self.headers("malformed"), 401, "AUTHENTICATION_INVALID"),
            (self.headers(area="unknown"), 403, "APP_AREA_MISMATCH"),
            (self.headers(self.token({"scope": "devices:read"})), 403, "AUTHORIZATION_DENIED"),
        )
        for headers, status, code in cases:
            with self.subTest(code=code):
                response = self.client.get("/v1/auth/session", headers=headers)
                self.assertEqual(response.status_code, status)
                self.assertEqual(set(response.get_json()["error"]), {"code", "message", "requestId"})
                self.assertEqual(response.get_json()["error"]["code"], code)
                self.assertIsInstance(response.get_json()["error"]["message"], str)

    def test_bodyless_logout_and_challenge(self):
        device_id = self.new_device()
        response = self.client.post(
            f"/v1/devices/{device_id}/challenge", headers=self.headers(),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.get_json()), {"challengeId", "message", "expiresAt"})
        self.assertEqual(self.client.post(
            "/v1/auth/logout", headers=self.headers(),
        ).status_code, 204)

    def test_logout_revokes_across_app_instances(self):
        token = self.token()
        self.assertEqual(self.client.post(
            "/v1/auth/logout", headers=self.headers(token), json={},
        ).status_code, 204)
        other_client = self.make_app().test_client()
        self.assertEqual(other_client.get(
            "/v1/auth/session", headers=self.headers(token),
        ).status_code, 403)

    def test_registration_list_and_conflict(self):
        device_id = self.new_device()
        response = self.client.get(f"/v1/devices/{device_id}", headers=self.headers())
        body = response.get_json()
        self.assertEqual(set(body), {
            "id", "installationId", "appArea", "identityState", "createdAt", "verifiedAt", "revokedAt",
        })
        self.assertEqual(body["identityState"], "pending")
        self.assertIsNone(body["verifiedAt"])
        self.assertIsNone(body["revokedAt"])
        self.assertNotIn("publicKey", body)
        self.assertEqual(self.register().status_code, 409)
        self.assertEqual(len(self.client.get(
            "/v1/devices", headers=self.headers(),
        ).get_json()["devices"]), 1)

    def test_ownership_for_all_resource_methods(self):
        device_id = self.new_device()
        foreign = self.token({"sub": "principal-b"})
        for method, suffix, body in (
            ("get", "", None), ("delete", "", None), ("post", "/challenge", {}),
            ("post", "/verify", {"challengeId": str(uuid.uuid4()), "signature": "AA=="}),
        ):
            response = getattr(self.client, method)(
                f"/v1/devices/{device_id}{suffix}", headers=self.headers(foreign), json=body,
            )
            self.assertEqual(response.status_code, 404)
        defense = self.token({"aud": "defense-api", "app_area": "niknolig-defense"})
        self.assertEqual(self.client.get(
            f"/v1/devices/{device_id}", headers=self.headers(defense, "niknolig-defense"),
        ).status_code, 404)
        self.assertEqual(self.client.get(
            "/v1/devices", headers=self.headers(foreign),
        ).get_json()["devices"], [])
        self.assertEqual(self.client.get(
            f"/v1/devices/{uuid.uuid4()}", headers=self.headers(),
        ).status_code, 404)

    def test_possession_valid_replay_and_terminal_revocation(self):
        device_id = self.new_device()
        challenge = self.new_challenge(device_id)
        self.assertEqual(challenge["message"].split("\n")[:5], [
            "NIKNOLIG-DEVICE-POSSESSION", "v1", "niknolig", device_id, challenge["challengeId"],
        ])
        body = self.signed(challenge)
        response = self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=body,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["identityState"], "verified")
        self.assertIsNotNone(response.get_json()["verifiedAt"])
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=body,
        ).status_code, 403)
        outstanding = self.new_challenge(device_id)
        revoke = self.client.delete(f"/v1/devices/{device_id}", headers=self.headers())
        self.assertEqual(revoke.status_code, 204)
        self.assertEqual(revoke.data, b"")
        revoked = self.client.get(f"/v1/devices/{device_id}", headers=self.headers()).get_json()
        self.assertEqual(revoked["identityState"], "revoked")
        revoked_at = revoked["revokedAt"]
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=self.signed(outstanding),
        ).status_code, 403)
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/challenge", headers=self.headers(), json={},
        ).status_code, 403)
        self.assertEqual(self.client.delete(
            f"/v1/devices/{device_id}", headers=self.headers(),
        ).status_code, 204)
        self.assertEqual(self.client.get(
            f"/v1/devices/{device_id}", headers=self.headers(),
        ).get_json()["revokedAt"], revoked_at)

    def test_wrong_signature_consumes_challenge(self):
        device_id = self.new_device()
        challenge = self.new_challenge(device_id)
        wrong_key = ec.generate_private_key(ec.SECP256R1())
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(),
            json=self.signed(challenge, wrong_key),
        ).status_code, 403)
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=self.signed(challenge),
        ).status_code, 403)
        self.assertEqual(self.client.get(
            f"/v1/devices/{device_id}", headers=self.headers(),
        ).get_json()["identityState"], "pending")

    def test_signature_requires_canonical_padded_base64(self):
        device_id = self.new_device()
        challenge = self.new_challenge(device_id)
        body = self.signed(challenge)
        invalid = dict(body, signature=body["signature"] + "====")
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=invalid,
        ).status_code, 400)
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=body,
        ).status_code, 200)

    def expire(self, device_id):
        self.store.challenges[device_id]["expired"] = True

    def test_expired_and_replaced_challenges(self):
        device_id = self.new_device()
        old = self.new_challenge(device_id)
        fresh = self.new_challenge(device_id)
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=self.signed(old),
        ).status_code, 403)
        self.expire(device_id)
        self.assertEqual(self.client.post(
            f"/v1/devices/{device_id}/verify", headers=self.headers(), json=self.signed(fresh),
        ).status_code, 403)

    def test_json_validation_size_and_key_validation(self):
        body = {"installationId": str(uuid.uuid4()), "publicKey": self.device_pem}
        invalid = [
            dict(body, principal="victim"), dict(body, state="verified"),
            dict(body, installationId="not-a-uuid"),
            dict(body, publicKey=self.device_key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).decode()),
            dict(body, publicKey=self.device_pem + self.device_key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).decode()),
            dict(body, publicKey=ec.generate_private_key(ec.SECP384R1()).public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()),
            dict(body, publicKey=123), {}, [], None,
        ]
        for value in invalid:
            response = self.client.post(
                "/v1/devices", headers=self.headers(), data=__import__("json").dumps(value),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400, response.get_json())
        response = self.client.post("/v1/devices", headers=self.headers(), data="x" * 16385,
                                    content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.post(
            "/v1/devices", headers=self.headers(), data="{}",
        ).status_code, 415)
        self.assertEqual(self.client.post(
            "/v1/devices", headers=self.headers(), data='{"x":1,"x":2}',
            content_type="application/json",
        ).status_code, 400)
        self.assertEqual(self.client.post(
            "/v1/auth/logout", headers=self.headers(), json={"jti": "foreign"},
        ).status_code, 400)

    def unavailable(self):
        self.store.available = False

    def test_database_unavailable_fails_closed(self):
        self.unavailable()
        self.assertEqual(self.client.get("/health/live").status_code, 200)
        self.assertEqual(self.client.get("/health/ready").status_code, 503)
        self.assertEqual(self.register().status_code, 503)
        self.assertEqual(self.client.get("/v1/auth/session", headers=self.headers()).status_code, 503)
        self.assertEqual(self.client.post(
            "/v1/auth/logout", headers=self.headers(), json={},
        ).status_code, 503)

    def limit(self):
        self.store.limited = True

    def test_persistent_rate_limit_interface(self):
        self.limit()
        response = self.client.get("/v1/auth/session", headers=self.headers())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["error"]["code"], "RATE_LIMITED")
        self.assertEqual(response.headers["Retry-After"], "60")

    def test_consistent_generic_errors(self):
        for method, path, status in (
            ("get", "/unknown", 404), ("put", "/v1/devices", 405),
            ("options", "/v1/devices", 405),
            ("get", "/v1/devices/not-uuid", 400),
        ):
            response = getattr(self.client, method)(path, headers=self.headers())
            self.assertEqual(response.status_code, status)
            self.assertEqual(set(response.get_json()["error"]), {"code", "message", "requestId"})
            self.assertEqual(response.get_json()["error"]["code"], (
                "NOT_FOUND" if status == 404 else "VALIDATION_FAILED"
            ))
            uuid.UUID(response.get_json()["error"]["requestId"])
            self.assertNotIn("Traceback", response.get_data(as_text=True))


@unittest.skipUnless(DEPS and os.getenv("TEST_DATABASE_DSN"),
                     "set TEST_DATABASE_DSN for disposable PostgreSQL integration tests")
class PostgreSQLAPITests(APITests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dsn = os.environ["TEST_DATABASE_DSN"]
        cls.schema = "api_test_" + uuid.uuid4().hex
        with psycopg.connect(cls.dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        try:
            with cls.connection(autocommit=True) as conn:
                root = Path(__file__).resolve().parents[1] / "migrations"
                conn.execute((root / "001_initial_contract.sql").read_text())
                conn.execute((root / "002_backend_api.sql").read_text())
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def connection(cls, autocommit=False):
        return psycopg.connect(
            cls.dsn, row_factory=dict_row, autocommit=autocommit,
            options=f"-c search_path={cls.schema} -c statement_timeout=3000 -c lock_timeout=3000",
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "schema"):
            with psycopg.connect(cls.dsn, autocommit=True) as conn:
                conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema)))

    def new_store(self):
        with self.connection() as conn:
            conn.execute("TRUNCATE device_installations, backend_device_challenges, "
                         "backend_token_revocations, backend_rate_limits, device_links CASCADE")
        store = PostgresStore(self.dsn, principal_limit=1000)
        store._connect = self.connection
        return store

    def expire(self, device_id):
        with self.connection() as conn:
            # Keep the schema's expires-after-created invariant intact.
            conn.execute(
                "UPDATE backend_device_challenges SET created_at = now() - interval '121 seconds', "
                "expires_at = now() - interval '1 second' WHERE device_id = %s", (device_id,),
            )

    def unavailable(self):
        def fail():
            raise Unavailable()
        self.store._connect = fail

    def limit(self):
        self.store.principal_limit = 0

    def test_schema_readiness_checks_actual_tables(self):
        with self.connection() as conn:
            conn.execute("ALTER TABLE backend_device_challenges RENAME TO missing_challenges")
        try:
            self.assertEqual(self.client.get("/health/ready").status_code, 503)
        finally:
            with self.connection() as conn:
                conn.execute("ALTER TABLE missing_challenges RENAME TO backend_device_challenges")

    def test_pending_registration_cap_and_list_bound(self):
        from backend.store import digest
        with self.connection() as conn:
            for index in range(100):
                conn.execute(
                    "INSERT INTO device_installations "
                    "(id, app_area, principal_reference, installation_reference, public_key_fingerprint, public_key) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (uuid.uuid4(), "niknolig", "principal-a", uuid.uuid4(),
                     digest(str(index)), self.device_pem),
                )
        self.assertEqual(self.register().status_code, 409)
        self.assertEqual(len(self.client.get(
            "/v1/devices", headers=self.headers(),
        ).get_json()["devices"]), 100)

    def test_database_rate_counter_is_shared_and_atomic(self):
        self.store.principal_limit = 5
        other_store = PostgresStore(self.dsn, principal_limit=5)
        other_store._connect = self.connection
        with patch("builtins.open", mock_open(read_data=self.public_pem)):
            second = create_app(self.config, other_store).test_client()
        statuses = [second.get("/v1/auth/session", headers=self.headers()).status_code for _ in range(7)]
        self.assertEqual(statuses, [200] * 5 + [429] * 2)
        with self.connection() as conn:
            self.assertEqual(conn.execute(
                "SELECT count(*) AS count FROM backend_rate_limits",
            ).fetchone()["count"], 2)

    def test_revocation_persists_in_independent_store(self):
        token = self.token()
        self.assertEqual(self.client.post(
            "/v1/auth/logout", headers=self.headers(token), json={},
        ).status_code, 204)
        other_store = PostgresStore(self.dsn)
        other_store._connect = self.connection
        with patch("builtins.open", mock_open(read_data=self.public_pem)):
            second = create_app(self.config, other_store).test_client()
        self.assertEqual(second.get(
            "/v1/auth/session", headers=self.headers(token),
        ).status_code, 403)

    def test_pending_cap_is_atomic_with_concurrent_registrations(self):
        from backend.store import digest
        with self.connection() as conn:
            for index in range(99):
                conn.execute(
                    "INSERT INTO device_installations "
                    "(id, app_area, principal_reference, installation_reference, public_key_fingerprint, public_key) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (uuid.uuid4(), "niknolig", "principal-a", uuid.uuid4(),
                     digest(str(index)), self.device_pem),
                )
        token = self.token()
        barrier = threading.Barrier(2)

        def register():
            key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
            client = self.make_app().test_client()
            barrier.wait()
            return client.post("/v1/devices", headers=self.headers(token), json={
                "installationId": str(uuid.uuid4()), "publicKey": key,
            }).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: register(), range(2)))
        self.assertEqual(sorted(statuses), [201, 409])

    def test_two_verifiers_only_one_succeeds(self):
        device_id = self.new_device()
        challenge = self.new_challenge(device_id)
        barrier = threading.Barrier(2)
        body = self.signed(challenge)
        token = self.token()

        def verify():
            client = self.make_app().test_client()
            barrier.wait()
            return client.post(f"/v1/devices/{device_id}/verify",
                               headers=self.headers(token), json=body).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: verify(), range(2)))
        self.assertEqual(sorted(statuses), [200, 403])

    def test_verify_racing_revoke_cannot_resurrect(self):
        device_id = self.new_device()
        challenge = self.new_challenge(device_id)
        barrier = threading.Barrier(2)
        body = self.signed(challenge)
        token = self.token()

        def operation(revoking):
            client = self.make_app().test_client()
            barrier.wait()
            if revoking:
                return client.delete(f"/v1/devices/{device_id}",
                                     headers=self.headers(token)).status_code
            return client.post(f"/v1/devices/{device_id}/verify",
                               headers=self.headers(token), json=body).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(operation, (False, True)))
        self.assertIn(statuses[0], (200, 403))
        self.assertEqual(statuses[1], 204)
        state = self.client.get(f"/v1/devices/{device_id}", headers=self.headers()).get_json()
        self.assertEqual(state["identityState"], "revoked")
        self.assertIsNotNone(state["revokedAt"])

    def test_logout_database_failure_returns_503_without_success(self):
        with patch.object(self.store, "logout", side_effect=Unavailable()):
            response = self.client.post("/v1/auth/logout", headers=self.headers(), json={})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
