import unittest

from tools.nold_guard import MAX_URL_LENGTH, triage_url


class NoldGuardUrlTriageTests(unittest.TestCase):
    def test_public_https_url_is_never_promoted_to_safe(self):
        result = triage_url("https://example.org/account")
        self.assertEqual("UNASSESSED", result["status"])
        self.assertEqual("heuristic", result["assessment"])
        self.assertFalse(result["verified"])
        self.assertFalse(result["networkAccess"])

    def test_plain_http_requires_review(self):
        result = triage_url("http://example.org/")
        self.assertEqual("REVIEW", result["status"])
        self.assertIn("unencrypted_http", result["reasons"])

    def test_local_and_private_hosts_are_flagged(self):
        for url in (
            "http://127.0.0.1/admin",
            "https://192.168.1.10/",
            "https://printer.local/",
            "https://localhost/",
        ):
            with self.subTest(url=url):
                result = triage_url(url)
                self.assertEqual("REVIEW", result["status"])
                self.assertTrue(result["reasons"])

    def test_userinfo_encoded_authority_and_backslashes_are_flagged(self):
        for url in (
            "https://trusted.example@attacker.example/",
            "https://trusted.example%40attacker.example/",
            "https://trusted.example\\@attacker.example/",
        ):
            with self.subTest(url=url):
                self.assertEqual("REVIEW", triage_url(url)["status"])

    def test_unsupported_and_malformed_urls_require_review(self):
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://[::1"):
            with self.subTest(url=url):
                self.assertEqual("REVIEW", triage_url(url)["status"])

    def test_punycode_and_numeric_host_forms_are_flagged(self):
        for url, expected_reason in (
            ("https://xn--pple-43d.example/", "punycode_host"),
            ("http://2130706433/", "ambiguous_numeric_host"),
        ):
            with self.subTest(url=url):
                result = triage_url(url)
                self.assertEqual("REVIEW", result["status"])
                self.assertIn(expected_reason, result["reasons"])

    def test_oversized_or_control_character_input_is_rejected(self):
        self.assertIn("invalid_or_oversized_input", triage_url("x" * (MAX_URL_LENGTH + 1))["reasons"])
        self.assertIn("invalid_url_characters", triage_url("https://example.org/\nheader")["reasons"])

    def test_outputs_never_echo_untrusted_url(self):
        secretish_url = "******example.org/path?token=hidden"
        result = triage_url(secretish_url)
        self.assertNotIn(secretish_url, str(result))
        self.assertNotIn("password", str(result))
        self.assertNotIn("hidden", str(result))


if __name__ == "__main__":
    unittest.main()
