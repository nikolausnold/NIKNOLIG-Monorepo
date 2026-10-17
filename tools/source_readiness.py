"""Offline assessment of declared source prerequisites; never enables access."""

import argparse
import json
import re
from pathlib import Path


DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "config/source-candidates.json"
CHECKS = (
    "access_and_license",
    "privacy_and_purpose",
    "provider_and_integrity",
    "api_and_hardware",
    "freshness_and_coverage",
    "quality_and_false_alarms",
    "securitychain_p0",
    "human_approval",
)
CATEGORIES = ("traffic", "camera", "airspace", "weather", "internet", "local_sensor")
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def assess_sources(data):
    if not isinstance(data, dict) or set(data) != {"version", "sources"}:
        raise ValueError("Expected version and sources only")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("Unsupported registry version")
    sources = data["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 20:
        raise ValueError("Expected between 1 and 20 source candidates")
    results, identifiers = [], set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"id", "category", "checks"}:
            raise ValueError("Expected source id, category and checks only")
        identifier = source["id"]
        if (not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier)
                or identifier in identifiers):
            raise ValueError("Invalid or duplicate source id")
        identifiers.add(identifier)
        if source["category"] not in CATEGORIES:
            raise ValueError("Unsupported source category")
        checks = source["checks"]
        if not isinstance(checks, dict) or set(checks) != set(CHECKS):
            raise ValueError("All prerequisite checks are required")
        if any(value not in ("pending", "documented") for value in checks.values()):
            raise ValueError("Checks must be pending or documented")
        blockers = [check for check in CHECKS if checks[check] != "documented"]
        results.append({
            "id": identifier,
            "category": source["category"],
            "status": "blocked" if blockers else "independent_review_required",
            "blockers": blockers,
            "access_enabled": False,
        })
    return {
        "version": 1,
        "mode": "offline_prerequisite_assessment",
        "evidence_verified": False,
        "release_authorized": False,
        "sources": results,
    }


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate registry key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)
    try:
        with args.registry.open("rb") as registry:
            content = registry.read(64_001)
        if len(content) > 64_000:
            raise ValueError("Registry exceeds size limit")
        report = assess_sources(json.loads(content, object_pairs_hook=_unique_keys))
    except (OSError, ValueError, RecursionError):
        print(json.dumps({
            "status": "invalid_input",
            "access_enabled": False,
            "release_authorized": False,
        }))
        return 2
    print(json.dumps(report, indent=2))
    return 1 if any(source["blockers"] for source in report["sources"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
