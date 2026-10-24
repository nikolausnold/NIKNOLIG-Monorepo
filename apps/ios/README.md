# Native iOS previews

`NIKNOLIG.xcodeproj` contains two independent native targets: `NIKNOLIG` and
`NIKNOLIG Defense`. They use the existing product identifiers
`com.niknolig.app` and `com.niknolig.defense`; neither target shares app data,
credentials, or runtime code with the other.

The apps implement local learning-profile preferences, a truthful local
assistant preview in NIKNOLIG, offline FAQs and typed escalation tickets through
the shared support core, separate user-triggered liveness and readiness checks, and
user-confirmed email handoff. The iOS code does not call the AI-support endpoint.
It adds no camera,
microphone, location, Bluetooth, or background permissions. Defense explicitly
states that emergency and infrastructure-detection features are unavailable;
it does not claim to dispatch assistance or transmit location.

The iOS 16.0 deployment target is a provisional technical baseline for
`NavigationStack`, not an approved support matrix or store decision. App Store
identifiers, account ownership, privacy declarations, signing team, release
approvals remain to be verified. Both targets now default to the operator-confirmed
`https://api.niknolig.com` for public health checks only. Override
`NIKNOLIG_BACKEND_URL` and `NIKNOLIG_DEFENSE_BACKEND_URL` independently at build
time if needed. An explicitly empty or invalid origin reports "not configured"
without opening a connection.

`GET /health/live` accepts only `{"status":"live"}`; `GET /health/ready` accepts
only `{"status":"ready"}`. A live process does not establish database readiness
or product availability. HTTP failures (including readiness `503`), timeouts,
network/TLS failures and invalid responses remain visible as distinct states.
The ephemeral sessions disable cookies, credential storage and caching, reject
redirects, limit responses to 4,096 bytes and keep the existing five-second
timeouts and system TLS validation. Neither check sends user data or enables
authentication, device binding or product data flows.

Open the project on macOS with Xcode and build each scheme separately. This
repository environment does not include macOS or Xcode, so no native iOS build,
simulator, device, signing, or TestFlight result is claimed. A successful build
would still not establish product or SecurityChain-P0 approval.

The support implementation is in
[`modules/support`](../../modules/support/README.md) and is compiled into both
native app targets. Its Swift package tests run with
`swift test --package-path modules/support/ios`.
