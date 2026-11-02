"""Fail-closed app-scope policy for claims verified by a trusted adapter."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Mapping

APP_AREAS = frozenset({"niknolig", "niknolig-defense"})
ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9:_-]{0,127}$")
REQUIRED_CLAIMS = frozenset(
    {"iss", "aud", "sub", "exp", "app_area", "actions", "device_verified"}
)
MAX_ACTIONS = 64


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    code: str


def authorize_verified_claims(
    claims: Any,
    *,
    expected_issuer: str,
    expected_audience: str,
    resource_app_area: str,
    action: str,
    now: int | None = None,
) -> AuthorizationDecision:
    """Authorize one action from trusted, signature-verified claims.

    This function does not parse or verify tokens and must never receive
    client-supplied claims directly.
    """
    if (
        not isinstance(claims, Mapping)
        or not REQUIRED_CLAIMS.issubset(claims)
        or not isinstance(expected_issuer, str)
        or not expected_issuer
        or not isinstance(expected_audience, str)
        or not expected_audience
    ):
        return AuthorizationDecision(False, "AUTHENTICATION_INVALID")

    subject = claims["sub"]
    actions = claims["actions"]
    expires_at = claims["exp"]
    if (
        claims["iss"] != expected_issuer
        or claims["aud"] != expected_audience
        or not isinstance(subject, str)
        or not subject.strip()
        or len(subject) > 256
        or type(expires_at) is not int
        or not isinstance(actions, list)
        or len(actions) > MAX_ACTIONS
        or any(
            not isinstance(candidate, str) or not ACTION_PATTERN.fullmatch(candidate)
            for candidate in actions
        )
        or len(actions) != len(set(actions))
    ):
        return AuthorizationDecision(False, "AUTHENTICATION_INVALID")

    current_time = int(time.time()) if now is None else now
    if type(current_time) is not int or expires_at <= current_time:
        return AuthorizationDecision(False, "AUTHENTICATION_INVALID")

    claim_app_area = claims["app_area"]
    if not isinstance(claim_app_area, str) or claim_app_area not in APP_AREAS:
        return AuthorizationDecision(False, "AUTHENTICATION_INVALID")
    if not isinstance(resource_app_area, str) or resource_app_area not in APP_AREAS:
        return AuthorizationDecision(False, "AUTHORIZATION_DENIED")
    if claim_app_area != resource_app_area:
        return AuthorizationDecision(False, "APP_AREA_MISMATCH")
    if claims["device_verified"] is not True:
        return AuthorizationDecision(False, "DEVICE_IDENTITY_UNVERIFIED")
    if not isinstance(action, str) or not ACTION_PATTERN.fullmatch(action):
        return AuthorizationDecision(False, "AUTHORIZATION_DENIED")
    if action not in actions:
        return AuthorizationDecision(False, "AUTHORIZATION_DENIED")

    return AuthorizationDecision(True, "AUTHORIZED")
