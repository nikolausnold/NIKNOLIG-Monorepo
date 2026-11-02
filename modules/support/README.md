# Shared app support

## What is running

`core/` and `ios/` provide the same local, deterministic support behavior to the
NIKNOLIG and NIKNOLIG Defense Android and iOS apps. They answer a small set of
common questions and map backend health failures to stable diagnostic codes.
They are not generative AI services, do not diagnose user devices beyond the
existing health check, and do not send requests to a network service.

Both apps preserve their separate package identities, local storage, and
authorizations. New unresolved tickets do not store or transmit the entered
question text: all four support surfaces (both Android activities and both iOS
views) encrypt only an empty string as the ticket's payload placeholder
(enforced by `test_support_queues_do_not_persist_free_text`). The placeholder is
AES-GCM ciphertext (Android Keystore key on Android, device-only Keychain key on
iOS), but it protects no content. What remains locally per unresolved question
is plaintext queue metadata: random ticket ID, app, request key (a random UUID,
not derived from the text), fixed issue/diagnostic codes, creation time, attempt
count, and handoff state. No backend ticket store exists, and the backend health
check receives no question text.

### Legacy ticket cleanup and backups

On the first opening of Support after this update, both Android apps and both
iOS apps inspect stored ticket payloads. A payload that decrypts to non-empty
text, or cannot be decrypted, is replaced with a newly encrypted empty string.
The migration retains the ticket ID, app, request key, issue/diagnostic codes,
creation time, attempts, and handoff state. If replacement or persistence
fails, the queue is not exposed for use; the original persisted record is not
intentionally discarded. Tickets whose payload already decrypts to an empty
string are left unchanged. No question text is sent to the backend or included
in an email draft.

Android tickets remain in app-private `SharedPreferences`. Both manifests set
`android:allowBackup="false"`. Android documents that on some manufacturers
device-to-device transfer may still occur despite this setting; no physical
device-transfer test was available ([Android backup documentation](https://developer.android.com/identity/data/autobackup)).
Restored legacy payloads are subject to the same first-open migration.

iOS tickets are stored in a dedicated file under the app's Application Support
directory, with the directory and file marked excluded from backup and file
protection set to `completeUntilFirstUserAuthentication`. On first access, the
store migrates the former `UserDefaults` value into this file, then removes the
legacy preference. The migration is exercised by package tests, but iCloud
backup/restore could not be exercised on this Linux runner. Backups made before
the update may still contain legacy encrypted payloads; the app cannot revoke or
edit historical backups. If such a backup restores the old preference, opening
Support migrates its payload before the ticket can be used.
The prior implementation had no backup exclusion for this preference. Apple's
[standard app-data backup](https://developer.apple.com/documentation/foundation/optimizing-your-app-s-data-for-icloud-backup)
includes Library data; the current exclusion uses
[`isExcludedFromBackupKey`](https://developer.apple.com/documentation/foundation/urlresourcekey/isexcludedfrombackupkey)
on the dedicated support directory and file. The payload key is
`AfterFirstUnlockThisDeviceOnly`; a restored legacy payload whose key is not
available is replaced with an empty encrypted payload rather than retained.

The queue is capped at 20 tickets, and launching an email draft can be retried
at most three times after an explicit launch failure.

The existing email path is a user-confirmed `mailto:` draft. The public NIKNOLIG
website also uses a `mailto:n_nold@hotmail.com` link in its contact section:
[`NIKNOLIG/index.html`](https://github.com/nikolausnold/NIKNOLIG/blob/main/index.html)
and
[`-NIKNOLIG-Defense-Website/index.html`](https://github.com/nikolausnold/-NIKNOLIG-Defense-Website/blob/main/index.html).
No website server-side mail sender, SMTP configuration, or automatic email
delivery path was found. Both mobile platforms reuse their existing
user-confirmed `mailto:` flow. A successful handoff is not proof of delivery.
Drafts include only the random ticket ID, app identity, and allowlisted fixed
issue/diagnostic codes. Question text, ciphertext, request keys, learning profiles,
and conversation content are never included. Stored payloads are not decrypted
for email.
The app won't reopen a handed-off ticket because doing so could create a
duplicate; the user's mail app owns draft storage, delivery retries, and its
outbox. The user can mark a handed-off ticket sent to complete it locally, or
explicitly delete a local ticket in any state (including uncertain or
retry-exhausted).
Deletion removes only that app's selected local record (metadata and placeholder);
it does not delete or recall drafts or sent mail in an external email app.

## Backend contract diagnosis and AI status

Both backend readiness implementations expose `GET /health/ready` with the
successful response `200 application/json` and exactly `{"status":"ready"}`.
Both Android clients request that route over HTTPS and validate that response.
The legacy `GET /health` route instead returns status `ok` plus service/version
metadata, and is not the readiness contract. A successful response
with a different content type or body is correctly rejected; accepting it would
weaken validation. No backend origin is configured by default in either app, and
no deployed origin or captured response was available here, so the reported
`InvalidResponse` could not be reproduced against a live endpoint. If it appears
with a configured deployment, verify that the origin routes `/health/ready` to
this backend rather than a legacy health endpoint or unrelated proxy response.

The shared AI-support preparation endpoint can scope `support` and
`electro-engel` requests independently to either app. The app claim must match
the authenticated principal and permission; a NIKNOLIG credential cannot make a
Defense request. This is not an activated production integration: the production ASGI
runtime and Caddy expose the same fail-closed support routes; the default service rejects requests
as `AI_DISABLED`, and no authenticated mobile client is enabled. Defense does
not gain the separate NIKNOLIG-local Elektro-Engel runtime.

## Operational limits and manual steps

- The backend AI support routes remain disabled by default, including in ASGI.
  There is no production authentication issuer, approved provider, or deployed
  support API.
- The health contract is implemented and covered by server/client tests, but a
  configured deployment's response cannot be verified without its origin and
  response evidence.
- Unresolved tickets are queued only on the device that created them. No server
  operator receives them until the user reviews and sends the email.
- If a mail app cannot be opened, the ticket remains queued; after three failed
  launch attempts, the app gives the recipient and ticket ID for manual email.
- A delivery failure after the mail app has opened must be retried from that
  mail app. The app cannot observe SMTP/mail-provider delivery results.
- The websites have contact `mailto:` links but no reusable server-side sender,
  SMTP configuration, or delivery API. Automatic mail is therefore unavailable;
  only the existing user-confirmed mobile draft is safe to reuse.
- Before release, operators must verify that the user-facing inbox is monitored
  and complete an on-device draft test using synthetic content. No test email
  was sent as part of this implementation.

## Tests

```sh
./gradlew :support-core:test
swift test --package-path modules/support/ios
python3 -m unittest tools.tests.test_support_flow
```

The core tests cover FAQ responses, unresolved questions, backend diagnostics,
per-app queue scoping, idempotent ticket creation, failed handoff retention,
bounded retries, and duplicate-prevention after a successful handoff.
They also cover metadata allowlisting and app-scoped deletion in every handoff
state, including exhausted retries, persistence failures, and late callbacks
after deletion. Migration tests assert that legacy payloads are replaced without
dropping metadata, that failed migrations leave the stored record available, and
that iOS moves the old `UserDefaults` value into its file store. Flow checks
ensure drafts never use question text or decrypted payloads and that deletion
controls remain available.
