import contextlib
import io
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch


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


class PackageVerificationTests(unittest.TestCase):
    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_retries_transient_package_service_failure(
        self, run_adb, sleep, diagnostics
    ):
        run_adb.side_effect = [
            subprocess.CompletedProcess(
                "adb",
                1,
                stdout="",
                stderr="cmd: Failure calling service package: Broken pipe (32)",
            ),
            subprocess.CompletedProcess(
                "adb", 0, stdout="package:/data/app/base.apk", stderr=""
            ),
        ]
        diagnostics.return_value = "installed APK (exit 0): package:/data/app/base.apk"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.verify_package_installed(
                "com.example.actual", attempts=2
            )

        self.assertEqual(2, run_adb.call_count)
        run_adb.assert_called_with(
            "shell", "pm", "path", "com.example.actual", timeout=15
        )
        diagnostics.assert_called_once_with("com.example.actual")
        sleep.assert_called_once_with(2)
        self.assertIn("Broken pipe (32)", output.getvalue())

    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_retries_timeout_and_logs_captured_output(
        self, run_adb, sleep, diagnostics
    ):
        run_adb.side_effect = [
            subprocess.TimeoutExpired(
                "adb", 15, output=b"partial stdout", stderr=b"partial stderr"
            ),
            subprocess.CompletedProcess(
                "adb", 0, stdout="package:/data/app/base.apk", stderr=""
            ),
        ]
        diagnostics.return_value = "installed APK (exit 0): package:/data/app/base.apk"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.verify_package_installed(
                "com.example.actual", attempts=2
            )

        self.assertEqual(2, run_adb.call_count)
        diagnostics.assert_called_once_with("com.example.actual")
        sleep.assert_called_once_with(2)
        self.assertIn("timed out after 15s", output.getvalue())
        self.assertIn("partial stdout", output.getvalue())
        self.assertIn("partial stderr", output.getvalue())

    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_does_not_retry_missing_package(self, run_adb, sleep, diagnostics):
        run_adb.return_value = subprocess.CompletedProcess(
            "adb", 0, stdout="", stderr=""
        )
        diagnostics.return_value = "installed APK (exit 0): <no output>"

        with self.assertRaisesRegex(AssertionError, "is not installed"):
            android_emulator_smoke.verify_package_installed("com.missing.package")

        run_adb.assert_called_once_with(
            "shell", "pm", "path", "com.missing.package", timeout=15
        )
        diagnostics.assert_called_once_with("com.missing.package")
        sleep.assert_not_called()


class InstallApkTests(unittest.TestCase):
    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_retries_transient_package_service_broken_pipe(self, run_adb, sleep, diagnostics):
        run_adb.side_effect = [
            subprocess.CompletedProcess(
                "adb",
                1,
                stdout="",
                stderr="cmd: Failure calling service package: Broken pipe (32)",
            ),
            subprocess.CompletedProcess("adb", 0, stdout="Success", stderr=""),
        ]
        diagnostics.return_value = (
            "adb state (exit 0): device; boot completed (exit 0): 1; "
            "user CE available (exit 0): true; installed APK (exit 1): <no output>"
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            android_emulator_smoke.install_apk(
                Path("/build/app-debug.apk"), "com.example.actual"
            )

        self.assertEqual(2, run_adb.call_count)
        run_adb.assert_called_with(
            "install", "-r", "--no-streaming", "/build/app-debug.apk", timeout=120
        )
        diagnostics.assert_called_once_with("com.example.actual")
        sleep.assert_called_once_with(5)
        self.assertIn("Broken pipe (32)", output.getvalue())
        self.assertIn("boot completed (exit 0): 1", output.getvalue())

    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_retries_android_17_package_service_npe_markers(
        self, run_adb, sleep, diagnostics
    ):
        errors = (
            "java.lang.NullPointerException at "
            "com.android.server.StorageManagerService.allocateBytes",
            "java.lang.NullPointerException at "
            "com.android.server.pm.PackageManagerInternal",
        )
        diagnostics.return_value = "package service is starting"

        for error in errors:
            with self.subTest(error=error):
                self.assertNotIn("broken pipe", error.lower())
                run_adb.reset_mock()
                run_adb.side_effect = [
                    subprocess.CompletedProcess("adb", 1, stdout="", stderr=error),
                    subprocess.CompletedProcess("adb", 0, stdout="Success", stderr=""),
                ]
                sleep.reset_mock()
                diagnostics.reset_mock()

                with contextlib.redirect_stdout(io.StringIO()):
                    android_emulator_smoke.install_apk(
                        Path("/build/app-debug.apk"), "com.example.actual"
                    )

                self.assertEqual(2, run_adb.call_count)
                self.assertEqual(
                    [
                        ("install", "-r", "/build/app-debug.apk"),
                        ("install", "-r", "--no-streaming", "/build/app-debug.apk"),
                    ],
                    [call.args for call in run_adb.call_args_list],
                )
                diagnostics.assert_called_once_with("com.example.actual")
                sleep.assert_called_once_with(5)

    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_stops_after_six_transient_failures_with_alternating_installs(
        self, run_adb, sleep, diagnostics
    ):
        error = (
            "java.lang.NullPointerException at "
            "com.android.server.StorageManagerService.allocateBytes"
        )
        run_adb.side_effect = [
            subprocess.CompletedProcess("adb", 1, stdout="", stderr=error)
            for _ in range(6)
        ]
        diagnostics.return_value = "package service is starting"

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(AssertionError, "allocateBytes"):
                android_emulator_smoke.install_apk(
                    Path("/build/app-debug.apk"), "com.example.actual"
                )

        self.assertEqual(6, run_adb.call_count)
        self.assertEqual(
            [
                ("install", "-r", "/build/app-debug.apk"),
                ("install", "-r", "--no-streaming", "/build/app-debug.apk"),
                ("install", "-r", "/build/app-debug.apk"),
                ("install", "-r", "--no-streaming", "/build/app-debug.apk"),
                ("install", "-r", "/build/app-debug.apk"),
                ("install", "-r", "--no-streaming", "/build/app-debug.apk"),
            ],
            [call.args for call in run_adb.call_args_list],
        )
        self.assertTrue(
            all(call.kwargs == {"timeout": 120} for call in run_adb.call_args_list)
        )
        self.assertEqual(6, diagnostics.call_count)
        self.assertEqual([5, 10, 15, 20, 25], [call.args[0] for call in sleep.call_args_list])

    @patch("tools.android_emulator_smoke.package_diagnostics")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_does_not_retry_permanent_install_error(self, run_adb, sleep, diagnostics):
        run_adb.return_value = subprocess.CompletedProcess(
            "adb", 1, stdout="", stderr="Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]"
        )
        diagnostics.return_value = "package state (exit 0): bad signing certificate"
        with self.assertRaisesRegex(AssertionError, "INSTALL_FAILED_UPDATE_INCOMPATIBLE"):
            android_emulator_smoke.install_apk(
                Path("/build/app-debug.apk"), "com.example.actual"
            )

        run_adb.assert_called_once()
        diagnostics.assert_called_once_with("com.example.actual")
        sleep.assert_not_called()


class ActivityReadinessTests(unittest.TestCase):
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.run_adb")
    def test_waits_until_app_is_resumed(self, run_adb, sleep):
        run_adb.side_effect = [
            subprocess.CompletedProcess(
                "adb",
                0,
                stdout="topResumedActivity=ActivityRecord{abc com.android.launcher/.Home}",
                stderr="",
            ),
            subprocess.CompletedProcess(
                "adb",
                0,
                stdout=(
                    "topResumedActivity=ActivityRecord{def "
                    "com.example.actual/com.example.actual.Launcher}"
                ),
                stderr="",
            ),
        ]

        android_emulator_smoke.wait_for_resumed_activity("com.example.actual", attempts=2)

        self.assertEqual(2, run_adb.call_count)
        sleep.assert_called_once_with(2)


class DeviceUiReadinessTests(unittest.TestCase):
    # KeyguardServiceDelegate.dump / KeyguardStateMonitor.dump layout from AOSP.
    UNLOCKED_POLICY = """WINDOW MANAGER POLICY STATE (dumpsys window policy)
    mSafeMode=false mSystemReady=true mSystemBooted=true
    KeyguardServiceDelegate
      showing=false
      inputRestricted=false
      occluded=false
      secure=false
      dreaming=false
      systemIsReady=true
      deviceHasKeyguard=true
      enabled=true
      offReason=OFF_BECAUSE_OF_USER
      currentUser=0
      bootCompleted=true
      screenState=SCREEN_STATE_ON
      interactiveState=INTERACTIVE_STATE_AWAKE
      KeyguardStateMonitor
        mIsShowing=false
        mSimSecure=false
        mInputRestricted=false
        mTrusted=false
        mCurrentUserId=0
    Looper state:
      showing=true
"""
    LOCKED_POLICY = UNLOCKED_POLICY.replace(
        "showing=false", "showing=true"
    ).replace("mIsShowing=false", "mIsShowing=true")

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_wakes_and_dismisses_keyguard_before_ui_testing(self, adb, sleep):
        adb.side_effect = [
            "",
            "",
            self.LOCKED_POLICY,
            self.UNLOCKED_POLICY,
        ]

        android_emulator_smoke.wake_and_unlock_device()

        self.assertEqual(
            [
                ("shell", "input", "keyevent", "KEYCODE_WAKEUP"),
                ("shell", "wm", "dismiss-keyguard"),
                ("shell", "dumpsys", "window", "policy"),
                ("shell", "dumpsys", "window", "policy"),
            ],
            [call.args for call in adb.call_args_list],
        )
        sleep.assert_called_once_with(1)

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_fails_if_keyguard_cannot_be_dismissed(self, adb, sleep):
        adb.side_effect = ["", "", *[self.LOCKED_POLICY] * 2]

        with self.assertRaisesRegex(
            AssertionError, "Android keyguard remained visible"
        ):
            android_emulator_smoke.wake_and_unlock_device(attempts=2)

        self.assertEqual(4, adb.call_count)
        self.assertEqual(2, sleep.call_count)

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_accepts_already_unlocked_keyguard(self, adb, sleep):
        adb.side_effect = ["", "", self.UNLOCKED_POLICY]

        android_emulator_smoke.wake_and_unlock_device(attempts=1)

        self.assertEqual(3, adb.call_count)
        sleep.assert_not_called()

    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_rejects_unknown_or_conflicting_keyguard_state(self, adb, sleep):
        for state in (
            "",
            "isKeyguardShowing=false",
            "showing=false\nmIsShowing=false",
            "    KeyguardServiceDelegate\n      secure=false\n"
            "    Other section\n      showing=false\n",
            self.UNLOCKED_POLICY.replace("showing=false", "showing=true"),
            self.UNLOCKED_POLICY.replace("mIsShowing=false", "mIsShowing=true"),
        ):
            with self.subTest(state=state):
                adb.side_effect = ["", "", state]
                with self.assertRaisesRegex(
                    AssertionError, "Android keyguard remained visible"
                ):
                    android_emulator_smoke.wake_and_unlock_device(attempts=1)


class HierarchyTests(unittest.TestCase):
    @patch("tools.android_emulator_smoke.subprocess.run")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_retries_transient_ui_automation_registration_failure(self, adb, sleep, run):
        adb.side_effect = [
            subprocess.CalledProcessError(137, "uiautomator", stderr=""),
            "UI hierarchy dumped",
            "<hierarchy><node /></hierarchy>",
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            hierarchy = android_emulator_smoke.hierarchy()

        self.assertEqual("hierarchy", hierarchy.tag)
        self.assertEqual(3, adb.call_count)
        self.assertEqual(2, run.call_count)
        self.assertIn("attempt 1 failed (exit 137)", output.getvalue())
        sleep.assert_called_once_with(2)

    @patch("tools.android_emulator_smoke.subprocess.run")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_retries_subprocess_timeout(self, adb, sleep, run):
        adb.side_effect = [
            subprocess.TimeoutExpired("uiautomator", 30),
            "UI hierarchy dumped",
            "<hierarchy><node /></hierarchy>",
        ]

        hierarchy = android_emulator_smoke.hierarchy()

        self.assertEqual("hierarchy", hierarchy.tag)
        self.assertEqual(3, adb.call_count)
        self.assertEqual(2, run.call_count)
        sleep.assert_called_once_with(2)

    @patch("tools.android_emulator_smoke.subprocess.run")
    @patch("tools.android_emulator_smoke.time.sleep")
    @patch("tools.android_emulator_smoke.adb")
    def test_does_not_retry_permanent_ui_automation_failure(self, adb, sleep, run):
        adb.side_effect = subprocess.CalledProcessError(
            1, "uiautomator", stderr="permission denied"
        )
        with self.assertRaisesRegex(AssertionError, "permission denied"):
            android_emulator_smoke.hierarchy()

        adb.assert_called_once()
        run.assert_called_once()
        sleep.assert_not_called()


class TapUntilTextTests(unittest.TestCase):
    def test_retries_the_tap_until_expected_text_appears(self):
        with (
            patch("tools.android_emulator_smoke.tap") as tap,
            patch("tools.android_emulator_smoke.wait_for_text") as wait_for_text,
        ):
            wait_for_text.side_effect = [
                AssertionError("Expected UI text not found"),
                "Enter a term or statement first.",
            ]

            result = android_emulator_smoke.tap_until_text(
                "assistant_request_button",
                "Enter a term",
                status_resource_id="assistant_request_status",
            )

        self.assertEqual("Enter a term or statement first.", result)
        self.assertEqual(
            [
                call("assistant_request_button"),
                call("assistant_request_status"),
                call("assistant_request_button"),
                call("assistant_request_status"),
            ],
            tap.call_args_list,
        )
        self.assertEqual(2, wait_for_text.call_count)

    def test_raises_after_all_tap_attempts(self):
        with (
            patch("tools.android_emulator_smoke.tap") as tap,
            patch(
                "tools.android_emulator_smoke.wait_for_text",
                side_effect=AssertionError("Expected UI text not found"),
            ) as wait_for_text,
        ):
            with self.assertRaisesRegex(AssertionError, "Expected UI text not found"):
                android_emulator_smoke.tap_until_text(
                    "assistant_request_button", "Enter a term"
                )

        self.assertEqual(3, tap.call_count)
        self.assertEqual(3, wait_for_text.call_count)


if __name__ == "__main__":
    unittest.main()
