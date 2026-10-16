import unittest
import json
import copy
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None


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
                "grantedByAppArea",
                "targetInstallationId",
                "targetAppArea",
                "purpose",
                "userFacingTextVersion",
                "grantedAt",
                "expiresAt",
            }.issubset(required)
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            3,
            len(schema["properties"]["purpose"]["oneOf"]),
        )
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
        self.assertIn("Keine Rohbilder", plan)
        self.assertIn("frische Peer-Authentifizierung", plan)
        self.assertIn("Keine Änderung an den separaten Quell-Repositories", plan)
        self.assertIn("minSdk 26", plan)
        self.assertIn("nicht durchgeführt", plan)

    def test_electro_engel_architecture_preserves_app_boundaries(self):
        root = BACKEND.parent
        settings = (root / "settings.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('include(":niknolig", ":niknolig-defense")', settings)
        for app in ("niknolig", "niknolig-defense"):
            build_file = (root / "apps" / app / "build.gradle.kts").read_text(
                encoding="utf-8"
            )
            self.assertNotRegex(build_file, r'\bproject\s*\(')

        architecture = (
            root / "docs/electro-engel-architecture-and-migration.md"
        ).read_text(encoding="utf-8")
        self.assertIn("keine Core-Runtime", architecture)
        self.assertIn("SecurityChain-P0 bleibt", architecture)
        self.assertIn("NIKNOLIG-Integration", architecture)
        self.assertIn("NIKNOLIG-Abhängigkeiten im Core", architecture)
        self.assertIn("python3 -m unittest discover -s backend/tests", architecture)

    @unittest.skipIf(
        Draft202012Validator is None,
        "jsonschema is optional; structural assertions still run",
    )
    def test_schemas_accept_valid_contracts_and_reject_negative_cases(self):
        schemas = {
            path.name.removesuffix(".schema.json"): json.loads(
                path.read_text(encoding="utf-8")
            )
            for path in (BACKEND / "contracts").glob("*.schema.json")
        }
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)

        consent = {
            "contractVersion": "1.0",
            "consentId": "00000000-0000-4000-8000-000000000001",
            "subjectRef": "opaque-subject-ref-001",
            "grantedByInstallationId": "00000000-0000-4000-8000-000000000002",
            "grantedByAppArea": "niknolig",
            "targetInstallationId": "00000000-0000-4000-8000-000000000003",
            "targetAppArea": "niknolig-defense",
            "purpose": {
                "code": "assistant_session_resume",
                "dataCategories": ["session_resume_marker"],
            },
            "userFacingTextVersion": "consent.v1",
            "grantedAt": "2026-10-16T00:00:00Z",
            "expiresAt": "2026-10-16T01:00:00Z",
        }
        event = {
            "contractVersion": "1.0",
            "eventId": "00000000-0000-4000-8000-000000000004",
            "eventType": "grant",
            "consentId": consent["consentId"],
            "actorInstallationId": consent["grantedByInstallationId"],
            "actorAppArea": "niknolig",
            "targetInstallationId": consent["targetInstallationId"],
            "targetAppArea": "niknolig-defense",
            "purposeCode": "assistant_session_resume",
            "occurredAt": "2026-10-16T00:00:00Z",
            "correlationId": "00000000-0000-4000-8000-000000000005",
        }
        capability = {
            "contractVersion": "1.0",
            "pluginId": "com.example.depth",
            "pluginVersion": "1.0.0",
            "sensorType": "depth_camera",
            "providerId": "android.camera2",
            "availability": "available",
            "permissionState": "granted",
            "requiredAndroidPermissions": ["android.permission.CAMERA"],
            "capabilities": ["depth_map"],
            "discoveredAt": "2026-10-16T00:00:00Z",
        }
        summary = {
            "contractVersion": "1.0",
            "sensorType": "depth_camera",
            "providerId": "android.camera2",
            "sourceInstallationId": consent["grantedByInstallationId"],
            "targetInstallationId": consent["targetInstallationId"],
            "purposeCode": "sensor_depth_summary",
            "capturedAt": "2026-10-16T00:00:00Z",
            "processedOnDevice": True,
            "dataClass": "derived_depth_summary",
            "retentionPolicyId": "approved-policy.pending",
            "transmission": "consented_remote",
            "consentId": consent["consentId"],
            "summary": {
                "metric": "nearest_depth_m",
                "value": 1.5,
                "unit": "m",
            },
        }
        valid_instances = {
            "device-consent-v1": consent,
            "consent-audit-event-v1": event,
            "sensor-capability-v1": capability,
            "sensor-summary-v1": summary,
        }
        invalid_instances = {
            "device-consent-v1": [
                {**consent, "targetInstallationId": None},
                {**consent, "consentId": "not-a-uuid"},
                {
                    **consent,
                    "purpose": {
                        "code": "assistant_session_resume",
                        "dataCategories": ["derived_depth_summary"],
                    },
                },
                {**consent, "unapprovedContent": "private message"},
            ],
            "consent-audit-event-v1": [
                {**event, "sensorPayload": "must not be logged"},
                {**event, "correlationId": "not-a-uuid"},
            ],
            "sensor-capability-v1": [
                {**capability, "permissionState": "denied"},
                {**capability, "sensorType": "infrared"},
                {**capability, "sensorType": "other"},
            ],
            "sensor-summary-v1": [
                {**summary, "processedOnDevice": False},
                {**summary, "sourceInstallationId": "not-a-uuid"},
                {key: value for key, value in summary.items() if key != "consentId"},
                {**summary, "dataClass": "derived_environment_summary"},
                {**summary, "rawImage": "base64-data"},
            ],
        }
        for name, instance in valid_instances.items():
            validator = Draft202012Validator(
                schemas[name],
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            )
            with self.subTest(schema=name, case="valid"):
                self.assertTrue(validator.is_valid(instance))
            for invalid in invalid_instances[name]:
                with self.subTest(schema=name, case="invalid"):
                    self.assertFalse(validator.is_valid(invalid))

    @unittest.skipIf(
        Draft202012Validator is None,
        "jsonschema is optional; UUID format validation was not run",
    )
    def test_uuid_formats_reject_malformed_identifiers(self):
        checker = Draft202012Validator.FORMAT_CHECKER
        self.assertIn("uuid", checker.checkers)
        for path in (BACKEND / "contracts").glob("*.schema.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            for name, property_schema in schema["properties"].items():
                if property_schema.get("format") != "uuid":
                    continue
                validator = Draft202012Validator(
                    property_schema, format_checker=checker
                )
                with self.subTest(schema=path.name, field=name):
                    self.assertTrue(
                        validator.is_valid("00000000-0000-4000-8000-000000000001")
                    )
                    for invalid in ("not-a-uuid", "", "0" * 32):
                        self.assertFalse(validator.is_valid(invalid))

    @unittest.skipIf(
        Draft202012Validator is None
        or "date-time" not in Draft202012Validator.FORMAT_CHECKER.checkers,
        "optional RFC 3339 checker unavailable; timestamp validation was not run",
    )
    def test_timestamp_formats_reject_malformed_values(self):
        for path in (BACKEND / "contracts").glob("*.schema.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            for name, property_schema in schema["properties"].items():
                if property_schema.get("format") != "date-time":
                    continue
                validator = Draft202012Validator(
                    property_schema,
                    format_checker=Draft202012Validator.FORMAT_CHECKER,
                )
                with self.subTest(schema=path.name, field=name):
                    self.assertTrue(validator.is_valid("2026-10-16T00:00:00Z"))
                    for invalid in (
                        "not-a-timestamp",
                        "2026-02-30T00:00:00Z",
                        "2026-10-16T00:00:00",
                    ):
                        self.assertFalse(validator.is_valid(invalid))


if __name__ == "__main__":
    unittest.main()
