import contextlib
import io
import os
import subprocess
from pathlib import Path
import tempfile
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
    def test_status_timeout_with_zero_exit_is_logged_and_retried(self, run, adb, sleep):
        run.side_effect = [
            subprocess.CompletedProcess(
                "adb", 0, stdout="Warning: Activity not started\nStatus: timeout", stderr=""
            ),
            subprocess.CompletedProcess("adb", 0, stdout="Status: ok", stderr=""),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.start_activity("example", ".MainActivity")

        self.assertEqual(2, run.call_count)
        self.assertIn("attempt 1 failed:", output.getvalue())
        self.assertIn("Status: timeout", output.getvalue())
        adb.assert_called_once_with("shell", "input", "keyevent", "KEYCODE_HOME")
        sleep.assert_called_once_with(3)

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


class ApkLaunchTargetTests(unittest.TestCase):
    def test_resolves_application_id_and_launcher_from_apk_badging(self):
        badging = (
            "package: name='com.example.actual' versionCode='1'\n"
            "launchable-activity: name='com.example.actual.Launcher' label='Example'\n"
        )
        self.assertEqual(
            ("com.example.actual", "com.example.actual.Launcher"),
            android_emulator_smoke.parse_apk_launch_target(badging),
        )

    def test_expands_relative_launcher_name(self):
        badging = (
            "package: name='com.example.actual' versionCode='1'\n"
            "launchable-activity: name='.Launcher' label='Example'\n"
        )
        self.assertEqual(
            ("com.example.actual", "com.example.actual.Launcher"),
            android_emulator_smoke.parse_apk_launch_target(badging),
        )

    def test_fails_with_manifest_output_when_launcher_is_missing(self):
        with self.assertRaisesRegex(AssertionError, "no application ID or launcher activity"):
            android_emulator_smoke.parse_apk_launch_target(
                "package: name='com.example.actual'\n"
            )

    @patch("tools.android_emulator_smoke.subprocess.run")
    def test_reads_badging_from_built_apk(self, run):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / "build-tools" / "35.0.0"
            tools.mkdir(parents=True)
            aapt = tools / "aapt"
            aapt.touch()
            run.return_value = subprocess.CompletedProcess(
                "aapt",
                0,
                stdout=(
                    "package: name='com.example.actual'\n"
                    "launchable-activity: name='.Launcher'\n"
                ),
                stderr="",
            )
            with patch(
                "tools.android_emulator_smoke.ANDROID_BUILD_TOOLS",
                tools.parent,
            ):
                target = android_emulator_smoke.resolve_apk_launch_target(
                    Path("/build/app-debug.apk")
                )

        self.assertEqual(
            ("com.example.actual", "com.example.actual.Launcher"),
            target,
        )
        run.assert_called_once_with(
            [str(aapt), "dump", "badging", "/build/app-debug.apk"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )


class ClearAppDataTests(unittest.TestCase):
    def test_retries_known_transient_package_manager_failure(self):
        clear_attempts = 0

        def fake_run_adb(*args, **kwargs):
            nonlocal clear_attempts
            if args == ("shell", "pm", "clear", "com.example.actual"):
                clear_attempts += 1
                if clear_attempts == 1:
                    return subprocess.CompletedProcess(
                        "adb", 224, stdout="", stderr="Can't find service: package"
                    )
                return subprocess.CompletedProcess("adb", 0, stdout="Success", stderr="")
            if args == ("get-state",):
                return subprocess.CompletedProcess("adb", 0, stdout="device", stderr="")
            if args == ("shell", "getprop", "sys.boot_completed"):
                return subprocess.CompletedProcess("adb", 0, stdout="1", stderr="")
            if args == ("shell", "getprop", "sys.user.0.ce_available"):
                return subprocess.CompletedProcess("adb", 0, stdout="true", stderr="")
            if args == ("shell", "pm", "path", "com.example.actual"):
                return subprocess.CompletedProcess(
                    "adb", 0, stdout="package:/data/app/base.apk", stderr=""
                )
            if args == ("shell", "dumpsys", "package", "com.example.actual"):
                return subprocess.CompletedProcess(
                    "adb", 0, stdout="Package [com.example.actual]", stderr=""
                )
            self.fail(f"Unexpected adb command: {args}")

        with (
            patch("tools.android_emulator_smoke.run_adb", side_effect=fake_run_adb),
            patch("tools.android_emulator_smoke.time.sleep") as sleep,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            android_emulator_smoke.clear_app_data("com.example.actual")

        self.assertEqual(2, clear_attempts)
        sleep.assert_called_once_with(2)
        self.assertIn("Can't find service: package", output.getvalue())
        self.assertIn("boot completed (exit 0): 1", output.getvalue())
        self.assertIn("installed APK (exit 0): package:/data/app/base.apk", output.getvalue())

    def test_retries_empty_exit_224_when_emulator_and_package_are_ready(self):
        clear_attempts = 0
        def fake_run_adb(*args, **kwargs):
            nonlocal clear_attempts
            if args == ("shell", "pm", "clear", "com.example.actual"):
                clear_attempts += 1
                if clear_attempts == 1:
                    return subprocess.CompletedProcess("adb", 224, stdout="", stderr="")
                return subprocess.CompletedProcess("adb", 0, stdout="Success", stderr="")
            if args == ("get-state",):
                return subprocess.CompletedProcess("adb", 0, stdout="device", stderr="")
            if args == ("shell", "getprop", "sys.boot_completed"):
                return subprocess.CompletedProcess("adb", 0, stdout="1", stderr="")
            if args == ("shell", "getprop", "sys.user.0.ce_available"):
                return subprocess.CompletedProcess("adb", 0, stdout="true", stderr="")
            if args == ("shell", "pm", "path", "com.example.actual"):
                return subprocess.CompletedProcess(
                    "adb", 0, stdout="package:/data/app/base.apk", stderr=""
                )
            if args == ("shell", "dumpsys", "package", "com.example.actual"):
                return subprocess.CompletedProcess(
                    "adb", 0, stdout="Package [com.example.actual]", stderr=""
                )
            self.fail(f"Unexpected adb command: {args}")

        with (
            patch("tools.android_emulator_smoke.run_adb", side_effect=fake_run_adb),
            patch("tools.android_emulator_smoke.time.sleep") as sleep,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            android_emulator_smoke.clear_app_data("com.example.actual")

        self.assertEqual(2, clear_attempts)
        sleep.assert_called_once_with(2)
        self.assertIn("exit 224", output.getvalue())
        self.assertIn("Package [com.example.actual]", output.getvalue())

    def test_does_not_retry_exit_224_when_package_is_not_installed(self):
        commands = []

        def fake_run_adb(*args, **kwargs):
            commands.append(args)
            if args == ("shell", "pm", "clear", "com.example.actual"):
                return subprocess.CompletedProcess("adb", 224, stdout="", stderr="")
            if args == ("get-state",):
                return subprocess.CompletedProcess("adb", 0, stdout="device", stderr="")
            if args == ("shell", "getprop", "sys.boot_completed"):
                return subprocess.CompletedProcess("adb", 0, stdout="1", stderr="")
            if args == ("shell", "getprop", "sys.user.0.ce_available"):
                return subprocess.CompletedProcess("adb", 0, stdout="true", stderr="")
            if args == ("shell", "pm", "path", "com.example.actual"):
                return subprocess.CompletedProcess("adb", 1, stdout="", stderr="")
            if args == ("shell", "dumpsys", "package", "com.example.actual"):
                return subprocess.CompletedProcess("adb", 0, stdout="Unable to find package", stderr="")
            self.fail(f"Unexpected adb command: {args}")

        with patch("tools.android_emulator_smoke.run_adb", side_effect=fake_run_adb):
            with self.assertRaisesRegex(AssertionError, r"exit 224.*installed APK \(exit 1\)"):
                android_emulator_smoke.clear_app_data("com.example.actual")

        self.assertEqual(
            1,
            commands.count(("shell", "pm", "clear", "com.example.actual")),
        )

    def test_does_not_retry_permanent_package_error(self):
        run = patch(
            "tools.android_emulator_smoke.run_adb",
            return_value=subprocess.CompletedProcess(
                "adb", 1, stdout="Failure [package not found]", stderr=""
            ),
        )
        with run as mocked_run:
            with self.assertRaisesRegex(AssertionError, "Failure \\[package not found\\]"):
                android_emulator_smoke.clear_app_data("com.missing.package")

        self.assertEqual(
            1,
            sum(
                call.args[:4] == ("shell", "pm", "clear", "com.missing.package")
                for call in mocked_run.call_args_list
            ),
        )


if __name__ == "__main__":
    unittest.main()
