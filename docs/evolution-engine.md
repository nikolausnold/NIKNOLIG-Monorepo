# Elektro-Engel Evolution Engine

**Status: local, deterministic proposal evaluator; no autonomous runtime agent.**

Run one bounded evaluation from the repository root:

```sh
python3 tools/evolution_engine.py
python3 tools/evolution_engine.py --format json --limit 10
python3 -m unittest discover -s tools/tests
```

The engine reads only its curated JSON backlog and the cited, size-limited
repository text excerpts. It validates evidence paths and exact cited line
excerpts, keeps `verified`, `hypothesis`, and `open` states distinct, calculates
a deterministic benefit/effort/risk/feasibility score, and derives the tier
instead of trusting a tier supplied by an idea author. Output includes goals,
success criteria, dependencies, side effects, lifecycle state, blockers,
evidence locations, and a next step. Likely credential-like text in reportable
fields is rejected, and cited source excerpts are validated but not emitted.

## Decision tiers

- **AUTO**: candidate is reversible, limited to documentation/tests, at most
  three files, effort at most 2/5 and risk at most 1/5, with no locked or
  infrastructure/dependency/data-retention risk. AUTO is eligibility for a
  bounded development task, not permission for this CLI to edit files.
- **VORSCHLAG**: needs review/planning before work, including CI or
  infrastructure changes, application behavior, dependencies, or higher risk.
- **GESPERRT**: touches authentication, authorization, keys, permissions,
  sensors, personal data, production/deployment, paid/external services,
  cross-repository changes, irreversible actions, or SecurityChain P0. The
  engine cannot override this classification.

Even AUTO may only be implemented within an explicitly approved task and normal
review/test boundaries. The repository's P0 rules remain immutable. No tier
authorizes changes to security policy, access control, permissions, signing,
production, budget, user data, or the separate app repositories.

## Boundedness and limitations

Each invocation is exactly one cycle with no background schedule, agent loop,
retry loop, build, test subprocess, network request, service access, file write,
deployment, or secret read. At most 20 ideas are accepted; a caller can display
at most 20. The backlog and each cited source have size limits; citations are
restricted to repository text paths and exact line excerpts. Secret-like text
in reportable fields is rejected and evidence excerpts are not echoed. The CLI
does not scan the entire repository or generate ideas using an LLM. The initial
backlog is a small, evidence-cited human-curated set, not a claim of autonomous
discovery. No Hetzner endpoint, budget, or paid service is used.

The optional `jsonschema` test dependency is not required by this evaluator.
Current automated checks validate backlog structure and cited evidence and run
the separate contract tests. The engine reports candidate plans only; actual
code changes still require an authorized coding workflow, tests, review, and
approval appropriate to the risk.

## Initial backlog

`evolution/ideas.json` records:

1. an AUTO-candidate documentation-only accessibility checklist (a hypothesis,
   not a claim of existing accessibility defects);
2. a CI test invocation proposal;
3. cross-device session transfer, GESPERRT pending P0 and identity/transport
   decisions; and
4. sensor runtime support, GESPERRT pending permissions, device proof, privacy
   policy, and real hardware testing.

No app modules or manifest permissions are changed by this tool. NIKNOLIG and
NIKNOLIG Defense remain distinct. Each future app integration needs a separate
scoped plan and review in its own repository; no shareable session, device
action, sensor access, or production endpoint is enabled here.
