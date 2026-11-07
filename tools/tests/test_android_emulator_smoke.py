import contextlib
import io
import os
import subprocess
import unittest
from unittest.mock import patch


with patch.dict(os.environ, {"ANDROID_HOME": "/android-sdk"}):
    from tools import android_emulator_smoke


class StartActivityTests(unittest.TestCase):
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_timeout_is_logged_and_retried(self, run, adb, sleep):
        run.side_effect = [
            subprocess.TimeoutExpired("adb", 60, output=b"partial stdout", stderr=b"partial stderr"),
            subprocess.CompletedProcess("adb", 0, stdout="Started", stderr=""),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.start_activity("example", ".MainActivity")

        self.assertEqual(2, run.call_count)
        self.assertIn("attempt 1 failed: timed out after 60s", output.getvalue())
        self.assertIn("partial stdout", output.getvalue())
        self.assertIn("partial stderr", output.getvalue())
        adb.assert_called_once_with("shell", "input", "keyevent", "KEYCODE_HOME")
        sleep.assert_called_once_with(3)

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_timeouts_are_bounded_and_report_last_output(self, run, adb, sleep):
        run.side_effect = [
            subprocess.TimeoutExpired("adb", 60),
            subprocess.TimeoutExpired("adb", 60, output=b"last \xffoutput"),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(AssertionError, "(?s)timed out after 60s.*last \ufffdoutput"):
                android_emulator_smoke.start_activity("example", ".MainActivity", attempts=2)

        self.assertEqual(2, run.call_count)
        self.assertEqual(2, adb.call_count)
        self.assertEqual(2, sleep.call_count)
        self.assertIn("attempt 1 failed: timed out after 60s", output.getvalue())
        self.assertIn("attempt 2 failed: timed out after 60s", output.getvalue())

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_nonzero_exit_still_retries(self, run, adb, sleep):
        run.side_effect = [
            subprocess.CompletedProcess("adb", 1, stdout="", stderr="failed"),
            subprocess.CompletedProcess("adb", 0, stdout="Started", stderr=""),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.start_activity("example", ".MainActivity")

        self.assertEqual(2, run.call_count)
        self.assertIn("failed", output.getvalue())
        adb.assert_called_once()
        sleep.assert_called_once()

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_home_keyevent_failure_does_not_stop_retries(self, run, adb, sleep):
        run.side_effect = [
            subprocess.CompletedProcess("adb", 1, stdout="", stderr="launch failed"),
            subprocess.CompletedProcess("adb", 0, stdout="Started", stderr=""),
        ]
        adb.side_effect = subprocess.CalledProcessError(1, "adb", stderr="home failed")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.start_activity("example", ".MainActivity")

        self.assertEqual(2, run.call_count)
        self.assertIn("HOME keyevent failed", output.getvalue())
        self.assertIn("attempt 1 failed: launch failed", output.getvalue())
        adb.assert_called_once()
        sleep.assert_called_once_with(3)

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_home_keyevent_timeout_does_not_stop_retries(self, run, adb, sleep):
        run.side_effect = [
            subprocess.CompletedProcess("adb", 1, stdout="", stderr="launch failed"),
            subprocess.CompletedProcess("adb", 0, stdout="Started", stderr=""),
        ]
        adb.side_effect = subprocess.TimeoutExpired("adb", 30)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.start_activity("example", ".MainActivity")

        self.assertEqual(2, run.call_count)
        self.assertIn("HOME keyevent failed", output.getvalue())
        self.assertIn("attempt 1 failed: launch failed", output.getvalue())
        adb.assert_called_once()
        sleep.assert_called_once_with(3)


if __name__ == "__main__":
    unittest.main()
