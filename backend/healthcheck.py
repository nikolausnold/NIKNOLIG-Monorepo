"""Container readiness probe; dependency failures must fail the probe."""

import json
from urllib.request import urlopen


def main():
    try:
        with urlopen("http://127.0.0.1:8000/health/ready", timeout=5) as response:
            if response.status != 200 or json.load(response) != {"status": "ready"}:
                raise ValueError("Not ready")
    except Exception:
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
