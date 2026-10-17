#!/usr/bin/env python3
"""Offline, bounded NOLD provenance and sandbox validation primitives."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

CORE_VERSION = "0.1.0"
MAX_FIXTURE_BYTES = 64_000
MAX_CASES = 100
MAX_LEDGER_ENTRIES = 1_000
MAX_CLAIM_CHARS = 2_000
MAX_SOURCES = 5
MAX_SOURCE_CHARS = 500
CASE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(?:password|token|secret|api[_-]?key)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
KINDS = {"fact", "assumption", "unknown"}


class CoreInputError(ValueError):
    """An input failed a bounded core validation rule."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class KnowledgeEntry:
    """A claim and its declared provenance; no claim is independently verified."""

    kind: str
    claim: str
    sources: tuple[str, ...]
    recorded_at: str
    confidence: float


def validate_entry(value: Any) -> KnowledgeEntry:
    """Validate a provenance record without asserting the claim is true."""
    if not isinstance(value, dict) or set(value) != {
        "kind",
        "claim",
        "sources",
        "recordedAt",
        "confidence",
    }:
        raise CoreInputError("invalid_record_shape")

    kind = value["kind"]
    if not isinstance(kind, str) or kind not in KINDS:
        raise CoreInputError("invalid_kind")

    claim = value["claim"]
    if not isinstance(claim, str) or not claim.strip() or len(claim) > MAX_CLAIM_CHARS:
        raise CoreInputError("invalid_claim")
    if any(pattern.search(claim) for pattern in SECRET_PATTERNS):
        raise CoreInputError("sensitive_text_rejected")

    sources = value["sources"]
    if (
        not isinstance(sources, list)
        or len(sources) > MAX_SOURCES
        or any(
            not isinstance(source, str)
            or not source.strip()
            or len(source) > MAX_SOURCE_CHARS
            or any(pattern.search(source) for pattern in SECRET_PATTERNS)
            for source in sources
        )
    ):
        raise CoreInputError("invalid_sources")

    recorded_at = value["recordedAt"]
    if not isinstance(recorded_at, str):
        raise CoreInputError("invalid_timestamp")
    try:
        parsed_timestamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise CoreInputError("invalid_timestamp") from error
    if parsed_timestamp.tzinfo is None:
        raise CoreInputError("invalid_timestamp")

    confidence = value["confidence"]
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        raise CoreInputError("invalid_confidence")
    if kind == "fact" and (not sources or confidence == 0):
        raise CoreInputError("fact_requires_source_and_confidence")
    if kind == "assumption" and confidence >= 1:
        raise CoreInputError("assumption_cannot_be_certain")
    if kind == "unknown" and (sources or confidence != 0):
        raise CoreInputError("unknown_must_not_claim_evidence")

    return KnowledgeEntry(
        kind=kind,
        claim=claim,
        sources=tuple(sources),
        recorded_at=parsed_timestamp.isoformat(),
        confidence=float(confidence),
    )


class KnowledgeLedger:
    """An in-memory append-only ledger; persistence and truth verification are external."""

    def __init__(self, capacity: int = MAX_LEDGER_ENTRIES):
        if type(capacity) is not int or not 1 <= capacity <= MAX_LEDGER_ENTRIES:
            raise CoreInputError("invalid_ledger_capacity")
        self._capacity = capacity
        self._entries: list[KnowledgeEntry] = []

    def append(self, value: Any) -> KnowledgeEntry:
        if len(self._entries) >= self._capacity:
            raise CoreInputError("ledger_capacity_reached")
        entry = validate_entry(value)
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> tuple[KnowledgeEntry, ...]:
        return tuple(self._entries)


def evaluate_fixture(fixture: Any) -> dict[str, Any]:
    """Run versioned provenance cases using validators only; no dynamic code execution."""
    if (
        not isinstance(fixture, dict)
        or set(fixture) != {"schemaVersion", "cases"}
        or type(fixture["schemaVersion"]) is not int
        or fixture["schemaVersion"] != 1
    ):
        raise CoreInputError("invalid_fixture")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise CoreInputError("invalid_case_count")

    results = []
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "record", "expectedValid"}:
            raise CoreInputError("invalid_case_shape")
        case_id = case["id"]
        if (
            not isinstance(case_id, str)
            or not CASE_ID_PATTERN.fullmatch(case_id)
            or case_id in seen_ids
        ):
            raise CoreInputError("invalid_case_id")
        seen_ids.add(case_id)
        if type(case["expectedValid"]) is not bool:
            raise CoreInputError("invalid_expected_result")

        try:
            validate_entry(case["record"])
            actual_valid = True
            error_code = None
        except CoreInputError as error:
            actual_valid = False
            error_code = error.code
        results.append(
            {
                "id": case_id,
                "passed": actual_valid is case["expectedValid"],
                "expectedValid": case["expectedValid"],
                "actualValid": actual_valid,
                "errorCode": error_code,
            }
        )

    return {
        "coreVersion": CORE_VERSION,
        "schemaVersion": 1,
        "networkAccess": False,
        "fixtureCodeExecuted": False,
        "passed": all(result["passed"] for result in results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures" / "nold-core-v1.json",
    )
    args = parser.parse_args(argv)
    try:
        fixture_path = args.fixture.resolve(strict=True)
        if fixture_path.stat().st_size > MAX_FIXTURE_BYTES:
            raise CoreInputError("fixture_too_large")
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        report = evaluate_fixture(fixture)
    except (OSError, UnicodeError, json.JSONDecodeError, CoreInputError) as error:
        code = error.code if isinstance(error, CoreInputError) else "fixture_unavailable_or_invalid"
        print(f"nold-core: {code}", file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
