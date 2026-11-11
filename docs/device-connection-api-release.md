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
| Status/Ereignisse | `PUT /v1/status` (nur mit mindestens einer aktiven ausgehenden `status:read`-Freigabe; sonst `403`), `GET /v1/links/{id}/peer/status` (erfordert die entsprechende Freigabe des Peers), `POST/GET /v1/events`, `GET /v1/links/{id}/peer/events` |

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

## 2. Automatisierte Tests

- Der lokale Lauf `python -m unittest discover -s backend/tests` führte 261 Tests aus;
  59 wurden übersprungen, darunter die PostgreSQL-Integrationstests, da in dieser Umgebung
  kein PostgreSQL-Testdienst verfügbar war. Diese lokalen Ergebnisse belegen daher keine
  PostgreSQL-Integration.
- Der aktuelle GitHub-Actions-Lauf mit PostgreSQL-Service führte den Backend- und
  Tooling-Regressionsschritt erfolgreich aus; Commit und Run-ID stehen in Abschnitt 8.
- Die Tests decken Registrierung/Besitznachweis, Replay, Refresh-Rotation und
  -Wiederverwendung, Pairing inkl. Ablauf/Fremdzugriff/Rate-Limit, Freigaben,
  Widerruf von Link/Gerät/Sitzung, Validierung und DB-Rollenrechte ab.
- Automatisierte API-Tests verwenden Test-Principal-Verifier und simulierte
  Schlüssel. **Das ist kein Nachweis für echte Geräteverbindung.**

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

**Neu in diesem Stand (Code, durch CI gebaut; nicht auf echten Geräten getestet):**

- **QR-Kopplung:** Das Gerät mit offenem Pairing zeigt den Einmalcode zusätzlich als QR
  (`niknolig-pair://pair?v=1&area=…&code=…`, ZXing-Encoder); das andere Gerät scannt mit dem
  Google-Play-Dienste-Codescanner (keine Kamera-Berechtigung). Der Parser (`PairingQr`) akzeptiert nur
  wohlgeformte Payloads der *anderen* App; ohne Play-Dienste bleibt die manuelle Codeeingabe.
- **Geräteerkennung (Android NSD):** Während ein Pairing offen ist, kündigt das Gerät `_niknolig-pair._tcp`
  mit App-Bereich und Gerätename an; die andere App zeigt solche Geräte als Hinweis. Der Code wird nie
  gesendet, Erkennung begründet kein Vertrauen – Kopplung erfordert weiterhin Code/QR und die gegenseitige
  Bestätigung des Abgleichscodes auf beiden Geräten (serverseitig erzwungen).
- **Geräteschlüssel:** Der Android-Client verwendet ausschließlich nicht exportierbare Ed25519-Schlüssel im
  Android Keystore (Android 13+). Geräte ohne unterstützte Keystore-Ed25519-Implementierung und bestehende
  Installationen mit einem früheren Software-Schlüssel bleiben gesperrt; es gibt keinen Software-Fallback.
  RFC-8032-Software-Signer wird nur noch in JVM-Tests verwendet und ist nicht Teil des App-Artefakts.
- **Konto und `app_area`:** Vor der Registrierung prüft der Client den `app_metadata.app_area`-Claim und das
  Ablaufdatum und zeigt verständliche Fehler (fehlt / anderer Bereich / abgelaufen). Autorität bleibt das
  Backend. Gesetzt wird der Claim nur serverseitig: `tools/provision_app_area.py` (Operator-Werkzeug mit
  Service-Role-Key, Dry-Run standardmäßig).
- **Staging-Integrationstest:** `StagingIntegrationTest` führt den echten Client-Code (HTTPS, Ed25519,
  Pairing, Freigabe, Statusabruf, Widerruf) gegen ein Staging-Backend aus. Workflow
  `device-staging.yml` (nur manuell, Environment `staging`) benötigt Variablen/Secrets
  `NIKNOLIG_STAGING_URL`, `NIKNOLIG_STAGING_AUTH_URL`, `NIKNOLIG_STAGING_AUTH_KEY` und zwei Testkonten
  (`…_APP_EMAIL|PASSWORD`, `…_DEFENSE_EMAIL|PASSWORD`, `app_area` je gesetzt). Ohne Konfiguration
  wird der Test übersprungen bzw. der Workflow schlägt fehl – ein Skip gilt nie als bestanden.
  **Für diese Nacharbeit nicht ausgeführt**; siehe Validierungsstand in Abschnitt 8.
- Anzeigen von Code/QR sind mit `FLAG_SECURE` gegen Screenshots geschützt.

**Offen:** Test mit zwei echten Android-Geräten (inkl. Keystore-Ed25519 auf realer Hardware und
negativer Prüfung, dass nicht unterstützte Android-Versionen ohne Keystore-Ed25519 fail-closed bleiben),
NSD-Verhalten in echten WLANs (Client-Isolation, VPN), Ausführung des Staging-Tests,
Bereitstellung der Konto-Konfiguration, SecurityChain-P0-Freigabe.

- **iOS-Client / Smart-TV:** keine Pairing-Oberfläche, kein iOS-Keychain-Schlüssel;
  keine BLE-Erkennung. Elektro-Engel-Chat nutzt das bestehende Backend.
- Android-Debug-Builds, Android-Unit-Tests und Android-Lint laufen über den bestehenden Workflow (siehe
  Abschnitt 8). CI ersetzt weder die Installation auf echten Geräten noch den Staging-Integrationstest.
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
3. Unabhängige Prüfung und Abnahme der vorhandenen Client-Umsetzung.
4. Test mit zwei echten Android-Geräten und Smart-TV-Hardware, soweit vorgesehen.
5. Staging-Deployment mit echten Secrets, danach Produktivfreigabe.

## Zwei-Geräte-Hardwaretest (NICHT durchgeführt)

Status: **offen**. Kein Test mit zwei realen Android-Geräten wurde ausgeführt; `DEVICE_LINK_P0_APPROVED`
bleibt bis zur schriftlichen SecurityChain-P0-Freigabe geschlossen. Ergebnisse unten erst nach
tatsächlicher Durchführung eintragen (Datum, Gerät, Android-Version, Build-SHA).

**Voraussetzungen:** Staging-Backend (HTTPS, Gerät-API aktiv), zwei Testkonten mit gesetztem `app_area`
(`tools/provision_app_area.py`), Debug-Builds beider Apps mit
`-PdeviceLinkP0Approved=true -PniknoligBackendUrl=… -PniknoligAccountAuthUrl|Key=…` (nur Testbuilds, nicht
veröffentlichen), Gerät A mit NIKNOLIG und Gerät B mit NIKNOLIG Defense, beide im selben WLAN. Beide Geräte
müssen Android 13+ und eine funktionsfähige Ed25519-Implementierung im Android Keystore unterstützen;
ältere Geräte werden ohne Software-Fallback abgewiesen.

| # | Schritt | Erwartung | Ergebnis |
|---|---------|-----------|----------|
| 1 | Beide Apps öffnen → Geräteverbindung | Anmeldeformular, Hinweis auf nicht exportierbaren Keystore-Schlüssel | offen |
| 2 | Mit falschem Konto (anderer `app_area`) anmelden | Verständliche Fehlermeldung, keine Registrierung | offen |
| 3 | Mit richtigem Konto anmelden und registrieren | „Gerät registriert“ | offen |
| 4 | A: Kopplungscode erzeugen | Code + QR sichtbar; Screenshot wird blockiert | offen |
| 5 | B: Hinweis „Gerät in der Nähe“ (NSD) erscheint | Nur Name/Bereich, kein Code | offen |
| 6 | B: QR scannen (alternativ Code tippen) | Abgleichscode auf beiden Geräten identisch (6 Ziffern) | offen |
| 7 | Nur auf einem Gerät bestätigen, anschließend mehr als 300 s warten | Pairing läuft ab, keine Verbindung (120 s gelten nur für unbeanspruchte Angebote) | offen |
| 8 | Neues Pairing, Abgleichscode absichtlich ablehnen | Beide Seiten „abgebrochen“ | offen |
| 9 | Neues Pairing, auf A die App verlassen | Pairing serverseitig abgebrochen | offen |
| 10 | Neues Pairing, beide bestätigen | Verbindung aktiv, Peer-Name + Schlüsselabdruck | offen |
| 11 | Verbindungsabbruch: WLAN/Daten auf B aus, 1 min, wieder an | Offline-Meldung, danach Wiederverbindung ohne neue Kopplung | offen |
| 12 | Defense: Status freigeben (24 h); NIKNOLIG ruft Status ab | Lokaler Diagnosestatus sichtbar | offen |
| 13 | Freigabe widerrufen; NIKNOLIG ruft Status ab | Abruf wird mit „Berechtigung fehlt“ abgelehnt; Defense lädt nichts mehr hoch | offen |
| 14 | Verbindung trennen | Beide Seiten ohne aktive Verbindung | offen |
| 15 | Erneut koppeln (Wiederverbinden) | Neue Verbindung funktioniert | offen |
| 16 | Gerät widerrufen | Serverseitig entfernt, lokal Schlüssel/Sitzung gelöscht, neue Registrierung nötig | offen |
| 17 | Zwei NIKNOLIG- oder zwei Defense-Geräte koppeln | Abgelehnt (Bereichsregel) | offen |
| 18 | `StagingIntegrationTest` über Workflow `device-staging.yml` | Grün, nicht übersprungen | offen |

Freigabekriterium: alle Zeilen bestanden, keine sicherheitskritische Abweichung, schriftliche
P0-Freigabe – erst danach `DEVICE_LINK_P0_APPROVED` in Release-Builds aktivieren.

## 8. Validierungsstand (2026-11-11)

- **Android-CI:** [Workflow-Lauf 43041221763](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/43041221763),
  Code-Commit `6e6780257fecd522ca5a3f0da93a48e7f1a15ad8`: beide Debug-APKs gebaut, Android-Unit-Tests und
  Lint für beide Apps bestanden; Paketidentitäten und APK-Signaturen geprüft. Separate Debug-APK-Artefakte
  wurden hochgeladen. Die CI-Simulation ist kein Hardware- oder Staging-Nachweis.
- **Backend-/Tooling-CI:** [Workflow-Lauf 43041221755](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/43041221755),
  gleicher Code-Commit: Backend-Regressionstests mit PostgreSQL-Service sowie Tooling-Tests erfolgreich.
- **Lokaler Gradle-Lauf:** konnte vor Task-Ausführung das Android-Gradle-Plugin `9.5.1` nicht auflösen.
  Die erfolgreiche Build-/Test-/Lint-Validierung erfolgte daher über GitHub Actions.
- **Staging:** `StagingIntegrationTest` und der manuelle Workflow `device-staging.yml` sind vorbereitet,
  wurden bis zu diesem Stand aber nicht ausgeführt. Es liegt kein Staging-Ergebnis vor; der Workflow
  benötigt die in Abschnitt 3 genannten HTTPS-URLs, Konten und Secrets und bricht bei einem übersprungenen
  Test ab.
- **Echte Geräte / P0:** kein Zwei-Geräte-Test wurde ausgeführt. `DEVICE_LINK_P0_APPROVED` bleibt
  standardmäßig geschlossen; es liegt keine schriftliche P0-Freigabe vor. CI-Erfolg ist keine
  Staging-, Hardware- oder Produktionsfreigabe. Auto-Merge- und bestehende Schutzregeln wurden nicht geändert.
