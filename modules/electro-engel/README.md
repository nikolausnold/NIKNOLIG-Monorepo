# Elektro-Engel Wirklichkeits-Dekoder

This directory contains a deterministic, offline analysis module. It is not a
generative AI system and does not verify facts. Its rules make their limits and
source status explicit; they are intended to help users formulate questions,
not to diagnose people or prescribe a worldview.

## Contracts and boundaries

`AnalysisRequest` / `ElectroEngelRequest` contains a mode, text (maximum 1,000
characters and 2,048 UTF-8 bytes), and optional refinement (maximum 500
characters). The four modes return named sections, an uncertainty notice, an
explicit unchecked-source status, and an empty source list. Empty, oversized,
and control-character input fails closed. Inputs are not logged, persisted, or
sent over a network.

The rule cues and curated glosses currently support German text. The Kotlin/JVM
core lives in `core/` and has no Android, app, network, or provider dependency.
NIKNOLIG Android consumes it as `:electro-engel-core`;
NIKNOLIG Defense does not. The iOS implementation is a Foundation-only Swift
package in `ios/`, compiled into the NIKNOLIG target. Its small rule set mirrors
the Kotlin behavior; there is no common generated implementation, so parity is
maintained by behavioral tests and review.

| Mode | Output |
| --- | --- |
| Word breakdown | Working gloss for five curated German terms or an explicit unknown-term notice; history is never inferred; culture and personal meaning are separated. |
| Convention scan | Zero or more language-cue categories: empirical, definitional, social convention, normative, and personal, with rationale and an explicit heuristic limitation. |
| Perspective shift | Historical, cultural, and philosophical questions, shared/different lenses, and a counter-question; no specific group or period is attributed an unsupported view. |
| Fact/thinking check | Heuristic sentence labels for potentially checkable claims, opinions, hypotheses, and conclusions; flags absolutist wording and possible contradictions without declaring truth. |

The keyword and contradiction detectors are intentionally conservative but
incomplete. A match is only a prompt for human review; a missing match is not
proof that a statement is sound. The curated glosses are working descriptions,
not source-backed dictionary entries. No external source lookup currently
exists, and the UI never claims one was performed.

## AI integration status

The existing `backend/ai_support.py` and `/v1/ai/support` contract are a separate,
fail-closed support-reply preparation path. They are not an analysis API, have
no production identity/provider transport, and default to disabled. This module
does not call them. The remote-adapter interfaces represent a future boundary
only; the shipped availability state is `AI_DISABLED`. No provider, endpoint,
credential, or paid service is configured. An approved analysis-specific
contract, identity and consent flow, provider review, source policy, costs and
privacy/security approvals are prerequisites before any remote integration.

Timeout and provider failures map to generic typed errors. They must never be
interpreted as an analysis, and raw error text is not shown to users.

## Build and tests

```sh
./gradlew :electro-engel-core:test
swift test --package-path modules/electro-engel/ios
```

The native iOS application itself still requires macOS/Xcode for a full build.
The module uses Kotlin/JVM 17 and Swift Foundation only. It can be extracted
later with its API contract and tests; app navigation and UI remain in their
respective app projects.
