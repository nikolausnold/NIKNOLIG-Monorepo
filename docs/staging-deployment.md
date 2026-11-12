# Staging-Deployment der Geräte-API (Hetzner)

## Befund

Lauf [43073868673](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/43073868673) von
`device-staging.yml` (nach Einrichtung von TLS) scheiterte mit
`POST /v1/devices` → **HTTP 404**. Davor (Lauf 43054157534) lieferte der Server einen TLS-Alert
`internal_error`. TLS ist jetzt in Ordnung. Der 404 bedeutet: Auf `staging-api.niknolig.com` läuft ein
Backend **ohne aktive Geräte-API**. Der Code (`backend/device_api.py`, Migration `002_device_api.sql`,
Android-Client) liegt bereits im Repository; die Routen werden nur gemountet, wenn
`DEVICE_API_ENABLED=1` und alle Secrets gültig sind (fail closed). `/health/live` und `/db/health`
antworten auch ohne Geräte-API mit 200 und beweisen sie daher nicht.

Repository-Änderungen aktualisieren den Server nicht. Die folgenden Schritte müssen auf dem Server
ausgeführt werden. Sie wurden von dieser Änderung **nicht** ausgeführt.

## Voraussetzungen

- Docker + Compose-Plugin; Host-PostgreSQL erreichbar für Container (`listen_addresses` und
  `pg_hba.conf` für die Docker-Bridge, z. B. `172.17.0.0/16`) mit Datenbank `nold_staging`.
- Passwortdateien (Modus `0400`, nicht im Repository) für: Migrationsrolle, `backend_health`,
  `backend_device_api`, sowie ein zufälliges Token-Secret (`openssl rand -base64 48`).
  Die Rollen `backend_health` und `backend_device_api` legt `migrate.py` an bzw. setzt deren Passwort.
- Supabase-Werte (öffentlich): `AUTH_ISSUER=https://<projekt>.supabase.co/auth/v1`,
  `AUTH_JWKS_URL=<issuer>/.well-known/jwks.json`, `AUTH_AUDIENCE=authenticated`.
- Zwei Testkonten mit `app_metadata.app_area` = `niknolig` bzw. `niknolig-defense`
  (`tools/provision_app_area.py`).

## Ablauf

```bash
git pull && cd backend
# 1. Backup (Pflicht vor Migration 002)
pg_dump -Fc nold_staging > ~/nold_staging-$(date +%F).dump
# 2. Konfiguration (Pfade/Werte anpassen)
export STAGING_MIGRATOR_USER=... POSTGRES_PASSWORD_SECRET_FILE=/etc/niknolig/staging/migrator.pw \
  HEALTH_PASSWORD_SECRET_FILE=/etc/niknolig/staging/health.pw \
  DEVICE_API_PASSWORD_SECRET_FILE=/etc/niknolig/staging/device_api.pw \
  DEVICE_TOKEN_SECRET_HOST_FILE=/etc/niknolig/staging/token.secret \
  AUTH_ISSUER=... AUTH_JWKS_URL=...
# 3. Migrationen 000–002 (bewusste, manuelle Freigabe durch den Betreiber)
docker compose -f compose.staging.yaml build
docker compose -f compose.staging.yaml run --rm migrate
# 4. API starten (nur 127.0.0.1:8001)
docker compose -f compose.staging.yaml up -d api
```

Der bestehende TLS-Reverse-Proxy muss `/v1/devices*`, `/v1/sessions*`, `/v1/pairings*`, `/v1/links*`,
`/v1/grants/*`, `/v1/status`, `/v1/events` sowie `/health/*` an `127.0.0.1:8001` weiterleiten
(Pfadliste wie in `backend/Caddyfile`). Wird ein Wildcard-`proxy_pass` auf Port 8001 verwendet, ist
nichts weiter nötig.

## Readiness-Verbindungen

`/health/ready` nutzt eine eigene, nur lesende Verbindung (`default_transaction_read_only=on`) als
`backend_health` (`HEALTH_DB_USER` + `HEALTH_DB_PASSWORD_FILE`); die Rollenprüfung verlangt genau diese
Rolle. Die API selbst nutzt weiter `backend_device_api`, und `device_store.ping` prüft zusätzlich diese
Rolle samt Schema. Fehlt eine der beiden Variablen oder das Secret, antwortet `/health/ready` mit 503
(fail closed). Schlägt `/health/ready` mit 503 fehl, zuerst prüfen: Passwort von `backend_health`
stimmt mit `health.pw` überein (Migration setzt es), Migration 002 wurde angewendet, Rolle
`backend_device_api` hat das Passwort aus `device_api.pw`. Der Container auf Port 8000 bleibt unberührt.

## Verifikation

```bash
curl -fsS https://staging-api.niknolig.com/health/ready
# Ohne Token muss 401 kommen, nicht 404:
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://staging-api.niknolig.com/v1/devices
```

Danach den Workflow
[Device link staging integration](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/device-staging.yml)
manuell starten. Er muss grün sein und darf nicht übersprungen werden.

## Rollback

Siehe `docs/device-connection-api-release.md`, Abschnitt 4: `DEVICE_API_ENABLED=0` (Routen entfallen,
Daten bleiben) oder Wiederherstellung des `pg_dump`.

## Status

Staging-Test: **nicht grün** (Stand Lauf 43073868673, 404). Hardware-Abnahme mit zwei Geräten und
SecurityChain-P0-Freigabe bleiben offen.
