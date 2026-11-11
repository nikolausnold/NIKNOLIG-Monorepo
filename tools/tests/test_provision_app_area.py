import io
import json
import os
import unittest
from unittest import mock

from tools import provision_app_area as tool

USER = "11111111-2222-3333-4444-555555555555"
ENV = {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "service-key"}


class FakeOpener:
    def __init__(self, reply):
        self.reply, self.requests = reply, []

    def open(self, request, timeout):
        self.requests.append(request)
        return io.BytesIO(json.dumps(self.reply).encode())


class ProvisionAppAreaTests(unittest.TestCase):
    def run_tool(self, args, env=ENV, opener=None):
        with mock.patch.dict(os.environ, env, clear=True):
            return tool.main(args, opener)

    def test_dry_run_sends_nothing(self):
        opener = FakeOpener({})
        self.assertEqual(0, self.run_tool(["--user-id", USER, "--area", "niknolig"], opener=opener))
        self.assertEqual([], opener.requests)

    def test_apply_sets_only_the_area_claim_over_https(self):
        opener = FakeOpener({"app_metadata": {"app_area": "niknolig-defense"}})
        code = self.run_tool(["--user-id", USER, "--area", "niknolig-defense", "--apply"], opener=opener)
        self.assertEqual(0, code)
        request = opener.requests[0]
        self.assertEqual(f"https://example.supabase.co/auth/v1/admin/users/{USER}", request.full_url)
        self.assertEqual({"app_metadata": {"app_area": "niknolig-defense"}}, json.loads(request.data))

    def test_unconfirmed_claim_fails(self):
        opener = FakeOpener({"app_metadata": {}})
        self.assertEqual(1, self.run_tool(["--user-id", USER, "--area", "niknolig", "--apply"], opener=opener))

    def test_rejects_unsafe_configuration(self):
        for env in (
            {**ENV, "SUPABASE_URL": "http://example.supabase.co"},
            {**ENV, "SUPABASE_URL": "https://example.supabase.co/path"},
            {**ENV, "SUPABASE_URL": "https://user@example.supabase.co"},
            {"SUPABASE_URL": ENV["SUPABASE_URL"]},
        ):
            self.assertEqual(2, self.run_tool(["--user-id", USER, "--area", "niknolig", "--apply"], env=env))
        with self.assertRaises(SystemExit):
            self.run_tool(["--user-id", USER, "--area", "other"])
        self.assertEqual(2, self.run_tool(["--user-id", "../x", "--area", "niknolig"]))


if __name__ == "__main__":
    unittest.main()
