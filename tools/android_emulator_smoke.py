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
NETWORK_ERROR_TEXT = (
    "Backend konnte nicht sicher erreicht werden",
    "The backend could not be reached securely",
)


def adb(*args, timeout=30):
    return subprocess.run(
        [ADB, *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    ).stdout.strip()


def start_activity(package, main_activity, attempts=5):
    # am can fail transiently right after install/pm clear while the system settles.
    result = None
    for attempt in range(attempts):
        result = subprocess.run(
            [ADB, "shell", "am", "start", "-W", "-n", f"{package}/{main_activity}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode == 0 and "Error" not in output:
            return
        print(f"am start attempt {attempt + 1} failed: {output.strip()}", flush=True)
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
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


def hierarchy():
    adb("shell", "uiautomator", "dump", "/sdcard/window.xml", timeout=30)
    return ET.fromstring(adb("exec-out", "cat", "/sdcard/window.xml"))


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


def test_app(package, brand, main_activity, server):
    adb("shell", "pm", "clear", package)
    package_state = adb("shell", "dumpsys", "package", package)
    if re.search(
        r"(?m)^\s*android\.permission\.INTERNET:\s+granted=true(?:,|$)",
        package_state,
    ) is None:
        raise AssertionError(f"{package} INTERNET is not granted")

    start_activity(package, main_activity)
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
            test_app(
                "com.niknolig.app",
                "NIKNOLIG",
                ".MainActivity",
                server,
            )
            test_app(
                "com.niknolig.defense",
                "NIKNOLIG Defense",
                ".MainActivity",
                server,
            )
        finally:
            server.close()


if __name__ == "__main__":
    main()
