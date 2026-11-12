import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


class StagingConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.compose = (BACKEND / "compose.staging.yaml").read_text()
        self.deploy_script = (BACKEND / "scripts/staging-deploy.sh").read_text()

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

    def test_staging_script_uses_canonical_paths_and_validated_compose_settings(self):
        self.assertIn('SECRETS_DIR="$(realpath -m -- "$SECRETS_DIR")"', self.deploy_script)
        self.assertIn("get() { grep -E", self.deploy_script)
        self.assertIn("| cut -d= -f2- || true; }", self.deploy_script)
        self.assertIn('export STAGING_SECRETS_DIR="$SECRETS_DIR" STAGING_DB_NAME', self.deploy_script)
        self.assertIn("export AUTH_ISSUER AUTH_AUDIENCE AUTH_JWKS_URL", self.deploy_script)
        self.assertIn("env -u COMPOSE_PROJECT_NAME docker compose --project-name niknolig-staging", self.deploy_script)

    def test_staging_verification_checks_authentication_on_protected_route(self):
        self.assertIn("http://127.0.0.1:8001/v1/devices/me", self.deploy_script)
        self.assertIn('[[ "$code" == 401 ]] ||', self.deploy_script)
        self.assertIn('https://$STAGING_HOST/v1/devices/me', self.deploy_script)
        self.assertIn("Public unauthenticated protected route returned $code (expected 401)", self.deploy_script)
        self.assertNotIn("-X POST", self.deploy_script)

    def test_staging_secrets_are_readable_only_by_the_container_uid(self):
        self.assertIn("setfacl -b --", self.deploy_script)
        self.assertIn('chmod 600 "$SECRETS_DIR/$name"', self.deploy_script)
        self.assertIn("setfacl -m u:10001:r--", self.deploy_script)
        self.assertIn('command -v getfacl >/dev/null', self.deploy_script)
        self.assertIn('$(stat -c %a "$file")" == 640', self.deploy_script)
        self.assertIn("'user:10001:r--\\n'", self.deploy_script)
        self.assertIn("'group::---\\n'", self.deploy_script)

    def test_deploy_starts_database_and_backs_up_before_migration(self):
        deploy = self.deploy_script.split('  deploy)', 1)[1].split('  verify)', 1)[0]
        self.assertLess(deploy.index("dc up -d --wait postgres"), deploy.index("backup"))
        self.assertLess(deploy.index("backup"), deploy.index("dc run --rm migrate"))


if __name__ == "__main__":
    unittest.main()
