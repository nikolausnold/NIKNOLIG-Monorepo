# Geräteverbindungs-API – Umsetzungsstand und Release-Gates

**Sicherheitsfreigabe P0: BLOCKED** (siehe Abschnitt 6). Es wird keine
SecurityChain-P0-Konformität behauptet.

## 1. Tatsächlich implementiert (Backend)

Neu in `backend/`: `device_security.py` (Kryptografie, Tokens, Rate-Limiter),
`device_store.py` (PostgreSQL-Zustandsübergänge), `device_api.py` (FastAPI-Routen),
`migrations/002_device_api.sql`, `tests/test_device_api.py`.

| Bereich | Endpunkte |
| --- | --- |
| Geräteidentität | `POST /v1/devices` (Supabase-JWT + Ed25519-Besitznachweis), `DELETE /v1/devices/{id}` (Eigentümer-JWT oder Gerät selbst), `GET /v1/devices/me` |
| Sitzungen | `POST /v1/devices/{id}/challenge`, `POST /v1/devices/{id}/session`, `POST /v1/sessions/refresh`, `GET /v1/sessions`, `DELETE /v1/sessions/current` |
| Pairing | `POST /v1/pairings`, `POST /v1/pairings/claim`, `GET /v1/pairings/{id}`, `POST /v1/pairings/{id}/confirm`, `POST /v1/pairings/{id}/cancel` |
| Verbindungen | `GET /v1/links`, `DELETE /v1/links/{id}` |
| Freigaben | `POST/GET /v1/links/{id}/grants`, `DELETE /v1/grants/{id}` (Scopes: `status:read`, `events:read`, `alerts:send`) |
| Status/Ereignisse | `PUT /v1/status`, `GET /v1/links/{id}/peer/status`, `POST/GET /v1/events`, `GET /v1/links/{id}/peer/events` |

Sicherheitsmechanismen: gerätegebundene HMAC-Access-Tokens (300 s) mit
Serverprüfung der Live-Session (sofortiger Widerruf); rotierende Refresh-Tokens
(nur SHA-256-Hash gespeichert; jeder bereits verbrauchte Hash bleibt erhalten, jede Wiederverwendung widerruft die Session);
einmalige, 60 s gültige Challenges (Replay-Schutz); 8-stelliger Einmalcode
(HMAC-gehasht, 120 s, einmal einlösbar) plus 6-stelliger Abgleichscode und
**gegenseitige Bestätigung** beider Geräte; Link nur zwischen NIKNOLIG und
Defense (bestehende DB-Regel); Freigaben gerichtet, Scope-begrenzt, höchstens
7 Tage, Widerruf mit Link; Rate-Limits (Claim-Fehlversuche, Challenge/Session,
Registrierung, Schreib-/Lesezugriffe); Body-Limit 8 KiB, strikte Schemas,
generische Fehler ohne Eingabe-Echo; Audit-Ereignisse ohne Schlüssel, Tokens
oder Codes; eigene DB-Rolle `backend_device_api`: Audit-Ereignisse und Refresh-
Historie nur SELECT/INSERT, kein DDL, vorhandene privilegierte Rollen werden
abgelehnt; Body muss innerhalb von 10 s eintreffen (sonst 408); abgelaufene
Challenges werden begrenzt bereinigt.

Rückwärtskompatibilität: Migrationen 000/001 unverändert; 002 ist additiv und
nur mit `--approve-device-api-schema` bzw. `APPROVE_DEVICE_API_SCHEMA=1`
anwendbar, setzt 001 voraus. Ohne `DEVICE_API_ENABLED=1` und vollständige Secrets
(`DEVICE_TOKEN_SECRET_FILE`, `DEVICE_API_DB_PASSWORD_FILE`, `AUTH_*`) existieren
die Routen nicht (404, fail closed). Elektro Engel nutzt unverändert
`/v1/ai/support`.

Rate-Limits sind prozesslokal (ein API-Container); bei Skalierung auf mehrere
Instanzen ist ein gemeinsamer Zähler nötig.

## 2. Tests (lokal, PostgreSQL 16)

- `python3 -m unittest discover -s backend/tests`: 250 Tests, OK (1 bestehender Skip).
- `python3 -m unittest discover -s tools/tests`: 93 Tests, OK.
- Neue Tests (39) decken Registrierung/Besitznachweis, Replay, Refresh-Rotation und
  -Wiederverwendung, Pairing inkl. Ablauf/Fremdzugriff/Rate-Limit, Freigaben,
  Widerruf von Link/Gerät/Sitzung, Validierung und DB-Rollenrechte ab.
- Alle Tests laufen gegen die API mit Test-Principal-Verifier und simulierten
  Schlüsseln in-process. **Das ist kein Nachweis für echte Geräteverbindung.**

## 3. Nicht umgesetzt (ehrlich)

Android-Client (neu): `:device-link-core` enthält Protokoll, JSON-Codec,
HTTPS-Transport (nur HTTPS, keine Redirects, Timeouts, Größenlimit) und
`DeviceLinkService` (Registrierung, Challenge-Session, Refresh mit Rotation und
Fallback auf neue Challenge, Pairing, Verbindungen, Freigaben, Widerruf, Status).
Beide Apps haben eine `DeviceLinkActivity` (Button auf dem Startbildschirm) mit
Ed25519-Schlüssel im Android Keystore (nur Android 13+/API 33), Keystore-
verschlüsselten Sitzungstoken, Konto-Anmeldung (Supabase-Passwort-Login; Passwort und
JWT werden nicht gespeichert), Einmalcode-Pairing mit gegenseitigem Abgleichscode,
Freigabe/Widerruf, Gerätewiderruf und verständlichen Fehlermeldungen.
NIKNOLIG Defense meldet nach Aktualisierung den lokalen Diagnosestatus (3 Prüfungen);
NIKNOLIG ruft ihn nur mit Freigabe ab.

**Das Gate bleibt standardmäßig geschlossen.** Ohne Build-Eigenschaft
`-PdeviceLinkP0Approved=true` (oder `NIKNOLIG_DEVICE_LINK_P0_APPROVED=true`) zeigt die
Oberfläche nur den Sperrhinweis. Konto-Login benötigt zusätzlich
`-PniknoligAccountAuthUrl`/`-PniknoligAccountAuthKey` (bzw.
`-PniknoligDefenseAccountAuthUrl`/`-PniknoligDefenseAccountAuthKey`; Umgebungsvariablen
`NIKNOLIG_ACCOUNT_AUTH_URL|KEY`, `NIKNOLIG_DEFENSE_ACCOUNT_AUTH_URL|KEY`), und das
Konto-JWT muss den Claim `app_metadata.app_area` tragen.
JVM-Tests des Moduls (inkl. Refresh-/Fallback-/Widerrufspfade) laufen in CI.

**Offen:** Kopplung per QR-Code (kein Scanner/Generator ohne neue Abhängigkeit), Geräteerkennung
im lokalen Netz (NSD/BLE), Geräte unter Android 12 und älter (kein Keystore-Ed25519),
Test mit zwei echten Android-Geräten inkl. Verifikation von Keystore-Ed25519 auf
echter Hardware, Staging-Smoke-Test.

- **iOS-Client / Smart-TV:** keine Pairing-Oberfläche, kein iOS-Keychain-Schlüssel;
  kein QR-Scan und keine lokale Geräteerkennung (NSD/BLE) auf Android. Elektro-Engel-Chat
  nutzt das bestehende Backend.
- Android-/iOS-Builds, Installation und Integrationstest wurden in dieser
  Umgebung nicht ausgeführt (kein Android-SDK/macOS-Runner); sie laufen über die
  bestehenden Workflows.
- Zwei Geräte derselben App (z. B. zwei NIKNOLIG-Smartphones) sind durch die
  bestehende DB-Regel `device_links_distinct_app_areas` ausgeschlossen; Änderung
  erfordert eine eigene Migration und Freigabe.
- Lizenzregeln (0,75 €, 5 Tage, 48 h) wurden nicht verändert.

## 4. Backend-Deployment

Nicht ausgeführt. Ablauf: Secrets bereitstellen → **vollständiges Datenbank-Backup
(`pg_dump`)** → `APPROVE_DEVICE_API_SCHEMA=1` migrieren → Staging-Smoke-Test
(Registrierung, Pairing, Widerruf) → `DEVICE_API_ENABLED=1`.

**Rollback:** Ein reiner Image-Rollback auf eine Version vor diesem PR ist nach
Migration 002 *nicht* möglich: deren Migrations- und Readiness-Prüfung lehnt den
Ledger-Eintrag `002_device_api` ab, und 002 erweitert eine Tabelle aus 001.
Zulässig sind (a) ein Rollback auf ein Image, das 002 kennt, mit
`DEVICE_API_ENABLED=0` (Routen verschwinden, Daten bleiben), oder (b) die separat
freigegebene Wiederherstellung des Backups vor der Migration. Tabellen allein zu
löschen genügt nicht.

Caddy leitet `/v1/devices|sessions|pairings|links|grants|status|events` weiter.
Fehlerhafte oder unvollständige Konfiguration (leeres DB-Secret usw.) lässt die
Routen fehlen; `/health/ready` prüft bei aktivierter API zusätzlich den
Device-Store.

## 5. Android-/iOS-Release

Keine neuen Artefakte, keine Store-Veröffentlichung. Bestehende Signierung und
Auto-Merge-Konfiguration sind unverändert.

## 6. Sicherheitsfreigabe: BLOCKED

Gründe: SecurityChain-P0-Spezifikation ist weiterhin nicht schriftlich
freigegeben; kein unabhängiger Review; Clients ohne Keystore/Keychain und TLS-
Pinning-/Transportnachweis; keine physische Zwei-Geräte-Abnahme; kein
Staging-Smoke-Test.

## 7. Erforderliche externe Schritte

1. Schriftliche P0-/Datenfluss-Freigabe (siehe `device-link-security-design.md`).
2. Unabhängiger Security-Review des Protokolls.
3. Client-Umsetzung (Keystore/Keychain, Pairing-UI, Discovery) und Builds.
4. Test mit zwei echten Smartphones und Smart-TV-Hardware.
5. Staging-Deployment mit echten Secrets, danach Produktivfreigabe.
