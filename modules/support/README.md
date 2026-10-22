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
The app won't reopen a handed-off ticket because doing so could create a
duplicate; the user's mail app owns draft storage, delivery retries, and its
outbox. The user must confirm the email was sent before removing the ticket from
the local queue.

## Operational limits and manual steps

- The backend AI support routes remain local-preparation-only and disabled.
  There is no production authentication issuer, approved provider, or deployed
  support API.
- Unresolved tickets are queued only on the device that created them. No server
  operator receives them until the user reviews and sends the email.
- If a mail app cannot be opened, the ticket remains queued; after three failed
  launch attempts, the app gives the recipient and ticket ID for manual email.
- A delivery failure after the mail app has opened must be retried from that
  mail app. The app cannot observe SMTP/mail-provider delivery results.
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
