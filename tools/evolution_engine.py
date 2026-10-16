#!/usr/bin/env python3
"""Bounded, offline prioritization for reviewed repository improvement ideas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKLOG = REPOSITORY_ROOT / "evolution" / "ideas.json"
MAX_CYCLE_ITEMS = 20
MAX_BACKLOG_BYTES = 256_000
MAX_EVIDENCE_BYTES = 256_000
MAX_EVIDENCE_PER_IDEA = 5
ALLOWED_EVIDENCE_SUFFIXES = {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".kt",
    ".kts",
    ".py",
    ".sql",
}
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".gradle",
    ".idea",
    ".env",
    "secrets",
    "keystore",
}
LOCKED_FLAGS = {
    "authentication",
    "authorization",
    "security_policy",
    "securitychain_p0",
    "permissions",
    "sensor_access",
    "personal_data",
    "production_deployment",
    "paid_service",
    "external_service",
    "destructive",
    "irreversible",
    "credentials",
    "key_management",
    "cross_repository",
}
KNOWN_FLAGS = LOCKED_FLAGS | {
    "ci_pipeline",
    "infrastructure",
    "new_dependency",
    "data_retention",
    "performance",
    "accessibility",
    "documentation",
    "test_coverage",
}
KNOWN_SCOPES = {
    "documentation",
    "tests",
    "application",
    "backend",
    "ci",
    "infrastructure",
    "operations",
}
KNOWN_EVIDENCE_STATES = {"verified", "hypothesis", "open"}
SCORE_FIELDS = ("impact", "effort", "risk", "feasibility")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(?:password|token|secret|api[_-]?key)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class BacklogError(ValueError):
    """Raised when a backlog is invalid or contains unverifiable evidence."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BacklogError(message)


def _require_safe_text(value: Any, description: str) -> None:
    _require(isinstance(value, str) and value.strip(), f"{description} is required")
    _require(
        not any(pattern.search(value) for pattern in SENSITIVE_TEXT_PATTERNS),
        f"{description} contains secret-like text and will not be reported",
    )


def _safe_evidence_excerpt(root: Path, evidence: dict[str, Any], idea_id: str) -> None:
    path_text = evidence.get("path")
    _require(isinstance(path_text, str) and path_text, f"{idea_id}: evidence path required")
    relative = Path(path_text)
    _require(not relative.is_absolute(), f"{idea_id}: absolute evidence path is forbidden")
    _require(
        not any(part.lower() in FORBIDDEN_PATH_PARTS for part in relative.parts),
        f"{idea_id}: evidence path is outside the readable source allowlist",
    )
    _require(
        relative.suffix.lower() in ALLOWED_EVIDENCE_SUFFIXES,
        f"{idea_id}: unsupported evidence file type",
    )
    source = (root / relative).resolve()
    _require(source.is_relative_to(root.resolve()), f"{idea_id}: evidence path escapes repository")
    _require(source.is_file(), f"{idea_id}: evidence file does not exist: {path_text}")
    _require(source.stat().st_size <= MAX_EVIDENCE_BYTES, f"{idea_id}: evidence file is too large")

    start = evidence.get("startLine")
    end = evidence.get("endLine")
    _require(type(start) is int and type(end) is int, f"{idea_id}: evidence line numbers must be integers")
    _require(start >= 1 and end >= start and end - start <= 20, f"{idea_id}: invalid evidence line range")
    excerpt = evidence.get("excerpt")
    _require(isinstance(excerpt, str) and excerpt.strip(), f"{idea_id}: evidence excerpt required")
    lines = source.read_text(encoding="utf-8").splitlines()
    _require(end <= len(lines), f"{idea_id}: evidence range exceeds file: {path_text}")
    cited_text = "\n".join(lines[start - 1 : end])
    _require(excerpt in cited_text, f"{idea_id}: excerpt does not match cited lines in {path_text}")
    state = evidence.get("state")
    _require(
        isinstance(state, str) and state in KNOWN_EVIDENCE_STATES,
        f"{idea_id}: evidence state must be verified, hypothesis, or open",
    )


def validate_backlog(data: Any, root: Path = REPOSITORY_ROOT) -> list[dict[str, Any]]:
    _require(isinstance(data, dict), "backlog must be a JSON object")
    _require(data.get("schemaVersion") == 1, "schemaVersion must equal 1")
    ideas = data.get("ideas")
    _require(isinstance(ideas, list), "ideas must be a list")
    _require(len(ideas) <= MAX_CYCLE_ITEMS, f"backlog exceeds the {MAX_CYCLE_ITEMS}-idea cycle limit")

    seen_ids: set[str] = set()
    for idea in ideas:
        _require(isinstance(idea, dict), "each idea must be an object")
        idea_id = idea.get("id")
        _require(isinstance(idea_id, str) and ID_PATTERN.fullmatch(idea_id), "idea id must be kebab-case")
        _require(idea_id not in seen_ids, f"duplicate idea id: {idea_id}")
        seen_ids.add(idea_id)

        for field in ("title", "goal", "rationale"):
            _require_safe_text(idea.get(field), f"{idea_id}: {field}")
            _require(len(idea[field]) <= 2_000, f"{idea_id}: {field} exceeds 2000 characters")
        criteria = idea.get("successCriteria")
        _require(
            isinstance(criteria, list)
            and len(criteria) <= 10
            and criteria
            and all(isinstance(item, str) and item.strip() for item in criteria),
            f"{idea_id}: non-empty successCriteria required",
        )
        for criterion in criteria:
            _require_safe_text(criterion, f"{idea_id}: success criterion")
            _require(len(criterion) <= 2_000, f"{idea_id}: success criterion exceeds 2000 characters")

        scores = idea.get("score")
        _require(isinstance(scores, dict), f"{idea_id}: score object required")
        for field in SCORE_FIELDS:
            value = scores.get(field)
            _require(type(value) is int and 1 <= value <= 5, f"{idea_id}: {field} must be an integer from 1 to 5")

        scope = idea.get("scope")
        _require(isinstance(scope, str) and scope in KNOWN_SCOPES, f"{idea_id}: unknown scope")
        reversible = idea.get("reversible")
        _require(type(reversible) is bool, f"{idea_id}: reversible must be boolean")
        file_count = idea.get("estimatedFiles")
        _require(type(file_count) is int and 1 <= file_count <= 20, f"{idea_id}: estimatedFiles must be 1..20")

        flags = idea.get("riskFlags")
        _require(isinstance(flags, list), f"{idea_id}: riskFlags must be a list")
        _require(all(isinstance(flag, str) for flag in flags), f"{idea_id}: risk flags must be strings")
        _require(all(flag in KNOWN_FLAGS for flag in flags), f"{idea_id}: unknown risk flag")
        _require(len(flags) == len(set(flags)), f"{idea_id}: duplicate risk flag")

        dependencies = idea.get("dependencies", [])
        _require(
            isinstance(dependencies, list)
            and len(dependencies) <= 10
            and all(isinstance(value, str) and value.strip() for value in dependencies),
            f"{idea_id}: dependencies must be a list of non-empty strings",
        )
        for dependency in dependencies:
            _require_safe_text(dependency, f"{idea_id}: dependency")
            _require(len(dependency) <= 2_000, f"{idea_id}: dependency exceeds 2000 characters")
        side_effects = idea.get("sideEffects")
        _require(
            isinstance(side_effects, list)
            and len(side_effects) <= 10
            and all(isinstance(value, str) and value.strip() for value in side_effects),
            f"{idea_id}: sideEffects must be a list of non-empty strings",
        )
        for side_effect in side_effects:
            _require_safe_text(side_effect, f"{idea_id}: side effect")
            _require(len(side_effect) <= 2_000, f"{idea_id}: side effect exceeds 2000 characters")
        lifecycle = idea.get("lifecycle")
        _require(isinstance(lifecycle, dict), f"{idea_id}: lifecycle record required")
        for field in ("status", "decision", "outcome"):
            _require(isinstance(lifecycle.get(field), str), f"{idea_id}: lifecycle {field} must be a string")
        _require(
            lifecycle.get("status") in {"proposed", "deferred", "implemented", "rejected"},
            f"{idea_id}: invalid lifecycle status",
        )
        _require(
            lifecycle.get("decision") in {"pending", "approved", "declined"},
            f"{idea_id}: invalid lifecycle decision",
        )
        _require(
            lifecycle.get("outcome") in {"not_run", "passed", "failed", "not_applicable"},
            f"{idea_id}: invalid lifecycle outcome",
        )
        evidence = idea.get("evidence")
        _require(
            isinstance(evidence, list)
            and 1 <= len(evidence) <= MAX_EVIDENCE_PER_IDEA,
            f"{idea_id}: expected 1..{MAX_EVIDENCE_PER_IDEA} evidence citations",
        )
        for citation in evidence:
            _require(isinstance(citation, dict), f"{idea_id}: evidence entries must be objects")
            _safe_evidence_excerpt(root, citation, idea_id)

    return ideas


def priority_score(scores: dict[str, int]) -> int:
    """Higher impact/feasibility and lower effort/risk yield higher priority."""
    return (
        scores["impact"] * 3
        + scores["feasibility"] * 2
        - scores["effort"] * 2
        - scores["risk"] * 3
    )


def classify(idea: dict[str, Any]) -> tuple[str, list[str]]:
    """Derive a governance tier; backlog authors cannot set their own tier."""
    flags = set(idea["riskFlags"])
    blockers = sorted(flags & LOCKED_FLAGS)
    if not idea["reversible"]:
        blockers.append("irreversible")
    if blockers:
        return "GESPERRT", sorted(set(blockers))

    auto_eligible = (
        idea["scope"] in {"documentation", "tests"}
        and idea["score"]["risk"] <= 1
        and idea["score"]["effort"] <= 2
        and idea["reversible"]
        and idea["estimatedFiles"] <= 3
        and not flags.intersection({"ci_pipeline", "infrastructure", "new_dependency", "data_retention"})
    )
    if auto_eligible:
        return "AUTO", []
    return "VORSCHLAG", []


def evidence_confidence(idea: dict[str, Any]) -> str:
    states = {entry["state"] for entry in idea["evidence"]}
    if "open" in states:
        return "offen"
    if "hypothesis" in states:
        return "Hypothese"
    return "belegt"


def build_report(ideas: list[dict[str, Any]], limit: int = MAX_CYCLE_ITEMS) -> dict[str, Any]:
    _require(type(limit) is int and 1 <= limit <= MAX_CYCLE_ITEMS, f"limit must be 1..{MAX_CYCLE_ITEMS}")
    ranked = []
    for idea in ideas:
        tier, blockers = classify(idea)
        ranked.append(
            {
                "id": idea["id"],
                "title": idea["title"],
                "goal": idea["goal"],
                "rationale": idea["rationale"],
                "successCriteria": idea["successCriteria"],
                "score": priority_score(idea["score"]),
                "dimensions": idea["score"],
                "tier": tier,
                "blockers": blockers,
                "evidenceConfidence": evidence_confidence(idea),
                "dependencies": idea.get("dependencies", []),
                "sideEffects": idea["sideEffects"],
                "lifecycle": idea["lifecycle"],
                "evidence": [
                    {
                        "path": citation["path"],
                        "startLine": citation["startLine"],
                        "endLine": citation["endLine"],
                        "state": citation["state"],
                    }
                    for citation in idea["evidence"]
                ],
                "nextStep": (
                    "Nur innerhalb der begrenzten, freigegebenen Dokumentations-/Testgrenzen umsetzen und erneut prüfen."
                    if tier == "AUTO"
                    else "Plan zur menschlichen Prüfung vorlegen; keine Änderung durch diesen Lauf."
                    if tier == "VORSCHLAG"
                    else "Nicht umsetzen; erforderliche Sicherheits-/Produktfreigabe zuerst dokumentieren."
                ),
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["id"]))
    selected = ranked[:limit]
    return {
        "engineVersion": "1.0",
        "cycle": {
            "runs": 1,
            "maxIdeas": MAX_CYCLE_ITEMS,
            "selected": len(selected),
            "repeatAutomatically": False,
        },
        "execution": {
            "repositoryWrites": False,
            "commandsRun": False,
            "networkAccess": False,
            "deployments": False,
            "secretsRead": False,
            "appOrSensorRuntimeChanged": False,
        },
        "ideas": selected,
    }


def _render_text(report: dict[str, Any]) -> str:
    lines = [
        "Elektro-Engel Evolution Engine (offline, one-shot)",
        f"Cycle: {report['cycle']['selected']} selected; automatic repeat disabled.",
        "No repository writes, commands, network calls, deployments, or secret reads.",
    ]
    for index, idea in enumerate(report["ideas"], start=1):
        lines.extend(
            [
                "",
                f"{index}. [{idea['tier']}] {idea['title']} — score {idea['score']} ({idea['evidenceConfidence']})",
                f"   Goal: {idea['goal']}",
                f"   Why: {idea['rationale']}",
                f"   Success: {'; '.join(idea['successCriteria'])}",
            ]
        )
        if idea["blockers"]:
            lines.append(f"   Blockers: {', '.join(idea['blockers'])}")
        if idea["dependencies"]:
            lines.append(f"   Dependencies: {'; '.join(idea['dependencies'])}")
        if idea["sideEffects"]:
            lines.append(f"   Side effects: {'; '.join(idea['sideEffects'])}")
        lines.append(
            f"   Lifecycle: {idea['lifecycle']['status']}/{idea['lifecycle']['decision']}/"
            f"{idea['lifecycle']['outcome']}"
        )
        lines.append(f"   Next: {idea['nextStep']}")
        for evidence in idea["evidence"]:
            lines.append(
                f"   Evidence: {evidence['path']}:{evidence['startLine']}-{evidence['endLine']} "
                f"({evidence['state']})"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--limit", type=int, default=MAX_CYCLE_ITEMS)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        backlog_path = args.backlog.resolve()
        _require(
            backlog_path.is_relative_to(REPOSITORY_ROOT.resolve()),
            "backlog must be inside the repository",
        )
        _require(backlog_path.stat().st_size <= MAX_BACKLOG_BYTES, "backlog exceeds the size limit")
        data = json.loads(backlog_path.read_text(encoding="utf-8"))
        ideas = validate_backlog(data)
        report = build_report(ideas, args.limit)
    except (OSError, UnicodeError, json.JSONDecodeError, BacklogError) as error:
        print(f"evolution-engine: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
