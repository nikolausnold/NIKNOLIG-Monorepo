"""Strict Supabase-compatible JWT verification for protected API operations."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

APP_AREAS = frozenset({"niknolig", "niknolig-defense"})
ALLOWED_ALGORITHMS = ("ES256", "RS256")
MAX_TOKEN_LENGTH = 16_384


class AuthenticationConfigurationError(ValueError):
    pass


class AuthenticationUnavailable(RuntimeError):
    pass


class InvalidAccessToken(ValueError):
    pass


class AppAreaMismatch(PermissionError):
    pass


def _valid_https_url(value: object, *, path: str | None = None) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and parsed.query == ""
        and parsed.fragment == ""
        and (path is None or parsed.path == path)
    )


class SupabaseTokenAuthenticator:
    def __init__(self, settings: Mapping[str, str], jwks_client=None):
        self.issuer = settings.get("AUTH_ISSUER", "").strip().rstrip("/")
        self.audience = settings.get("AUTH_AUDIENCE", "").strip()
        self.app_area = settings.get("BACKEND_APP_AREA", "").strip()
        self.jwks_url = settings.get("AUTH_JWKS_URL", "").strip()

        issuer = urlparse(self.issuer)
        jwks = urlparse(self.jwks_url)
        if (
            not _valid_https_url(self.issuer, path="/auth/v1")
            or not _valid_https_url(
                self.jwks_url, path="/auth/v1/.well-known/jwks.json"
            )
            or issuer.hostname != jwks.hostname
            or not issuer.hostname.endswith(".supabase.co")
            or not self.audience
            or len(self.audience) > 256
            or self.app_area not in APP_AREAS
        ):
            raise AuthenticationConfigurationError(
                "Supabase issuer, JWKS, audience, and app area must be configured."
            )

        self._jwks_client = jwks_client or PyJWKClient(
            self.jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=300,
            timeout=3,
        )

    def authenticate(self, token: str) -> tuple[str, str]:
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
            raise InvalidAccessToken
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                leeway=30,
                options={
                    "require": ["exp", "iss", "aud", "sub"],
                },
            )
        except PyJWKClientConnectionError as error:
            raise AuthenticationUnavailable from error
        except (PyJWTError, TypeError, ValueError) as error:
            raise InvalidAccessToken from error

        subject = claims.get("sub")
        app_metadata = claims.get("app_metadata")
        if (
            not isinstance(subject, str)
            or not subject.strip()
            or len(subject) > 256
            or not isinstance(app_metadata, Mapping)
        ):
            raise InvalidAccessToken
        claim_app_area = app_metadata.get("app_area")
        if claim_app_area not in APP_AREAS:
            raise InvalidAccessToken
        if claim_app_area != self.app_area:
            raise AppAreaMismatch
        return subject, self.app_area
