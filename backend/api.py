"""Opt-in reference API. No token issuance, attestation, or production approval."""

import base64
import binascii
import json
import os
import time
import uuid
from functools import wraps
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from backend.store import Conflict, Denied, NotFound, PostgresStore, RateLimited, Unavailable, digest


SCOPES = frozenset(("auth:read", "auth:revoke", "devices:read", "devices:write"))
AREAS = {"niknolig": "AUTH_AUDIENCE_NIKNOLIG", "niknolig-defense": "AUTH_AUDIENCE_DEFENSE"}


class APIError(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


def _enabled(value):
    return value is True or (isinstance(value, str) and value.lower() == "true")


def _uuid(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError()
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise APIError(400, "invalid_request") from None


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _body(fields):
    if request.mimetype != "application/json":
        raise APIError(415, "unsupported_media_type")
    try:
        value = json.loads(request.get_data(), object_pairs_hook=_object)
    except (ValueError, UnicodeDecodeError):
        raise APIError(400, "invalid_request") from None
    if not isinstance(value, dict) or set(value) != set(fields):
        raise APIError(400, "invalid_request")
    return value


def create_app(config=None, store=None):
    app = Flask(__name__)
    app.config.update(
        BACKEND_API_ENABLED=os.getenv("BACKEND_API_ENABLED", "false"),
        BACKEND_ALLOW_INSECURE_LOCAL=os.getenv("BACKEND_ALLOW_INSECURE_LOCAL", "false"),
        AUTH_PUBLIC_KEY_FILE=os.getenv("AUTH_PUBLIC_KEY_FILE", ""),
        AUTH_ISSUER=os.getenv("AUTH_ISSUER", ""),
        AUTH_AUDIENCE_NIKNOLIG=os.getenv("AUTH_AUDIENCE_NIKNOLIG", ""),
        AUTH_AUDIENCE_DEFENSE=os.getenv("AUTH_AUDIENCE_DEFENSE", ""),
        DATABASE_DSN=os.getenv("DATABASE_DSN", ""),
        MAX_CONTENT_LENGTH=16 * 1024,
        DEBUG=False,
        PROPAGATE_EXCEPTIONS=False,
    )
    if config:
        app.config.update(config)
    # Do not permit a caller's debug setting to expose production error details.
    app.config.update(DEBUG=False, PROPAGATE_EXCEPTIONS=False, MAX_CONTENT_LENGTH=16 * 1024)
    authority = store if store is not None else PostgresStore(app.config["DATABASE_DSN"])
    verification_key = None
    try:
        issuer = app.config["AUTH_ISSUER"]
        parsed = urlsplit(issuer)
        audiences = [app.config[key] for key in AREAS.values()]
        if (not isinstance(issuer, str) or parsed.scheme != "https" or not parsed.netloc
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or any(not isinstance(a, str) or not a or len(a) > 512 for a in audiences)
                or audiences[0] == audiences[1]):
            raise ValueError()
        with open(app.config["AUTH_PUBLIC_KEY_FILE"], "rb") as key_file:
            key_bytes = key_file.read(16 * 1024 + 1)
        if len(key_bytes) > 16 * 1024:
            raise ValueError()
        verification_key = serialization.load_pem_public_key(key_bytes)
        if not isinstance(verification_key, rsa.RSAPublicKey) or verification_key.key_size < 2048:
            raise ValueError()
    except (OSError, ValueError, TypeError):
        verification_key = None

    @app.before_request
    def request_context():
        # Never reflect caller-controlled identifiers or trust forwarded headers.
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Request-ID"] = g.request_id
        return response

    def error(status, code):
        return jsonify(error={"code": code, "requestId": g.request_id}), status

    @app.errorhandler(APIError)
    def api_error(exc):
        return error(exc.status, exc.code)

    @app.errorhandler(Unavailable)
    def unavailable(_exc):
        return error(503, "unavailable")

    @app.errorhandler(Conflict)
    def conflict(_exc):
        return error(409, "conflict")

    @app.errorhandler(NotFound)
    def not_found(_exc):
        return error(404, "not_found")

    @app.errorhandler(Denied)
    def denied(_exc):
        return error(403, "forbidden")

    @app.errorhandler(RateLimited)
    def rate_limited(_exc):
        response, status = error(429, "rate_limited")
        response.headers["Retry-After"] = "60"
        return response, status

    @app.errorhandler(HTTPException)
    def http_error(exc):
        codes = {400: "invalid_request", 404: "not_found", 405: "method_not_allowed",
                 413: "request_too_large", 415: "unsupported_media_type"}
        return error(exc.code, codes.get(exc.code, "invalid_request"))

    @app.errorhandler(Exception)
    def unexpected(_exc):
        # Deliberately no exception/payload logging: DB errors may contain values.
        return error(500, "internal_error")

    def protected(scope):
        def decorate(function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                if not _enabled(app.config["BACKEND_API_ENABLED"]) or verification_key is None:
                    raise APIError(503, "unavailable")
                if not request.is_secure and not _enabled(app.config["BACKEND_ALLOW_INSECURE_LOCAL"]):
                    raise APIError(400, "https_required")
                area = request.headers.get("X-App-Area", "")
                if area not in AREAS:
                    raise APIError(401, "unauthorized")
                authorization = request.headers.get("Authorization", "")
                if (not authorization.startswith("Bearer ") or len(authorization) > 8199
                        or len(authorization.split()) != 2):
                    raise APIError(401, "unauthorized")
                token = authorization[7:]
                try:
                    header = jwt.get_unverified_header(token)
                    if header.get("typ") != "at+jwt" or header.get("alg") != "RS256" or header.get("crit"):
                        raise ValueError()
                    claims = jwt.decode(
                        token, verification_key, algorithms=["RS256"],
                        issuer=app.config["AUTH_ISSUER"], audience=app.config[AREAS[area]],
                        options={"require": ["iss", "aud", "sub", "exp", "iat", "jti", "app_area", "scope"],
                                 "strict_aud": True},
                        leeway=0,
                    )
                    if (claims["app_area"] != area
                            or any(type(claims[c]) is not int for c in ("iat", "exp"))
                            or claims["exp"] <= claims["iat"]
                            or claims["exp"] - claims["iat"] > 900
                            or claims["iat"] > time.time()
                            or any(not isinstance(claims[c], str) or not claims[c].strip()
                                   or len(claims[c]) > 256 for c in ("sub", "jti"))
                            or not isinstance(claims["scope"], str)):
                        raise ValueError()
                    scopes = claims["scope"].split()
                    if len(scopes) != len(set(scopes)) or not set(scopes) <= SCOPES:
                        raise ValueError()
                except (jwt.PyJWTError, ValueError, TypeError, KeyError):
                    raise APIError(401, "unauthorized") from None
                token_hash = digest(claims["iss"], claims["jti"])
                authority.authorize(token_hash, area, claims["sub"])
                if scope not in scopes:
                    raise APIError(403, "forbidden")
                g.area, g.principal, g.scopes = area, claims["sub"], sorted(scopes)
                g.token_hash, g.expires = token_hash, claims["exp"]
                return function(*args, **kwargs)
            return wrapped
        return decorate

    @app.get("/health/live")
    def live():
        return jsonify(status="ok")

    @app.get("/health/ready")
    def ready():
        if (not _enabled(app.config["BACKEND_API_ENABLED"]) or verification_key is None
                or not authority.ready()):
            raise APIError(503, "unavailable")
        return jsonify(status="ready")

    @app.get("/v1/auth/session")
    @protected("auth:read")
    def session():
        return jsonify(principal=g.principal, appArea=g.area, scopes=g.scopes)

    @app.post("/v1/auth/logout")
    @protected("auth:revoke")
    def logout():
        _body(())
        authority.logout(g.token_hash, g.expires)
        return "", 204

    @app.get("/v1/devices")
    @protected("devices:read")
    def devices():
        return jsonify(devices=authority.list_devices(g.area, g.principal))

    @app.post("/v1/devices")
    @protected("devices:write")
    def register():
        body = _body(("installationId", "publicKey"))
        installation_id = _uuid(body["installationId"])
        try:
            if not isinstance(body["publicKey"], str) or len(body["publicKey"]) > 2048:
                raise ValueError()
            key = serialization.load_pem_public_key(body["publicKey"].encode("ascii"))
            if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
                raise ValueError()
            public_key = key.public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("ascii")
            fingerprint_hash = hashes.Hash(hashes.SHA256())
            fingerprint_hash.update(key.public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
            ))
            fingerprint = fingerprint_hash.finalize().hex()
        except (ValueError, TypeError, UnicodeError):
            raise APIError(400, "invalid_request") from None
        result = authority.register(g.area, g.principal, installation_id, public_key, fingerprint)
        return jsonify(result), 201

    @app.get("/v1/devices/<device_id>")
    @protected("devices:read")
    def device(device_id):
        return jsonify(authority.get_device(g.area, g.principal, _uuid(device_id)))

    @app.delete("/v1/devices/<device_id>")
    @protected("devices:write")
    def revoke(device_id):
        return jsonify(authority.revoke(g.area, g.principal, _uuid(device_id)))

    @app.post("/v1/devices/<device_id>/challenge")
    @protected("devices:write")
    def challenge(device_id):
        _body(())
        return jsonify(authority.challenge(g.area, g.principal, _uuid(device_id))), 201

    @app.post("/v1/devices/<device_id>/verify")
    @protected("devices:write")
    def verify(device_id):
        body = _body(("challengeId", "signature"))
        challenge_id = _uuid(body["challengeId"])
        try:
            if not isinstance(body["signature"], str) or len(body["signature"]) > 144:
                raise ValueError()
            signature = base64.b64decode(body["signature"], validate=True)
        except (ValueError, binascii.Error):
            raise APIError(400, "invalid_request") from None
        return jsonify(authority.verify(
            g.area, g.principal, _uuid(device_id), challenge_id, signature,
        ))

    return app


app = create_app()
