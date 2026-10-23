# Shared app support

## What is running

`core/` and `ios/` provide the same local, deterministic support behavior to the
NIKNOLIG and NIKNOLIG Defense Android and iOS apps. They answer a small set of
common questions and map backend health failures to stable diagnostic codes.
They are not generative AI services, do not diagnose user devices beyond the
existing health check, and do not send requests to a network service.

Both apps preserve their separate package identities, local storage, and
authorizations. Unresolved question text is encrypted before it is stored:
Android uses an AES-GCM key in Android Keystore, and iOS uses AES-GCM with a
device-only key in Keychain. Queue records also contain a random ticket ID, app,
fixed issue/diagnostic codes, creation time, attempt count, and handoff state.
Only ciphertext is stored in app-private preferences; Android backup is disabled
for both apps. The queue is capped at 20 tickets, and launching an email draft
can be retried at most three times after an explicit launch failure.

The existing email path is a user-confirmed `mailto:` draft. The public NIKNOLIG
website also uses a `mailto:n_nold@hotmail.com` link in its contact section:
[`NIKNOLIG/index.html`](https://github.com/nikolausnold/NIKNOLIG/blob/main/index.html)
and
[`NIKNOLIG-Defense-Website-/index.html`](https://github.com/nikolausnold/NIKNOLIG-Defense-Website-/blob/main/index.html).
No website server-side mail sender, SMTP configuration, or automatic email
delivery path was found. Both mobile platforms reuse their existing
user-confirmed `mailto:` flow. A successful handoff is not proof of delivery.
Drafts include only the random ticket ID, app identity, and allowlisted fixed
issue/diagnostic codes. Question text, ciphertext, request keys, learning profiles,
and conversation content are never included. Stored payloads are not decrypted
for email; encryption is only for local recovery.
The app won't reopen a handed-off ticket because doing so could create a
duplicate; the user's mail app owns draft storage, delivery retries, and its
outbox. The user can mark a handed-off ticket sent to complete it locally, or
explicitly delete a local ticket in any state (including uncertain or
retry-exhausted).
Deletion removes only that app's selected local record and encrypted payload;
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
Defense request. This is not a production integration: the production ASGI
runtime does not register AI routes, the default local service rejects requests
as `AI_DISABLED`, and no authenticated mobile client is enabled. Defense does
not gain the separate NIKNOLIG-local Elektro-Engel runtime.

## Operational limits and manual steps

- The backend AI support routes remain local-preparation-only and disabled.
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
after deletion. Flow checks ensure drafts never use question text or decrypted
payloads and that deletion controls remain available.
