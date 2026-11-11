import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


class StagingConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.compose = (BACKEND / "compose.staging.yaml").read_text()

    def test_staging_is_isolated_from_production(self):
        self.assertIn("name: niknolig-staging", self.compose)
        self.assertIn("staging-postgres-data", self.compose)
        self.assertNotIn("niknolig_health", self.compose)
        self.assertNotIn("/opt/nold/backend", self.compose)
        self.assertNotIn("443", self.compose)
        for secret in ("postgres_password", "health_password", "device_api_password", "device_token_secret"):
            self.assertIn("${STAGING_SECRETS_DIR:?", self.compose)
            self.assertIn(f"/{secret}", self.compose)

    def test_only_loopback_port_8001_is_published(self):
        self.assertEqual(1, self.compose.count("ports:"))
        self.assertIn('"127.0.0.1:8001:8000"', self.compose)
        self.assertIn("internal: true", self.compose)

    def test_device_api_and_supabase_auth_are_required(self):
        self.assertIn('DEVICE_API_ENABLED: "1"', self.compose)
        for name in ("AUTH_ISSUER", "AUTH_AUDIENCE", "AUTH_JWKS_URL"):
            self.assertIn(f"{name}: ${{{name}:?", self.compose)

    def test_no_credentials_in_templates(self):
        env = (BACKEND / "staging.env.example").read_text()
        self.assertNotIn("PASSWORD=", env.upper())
        self.assertIn("REPLACE_STAGING_REF", env)

    def test_staging_caddy_targets_only_staging_host_and_allowlisted_paths(self):
        caddy = (BACKEND / "Caddyfile.staging").read_text()
        self.assertIn("staging-api.niknolig.com {", caddy)
        self.assertNotIn("auto_https off", caddy)
        self.assertIn("reverse_proxy 127.0.0.1:8001", caddy)
        self.assertIn("respond 404", caddy)

    def test_device_modules_are_in_the_docker_build_context(self):
        ignore = (BACKEND / ".dockerignore").read_text().split()
        dockerfile = (BACKEND / "Dockerfile").read_text()
        for module in ("device_security.py", "device_store.py", "device_api.py"):
            self.assertIn(f"!{module}", ignore)
            self.assertIn(module, dockerfile)


if __name__ == "__main__":
    unittest.main()
