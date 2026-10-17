#!/usr/bin/env python3
"""Offline heuristic URL triage; it never fetches, resolves, or follows a URL."""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit

MAX_URL_LENGTH = 2_048
CONTROL_CHARACTERS = re.compile(r"[\x00-\x20\x7f]")
NUMERIC_HOST = re.compile(r"^[0-9.]+$")
LOCAL_SUFFIXES = (".localhost", ".local", ".test", ".invalid", ".example")


def _result(status: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "assessment": "heuristic",
        "verified": False,
        "networkAccess": False,
        "reasons": reasons,
    }


def triage_url(value: Any) -> dict[str, Any]:
    """Flag structural URL risks without claiming that a URL is safe or malicious."""
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        return _result("REVIEW", ["invalid_or_oversized_input"])
    if CONTROL_CHARACTERS.search(value) or "\\" in value:
        return _result("REVIEW", ["invalid_url_characters"])

    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return _result("REVIEW", ["malformed_url"])

    reasons: list[str] = []
    if scheme not in {"http", "https"}:
        reasons.append("unsupported_scheme")
    elif scheme != "https":
        reasons.append("unencrypted_http")

    if not parsed.netloc or not host:
        reasons.append("missing_host")
        return _result("REVIEW", reasons)
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        reasons.append("userinfo_in_authority")
    if "%" in parsed.netloc:
        reasons.append("encoded_authority")

    normalized_host = host.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        address = None

    if address is not None:
        reasons.append("ip_literal_host")
        if not address.is_global:
            reasons.append("non_global_ip_literal")
    else:
        if NUMERIC_HOST.fullmatch(normalized_host):
            reasons.append("ambiguous_numeric_host")
        if not normalized_host or "." not in normalized_host:
            reasons.append("single_label_host")
        if normalized_host.endswith(LOCAL_SUFFIXES):
            reasons.append("non_public_host_suffix")
        try:
            ascii_host = normalized_host.encode("idna").decode("ascii")
        except UnicodeError:
            reasons.append("invalid_internationalized_host")
        else:
            if ascii_host != normalized_host:
                reasons.append("internationalized_or_punycode_host")
            if any(label.startswith("xn--") for label in ascii_host.split(".")):
                reasons.append("punycode_host")

    if port is not None and not 1 <= port <= 65535:
        reasons.append("invalid_port")
    if reasons:
        return _result("REVIEW", sorted(set(reasons)))
    return _result("UNASSESSED", [])
