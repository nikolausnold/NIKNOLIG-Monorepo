"""Fail-closed operator preflight; does not establish DNS, reachability or P0 approval."""

import ipaddress
import os
import re
import ssl
import time


def validate_hostname(hostname, confirmed):
    if not hostname or hostname != confirmed or hostname != hostname.lower() or len(hostname) > 253:
        raise ValueError("An explicit, operator-confirmed real hostname is required")
    labels = hostname.split(".")
    if len(labels) < 2 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ) or not re.fullmatch(r"[a-z]{2,63}", labels[-1]):
        raise ValueError("A public DNS hostname, not a URL or IP, is required")
    reserved = (
        "localhost", "local", "internal", "invalid", "test", "example", "onion",
        "example.com", "example.net", "example.org",
    )
    if any(hostname == suffix or hostname.endswith("." + suffix) for suffix in reserved):
        raise ValueError("Reserved and local hostnames are not production targets")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return hostname
    raise ValueError("IP addresses are not production hostnames")


def validate_tls(hostname, certificate, private_key):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, private_key)
    # Decode the supplied leaf without adding a certificate-parsing dependency.
    cert = ssl._ssl._test_decode_cert(certificate)
    dns_names = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"]
    # Exact SAN binding is intentionally stricter than accepting wildcard certificates.
    if hostname not in dns_names:
        raise ValueError("The certificate requires an exact hostname SAN")
    now = time.time()
    if not ssl.cert_time_to_seconds(cert["notBefore"]) <= now < ssl.cert_time_to_seconds(cert["notAfter"]):
        raise ValueError("The certificate is not currently valid")


def main():
    try:
        hostname = validate_hostname(
            os.environ.get("BACKEND_HOSTNAME", ""),
            os.environ.get("BACKEND_HOSTNAME_CONFIRMED", ""),
        )
        validate_tls(hostname, "/run/secrets/tls_certificate", "/run/secrets/tls_private_key")
    except Exception:
        raise SystemExit("Deployment preflight failed: confirm a real hostname and matching valid TLS files.") from None
    print("Local hostname/certificate preflight passed; external DNS/TLS/security verification is still required.")


if __name__ == "__main__":
    main()
