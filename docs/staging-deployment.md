# Staging-Backend (Hetzner) – Bereitstellung und Status

Ziel: `https://staging-api.niknolig.com` → Caddy (Host) → `127.0.0.1:8001` → API-Container mit
eigener PostgreSQL-Datenbank. Produktion (`https://api.niknolig.com`, `/opt/nold/backend`) wird
nicht verändert.

## Bereitstellung

- `backend/compose.staging.yaml` definiert das isolierte Compose-Projekt `niknolig-staging` mit
  eigenem Netzwerk, Datenbank-Volume und Secrets. Migrationen 001 und 002 sind nur hier freigegeben;
  die API wird ausschließlich auf `127.0.0.1:8001` veröffentlicht.
- `backend/scripts/staging-deploy.sh` bietet `init-secrets`, `preflight`, `backup`, `deploy` und
  `verify`. Es läuft nur aus `/opt/nold/staging/backend`; `deploy` prüft die Konfiguration, sichert
  eine laufende Staging-Datenbank und führt danach Migration und Deployment aus.
- `backend/staging.env.example` enthält nicht geheime Konfigurationswerte. Auf dem Server als
  `staging.env` kopieren, Modus `600` setzen und die Werte des Supabase-Staging-Projekts eintragen.
  Staging-Secrets getrennt von Produktions-Secrets halten.

## Lokale Verifikation

- Backend-Tests: 267 OK (1 bereits zuvor übersprungen) mit einer kurzlebigen PostgreSQL-Datenbank.
- Staging-Stack gebaut; Migrationen 001/002 gegen eine frische Staging-Datenbank erfolgreich;
  `/health/ready` 200; geschützte Geräte-Routen ohne Token 401; unauthentifizierte Registrierung
  zurückgewiesen.
- Der Test mit nicht internem Netzwerk war nötig, weil die Sandbox DNS in `internal`-Netzen nicht
  bereitstellte; die Loopback-Portweiterleitung ließ sich dort nicht prüfen.

## Noch auf Hetzner auszuführen

1. `A staging-api.niknolig.com` auf `95.217.218.15` setzen.
2. Den Code nach `/opt/nold/staging/backend` bringen; `staging.env` aus der Vorlage erstellen und
   auf Modus `600` setzen. Nur das Supabase-Staging-Projekt konfigurieren.
3. `scripts/staging-deploy.sh init-secrets` und danach `scripts/staging-deploy.sh preflight`
   ausführen. Für den optionalen Abgleich dürfen `PRODUCTION_SECRETS_DIR` und
   `PRODUCTION_AUTH_ISSUER` gesetzt werden.
4. Port 443 gehört aktuell dem Produktions-Compose-Caddy. Keinen Site-Block in diesem
   Bridge-Container auf `host.docker.internal:8001` richten: Die API ist nur auf Host-Loopback
   veröffentlicht und aus dem Container nicht erreichbar. `Caddyfile.staging` funktioniert mit
   einem Host-Caddy, der `127.0.0.1:8001` erreicht, aber erst nach einer ausdrücklich freigegebenen
   Änderung der Produktions-Proxy-/Port-443-Architektur. Alternativ ist eine separat genehmigte,
   tatsächlich erreichbare Netzwerkroute erforderlich. Ohne eine davon keine öffentliche
   Staging-Route aktivieren.
5. `scripts/staging-deploy.sh deploy` ausführen und danach `scripts/staging-deploy.sh verify`.
6. Zwei Staging-Testkonten mit `app_metadata.app_area` (`tools/provision_app_area.py`) anlegen
   und die Variablen/Secrets für das GitHub-Environment `staging` einrichten.
7. Den Workflow [Device link staging integration](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/device-staging.yml)
   manuell starten; vor einer Freigabe muss er erfolgreich sein.

## Readiness und Status

`/health/ready` verwendet `backend_health` mit `HEALTH_DB_USER` und
`HEALTH_DB_PASSWORD_FILE` für eine schreibgeschützte Verbindung. Die API selbst verwendet
`backend_device_api`; beide Secrets werden durch `migrate.py` eingerichtet. Bei HTTP 503 zuerst
Migration 002 und beide Rollenzugangsdaten prüfen. Ein Rollback des Geräte-API-Schemas ist eine
separate, ausdrücklich freizugebende Datenbankänderung.

Der vorherige Lauf [43073868673](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/43073868673)
von `device-staging.yml` meldete `POST /v1/devices` → **HTTP 404**. Das zeigte, dass die damals
laufende Instanz die Geräte-API nicht bereitstellte. Repository-Änderungen aktualisieren den Server
nicht; ein erfolgreicher Test gegen die hier beschriebene Bereitstellung ist weiterhin offen.
`StagingIntegrationTest` wurde mangels Serverzugriff und Supabase-Staging-Zugangsdaten nicht gegen
Hetzner ausgeführt. Android-Builds laufen in CI. Keine Produktionsfreigabe; SecurityChain-P0 bleibt
BLOCKED.
