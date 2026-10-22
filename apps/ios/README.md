# Native iOS previews

`NIKNOLIG.xcodeproj` contains two independent native targets: `NIKNOLIG` and
`NIKNOLIG Defense`. They use the existing product identifiers
`com.niknolig.app` and `com.niknolig.defense`; neither target shares app data,
credentials, or runtime code with the other.

The apps implement only flows already present in the Android previews: local
learning-profile preferences, a truthful local assistant preview in NIKNOLIG,
the existing health-only readiness check, and user-confirmed email handoff.
The iOS code does not call the AI-support endpoint. It adds no camera,
microphone, location, Bluetooth, or background permissions. Defense explicitly
states that emergency and infrastructure-detection features are unavailable;
it does not claim to dispatch assistance or transmit location.

The iOS 16.0 deployment target is a provisional technical baseline for
`NavigationStack`, not an approved support matrix or store decision. App Store
identifiers, account ownership, privacy declarations, signing team, release
approvals, and an approved production backend URL remain to be verified. The
backend URL build settings default to empty and must not be replaced with an
unapproved endpoint.

Open the project on macOS with Xcode and build each scheme separately. This
repository environment does not include macOS or Xcode, so no native iOS build,
simulator, device, signing, or TestFlight result is claimed. A successful build
would still not establish product or SecurityChain-P0 approval.
