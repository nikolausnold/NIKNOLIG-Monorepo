import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


class BackendContractTests(unittest.TestCase):
    def test_openapi_only_exposes_non_sensitive_health_operations(self):
        contract = (BACKEND / "openapi.yaml").read_text(encoding="utf-8")
        self.assertIn("openapi: 3.1.0", contract)
        self.assertIn("/health/live:", contract)
        self.assertIn("/health/ready:", contract)
        self.assertIn("security: []", contract)
        self.assertIn("AUTHENTICATION_REQUIRED", contract)
        self.assertIn("APP_AREA_MISMATCH", contract)
        self.assertIn("REPLAY_DETECTED", contract)
        self.assertNotIn("/v1/", contract)
        self.assertIn("specified or implemented", contract)

    def test_migration_separates_app_domains_and_does_not_store_private_keys(self):
        migration = (BACKEND / "migrations/001_initial_contract.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("'niknolig'", migration)
        self.assertIn("'niknolig-defense'", migration)
        self.assertIn("public_key_fingerprint", migration)
        self.assertIn("identity_state <> 'verified' OR public_key_fingerprint IS NOT NULL", migration)
        self.assertIn("CHECK (first_device_id <> second_device_id)", migration)
        self.assertIn("CHECK (first_app_area <> second_app_area)", migration)
        self.assertIn("identity_state <> 'verified' OR verified_at IS NOT NULL", migration)
        self.assertIn("grants no action or", migration)
        self.assertNotIn("private_key", migration.lower())

    def test_compose_is_loopback_only_and_requires_local_password(self):
        compose = (BACKEND / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:${POSTGRES_PORT:-54329}:5432", compose)
        self.assertIn("${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD", compose)
        self.assertIn("internal: true", compose)
        self.assertIn("pg_isready", compose)
        self.assertNotIn("0.0.0.0:", compose)
        self.assertNotIn("api:", compose)

    def test_example_configuration_contains_no_password_value(self):
        example = (BACKEND / ".env.example").read_text(encoding="utf-8")
        self.assertIn("POSTGRES_PASSWORD=", example)
        self.assertNotRegex(example, r"(?m)^POSTGRES_PASSWORD=.+$")


if __name__ == "__main__":
    unittest.main()
