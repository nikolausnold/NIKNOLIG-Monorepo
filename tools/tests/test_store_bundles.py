import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/android-release.yml"


@unittest.skipUnless(
    all(shutil.which(tool) for tool in ("bash", "keytool", "jar", "jarsigner")),
    "JDK and bash are required for bundle signature regression tests",
)
class StoreBundleSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="niknolig-store-test-")
        cls.addClassCleanup(cls.workspace.cleanup)
        cls.root = Path(cls.workspace.name)
        cls.environment = dict(os.environ, STORE_TEST_PASSWORD="local-test-only")
        cls.alias = "upload-test"
        for name in ("trusted", "other"):
            cls.run_jdk(
                "keytool", "-genkeypair", "-alias", cls.alias,
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
                "-dname", "CN=LocalBundleTest", "-storetype", "PKCS12",
                "-keystore", str(cls.root / f"{name}.p12"),
                "-storepass:env", "STORE_TEST_PASSWORD",
            )
        (cls.root / "payload.txt").write_text("Bundle signature fixture\n")
        cls.unsigned = cls.root / "unsigned.aab"
        cls.run_jdk(
            "jar", "--create", "--file", str(cls.unsigned),
            "-C", str(cls.root), "payload.txt",
        )
        cls.signed = cls.root / "signed.aab"
        shutil.copyfile(cls.unsigned, cls.signed)
        cls.run_jdk(
            "jarsigner", "-keystore", str(cls.root / "trusted.p12"),
            "-storetype", "PKCS12", "-storepass:env", "STORE_TEST_PASSWORD",
            str(cls.signed), cls.alias,
        )
        match = re.search(
            r"^          verify_bundle\(\) \{.*?^          \}",
            WORKFLOW.read_text(), re.MULTILINE | re.DOTALL,
        )
        if match is None:
            raise AssertionError("Workflow bundle verifier is missing")
        cls.verifier = textwrap.dedent(match.group())

    @classmethod
    def run_jdk(cls, *command):
        subprocess.run(
            command, env=cls.environment, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name)

    def prepare_bundle(self, source, module="niknolig"):
        output = self.cwd / "apps" / module / "build/outputs/bundle/release"
        output.mkdir(parents=True)
        bundle = output / "app-release.aab"
        shutil.copyfile(source, bundle)
        return bundle

    def verify(self, module="niknolig", store="trusted"):
        return subprocess.run(
            ["bash", "-c", 'set -euo pipefail\n' + self.verifier +
             '\nverify_bundle "$@"', "bundle-test", module,
             str(self.root / f"{store}.p12"), self.alias, "STORE_TEST_PASSWORD"],
            cwd=self.cwd, env=self.environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    def test_accepts_signed_bundle_for_each_separate_app(self):
        for module in ("niknolig", "niknolig-defense"):
            self.prepare_bundle(self.signed, module)
            result = self.verify(module)
            with self.subTest(module=module):
                self.assertEqual(0, result.returncode, result.stdout)

    def test_rejects_missing_empty_and_multiple_bundles(self):
        self.assertNotEqual(0, self.verify().returncode)
        bundle = self.prepare_bundle(self.signed)
        bundle.write_bytes(b"")
        self.assertNotEqual(0, self.verify().returncode)
        shutil.copyfile(self.signed, bundle)
        shutil.copyfile(self.signed, bundle.with_name("extra.aab"))
        self.assertNotEqual(0, self.verify().returncode)

    def test_rejects_unsigned_bundle(self):
        self.prepare_bundle(self.unsigned)
        self.assertNotEqual(0, self.verify().returncode)

    def test_rejects_wrong_upload_certificate_even_with_same_alias(self):
        self.prepare_bundle(self.signed)
        self.assertNotEqual(0, self.verify(store="other").returncode)

    def test_rejects_unsigned_additional_entries(self):
        bundle = self.prepare_bundle(self.signed)
        with zipfile.ZipFile(bundle, "a") as archive:
            archive.writestr("unsigned.txt", "Unverified content")
        self.assertNotEqual(0, self.verify().returncode)

    def test_rejects_tampered_signed_content(self):
        bundle = self.prepare_bundle(self.signed)
        with zipfile.ZipFile(self.signed) as source, zipfile.ZipFile(bundle, "w") as target:
            for entry in source.infolist():
                data = source.read(entry.filename)
                target.writestr(entry, b"Tampered" if entry.filename == "payload.txt" else data)
        self.assertNotEqual(0, self.verify().returncode)


class StorePreparationTests(unittest.TestCase):
    def test_separate_bundles_built_verified_then_uploaded_without_store_access(self):
        workflow = WORKFLOW.read_text()
        verification = workflow.index("- name: Verify package identities and release signatures")
        for module, alias, secret in (
            ("niknolig", "niknolig", "NIKNOLIG_RELEASE"),
            ("niknolig-defense", "niknolig-defense", "NIKNOLIG_DEFENSE_RELEASE"),
        ):
            with self.subTest(module=module):
                self.assertIn(f":{module}:bundleRelease", workflow)
                self.assertIn(
                    f'verify_bundle {module} "${secret}_STORE_FILE" \\\n'
                    f'            "${secret}_KEY_ALIAS" {secret}_STORE_PASSWORD',
                    workflow,
                )
                self.assertIn(f"{secret}_KEY_ALIAS: {alias}", workflow)
                self.assertIn(f"name: {module}-store-aab-", workflow)
                upload = workflow.index(f"path: apps/{module}/build/outputs/bundle/release/*.aab")
                self.assertLess(verification, upload)
                self.assertIn("retention-days: 14", workflow[upload:upload + 160])
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("androidpublisher", workflow.lower())
        self.assertNotIn("fastlane", workflow.lower())
        self.assertNotIn("PLAY_SERVICE_ACCOUNT", workflow)


if __name__ == "__main__":
    unittest.main()
