import os
import sys
import time
import unittest
import uuid
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asgi
import device_api
import device_security as sec
import device_store
import migrate
from authentication import InvalidAccessToken

SECRET = b"s" * 48
ADMIN_URL = os.environ.get("BACKEND_TEST_DATABASE_URL")


class SecurityPrimitives(unittest.TestCase):
    def test_access_token_is_signed_and_expires(self):
        device, session = uuid.uuid4(), uuid.uuid4()
        token, expires = sec.issue_access_token(SECRET, device_id=device, session_id=session, area="niknolig", now=1000)
        self.assertEqual(expires, 1000 + sec.ACCESS_TOKEN_TTL_SECONDS)
        self.assertEqual(sec.verify_access_token(SECRET, token, now=1001)["sub"], str(device))
        with self.assertRaises(sec.TokenError):
            sec.verify_access_token(SECRET, token, now=expires)
        with self.assertRaises(sec.TokenError):
            sec.verify_access_token(b"x" * 48, token, now=1001)
        head, body, signature = token.split(".")
        with self.assertRaises(sec.TokenError):
            sec.verify_access_token(SECRET, f"{head}.{body}A.{signature}", now=1001)
        with self.assertRaises(sec.TokenError):
            sec.verify_access_token(SECRET, "v1.e30.AAAA", now=1001)

    def test_rate_limiter_window_and_bounds(self):
        now = [0.0]
        limiter = sec.SlidingWindowLimiter(2, 10, max_keys=2, clock=lambda: now[0])
        self.assertTrue(limiter.allow("a") and limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.exhausted("a"))
        self.assertTrue(limiter.allow("b"))
        self.assertFalse(limiter.allow("c"))  # bounded memory fails closed
        now[0] = 11
        self.assertTrue(limiter.allow("a"))

    def test_pairing_code_format_and_base64url_strictness(self):
        code = sec.new_pairing_code()
        self.assertEqual(sec.normalize_pairing_code(code.lower()), code)
        self.assertIsNone(sec.normalize_pairing_code("0O1I2345"))
        with self.assertRaises(ValueError):
            sec.b64url_decode("AA==")

    def test_short_secret_rejected(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w") as handle:
            handle.write("short")
            handle.flush()
            with self.assertRaises(ValueError):
                sec.load_signing_secret(handle.name)


@unittest.skipUnless(ADMIN_URL, "explicit disposable PostgreSQL test database required")
class DeviceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "device_api_" + uuid.uuid4().hex[:12]
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{cls.name}"')
        params = psycopg.conninfo.conninfo_to_dict(ADMIN_URL)
        params["dbname"] = cls.name
        cls.params = params
        with psycopg.connect(**params) as connection:
            migrate.migrate(connection, approve_contract=True, approve_device_api=True)
        cls.store = device_store.DeviceStore(lambda: psycopg.connect(**params), SECRET)

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{cls.name}" WITH (FORCE)')

    def setUp(self):
        def principal(token):
            kind, _, rest = token.partition(":")
            sub, _, area = rest.partition(":")
            if kind != "principal" or not sub or area not in ("niknolig", "niknolig-defense"):
                raise InvalidAccessToken
            return sub, area

        application = asgi.create_app(
            readiness_probe=lambda *_: None, environment="production")
        device_api.install(application, store=self.store, secret=SECRET, authenticate_principal=principal)
        self.client = TestClient(application)

    # ---- helpers --------------------------------------------------------
    def phone(self, area, sub=None, name="Phone"):
        return Phone(self.client, area, sub or f"user-{uuid.uuid4()}", name)

    def pair(self, a, b):
        pairing = a.post("/v1/pairings").json()
        claimed = b.post("/v1/pairings/claim", {"code": pairing["code"]})
        self.assertEqual(claimed.status_code, 200, claimed.text)
        self.assertEqual(a.post(f"/v1/pairings/{pairing['pairingId']}/confirm").status_code, 200)
        done = b.post(f"/v1/pairings/{pairing['pairingId']}/confirm").json()
        self.assertEqual(done["state"], "confirmed")
        return done["linkId"]

    # ---- identity and sessions -----------------------------------------
    def test_registration_requires_valid_principal_and_proof_of_possession(self):
        key = Ed25519PrivateKey.generate()
        public = Phone.public_bytes(key)
        installation = str(uuid.uuid4())
        body = {"installationId": installation, "publicKey": sec.b64url_encode(public),
                "proof": sec.b64url_encode(key.sign(b"wrong")), "displayName": "X"}
        response = self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer principal:u1:niknolig"})
        self.assertEqual(response.status_code, 401)
        body["proof"] = sec.b64url_encode(key.sign(sec.registration_message("niknolig", installation, "u1")))
        self.assertEqual(self.client.post("/v1/devices", json=body).status_code, 401)
        self.assertEqual(self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer bad"}).status_code, 401)
        ok = self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer principal:u1:niknolig"})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["fingerprint"], sec.fingerprint(public))
        again = self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer principal:u1:niknolig"})
        self.assertEqual(again.json()["id"], ok.json()["id"])
        other = Ed25519PrivateKey.generate()
        body["publicKey"] = sec.b64url_encode(Phone.public_bytes(other))
        body["proof"] = sec.b64url_encode(other.sign(sec.registration_message("niknolig", installation, "u1")))
        self.assertEqual(self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer principal:u1:niknolig"}).status_code, 409)
        body["installationId"] = "not-a-uuid"
        self.assertEqual(self.client.post("/v1/devices", json=body, headers={"Authorization": "Bearer principal:u1:niknolig"}).status_code, 400)

    def test_challenge_is_single_use_and_signature_bound_to_device(self):
        phone = self.phone("niknolig")
        nonce = self.client.post(f"/v1/devices/{phone.device_id}/challenge").json()["nonce"]
        signature = sec.b64url_encode(phone.key.sign(sec.session_message(phone.device_id, nonce)))
        body = {"nonce": nonce, "signature": signature}
        self.assertEqual(self.client.post(f"/v1/devices/{phone.device_id}/session", json=body).status_code, 201)
        self.assertEqual(self.client.post(f"/v1/devices/{phone.device_id}/session", json=body).status_code, 401)
        other = self.phone("niknolig")
        nonce = self.client.post(f"/v1/devices/{other.device_id}/challenge").json()["nonce"]
        forged = sec.b64url_encode(phone.key.sign(sec.session_message(other.device_id, nonce)))
        self.assertEqual(self.client.post(f"/v1/devices/{other.device_id}/session", json={"nonce": nonce, "signature": forged}).status_code, 401)
        unknown = str(uuid.uuid4())
        self.assertEqual(self.client.post(f"/v1/devices/{unknown}/challenge").status_code, 200)

    def test_refresh_rotation_and_reuse_detection_revokes_session(self):
        phone = self.phone("niknolig")
        first_refresh = phone.refresh_token
        rotated = self.client.post("/v1/sessions/refresh", json={"refreshToken": first_refresh})
        self.assertEqual(rotated.status_code, 200)
        new = rotated.json()
        self.assertNotEqual(new["refreshToken"], first_refresh)
        self.assertEqual(phone.get("/v1/devices/me", token=new["accessToken"]).status_code, 200)
        replay = self.client.post("/v1/sessions/refresh", json={"refreshToken": first_refresh})
        self.assertEqual(replay.status_code, 401)
        self.assertEqual(phone.get("/v1/devices/me", token=new["accessToken"]).status_code, 401)
        self.assertEqual(self.client.post("/v1/sessions/refresh", json={"refreshToken": new["refreshToken"]}).status_code, 401)
        kinds = [e["kind"] for e in phone.open_new_session().get("/v1/events").json()["events"]]
        self.assertIn("session_refresh_reuse_detected", kinds)

    def test_logout_revokes_only_current_session(self):
        phone = self.phone("niknolig")
        token = phone.access_token
        self.assertEqual(phone.delete("/v1/sessions/current").status_code, 200)
        self.assertEqual(phone.get("/v1/devices/me", token=token).status_code, 401)

    def test_tampered_missing_and_unknown_tokens_rejected(self):
        phone = self.phone("niknolig")
        self.assertEqual(self.client.get("/v1/links").status_code, 401)
        self.assertEqual(self.client.get("/v1/links", headers={"Authorization": "Bearer " + phone.access_token[:-2] + "AA"}).status_code, 401)
        forged, _ = sec.issue_access_token(b"k" * 48, device_id=uuid.UUID(phone.device_id), session_id=uuid.uuid4(), area="niknolig")
        self.assertEqual(self.client.get("/v1/links", headers={"Authorization": "Bearer " + forged}).status_code, 401)
        valid_signature_unknown_session, _ = sec.issue_access_token(SECRET, device_id=uuid.UUID(phone.device_id), session_id=uuid.uuid4(), area="niknolig")
        self.assertEqual(self.client.get("/v1/links", headers={"Authorization": "Bearer " + valid_signature_unknown_session}).status_code, 401)

    # ---- pairing --------------------------------------------------------
    def test_mutual_pairing_creates_link_with_matching_short_code(self):
        main, defense = self.phone("niknolig", name="Main"), self.phone("niknolig-defense", name="Def")
        pairing = main.post("/v1/pairings").json()
        self.assertEqual(len(pairing["code"]), 8)
        claimed = defense.post("/v1/pairings/claim", {"code": pairing["code"].lower()}).json()
        view = main.get(f"/v1/pairings/{pairing['pairingId']}").json()
        self.assertEqual(claimed["shortAuthString"], view["shortAuthString"])
        self.assertEqual(view["peer"]["displayName"], "Def")
        self.assertEqual(view["state"], "claimed")
        # a single confirmation does not activate a link
        main.post(f"/v1/pairings/{pairing['pairingId']}/confirm")
        self.assertEqual(main.get("/v1/links").json()["links"], [])
        done = defense.post(f"/v1/pairings/{pairing['pairingId']}/confirm").json()
        self.assertEqual(done["state"], "confirmed")
        for side, peer in ((main, "Def"), (defense, "Main")):
            links = side.get("/v1/links").json()["links"]
            self.assertEqual([l["peer"]["displayName"] for l in links], [peer])
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 404)

    def test_pairing_rejects_outsiders_same_area_and_cancelled(self):
        main, same, defense, outsider = (self.phone("niknolig"), self.phone("niknolig"),
                                         self.phone("niknolig-defense"), self.phone("niknolig-defense"))
        pairing = main.post("/v1/pairings").json()
        self.assertEqual(same.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 404)
        self.assertEqual(main.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 404)
        defense.post("/v1/pairings/claim", {"code": pairing["code"]})
        self.assertEqual(outsider.get(f"/v1/pairings/{pairing['pairingId']}").status_code, 404)
        self.assertEqual(outsider.post(f"/v1/pairings/{pairing['pairingId']}/confirm").status_code, 404)
        self.assertEqual(defense.post(f"/v1/pairings/{pairing['pairingId']}/cancel").status_code, 200)
        self.assertEqual(main.post(f"/v1/pairings/{pairing['pairingId']}/confirm").status_code, 409)

    def test_expired_pairing_cannot_be_claimed_or_confirmed(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        pairing = main.post("/v1/pairings").json()
        with psycopg.connect(**self.params) as connection:
            connection.execute("UPDATE device_pairings SET expires_at = now() - interval '1 second' WHERE id = %s", (pairing["pairingId"],))
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 404)
        self.assertEqual(main.get(f"/v1/pairings/{pairing['pairingId']}").json()["state"], "expired")

    def test_failed_claims_are_rate_limited_per_device(self):
        defense = self.phone("niknolig-defense")
        statuses = [defense.post("/v1/pairings/claim", {"code": "AAAAAAAA"}).status_code for _ in range(7)]
        self.assertEqual(statuses[:5], [404] * 5)
        self.assertEqual(statuses[5:], [429, 429])

    def test_new_pairing_cancels_previous_open_pairing(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        first = main.post("/v1/pairings").json()
        main.post("/v1/pairings")
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": first["code"]}).status_code, 404)

    def test_duplicate_active_link_is_rejected(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        self.pair(main, defense)
        pairing = main.post("/v1/pairings").json()
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 409)

    # ---- grants, status, events ----------------------------------------
    def test_grants_are_least_privilege_directional_and_revocable(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        defense.put("/v1/status", {"state": "warning", "detail": "Unknown network"})
        self.assertEqual(main.get(f"/v1/links/{link}/peer/status").status_code, 403)
        grant = defense.post(f"/v1/links/{link}/grants", {"scope": "status:read", "ttlSeconds": 3600})
        self.assertEqual(grant.status_code, 201)
        self.assertEqual(main.get(f"/v1/links/{link}/peer/status").json()["state"], "warning")
        # grant is one-directional and scope-specific
        self.assertEqual(defense.get(f"/v1/links/{link}/peer/status").status_code, 403)
        self.assertEqual(main.get(f"/v1/links/{link}/peer/events").status_code, 403)
        self.assertEqual(main.delete(f"/v1/grants/{grant.json()['grantId']}").status_code, 404)
        listed = main.get(f"/v1/links/{link}/grants").json()["grants"]
        self.assertEqual([g["direction"] for g in listed], ["received"])
        self.assertEqual(defense.delete(f"/v1/grants/{grant.json()['grantId']}").status_code, 200)
        self.assertEqual(main.get(f"/v1/links/{link}/peer/status").status_code, 403)

    def test_grant_validation_and_expiry_cap(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        for body in ({"scope": "admin", "ttlSeconds": 3600}, {"scope": "status:read", "ttlSeconds": 10 ** 9},
                     {"scope": "status:read", "ttlSeconds": 3600, "extra": 1}):
            self.assertEqual(main.post(f"/v1/links/{link}/grants", body).status_code, 400)
        self.assertEqual(main.post(f"/v1/links/{uuid.uuid4()}/grants", {"scope": "status:read", "ttlSeconds": 3600}).status_code, 404)
        outsider = self.phone("niknolig")
        self.assertEqual(outsider.post(f"/v1/links/{link}/grants", {"scope": "status:read", "ttlSeconds": 3600}).status_code, 404)
        grant = main.post(f"/v1/links/{link}/grants", {"scope": "events:read", "ttlSeconds": 60}).json()
        with psycopg.connect(**self.params) as connection:
            connection.execute("UPDATE device_grants SET expires_at = now() + interval '1 second', created_at = now() - interval '1 hour' WHERE id = %s", (grant["grantId"],))
            connection.execute("UPDATE device_grants SET expires_at = now() - interval '1 second' WHERE id = %s", (grant["grantId"],))
        self.assertEqual(defense.get(f"/v1/links/{link}/peer/events").status_code, 403)

    def test_alerts_require_recipient_grant_and_appear_in_log(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        alert = {"kind": "security_warning", "detail": "Suspicious pairing attempt", "linkId": link}
        self.assertEqual(defense.post("/v1/events", alert).status_code, 403)
        main.post(f"/v1/links/{link}/grants", {"scope": "alerts:send", "ttlSeconds": 3600})
        self.assertEqual(defense.post("/v1/events", alert).status_code, 201)
        events = main.get("/v1/events").json()["events"]
        self.assertEqual(events[0]["kind"], "security_warning")
        self.assertEqual(events[0]["sourceDeviceId"], defense.device_id)
        self.assertEqual(defense.post("/v1/events", {"kind": "link_revoked"}).status_code, 400)
        self.assertEqual(defense.post("/v1/events", {"kind": "info", "detail": "a\x00b"}).status_code, 400)

    def test_peer_events_visible_only_with_grant(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        defense.post("/v1/events", {"kind": "protection_applied", "detail": "Blocked"})
        self.assertEqual(main.get(f"/v1/links/{link}/peer/events").status_code, 403)
        defense.post(f"/v1/links/{link}/grants", {"scope": "events:read", "ttlSeconds": 3600})
        kinds = [e["kind"] for e in main.get(f"/v1/links/{link}/peer/events?limit=5").json()["events"]]
        self.assertIn("protection_applied", kinds)
        self.assertEqual(main.get(f"/v1/links/{link}/peer/events?limit=0").status_code, 400)

    def test_link_revocation_removes_grants_and_notifies_peer(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        defense.post(f"/v1/links/{link}/grants", {"scope": "status:read", "ttlSeconds": 3600})
        self.assertEqual(main.delete(f"/v1/links/{link}").status_code, 200)
        self.assertEqual(main.get(f"/v1/links/{link}/peer/status").status_code, 404)
        self.assertEqual(defense.get("/v1/links").json()["links"], [])
        self.assertEqual(defense.delete(f"/v1/links/{link}").status_code, 404)
        self.assertEqual(defense.get("/v1/events").json()["events"][0]["kind"], "link_revoked")
        # relinking requires a fresh mutual confirmation
        self.pair(main, defense)

    def test_device_revocation_by_owner_kills_sessions_and_links(self):
        main, defense = self.phone("niknolig", sub="owner"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        token = main.access_token
        stranger = self.client.delete(f"/v1/devices/{main.device_id}", headers={"Authorization": "Bearer principal:mallory:niknolig"})
        self.assertEqual(stranger.status_code, 404)
        wrong_area = self.client.delete(f"/v1/devices/{main.device_id}", headers={"Authorization": "Bearer principal:owner:niknolig-defense"})
        self.assertEqual(wrong_area.status_code, 404)
        peer_try = defense.delete(f"/v1/devices/{main.device_id}")
        self.assertEqual(peer_try.status_code, 403)
        revoked = self.client.delete(f"/v1/devices/{main.device_id}", headers={"Authorization": "Bearer principal:owner:niknolig"})
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(main.get("/v1/links", token=token).status_code, 401)
        self.assertEqual(self.client.post("/v1/sessions/refresh", json={"refreshToken": main.refresh_token}).status_code, 401)
        self.assertEqual(defense.get("/v1/links").json()["links"], [])
        nonce = self.client.post(f"/v1/devices/{main.device_id}/challenge").json()["nonce"]
        signature = sec.b64url_encode(main.key.sign(sec.session_message(main.device_id, nonce)))
        self.assertEqual(self.client.post(f"/v1/devices/{main.device_id}/session", json={"nonce": nonce, "signature": signature}).status_code, 401)
        self.assertEqual(defense.get("/v1/events").json()["events"][0]["kind"], "link_revoked")
        self.assertNotEqual(link, "")

    def test_device_can_revoke_itself(self):
        phone = self.phone("niknolig")
        self.assertEqual(phone.delete(f"/v1/devices/{phone.device_id}").status_code, 200)
        self.assertEqual(phone.get("/v1/devices/me").status_code, 401)

    # ---- request hardening ---------------------------------------------
    def test_validation_errors_are_generic_and_do_not_echo_input(self):
        phone = self.phone("niknolig")
        secret_value = "SUPER-SECRET-REFRESH"
        response = phone.post("/v1/pairings/claim", {"code": secret_value * 3})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("SECRET", response.text)
        raw = self.client.post("/v1/sessions/refresh", content=b"{", headers={"content-type": "application/json"})
        self.assertEqual(raw.status_code, 400)
        wrong_type = self.client.post("/v1/sessions/refresh", content=b"{}", headers={"content-type": "text/plain"})
        self.assertEqual(wrong_type.status_code, 400)
        large = self.client.post("/v1/sessions/refresh", content=b"{" + b" " * 9000 + b"}", headers={"content-type": "application/json"})
        self.assertEqual(large.status_code, 413)
        self.assertEqual(self.client.get("/v1/events", params={"before": "x"}, headers={"Authorization": "Bearer " + phone.access_token}).status_code, 400)

    def test_responses_are_not_cacheable(self):
        phone = self.phone("niknolig")
        response = phone.get("/v1/links")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unauthenticated_endpoints_are_rate_limited(self):
        target = str(uuid.uuid4())
        codes = [self.client.post(f"/v1/devices/{target}/challenge").status_code for _ in range(12)]
        self.assertEqual(codes[:10], [200] * 10)
        self.assertEqual(codes[10:], [429, 429])

    def test_routes_absent_without_configuration(self):
        application = asgi.create_app(readiness_probe=lambda *_: None, environment="production")
        self.assertFalse(device_api.install_from_environment(application, {}))
        self.assertEqual(TestClient(application).post("/v1/pairings").status_code, 404)

    # ---- review-driven regressions -------------------------------------
    def test_slow_body_is_aborted_with_408_and_handler_never_runs(self):
        import asyncio
        calls = []
        original = device_api.BODY_DEADLINE_SECONDS
        device_api.BODY_DEADLINE_SECONDS = 0.2
        self.addCleanup(setattr, device_api, "BODY_DEADLINE_SECONDS", original)
        application = self.client.app
        original_refresh = self.store.refresh_session
        self.store.refresh_session = lambda token: calls.append(token)
        self.addCleanup(setattr, self.store, "refresh_session", original_refresh)

        async def run():
            sent, started = [], asyncio.Event()

            async def receive():
                if not started.is_set():
                    started.set()
                    return {"type": "http.request", "body": b'{"refreshToken":"', "more_body": True}
                await asyncio.sleep(30)

            async def send(message):
                sent.append(message)

            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
                     "scheme": "https", "path": "/v1/sessions/refresh", "raw_path": b"/v1/sessions/refresh",
                     "query_string": b"", "root_path": "", "server": ("t", 443), "client": ("c", 1),
                     "headers": [(b"content-type", b"application/json"), (b"content-length", b"70")]}
            await asyncio.wait_for(application(scope, receive, send), 5)
            return sent

        sent = asyncio.run(run())
        self.assertEqual(sent[0]["status"], 408)
        self.assertEqual(calls, [])

    def test_concurrent_failed_claims_cannot_exceed_attempt_budget(self):
        import asyncio
        import httpx
        defense = self.phone("niknolig-defense")
        attempts = []
        original = self.store.claim_pairing
        self.store.claim_pairing = lambda device, code: (attempts.append(code), original(device, code))[1]
        self.addCleanup(setattr, self.store, "claim_pairing", original)

        async def run():
            transport = httpx.ASGITransport(app=self.client.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
                responses = await asyncio.gather(*[
                    client.post("/v1/pairings/claim", json={"code": "AAAAAAAA"},
                                headers={"Authorization": "Bearer " + defense.access_token})
                    for _ in range(20)])
            return [r.status_code for r in responses]

        statuses = asyncio.run(run())
        self.assertEqual(statuses.count(404), 5)
        self.assertEqual(statuses.count(429), 15)
        self.assertLessEqual(len(attempts), 5)

    def test_successful_claim_does_not_consume_failure_budget(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        for _ in range(4):
            defense.post("/v1/pairings/claim", {"code": "AAAAAAAA"})
        pairing = main.post("/v1/pairings").json()
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": pairing["code"]}).status_code, 200)
        self.assertEqual(defense.post("/v1/pairings/claim", {"code": "AAAAAAAA"}).status_code, 404)

    def test_refresh_replay_of_older_token_after_two_rotations_revokes_session(self):
        phone = self.phone("niknolig")
        r0 = phone.refresh_token
        r1 = self.client.post("/v1/sessions/refresh", json={"refreshToken": r0}).json()
        r2 = self.client.post("/v1/sessions/refresh", json={"refreshToken": r1["refreshToken"]}).json()
        self.assertEqual(self.client.post("/v1/sessions/refresh", json={"refreshToken": r0}).status_code, 401)
        self.assertEqual(phone.get("/v1/devices/me", token=r2["accessToken"]).status_code, 401)
        self.assertEqual(self.client.post("/v1/sessions/refresh", json={"refreshToken": r2["refreshToken"]}).status_code, 401)

    def test_refresh_reports_remaining_not_full_lifetime(self):
        phone = self.phone("niknolig")
        with psycopg.connect(**self.params) as connection:
            connection.execute("UPDATE device_sessions SET expires_at = now() + interval '1 day' WHERE device_id = %s",
                               (phone.device_id,))
        reported = self.client.post("/v1/sessions/refresh", json={"refreshToken": phone.refresh_token}).json()
        self.assertTrue(86_000 <= reported["refreshTokenExpiresInSeconds"] <= 86_400)

    def test_legacy_installation_without_public_key_fails_closed_with_401(self):
        device_id = uuid.uuid4()
        with psycopg.connect(**self.params) as connection:
            connection.execute(
                "INSERT INTO device_installations(id, app_area, principal_reference, installation_reference, "
                "public_key_fingerprint, identity_state, verified_at) VALUES (%s, 'niknolig', 'legacy', %s, %s, 'verified', now())",
                (device_id, uuid.uuid4(), "a" * 64))
        nonce = self.client.post(f"/v1/devices/{device_id}/challenge").json()["nonce"]
        response = self.client.post(f"/v1/devices/{device_id}/session",
                                    json={"nonce": nonce, "signature": sec.b64url_encode(b"x" * 64)})
        self.assertEqual(response.status_code, 401)

    def test_expired_challenges_are_pruned_in_bounded_batches(self):
        phone = self.phone("niknolig")
        with psycopg.connect(**self.params) as connection:
            connection.execute("DELETE FROM device_challenges")
            connection.execute(
                "INSERT INTO device_challenges(nonce_hash, device_id, expires_at) "
                "SELECT sha256(g::text::bytea), %s, now() - interval '1 hour' FROM generate_series(1, 150) g",
                (phone.device_id,))
        self.store.create_challenge(uuid.UUID(phone.device_id))
        with psycopg.connect(**self.params) as connection:
            left = connection.execute("SELECT count(*) FROM device_challenges WHERE expires_at < now()").fetchone()[0]
        self.assertEqual(left, 50)

    def test_expired_link_no_longer_blocks_repairing(self):
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        link = self.pair(main, defense)
        defense.post(f"/v1/links/{link}/grants", {"scope": "status:read", "ttlSeconds": 3600})
        with psycopg.connect(**self.params) as connection:
            connection.execute("UPDATE device_links SET created_at = now() - interval '2 days', "
                               "expires_at = now() - interval '1 day' WHERE id = %s", (link,))
        self.assertEqual(main.get("/v1/links").json()["links"][0]["state"], "expired")
        new_link = self.pair(main, defense)
        self.assertNotEqual(new_link, link)
        with psycopg.connect(**self.params) as connection:
            state = connection.execute("SELECT state FROM device_links WHERE id = %s", (link,)).fetchone()[0]
        self.assertEqual(state, "expired")
        self.assertEqual(main.get(f"/v1/links/{new_link}/peer/status").status_code, 403)

    def test_revocation_does_not_deadlock_with_concurrent_confirmation(self):
        import threading
        main, defense = self.phone("niknolig"), self.phone("niknolig-defense")
        pairing = main.post("/v1/pairings").json()
        defense.post("/v1/pairings/claim", {"code": pairing["code"]})
        errors = []
        confirming = psycopg.connect(**self.params)
        confirming.execute("SET lock_timeout = '5s'")
        confirming.execute("SELECT 1 FROM device_pairings WHERE id = %s FOR UPDATE", (pairing["pairingId"],))
        worker = threading.Thread(target=lambda: self._revoke(main.device_id, errors))
        worker.start()
        time.sleep(0.7)  # revocation now holds the device row and waits for the pairing
        try:
            confirming.execute(
                "INSERT INTO device_links(id, first_device_id, first_app_area, second_device_id, second_app_area, "
                "state, expires_at, activated_at) VALUES (%s, %s, 'niknolig', %s, 'niknolig-defense', 'active', "
                "now() + interval '1 day', now())", (uuid.uuid4(), main.device_id, defense.device_id))
            confirming.commit()
        finally:
            confirming.close()
        worker.join(10)
        self.assertEqual(errors, [])
        self.assertEqual(defense.get("/v1/links").json()["links"], [])

    def _revoke(self, device_id, errors):
        try:
            self.store.revoke_device(uuid.UUID(device_id))
        except Exception as error:  # noqa: BLE001
            errors.append(error)

    def test_readiness_includes_device_store_and_invalid_configuration_disables_routes(self):
        application = asgi.create_app(readiness_probe=lambda *_: None, environment="production")
        asgi_probe = lambda check: None
        self.assertTrue(application.state is not None)

        async def noop(check):
            return None

        broken = asgi.create_app(readiness_probe=noop, environment="production")

        class Failing:
            def ping(self):
                raise RuntimeError("database unavailable")

        broken.state.device_store = Failing()
        self.assertEqual(TestClient(broken).get("/health/ready").status_code, 503)
        broken.state.device_store = self.store
        self.assertEqual(TestClient(broken).get("/health/ready").status_code, 200)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            empty, token = Path(directory, "empty"), Path(directory, "token")
            empty.write_text("")
            token.write_text("t" * 64)
            environment = {"DEVICE_API_ENABLED": "1", "DEVICE_TOKEN_SECRET_FILE": str(token),
                           "DEVICE_API_DB_PASSWORD_FILE": str(empty), "PGHOST": "h", "PGDATABASE": "d",
                           "DEVICE_API_DB_USER": "u", "AUTH_ISSUER": "https://x.supabase.co/auth/v1",
                           "AUTH_AUDIENCE": "authenticated",
                           "AUTH_JWKS_URL": "https://x.supabase.co/auth/v1/.well-known/jwks.json"}
            application = asgi.create_app(readiness_probe=noop, environment="production")
            self.assertFalse(device_api.install_from_environment(application, environment))
            self.assertEqual(TestClient(application).post("/v1/pairings").status_code, 404)
            empty.write_text("password-from-secret")
            application = asgi.create_app(readiness_probe=noop, environment="production")
            self.assertTrue(device_api.install_from_environment(application, environment))

    def test_existing_privileged_device_api_role_is_rejected(self):
        import tempfile
        with psycopg.connect(**self.params, autocommit=True) as admin:
            exists = admin.execute("SELECT 1 FROM pg_roles WHERE rolname = 'backend_device_api'").fetchone()
            if not exists:
                admin.execute("CREATE ROLE backend_device_api")
            admin.execute("GRANT pg_monitor TO backend_device_api")
        try:
            with tempfile.NamedTemporaryFile("w") as handle, psycopg.connect(**self.params) as connection:
                handle.write("role-password-different-from-admin")
                handle.flush()
                with self.assertRaisesRegex(RuntimeError, "unexpected ownership"):
                    migrate._configure_device_api_role(connection, handle.name)
        finally:
            with psycopg.connect(**self.params, autocommit=True) as admin:
                admin.execute("REVOKE pg_monitor FROM backend_device_api")

    # ---- schema and role -----------------------------------------------
    def test_schema_requires_contract_and_role_is_least_privilege(self):
        with psycopg.connect(**self.params) as connection:
            versions = [r[0] for r in connection.execute("SELECT version FROM backend_schema_migrations ORDER BY version")]
            self.assertEqual(versions, ["000_health_runtime", "001_initial_contract", "002_device_api"])
            migrate.check_ready(connection)
        name = "device_api_prereq_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{name}"')
        try:
            params = dict(self.params, dbname=name)
            with psycopg.connect(**params) as connection:
                with self.assertRaises(RuntimeError):
                    migrate.migrate(connection, approve_device_api=True)
        finally:
            with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
                admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')

    def test_device_api_role_cannot_delete_audit_events_or_alter_schema(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w") as handle, psycopg.connect(**self.params) as connection:
            handle.write("role-password-different-from-admin")
            handle.flush()
            migrate._configure_device_api_role(connection, handle.name)
        with psycopg.connect(**self.params, autocommit=True) as admin:
            admin.execute("SELECT 1")
            role = admin.execute(
                "SELECT has_table_privilege('backend_device_api', 'device_events', 'DELETE'), "
                "has_table_privilege('backend_device_api', 'device_events', 'INSERT'), "
                "has_table_privilege('backend_device_api', 'device_sessions', 'DELETE'), "
                "has_table_privilege('backend_device_api', 'device_events', 'UPDATE'), "
                "has_table_privilege('backend_device_api', 'device_refresh_history', 'UPDATE'), "
                "has_table_privilege('backend_device_api', 'backend_schema_migrations', 'SELECT'), "
                "has_schema_privilege('backend_device_api', 'public', 'CREATE')").fetchone()
        self.assertEqual(role, (False, True, False, False, False, False, False))


class Phone:
    def __init__(self, client, area, sub, name):
        self.client, self.area, self.sub, self.name = client, area, sub, name
        self.key = Ed25519PrivateKey.generate()
        installation = str(uuid.uuid4())
        public = self.public_bytes(self.key)
        body = {"installationId": installation, "publicKey": sec.b64url_encode(public),
                "proof": sec.b64url_encode(self.key.sign(sec.registration_message(area, installation, sub))),
                "displayName": name}
        response = client.post("/v1/devices", json=body, headers={"Authorization": f"Bearer principal:{sub}:{area}"})
        assert response.status_code == 201, response.text
        self.device_id = response.json()["id"]
        self._login()

    @staticmethod
    def public_bytes(key):
        return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def _login(self):
        nonce = self.client.post(f"/v1/devices/{self.device_id}/challenge").json()["nonce"]
        signature = sec.b64url_encode(self.key.sign(sec.session_message(self.device_id, nonce)))
        response = self.client.post(f"/v1/devices/{self.device_id}/session", json={"nonce": nonce, "signature": signature})
        assert response.status_code == 201, response.text
        tokens = response.json()
        self.access_token, self.refresh_token = tokens["accessToken"], tokens["refreshToken"]

    def open_new_session(self):
        self._login()
        return self

    def _headers(self, token):
        return {"Authorization": "Bearer " + (token or self.access_token)}

    def get(self, path, token=None, **kw):
        return self.client.get(path, headers=self._headers(token), **kw)

    def post(self, path, body=None):
        return self.client.post(path, json=body, headers=self._headers(None)) if body is not None else \
            self.client.post(path, headers=self._headers(None))

    def put(self, path, body):
        return self.client.put(path, json=body, headers=self._headers(None))

    def delete(self, path):
        return self.client.delete(path, headers=self._headers(None))


if __name__ == "__main__":
    unittest.main()
