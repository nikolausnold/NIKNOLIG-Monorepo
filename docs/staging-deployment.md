# Staging-Backend (Hetzner) – Bereitstellung und Status

Ziel: `https://staging-api.niknolig.com` → Caddy (Host) → `127.0.0.1:8001` → API-Container mit eigener
PostgreSQL-Datenbank. Produktion (`https://api.niknolig.com`, `/opt/nold/backend`) wird nicht verändert.

## Im Repository (neu)
- `backend/compose.staging.yaml`: eigenes Compose-Projekt `niknolig-staging` (eigenes Netz, Volume, Datenbank
  `niknolig_staging`, eigene Secrets aus `STAGING_SECRETS_DIR`), Migration 001+002 nur hier freigegeben,
  Geräte-API aktiv, Port nur `127.0.0.1:8001`. DB-Host/Port/Name/Benutzer sind konfigurierbar
  (`PGHOST`, `PGPORT`, `PGDATABASE`, `STAGING_DB_NAME`).
- `backend/Caddyfile.staging`: HTTPS (automatisches ACME) für `staging-api.niknolig.com`, gleiche Pfad-Allowlist wie Produktion.
- `backend/scripts/staging-deploy.sh`: `init-secrets | preflight | backup | deploy | verify`. Läuft nur aus
  `/opt/nold/staging/backend`, verlangt Modus 600, verwirft doppelte/produktive Secrets, erstellt vor jedem Deploy ein `pg_dump`.
- `backend/staging.env.example`: Vorlage ohne Zugangsdaten (`staging.env` ist git-ignoriert).
- Fix: `.dockerignore` schloss `device_*.py` aus dem Build-Kontext aus (Image war so nicht baubar).

## Verifiziert (lokal, Wegwerf-Umgebung)
- Backend-Tests: 267 OK (1 übersprungen, bereits vorher) mit disposable PostgreSQL.
- Staging-Stack gebaut; Migration 001/002 gegen frische Staging-DB erfolgreich; `/health/ready` 200;
  `/v1/devices/me` und `/v1/links` ohne Token 401; unauthentifizierte Registrierung 400.
  (Test mit nicht-internem Netz, da die Sandbox kein DNS in `internal`-Netzen bot; die veröffentlichte Loopback-Port-Weiterleitung war in der Sandbox nicht prüfbar.)

## NICHT verifiziert
- `StagingIntegrationTest` gegen `staging-api.niknolig.com`: **nicht ausgeführt** (kein Serverzugriff, keine Supabase-Staging-Zugangsdaten). Kein Skip wird als Bestanden gewertet.
- Android-Builds/-Tests: keine lokale SDK; laufen in der CI (`android-build.yml`).
- Keine Produktionsfreigabe; SecurityChain-P0 bleibt BLOCKED.

## Auf Hetzner (95.217.218.15) noch auszuführen
1. DNS: `A staging-api.niknolig.com → 95.217.218.15`.
2. Code nach `/opt/nold/staging/backend` bringen; `cp staging.env.example staging.env; chmod 600 staging.env`; Supabase-**Staging**-Projekt (nicht Produktion) eintragen.
3. `scripts/staging-deploy.sh init-secrets && scripts/staging-deploy.sh preflight` (optional `PRODUCTION_SECRETS_DIR`, `PRODUCTION_AUTH_ISSUER` setzen für Abgleich).
4. Port 443 gehört in Produktion dem Compose-Caddy. Entweder `Caddyfile.staging` in einen Host-Caddy auf 443 übernehmen (Produktion dann hinter diesen Caddy – Änderung am Live-Betrieb, bewusst freigeben) oder einen Site-Block im bestehenden Caddy ergänzen, der `host.docker.internal:8001` proxyt. Nicht automatisiert, um Produktion nicht zu unterbrechen.
5. `scripts/staging-deploy.sh deploy`, dann `scripts/staging-deploy.sh verify`.
6. Zwei Staging-Testkonten mit `app_metadata.app_area` (`tools/provision_app_area.py`) anlegen; im GitHub-Environment `staging` setzen: Variablen `NIKNOLIG_STAGING_URL=https://staging-api.niknolig.com`, `NIKNOLIG_STAGING_AUTH_URL`; Secrets `NIKNOLIG_STAGING_AUTH_KEY`, `…_APP_EMAIL|PASSWORD`, `…_DEFENSE_EMAIL|PASSWORD`.
7. Workflow „Device link staging integration“ manuell starten: https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/device-staging.yml – erst bei Erfolg weiter.
