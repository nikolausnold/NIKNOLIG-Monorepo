import json
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_server
from authentication import (
    AppAreaMismatch,
    AuthenticationConfigurationError,
    AuthenticationUnavailable,
    SupabaseTokenAuthenticator,
)


ISSUER = "https://test-project.supabase.co/auth/v1"
SETTINGS = {
    "AUTH_ISSUER": ISSUER,
    "AUTH_JWKS_URL": ISSUER + "/.well-known/jwks.json",
    "AUTH_AUDIENCE": "authenticated",
    "BACKEND_APP_AREA": "niknolig",
}


class MockJwksClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self.key)


class SupabaseAuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()

    def setUp(self):
        self.authenticator = SupabaseTokenAuthenticator(
            SETTINGS, jwks_client=MockJwksClient(self.public_key)
        )
        self.server = create_server(
            "127.0.0.1", 0, lambda: True, authenticator=self.authenticator
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def token(self, **changes):
        claims = {
            "iss": ISSUER,
            "aud": "authenticated",
            "sub": "synthetic-principal",
            "exp": int(time.time()) + 300,
            "app_metadata": {"app_area": "niknolig"},
            "user_metadata": {"app_area": "niknolig-defense"},
        }
        claims.update(changes)
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    def request(self, token=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = Request(self.base_url + "/v1/session", headers=headers)
        return urlopen(request, timeout=2)

    def test_valid_signature_and_server_managed_app_area_authenticate(self):
        with self.request(self.token()) as response:
            self.assertEqual(200, response.status)
            self.assertEqual(
                {"authenticated": True, "appArea": "niknolig"},
                json.load(response),
            )

    def test_missing_token_is_rejected(self):
        with self.assertRaises(HTTPError) as raised:
            self.request()
        self.assertEqual(401, raised.exception.code)
        self.assertEqual(
            "AUTHENTICATION_REQUIRED",
            json.load(raised.exception)["error"]["code"],
        )

    def test_invalid_signature_expiration_issuer_and_audience_are_rejected(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cases = (
            jwt.encode(
                {
                    "iss": ISSUER,
                    "aud": "authenticated",
                    "sub": "synthetic-principal",
                    "exp": int(time.time()) + 300,
                    "app_metadata": {"app_area": "niknolig"},
                },
                other_key,
                algorithm="RS256",
            ),
            self.token(exp=int(time.time()) - 1),
            self.token(iss="https://attacker.supabase.co/auth/v1"),
            self.token(aud="another-api"),
        )
        for token in cases:
            with self.subTest(token=token[:24]):
                with self.assertRaises(HTTPError) as raised:
                    self.request(token)
                self.assertEqual(401, raised.exception.code)
                self.assertEqual(
                    "AUTHENTICATION_INVALID",
                    json.load(raised.exception)["error"]["code"],
                )

    def test_client_editable_user_metadata_cannot_override_app_area(self):
        token = self.token(
            app_metadata={"app_area": "niknolig-defense"},
            user_metadata={"app_area": "niknolig"},
        )
        with self.assertRaises(HTTPError) as raised:
            self.request(token)
        self.assertEqual(403, raised.exception.code)
        self.assertEqual("APP_AREA_MISMATCH", json.load(raised.exception)["error"]["code"])

    def test_unavailable_jwks_fails_closed_without_token_details(self):
        class UnavailableClient:
            def get_signing_key_from_jwt(self, token):
                raise AuthenticationUnavailable

        self.server.authenticator = SupabaseTokenAuthenticator(
            SETTINGS, jwks_client=UnavailableClient()
        )
        with self.assertRaises(HTTPError) as raised:
            self.request(self.token())
        self.assertEqual(503, raised.exception.code)
        self.assertEqual("SERVICE_UNAVAILABLE", json.load(raised.exception)["error"]["code"])

    def test_authentication_configuration_is_limited_to_supabase_https_urls(self):
        for changes in (
            {"AUTH_ISSUER": "http://test-project.supabase.co/auth/v1"},
            {"AUTH_JWKS_URL": "https://attacker.example/auth/v1/.well-known/jwks.json"},
            {"BACKEND_APP_AREA": "other"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(AuthenticationConfigurationError):
                    SupabaseTokenAuthenticator(SETTINGS | changes)

    def test_product_area_claim_must_be_server_managed(self):
        token = self.token(app_metadata={}, user_metadata={"app_area": "niknolig"})
        with self.assertRaises(HTTPError) as raised:
            self.request(token)
        self.assertEqual(401, raised.exception.code)
        self.assertEqual("AUTHENTICATION_INVALID", json.load(raised.exception)["error"]["code"])


if __name__ == "__main__":
    unittest.main()
