import re
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path


ANDROID_HOME = Path(__import__("os").environ["ANDROID_HOME"])
ADB = str(ANDROID_HOME / "platform-tools" / "adb")
ANDROID_BUILD_TOOLS = ANDROID_HOME / "build-tools"
NETWORK_ERROR_TEXT = (
    "Backend konnte nicht sicher erreicht werden",
    "The backend could not be reached securely",
)
PACKAGE_MANAGER_TRANSIENT_ERRORS = (
    "broken pipe",
    "failure calling service package",
    "can't find service: package",
    "could not access the package manager",
    "package manager has died",
    "deadobjectexception",
    "device offline",
    "device not found",
    "connection reset",
    "timed out",
    "packagemanagerinternal",
    "storagemanagerservice.allocatebytes",
)


def run_adb(*args, timeout=30):
    return subprocess.run(
        [ADB, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def adb(*args, timeout=30):
    result = run_adb(*args, timeout=timeout)
    if result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode,
            [ADB, *args],
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def parse_apk_launch_target(badging):
    package = re.search(r"(?m)^package: name='([^']+)'", badging)
    activity = re.search(r"(?m)^launchable-activity: name='([^']+)'", badging)
    if package is None or activity is None:
        raise AssertionError(f"APK manifest has no application ID or launcher activity:\n{badging}")
    package_name = package.group(1)
    activity_name = activity.group(1)
    if activity_name.startswith("."):
        activity_name = f"{package_name}{activity_name}"
    elif "." not in activity_name:
        activity_name = f"{package_name}.{activity_name}"
    return package_name, activity_name


def resolve_apk_launch_target(apk):
    tools = sorted(
        (path for path in ANDROID_BUILD_TOOLS.glob("*/aapt") if path.is_file()),
        key=lambda path: tuple(int(part) for part in re.findall(r"\d+", path.parent.name)),
    )
    if not tools:
        raise AssertionError(f"Android build-tools aapt was not found under {ANDROID_BUILD_TOOLS}")
    result = subprocess.run(
        [str(tools[-1]), "dump", "badging", str(apk)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return parse_apk_launch_target(result.stdout)


def package_diagnostics(package):
    diagnostics = []
    for label, args in (
        ("adb state", ("get-state",)),
        ("boot completed", ("shell", "getprop", "sys.boot_completed")),
        ("user CE available", ("shell", "getprop", "sys.user.0.ce_available")),
        ("installed APK", ("shell", "pm", "path", package)),
        ("package state", ("shell", "dumpsys", "package", package)),
    ):
        try:
            result = run_adb(*args, timeout=10)
            output = (result.stdout + "\n" + result.stderr).strip()
            if label == "package state":
                output = output[:600]
            diagnostics.append(f"{label} (exit {result.returncode}): {output or '<no output>'}")
        except (OSError, subprocess.SubprocessError) as exc:
            diagnostics.append(f"{label}: {exc}")
    return "; ".join(diagnostics)


def clear_app_data(package, attempts=3):
    for attempt in range(attempts):
        try:
            result = run_adb("shell", "pm", "clear", package, timeout=30)
            output = f"{result.stdout}\n{result.stderr}".strip()
            if result.returncode == 0 and result.stdout.strip() == "Success":
                return
            returncode = result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value or ""
                for value in (exc.stdout, exc.stderr)
            )
            output = f"timed out after {exc.timeout}s\n{stdout}\n{stderr}".strip()
            returncode = "timeout"

        diagnostics = package_diagnostics(package)
        diagnostic_text = diagnostics.lower()
        transient = any(
            error in output.lower() for error in PACKAGE_MANAGER_TRANSIENT_ERRORS
        ) or (
            returncode == 224
            and not output
            and "adb state (exit 0): device" in diagnostic_text
            and "boot completed (exit 0): 1" in diagnostic_text
            and "user ce available (exit 0): true" in diagnostic_text
            and "installed apk (exit 0): package:" in diagnostic_text
        )
        message = (
            f"pm clear attempt {attempt + 1} failed for {package} "
            f"(exit {returncode}): {output or '<no output>'}; {diagnostics}"
        )
        print(message, flush=True)
        if not transient or attempt + 1 == attempts:
            raise AssertionError(message)
        time.sleep(2)


def verify_package_installed(package, attempts=3):
    for attempt in range(attempts):
        try:
            result = run_adb("shell", "pm", "path", package, timeout=15)
            output = f"{result.stdout}\n{result.stderr}".strip()
            returncode = result.returncode
            if returncode == 0 and result.stdout.strip().startswith("package:"):
                return
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value or ""
                for value in (exc.stdout, exc.stderr)
            )
            output = f"timed out after {exc.timeout}s\n{stdout}\n{stderr}".strip()
            returncode = "timeout"

        diagnostics = package_diagnostics(package)
        transient = any(
            error in output.lower() for error in PACKAGE_MANAGER_TRANSIENT_ERRORS
        )
        message = (
            f"APK package {package} is not installed "
            f"(verification attempt {attempt + 1}, exit {returncode}): "
            f"{output or '<no output>'}; {diagnostics}"
        )
        print(message, flush=True)
        if not transient or attempt + 1 == attempts:
            raise AssertionError(message)
        time.sleep(2)


def verify_installed_launcher(package, manifest_activity):
    verify_package_installed(package)
    return resolve_installed_launcher(package, manifest_activity)


def install_apk(apk, package, attempts=6):
    for attempt in range(attempts):
        try:
            # Alternate to the legacy installer when streamed installs hit
            # a not-yet-ready storage/package service.
            install_args = ("install", "-r") + (
                ("--no-streaming",) if attempt % 2 else ()
            )
            result = run_adb(*install_args, str(apk), timeout=120)
            output = f"{result.stdout}\n{result.stderr}".strip()
            returncode = result.returncode
            if returncode == 0 and "success" in result.stdout.lower():
                return
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value or ""
                for value in (exc.stdout, exc.stderr)
            )
            output = f"timed out after {exc.timeout}s\n{stdout}\n{stderr}".strip()
            returncode = "timeout"

        diagnostics = package_diagnostics(package)
        transient = any(
            error in output.lower() for error in PACKAGE_MANAGER_TRANSIENT_ERRORS
        )
        message = (
            f"APK install attempt {attempt + 1} failed for {package} "
            f"(exit {returncode}): {output or '<no output>'}; {diagnostics}"
        )
        print(message, flush=True)
        if not transient or attempt + 1 == attempts:
            raise AssertionError(message)
        time.sleep(5 * (attempt + 1))


def resolve_installed_launcher(package, manifest_activity, attempts=5):
    args = (
        "shell",
        "cmd",
        "package",
        "resolve-activity",
        "--brief",
        "-a",
        "android.intent.action.MAIN",
        "-c",
        "android.intent.category.LAUNCHER",
        "-p",
        package,
    )
    for attempt in range(attempts):
        try:
            result = run_adb(*args, timeout=15)
            output = f"{result.stdout}\n{result.stderr}".strip()
            returncode = result.returncode
            stdout = result.stdout
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value or ""
                for value in (exc.stdout, exc.stderr)
            )
            output = f"timed out after {exc.timeout}s\n{stdout}\n{stderr}".strip()
            returncode = "timeout"

        component = re.search(
            rf"(?m)^\s*{re.escape(package)}/([^\s]+)\s*$",
            stdout,
        )
        if returncode == 0 and component is not None:
            activity = component.group(1)
            if activity.startswith("."):
                activity = f"{package}{activity}"
            elif "." not in activity:
                activity = f"{package}.{activity}"
            if activity != manifest_activity:
                raise AssertionError(
                    f"Installed launcher for {package} is {activity}, "
                    f"but the APK manifest declares {manifest_activity}; "
                    f"{package_diagnostics(package)}"
                )
            return activity

        diagnostics = package_diagnostics(package)
        transient = (
            any(error in output.lower() for error in PACKAGE_MANAGER_TRANSIENT_ERRORS)
            or "no activity found" in output.lower()
            or (returncode == 0 and not output)
        )
        message = (
            f"Installed launcher resolution attempt {attempt + 1} failed for {package} "
            f"(exit {returncode}): {output or '<no output>'}; {diagnostics}"
        )
        print(message, flush=True)
        if not transient or attempt + 1 == attempts:
            raise AssertionError(message)
        time.sleep(2)


def start_activity(package, main_activity, attempts=5):
    # am can fail transiently right after install/pm clear while the system settles.
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                [ADB, "shell", "am", "start", "-W", "-n", f"{package}/{main_activity}"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = f"{result.stdout}\n{result.stderr}"
            if (
                result.returncode == 0
                and "Error" not in output
                and "Status: timeout" not in output
            ):
                print(f"Activity start succeeded for {package}/{main_activity}: {output.strip()}", flush=True)
                return
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = (
                value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
                for value in (exc.stdout, exc.stderr)
            )
            output = f"timed out after {exc.timeout}s\n{stdout}\n{stderr}"
        print(f"am start attempt {attempt + 1} failed: {output.strip()}", flush=True)
        try:
            adb("shell", "input", "keyevent", "KEYCODE_HOME")
        except (subprocess.SubprocessError, OSError) as exc:
            print(f"HOME keyevent failed: {exc}", flush=True)
        time.sleep(3)
    raise AssertionError(f"Could not start {package}/{main_activity}: {output.strip()}")


class HttpsProbeServer:
    def __init__(self, certificate, private_key):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, private_key)
        self.context = context
        self.connections = 0
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 18443))
        self.server.listen()
        self.server.settimeout(0.5)
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        self.thread.start()

    def _serve(self):
        while True:
            try:
                connection, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections += 1
            with connection:
                try:
                    with self.context.wrap_socket(connection, server_side=True) as secure_connection:
                        secure_connection.recv(4096)
                        body = b'{"status":"ready"}'
                        secure_connection.sendall(
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Content-Length: 18\r\n"
                            b"Connection: close\r\n\r\n"
                            + body
                        )
                except (OSError, ssl.SSLError):
                    pass

    def close(self):
        self.server.close()
        self.thread.join(timeout=2)


def hierarchy(attempts=6):
    for attempt in range(attempts):
        try:
            run_adb("shell", "rm", "-f", "/sdcard/window.xml", timeout=15)
            adb("shell", "uiautomator", "dump", "/sdcard/window.xml", timeout=30)
            return ET.fromstring(adb("exec-out", "cat", "/sdcard/window.xml"))
        except subprocess.CalledProcessError as exc:
            failure = exc
            output = "\n".join(value for value in (exc.stdout, exc.stderr) if value)
            transient = exc.returncode == 137 or any(
                error in output.lower()
                for error in (
                    "deadobjectexception",
                    "error while registering uitestautomationservice",
                )
            )
            message = (
                f"UI hierarchy attempt {attempt + 1} failed "
                f"(exit {exc.returncode}): {output or exc}"
            )
        except ET.ParseError as exc:
            failure = exc
            transient = True
            message = f"UI hierarchy attempt {attempt + 1} returned invalid XML: {exc}"

        print(message, flush=True)
        if not transient or attempt + 1 == attempts:
            raise AssertionError(message) from failure
        run_adb("shell", "killall", "uiautomator", timeout=15)
        time.sleep(3)


def screen_size():
    match = re.findall(r"(\d+)x(\d+)", adb("shell", "wm", "size"))
    if not match:
        raise AssertionError("Could not determine emulator display size")
    return tuple(map(int, match[-1]))


def visible_node(resource_id):
    width, height = screen_size()
    suffix = f":id/{resource_id}"
    for node in hierarchy().iter("node"):
        if not node.get("resource-id", "").endswith(suffix):
            continue
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
        if bounds is None:
            continue
        left, top, right, bottom = map(int, bounds.groups())
        x, y = (left + right) // 2, (top + bottom) // 2
        if 0 <= x < width and 0 <= y < height and node.get("enabled", "true") == "true":
            return x, y, node
    return None


def tap(resource_id):
    width, height = screen_size()
    for start_y, end_y in (
        (height * 4 // 5, height // 3),
        (height // 3, height * 4 // 5),
    ):
        for _ in range(10):
            target = visible_node(resource_id)
            if target is not None:
                x, y, _ = target
                adb("shell", "input", "tap", str(x), str(y))
                time.sleep(0.5)
                return
            adb(
                "shell",
                "input",
                "swipe",
                str(width // 2),
                str(start_y),
                str(width // 2),
                str(end_y),
                "350",
            )
            time.sleep(0.2)
    raise AssertionError(f"Could not find visible, enabled control {resource_id}")


def wait_for_text(*expected, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        text = " ".join(
            value
            for node in hierarchy().iter("node")
            for value in (node.get("text", ""), node.get("content-desc", ""))
            if value
        )
        if any(value in text for value in expected):
            return text
        time.sleep(0.5)
    raise AssertionError(f"Expected UI text not found: {expected}")


def wait_for_input_text(resource_id, expected, timeout=15):
    deadline = time.monotonic() + timeout
    suffix = f":id/{resource_id}"
    while time.monotonic() < deadline:
        for node in hierarchy().iter("node"):
            if (
                node.get("resource-id", "").endswith(suffix)
                and node.get("text") == expected
            ):
                return
        time.sleep(0.5)
    raise AssertionError(f"Expected {resource_id} to contain {expected!r}")


def has_resumed_activity(activity_state, package):
    return re.search(
        rf"(?m)^\s*(?:mResumedActivity|topResumedActivity)\s*[:=]\s*"
        rf"ActivityRecord\{{[^\n]*\b{re.escape(package)}/",
        activity_state,
    ) is not None


def wait_for_resumed_activity(package, attempts=5):
    for attempt in range(attempts):
        result = run_adb("shell", "dumpsys", "activity", "activities", timeout=15)
        if result.returncode == 0 and has_resumed_activity(result.stdout, package):
            return
        output = result.stdout.strip()
        message = (
            f"Activity readiness attempt {attempt + 1} failed for {package} "
            f"(exit {result.returncode}): {output[:800] or result.stderr.strip() or '<no output>'}"
        )
        print(message, flush=True)
        if attempt + 1 == attempts:
            raise AssertionError(f"{message}; {package_diagnostics(package)}")
        time.sleep(2)


def test_app(apk, brand, server):
    package, main_activity = resolve_apk_launch_target(apk)
    print(
        f"Testing {apk}: applicationId={package}, launcherActivity={main_activity}",
        flush=True,
    )
    install_apk(apk, package)
    main_activity = verify_installed_launcher(package, main_activity)
    clear_app_data(package)
    main_activity = verify_installed_launcher(package, main_activity)
    package_state = adb("shell", "dumpsys", "package", package)
    if re.search(
        r"(?m)^\s*android\.permission\.INTERNET:\s+granted=true(?:,|$)",
        package_state,
    ) is None:
        raise AssertionError(f"{package} INTERNET is not granted")

    start_activity(package, main_activity)
    wait_for_resumed_activity(package)
    wait_for_text(brand)

    tap("assistant_button")
    tap("assistant_request_button")
    wait_for_text("Bitte gib zuerst", "Enter a term")
    tap("assistant_close_button")

    tap("learning_profile_button")
    switch = visible_node("learning_enabled_switch")
    if switch is None:
        tap("learning_enabled_switch")
        switch = visible_node("learning_enabled_switch")
    else:
        _, _, node = switch
        if node.get("checked") != "true":
            tap("learning_enabled_switch")
    switch = visible_node("learning_enabled_switch")
    if switch is None or switch[2].get("checked") != "true":
        raise AssertionError(f"{package} could not enable the learning profile")

    tap("session_summary_input")
    adb("shell", "input", "text", "CIemulatorcheck")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    tap("save_session_summary_button")
    wait_for_text("Zusammenfassung lokal gespeichert", "Summary saved locally")

    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    adb("shell", "am", "force-stop", package)
    start_activity(package, main_activity)
    wait_for_text(brand)
    tap("learning_profile_button")
    wait_for_input_text("session_summary_input", "CIemulatorcheck")

    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    tap("support_contact_button")
    previous_connections = server.connections
    tap("support_check_ai")
    wait_for_text(*NETWORK_ERROR_TEXT, timeout=20)
    deadline = time.monotonic() + 5
    while server.connections == previous_connections and time.monotonic() < deadline:
        time.sleep(0.1)
    if server.connections <= previous_connections:
        raise AssertionError(f"{package} did not reach the local HTTPS test endpoint")

    activity_state = adb("shell", "dumpsys", "activity", "activities")
    if not has_resumed_activity(activity_state, package):
        raise AssertionError(f"{package} has no resumed or top-resumed activity")
    print(f"{package}: app start, assistant, profile persistence, INTERNET, HTTPS failure handling passed")


def main():
    with tempfile.TemporaryDirectory(prefix="android-emulator-smoke-") as directory:
        certificate = Path(directory) / "probe.crt"
        private_key = Path(directory) / "probe.key"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=emulator-network-probe.invalid",
                "-keyout",
                str(private_key),
                "-out",
                str(certificate),
            ],
            check=True,
            capture_output=True,
        )
        server = HttpsProbeServer(certificate, private_key)
        server.start()
        try:
            niknolig_apk = next(
                Path("apps/niknolig/build/outputs/apk/debug").glob("*.apk")
            )
            test_app(
                niknolig_apk,
                "NIKNOLIG",
                server,
            )
            defense_apk = next(
                Path("apps/niknolig-defense/build/outputs/apk/debug").glob("*.apk")
            )
            test_app(
                defense_apk,
                "NIKNOLIG Defense",
                server,
            )
        finally:
            server.close()


if __name__ == "__main__":
    main()
