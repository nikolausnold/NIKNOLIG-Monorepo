# Native iOS previews

`NIKNOLIG.xcodeproj` contains two independent native targets: `NIKNOLIG` and
`NIKNOLIG Defense`. They use the existing product identifiers
`com.niknolig.app` and `com.niknolig.defense`; neither target shares app data,
credentials, or runtime code with the other.

The apps implement local learning-profile preferences, a truthful local
assistant preview in NIKNOLIG, offline FAQs and typed escalation tickets through
the shared support core, the existing health-only readiness check, and
user-confirmed email handoff. The iOS code does not call the AI-support endpoint.
It adds no camera,
microphone, location, Bluetooth, or background permissions. Defense explicitly
states that emergency and infrastructure-detection features are unavailable;
it does not claim to dispatch assistance or transmit location.

The iOS 16.0 deployment target is a provisional technical baseline for
`NavigationStack`, not an approved support matrix or store decision. App Store
identifiers, account ownership, privacy declarations, signing team, release
approvals remain to be verified. Both targets default to the operator-specified
existing API origin `https://api.niknolig.com`, with separate per-app overrides.
The website origins remain `https://niknolig.com/` and
`https://defense.niknolig.com/`; they are not backend addresses. A configured
origin does not establish live connectivity, login or protected product access.

Open the project on macOS with Xcode and build each target separately. No shared
schemes are committed; CI uses explicit `-target` builds. The Linux editing
environment cannot run Xcode. The `iOS app builds` workflow compiles both targets
in Debug and Release for the simulator without signing, using separate example
origins. A configured CI job is not a successful build result: inspect its actual
run before claiming compilation. Neither simulator compilation nor core tests
establish signed device archives, TestFlight, product or SecurityChain-P0 approval.

The support implementation is in
[`modules/support`](../../modules/support/README.md) and is compiled into both
native app targets. Its Swift package tests run with
`swift test --package-path modules/support/ios`.

## Backend configuration gate

Both targets run `tools/validate_ios_backend.py` before compilation (Python 3
must be available on the Xcode host). The product bundle identifier selects
exactly one setting:

| Target | Build setting | Generated Info.plist key |
| --- | --- | --- |
| NIKNOLIG | `NIKNOLIG_BACKEND_URL` | `BackendBaseURL` |
| NIKNOLIG Defense | `NIKNOLIG_DEFENSE_BACKEND_URL` | `BackendBaseURL` |

The default origin is set independently in Debug and Release for each target.
An explicitly empty override is still permitted only in Debug; its health
client reports not configured.
Release and other configurations require the target's own nonempty HTTPS origin.
Nonempty Debug values undergo the same syntax checks. Credentials, paths beyond
`/`, queries, fragments, invalid ports, placeholder and loopback hosts fail the
build without printing the supplied URL. Validation never performs DNS or HTTP
requests and does not certify operator approval or production availability.
No fallback from one app's setting to the other is allowed. Two apps may use the
same origin only if the operator explicitly approves it for each app.

The simulator CI's explicit `*.example.com` overrides are isolated compilation fixtures,
never approved production settings. For actual device archives, the Apple
release operator must supply separately approved origins, an authorized signing
team, existing certificates/profiles and approved distribution/export settings.
This repository does not create or retrieve those credentials.
