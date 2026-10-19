"""Read-only repository inventory; no checkouts, builds, or source mutations.

Run: python -m tools.system_updates [--registry PATH] [--output PATH]
GITHUB_TOKEN optionally authenticates GET requests only to api.github.com.
External changed means SHA inequality, not ancestry or update safety. The local
GITHUB_SHA is the build reference (possibly a PR merge); its remote default
branch head is informational and is deliberately never compared with that SHA.
Pending entries (including iOS) are explicit onboarding gaps, not checked repos.
Optional related_to IDs document repository relationships, not runtime links.
Exit 0 means all configured repos were observed, not that all platforms are set
up or builds passed. Exit 1 means an observation failed; 2 means invalid input
or an unwritable report. Reports are still emitted on observation/input failure.
"""

import argparse
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "config/system-repositories.json"
SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
REPOSITORY = re.compile(r"nikolausnold/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


class InventoryError(ValueError):
    pass


def validate_registry(data):
    if not isinstance(data, dict) or set(data) != {"version", "repositories"}:
        raise InventoryError("Registry must contain version and repositories only")
    if type(data["version"]) is not int or data["version"] != 1:
        raise InventoryError("Unsupported registry version")
    entries = data["repositories"]
    if not isinstance(entries, list) or not entries:
        raise InventoryError("Repositories must be a nonempty list")
    ids, repositories = set(), set()
    local_count = 0
    for entry in entries:
        required = {"id", "kind", "repository", "baseline"}
        if (not isinstance(entry, dict) or not required <= set(entry)
                or set(entry) - required - {"related_to"}):
            raise InventoryError("Each entry requires id, kind, repository, baseline; only related_to is optional")
        identifier, kind = entry["id"], entry["kind"]
        repository, baseline = entry["repository"], entry["baseline"]
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in ids:
            raise InventoryError("Invalid or duplicate repository id")
        ids.add(identifier)
        if kind not in ("local", "external", "pending"):
            raise InventoryError("Unsupported repository kind")
        if kind == "pending":
            if repository is not None or baseline is not None:
                raise InventoryError("Pending entries must not name a repository or baseline")
            continue
        if (not isinstance(repository, str) or not REPOSITORY.fullmatch(repository)
                or repository.split("/")[1] in (".", "..")):
            raise InventoryError("Repository must be a safe nikolausnold/owner-repository path")
        if repository.lower() in repositories:
            raise InventoryError("Duplicate repository path")
        repositories.add(repository.lower())
        if kind == "local":
            local_count += 1
            if repository != "nikolausnold/NIKNOLIG-Monorepo" or baseline is not None:
                raise InventoryError("Local entry must be the monorepo with no baseline")
        elif not isinstance(baseline, str) or not SHA.fullmatch(baseline):
            raise InventoryError("External repositories require a full SHA baseline")
    if local_count != 1:
        raise InventoryError("Exactly one local monorepo entry is required")
    by_id = {entry["id"]: entry for entry in entries}
    for entry in entries:
        if "related_to" not in entry:
            continue
        target = entry["related_to"]
        if (entry["kind"] != "external" or not isinstance(target, str)
                or target == entry["id"] or target not in by_id
                or by_id[target]["kind"] != "external"):
            raise InventoryError("related_to must reference another registered external repository")
    return entries


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubReader:
    def __init__(self, token=None):
        self.token = token
        # Do not route bearer credentials through environment-configured proxies.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def get(self, path):
        if not path.startswith("/repos/") or "?" in path or "#" in path:
            raise InventoryError("Invalid GitHub API path")
        request = urllib.request.Request(
            "https://api.github.com" + path,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "NIKNOLIG-read-only-inventory",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": "Bearer " + self.token} if self.token else {}),
            },
            method="GET",
        )
        try:
            with self.opener.open(request, timeout=20) as response:
                payload = response.read(1_000_001)
            if len(payload) > 1_000_000:
                raise InventoryError("GitHub response exceeded size limit")
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise InventoryError("GitHub response must be an object")
            return result
        except urllib.error.HTTPError as exc:
            # Never echo exception URLs, response bodies, headers, or credentials.
            raise InventoryError(f"GitHub HTTP {exc.code}; repository not checked") from None
        except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError):
            raise InventoryError("GitHub response unavailable or invalid; repository not checked") from None

    def head(self, repository):
        # Defense in depth: even callers outside the registry cannot supply URLs.
        if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
            raise InventoryError("Unsafe repository path")
        metadata = self.get("/repos/" + repository)
        branch = metadata.get("default_branch")
        if (not isinstance(branch, str) or not branch or len(branch) > 255
                or any(ord(char) < 32 or ord(char) == 127 for char in branch)):
            raise InventoryError("Missing or invalid default branch; repository not checked")
        commit = self.get("/repos/" + repository + "/commits/" + urllib.parse.quote(branch, safe=""))
        sha = commit.get("sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise InventoryError("Missing or invalid head SHA; repository not checked")
        return branch, sha.lower()


def build_report(entries, reader, local_sha=None):
    if local_sha is not None and (not isinstance(local_sha, str) or not SHA.fullmatch(local_sha)):
        raise InventoryError("GITHUB_SHA must be a full commit SHA when provided")
    report = {
        "version": 1,
        "mode": "read_only_inventory",
        "semantics": {
            "changed": "External default-branch SHA differs from baseline; inventory only, no update adopted or build claim.",
            "local": "GITHUB_SHA is the local build reference; remote default head is informational, never compared.",
            "pending": "Not configured or checked; not a successful platform check.",
            "builds": "No builds, dispatches, installations, deployments, or external writes performed.",
        },
        "all_configured_repositories_checked": True,
        "pending_configuration": [],
        "repositories": [],
    }
    for entry in entries:
        result = dict(entry, observed_sha=None, default_branch=None, changed=None)
        if entry["kind"] == "pending":
            result.update(status="not_configured", reason="Repository onboarding pending")
            report["pending_configuration"].append(entry["id"])
        else:
            if entry["kind"] == "local":
                result["local_build_sha"] = local_sha.lower() if local_sha else None
                result["local_reference_status"] = "provided" if local_sha else "not_available"
            try:
                branch, sha = reader.head(entry["repository"])
                result.update(status="checked", default_branch=branch, observed_sha=sha)
                if entry["kind"] == "external":
                    result["changed"] = sha != entry["baseline"].lower()
            except InventoryError as exc:
                result.update(status="not_checked", reason=str(exc))
                report["all_configured_repositories_checked"] = False
        report["repositories"].append(result)
    return report


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError("Duplicate JSON key in registry")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, help="Write JSON here instead of stdout")
    args = parser.parse_args(argv)
    try:
        try:
            data = json.loads(args.registry.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
        except (OSError, ValueError):
            raise InventoryError("Registry cannot be read or is invalid JSON") from None
        entries = validate_registry(data)
        report = build_report(entries, GitHubReader(os.environ.get("GITHUB_TOKEN")),
                              os.environ.get("GITHUB_SHA"))
        exit_code = 0 if report["all_configured_repositories_checked"] else 1
    except InventoryError as exc:
        report = {"version": 1, "mode": "read_only_inventory", "status": "invalid_input",
                  "all_configured_repositories_checked": False, "error": str(exc), "repositories": []}
        exit_code = 2
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError:
            print(rendered, end="")
            return 2
    else:
        print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
