# Worker foundation

This project is a testable, fail-closed foundation for the two separate public
static-asset applications. It is not yet connected to either active Cloudflare
Worker and is not a production deployment configuration.

## Local checks

From this directory:

```sh
npm ci
npm test
npm run build
```

`npm run build` runs Wrangler dry-runs for `niknolig-preview` and
`niknolig-defense-preview`. It bundles the Worker only; it does not upload or
deploy anything.

## Security boundary

Only public `GET` and `HEAD` asset requests are supported. There are no account,
admin, write, or private-data routes, so this Worker foundation does not invent
an authentication protocol or accept credentials. App authorization is
fail-closed by the deployment's fixed `APP_AREA`; each application must receive
its own Cloudflare Static Assets binding. Requests outside the read-only method
allowlist are rejected. Responses receive restrictive browser security headers.
Logs contain only the app area, normalized method, status, event, and generated
request ID; URLs, query strings, headers, bodies, and exception text are omitted.

## Integration blockers

The repository does not contain confirmed production Worker source mappings or
Static Assets roots. The existing HTML/CSS/SVG files in the separate app
repositories are GitHub Pages sources, not verified Cloudflare Worker assets.
Before deployment, the owner must confirm, separately for each existing Worker:

- connected repository, production branch, and deployed commit;
- the exact Static Assets directory/root for that Worker;
- the preview deployment target and the already-configured, least-privilege
  preview credentials/permissions.

No production Worker name, route, asset directory, Cloudflare credential, or
preview deployment target is configured here. The GitHub Actions workflow runs
tests and dry-run builds only. A Cloudflare preview upload remains disabled
until an existing non-production target and credential binding are verifiable.
