"""Validate the app-specific Xcode backend setting without contacting a server."""

import ipaddress
import os
import re
import sys
from urllib.parse import urlsplit


VARIABLES = {
    "com.niknolig.app": "NIKNOLIG_BACKEND_URL",
    "com.niknolig.defense": "NIKNOLIG_DEFENSE_BACKEND_URL",
}


def validate(environment):
    variable = VARIABLES.get(environment.get("PRODUCT_BUNDLE_IDENTIFIER"))
    if variable is None:
        raise ValueError("Unknown app identity; backend configuration cannot be selected.")
    configuration = environment.get("CONFIGURATION")
    if not configuration:
        raise ValueError("Missing Xcode build configuration.")
    value = environment.get(variable, "").strip()
    if not value:
        if configuration == "Debug":
            return
        raise ValueError(f"Set {variable} to the operator-approved HTTPS origin for this app.")
    try:
        url = urlsplit(value)
        host = (url.hostname or "").lower().rstrip(".")
        port = url.port
        valid = (
            url.scheme.lower() == "https"
            and bool(host)
            and url.username is None
            and url.password is None
            and "?" not in value
            and "#" not in value
            and url.path in ("", "/")
            and (port is None or 1 <= port <= 65535)
            and not any(character.isspace() or ord(character) < 32 for character in value)
            and "\\" not in value
            and "%" not in url.netloc
            and not host.endswith(".invalid")
            and host != "invalid"
            and host != "localhost"
            and not host.endswith(".localhost")
        )
        if valid:
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                valid = len(host) <= 253 and all(
                    re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                    for label in host.split(".")
                ) and not re.fullmatch(r"[0-9.]+", host)
            else:
                if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
                    address = address.ipv4_mapped
                valid = not (address.is_loopback or address.is_unspecified)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            f"{variable} must be an HTTPS origin without credentials, path, query, "
            "fragment, placeholder or loopback host."
        )


def main():
    try:
        validate(os.environ)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
