import sys
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from authorization import authorize_verified_claims


class AuthorizationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.claims = {
            "iss": "test-issuer",
            "aud": "test-api",
            "sub": "synthetic-principal",
            "exp": 2_000,
            "app_area": "niknolig",
            "actions": ["profile:read"],
            "device_verified": True,
        }
        self.expected = {
            "expected_issuer": "test-issuer",
            "expected_audience": "test-api",
            "resource_app_area": "niknolig",
            "action": "profile:read",
            "now": 1_000,
        }

    def test_verified_claims_allow_only_the_scoped_action(self):
        decision = authorize_verified_claims(self.claims, **self.expected)
        self.assertTrue(decision.allowed)
        self.assertEqual("AUTHORIZED", decision.code)

    def test_cross_product_access_is_denied(self):
        expected = dict(self.expected, resource_app_area="niknolig-defense")
        decision = authorize_verified_claims(self.claims, **expected)
        self.assertFalse(decision.allowed)
        self.assertEqual("APP_AREA_MISMATCH", decision.code)

    def test_expired_or_malformed_claims_fail_closed(self):
        for changes in (
            {"exp": 1_000},
            {"aud": ["test-api"]},
            {"sub": ""},
            {"actions": ["profile:read", "profile:read"]},
            {"actions": ["profile:read", None]},
            {"app_area": []},
        ):
            with self.subTest(changes=changes):
                claims = dict(self.claims, **changes)
                decision = authorize_verified_claims(claims, **self.expected)
                self.assertFalse(decision.allowed)
                self.assertEqual("AUTHENTICATION_INVALID", decision.code)

    def test_wrong_issuer_or_audience_is_denied(self):
        for changes in (
            {"expected_issuer": "untrusted-issuer"},
            {"expected_audience": "other-api"},
        ):
            with self.subTest(changes=changes):
                expected = dict(self.expected, **changes)
                decision = authorize_verified_claims(self.claims, **expected)
                self.assertFalse(decision.allowed)
                self.assertEqual("AUTHENTICATION_INVALID", decision.code)

    def test_missing_or_unverified_device_is_denied(self):
        for device_verified in (False, None, 1):
            claims = dict(self.claims, device_verified=device_verified)
            decision = authorize_verified_claims(claims, **self.expected)
            self.assertFalse(decision.allowed)
            self.assertEqual("DEVICE_IDENTITY_UNVERIFIED", decision.code)

    def test_ungranted_action_and_malformed_context_are_denied(self):
        denied_action = authorize_verified_claims(
            self.claims, **dict(self.expected, action="profile:write")
        )
        self.assertFalse(denied_action.allowed)
        self.assertEqual("AUTHORIZATION_DENIED", denied_action.code)

        for claims, expected in (
            (None, self.expected),
            (self.claims, dict(self.expected, resource_app_area="other")),
            (self.claims, dict(self.expected, expected_issuer="")),
        ):
            with self.subTest(claims=claims, expected=expected):
                decision = authorize_verified_claims(claims, **expected)
                self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()
