import unittest
import json
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

    def test_device_transfer_consent_is_explicit_and_scoped(self):
        schema = json.loads(
            (BACKEND / "contracts/device-consent-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        required = set(schema["required"])
        self.assertTrue(
            {
                "grantedByInstallationId",
                "targetInstallationId",
                "purpose",
                "userFacingTextVersion",
                "grantedAt",
                "expiresAt",
            }.issubset(required)
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("assistant_messages", str(schema))
        self.assertNotIn("remote_control", str(schema))

    def test_sensor_contract_fails_closed_for_unknown_or_unapproved_capabilities(self):
        capability = json.loads(
            (BACKEND / "contracts/sensor-capability-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(capability["additionalProperties"])
        self.assertIn("unknown", capability["properties"]["availability"]["enum"])
        self.assertIn("revoked", capability["properties"]["permissionState"]["enum"])
        self.assertIn("allOf", capability)
        self.assertIn("extensionId", str(capability["allOf"]))

        summary = json.loads(
            (BACKEND / "contracts/sensor-summary-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(summary["additionalProperties"])
        self.assertEqual(True, summary["properties"]["processedOnDevice"]["const"])
        self.assertIn(
            "consented_remote",
            summary["properties"]["transmission"]["enum"],
        )
        self.assertIn("consentId", summary["required"])
        self.assertNotIn("rawImage", summary["properties"])
        self.assertNotIn("audioBytes", summary["properties"])
        self.assertNotIn("pointCloud", summary["properties"])

    def test_audit_contract_excludes_free_form_or_sensor_payloads(self):
        schema = json.loads(
            (BACKEND / "contracts/consent-audit-event-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertIn(
            "revoke",
            schema["properties"]["eventType"]["enum"],
        )
        self.assertIn("correlationId", schema["required"])
        self.assertNotIn("payload", schema["properties"])
        self.assertNotIn("notes", schema["properties"])

    def test_sensor_and_device_plan_keeps_p0_and_app_boundaries(self):
        plan = (
            BACKEND.parent / "docs/electro-engel-multidevice-sensors.md"
        ).read_text(encoding="utf-8")
        self.assertIn("P0: BLOCKED", plan)
        self.assertIn("keine Rohbilder", plan)
        self.assertIn("erneute Peer-Authentifizierung", plan)
        self.assertIn("keine Änderung an den separaten Quell-Repositories", plan)
        self.assertIn("minSdk 26", plan)
        self.assertIn("nicht durchgeführt", plan)


if __name__ == "__main__":
    unittest.main()
