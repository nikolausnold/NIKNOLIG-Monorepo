# Gemeinsame Backend-Grundlage

**Status: Health-only-Laufzeit mit optionaler PostgreSQL-Bereitschaftsprüfung,
lokal isoliert, nicht produktionsfreigegeben.**

Dieses Verzeichnis definiert gemeinsame, versionierte Verträge für die getrennten
Apps `com.niknolig.app` und `com.niknolig.defense`. `app.py` stellt ausschließlich
nicht-sensitive Health-Routen bereit; Produkt-, Authentifizierungs-, Geräte- und
Pairing-APIs, App-Clients, produktive Endpunkte und eine Cloudflare-/Deployment-
Konfiguration existieren nicht. NIKNOLIG und NIKNOLIG Defense bleiben getrennte
Sicherheits- und Release-Domänen; gemeinsame Verträge verleihen keine Rechte.
Elektro-Engel ist eine NIKNOLIG-Systemfunktion, keine dritte App.

## Artefakte

- [`openapi.yaml`](openapi.yaml): OpenAPI 3.1-Vertrag für nicht-sensitive
  Liveness-/Readiness-Prüfungen und einheitliche Fehlerantworten. Es sind bewusst
  noch keine operativen Geräte-, Profil- oder Pairing-Endpunkte freigegeben.
- [`app.py`](app.py): Health-only-HTTP-Laufzeit. Wenn
  `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER` und
  `DATABASE_PASSWORD` gesetzt sind, prüft `/health/ready` per authentifizierter
  Datenbankverbindung `SELECT 1`. Ohne Datenbankkonfiguration bleibt der
  eigenständige Health-only-Modus verfügbar.
- [`Dockerfile`](Dockerfile) und [`requirements.txt`](requirements.txt):
  lokaler API-Container mit festgelegter Psycopg-Version und unprivilegiertem
  Laufzeitbenutzer.
- [`migrations/001_initial_contract.sql`](migrations/001_initial_contract.sql):
  vorgeschlagenes relationales Modell für App-Bereiche, Installationen,
  Geräteidentitätsstatus und spätere Zwei-App-Link-Beziehungen. Das Anwenden der
  Migration ist bis zur Architektur-/Security-Freigabe gesperrt.
- [`compose.yaml`](compose.yaml): ausschließlich lokaler API- und
  PostgreSQL-Stack. Beide Host-Ports sind an Loopback gebunden; die Container
  kommunizieren über ein isoliertes internes Netzwerk.
- [`.env.example`](.env.example): Variablennamen ohne eingetragene Credentials.
- [`contracts/`](contracts/): versionierte, deklarative Entwürfe für
  Gerätewechsel-Zustimmung, minimierte Audit-Ereignisse, Sensor-Capabilities und
  abgeleitete Sensorzusammenfassungen. Sie sind nicht an eine Laufzeit-API
  angeschlossen.
- [`tests/test_contracts.py`](tests/test_contracts.py): Python-Standardbibliothek-
  Regressionstests für kritische Vertrags- und Isolationsinvarianten. Sie sind
  keine vollständige JSON-Schema-Validierung, Integration-, Sicherheits- oder
  Gerätetests.

Fehlercodes werden auf Implementierungsebene einheitlich zugeordnet:
`AUTHENTICATION_REQUIRED`/`AUTHENTICATION_INVALID` → 401;
`AUTHORIZATION_DENIED`/`APP_AREA_MISMATCH` → 403;
`DEVICE_IDENTITY_UNVERIFIED`/`PAIRING_REQUIRED`/`PAIRING_EXPIRED`/
`REPLAY_DETECTED` → 403 (Integritäts-/Sicherheitsereignisse beenden die Sitzung);
`VALIDATION_FAILED` → 400; `RATE_LIMITED` → 429; `CONFLICT` → 409;
`NOT_FOUND` → 404; `SERVICE_UNAVAILABLE` → 503; `INTERNAL_ERROR` → 500.
Antworten enthalten nur den stabilen Code, eine nicht-sensitive Nachricht und
eine Korrelations-ID; interne Details sind nicht offenzulegen.

## Grenzen und Sicherheitsanforderungen

1. **App-Bereiche:** Jeder Token und jede Ressource muss einem einzelnen
   `app_area` (`niknolig` oder `niknolig-defense`) zugeordnet sein.
   Autorisierung prüft bei jeder Operation App-Bereich, Akteur, Ressource und
   konkrete Aktion. Bereichsabweichungen werden abgelehnt; Defense erhält keine
   Rechte aus NIKNOLIG, einem gemeinsamen Konto, einer gemeinsamen API oder
   einem Linkstatus.
2. **Authentifizierung:** Geschützte API-Aufrufe benötigen künftig kurzlebige,
   widerrufbare Zugriffsnachweise mit festgelegtem Aussteller, Zielgruppe,
   Ablaufzeit, App-Bereich und minimalen Aktionsrechten. Tokenformat, Aussteller,
   Login-/Registrierungsfluss, Schlüsselrotation und Durchsetzung sind offen;
   aus dem Bearer-Schema des OpenAPI-Vertrags folgt keine implementierte oder
   freigegebene Authentifizierung.
3. **Geräteidentität:** Eine Installations-ID oder ein Android-Gerätename ist
   kein Authentizitätsnachweis. Vorgesehen ist eine registrierte
   App-Installation mit Challenge-basierter Besitzprüfung eines
   installationsgebundenen öffentlichen Schlüssels. Hardware-Backing,
   Attestierung, Neuinstallation, Backup/Restore, Rotation und Widerruf benötigen
   eine freigegebene Richtlinie. Private Schlüssel werden nie an das Backend
   übertragen; SQL speichert keinen privaten Schlüssel.
4. **Protokollgrenze:** Geräte sprechen ausschließlich eine versionierte API
   über TLS an; Apps erhalten keinen Datenbankzugriff. Für zukünftige
   Zwei-Geräte-Nachrichten sind Gegenseitigkeit, Frische/Replay-Schutz,
   explizite Nutzerzustimmung, erlaubte Aktionen, Grenzen für Payloads,
   Abbruch/Widerruf und erneute Peer-Authentifizierung festzulegen. Es gibt
   keinen stillschweigenden Offline-Queue-/Retry-Mechanismus.
5. **Datensparsamkeit:** Keine Finanztransaktionen, Zahlungsdaten, unnötigen
   Profildaten, Tokens, Schlüssel oder vollständigen Request-Payloads in Logs.
   Aufbewahrung, Löschung, Benutzeridentität und konkrete Nutzdaten sind noch
   nicht fachlich freigegeben.
6. **Healthchecks:** `/health/live` meldet nur Prozessverfügbarkeit. Mit
   vollständiger Datenbankkonfiguration führt `/health/ready` eine authentisierte
   PostgreSQL-Verbindung und `SELECT 1` aus; fehlende oder nicht erreichbare
   Abhängigkeiten ergeben HTTP 503 mit einer generischen Antwort. Ohne jegliche
   Datenbankkonfiguration bleibt der lokale, eigenständige Health-only-Modus
   bereit. Antworten legen keine Umgebungsvariablen, internen Hosts, Stacktraces
   oder Datenbankdetails offen.

## Lokale Datenbankumgebung

Docker Compose veröffentlicht PostgreSQL ausschließlich auf
`127.0.0.1:54329` und die Health-only-API auf `127.0.0.1:8000` (beide
konfigurierbar). Die API wartet auf den Datenbank-Healthcheck und validiert die
Verbindung anschließend selbst. API- und Datenbankcontainer laufen in einem
internen Netzwerk; der API-Container ist schreibgeschützt und unprivilegiert.
`.env` wird lokal aus `.env.example` erstellt und nicht eingecheckt. Das
Compose-Setup ist nicht für Deployment oder sensible Daten bestimmt.

Lokalen Wert für `POSTGRES_PASSWORD` in `backend/.env` eintragen und den Stack
starten:

```sh
docker compose --env-file backend/.env -f backend/compose.yaml up --build --detach
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
```

Für einen Stopp ohne Löschen des lokalen Datenbank-Volumes:

```sh
docker compose --env-file backend/.env -f backend/compose.yaml down
```

Das lokale Volume hat keine konfigurierte Backup-/Wiederherstellungsprozedur.
Backups, Restore-Tests, Hochverfügbarkeit, TLS, externe Erreichbarkeit und
Produktionsbetrieb sind nicht umgesetzt oder validiert.

## Lokaler Health-Server

Mit Python 3 starten:

```sh
python3 backend/app.py
```

Die Standardbindung ist `127.0.0.1:8000`. `BACKEND_HOST` und `BACKEND_PORT`
können als Umgebungsvariablen gesetzt werden. Die Anwendung lädt `.env` nicht
automatisch. Ohne gesetzte Datenbankparameter funktionieren die Health-Routen
im lokalen Health-only-Modus; mit vollständiger `DATABASE_*`-Konfiguration prüft
Readiness tatsächlich die PostgreSQL-Verbindung. Andere GET-Pfade geben eine
generische 404-Antwort zurück. Es gibt weiterhin keine Anmeldung, Gerätefunktion
oder Produkt-API. Die Laufzeit und Compose-Konfiguration sind nur für lokale
Entwicklung und Vertragstests gedacht: nicht öffentlich exponieren oder als
produktiven Internetserver verwenden. Serverplattform, TLS, Authentifizierung,
Betrieb und Deployment bleiben separat zu konfigurieren und freizugeben.

## SecurityChain-P0 und Freigabe

Im geprüften Repository liegt keine normative SecurityChain-P0-Fassung mit
prüfbaren Muss-/Abbruchkriterien. Daher wird keine P0-Konformität behauptet.
**Produktive Geräteintegration und die operative API bleiben BLOCKED**, bis
mindestens die verbindlichen P0-Kriterien, Bedrohungsmodell, Daten-/Aktionsumfang,
Rollen, Identitäts-/Authentifizierungsverfahren, Transport, Widerruf,
Aufbewahrung und Abnahmekriterien schriftlich von den Verantwortlichen
freigegeben und überprüfbar getestet sind. Die SQL-Modelle und zukünftigen
Routen in dieser Grundlage sind Vorschläge, keine Freigabe dieser offenen
Entscheidungen. Bei fehlender Prüfung gilt fail closed.

## Integration in den separaten App-Repositories

Die Quell-Repositories `nikolausnold/NIKNOLIG` und
`nikolausnold/NIKNOLIG-Defense` wurden nicht geändert. Nach Freigabe müssen
Änderungen getrennt und unabhängig reviewed werden:

| App-Repository | Vorgesehene Dateien / Schnittstellen | Abhängigkeit / Gate |
| --- | --- | --- |
| `nikolausnold/NIKNOLIG` | `app/build.gradle.kts` (geprüfte HTTP-/TLS-Clientabhängigkeit), `app/src/main/AndroidManifest.xml` (nur freigegebene Netzwerkrechte), `app/src/main/java/com/niknolig/app/` (eigener API-Client und app-spezifische Authentifizierung), `app/src/main/res/values/strings.xml` (Zustimmungs-/Fehlertexte), `app/src/test/` und `app/src/androidTest/` (Vertrag, Ablehnung, Widerruf) | Eigener App-Bereich `niknolig`; API-Client aus dem freigegebenen Vertrag generieren oder dagegen testen. Keine Defense-Credentials oder gemeinsamen Laufzeitrechte. |
| `nikolausnold/NIKNOLIG-Defense` | `app/build.gradle.kts` (separat geprüfte Clientabhängigkeit), `app/src/main/AndroidManifest.xml` (nur freigegebene Netzwerkrechte), `app/src/main/java/com/niknolig/defense/` (eigener API-Client und app-spezifische Authentifizierung), `app/src/main/res/values/strings.xml` (Zustimmungs-/Fehlertexte), `app/src/test/` und `app/src/androidTest/` (Vertrag, Ablehnung, Widerruf) | Eigener App-Bereich `niknolig-defense`; niemals das NIKNOLIG-Token oder dessen Installationsidentität wiederverwenden. |

Für beide Apps müssen zusätzlich Backend-Basis-URL pro Build-Variante, TLS-
Vertrauensregeln, Authentifizierung/Tokenbezug, Datenschutztexte und
Fehler-/Timeoutverhalten beschlossen werden. Diese Werte dürfen nicht aus
diesem lokalen Compose-Setup als Produktionskonfiguration übernommen werden.
Keine App-Repositories, URLs, Berechtigungen, Abhängigkeiten oder Workflows
werden durch dieses Monorepo automatisch geändert.

## Verifikation und nächste Schritte

`python3 -m unittest discover -s backend/tests` prüft Vertragsinvarianten und
die Health-only-Laufzeit. Sofern Docker Compose installiert ist, kann die lokale
Compose-Konfiguration mit diesem lokalen Platzhalter syntaktisch geprüft werden:

```sh
POSTGRES_PASSWORD=local-only-check docker compose \
  --env-file backend/.env.example -f backend/compose.yaml config --quiet
```

Die Python-Tests simulieren den Datenbanktreiber und belegen keinen laufenden
PostgreSQL-Container. Wenn Docker Compose verfügbar ist, kann der lokale Stack
zusätzlich mit einem eigens gesetzten lokalen Passwort gestartet und über beide
Health-Routen geprüft werden. Keine der Prüfungen belegt eine operative
Produkt-API, sichere Benutzer-/Geräteauthentifizierung, P0-Freigabe oder
Verbindung zwischen zwei physischen Geräten.

Gerätewechsel-, Sensorverträge, Android API-/Berechtigungsanforderungen und
Geräteabnahmeplan stehen in
[`docs/electro-engel-multidevice-sensors.md`](../docs/electro-engel-multidevice-sensors.md).
Sie genehmigen keine Implementierung und lockern das P0-Gate nicht.

Die Android-/iOS-übergreifende Vertrags- und Backend-Architektur, vorhandene
Vertragslücken, Testparität und der Integrationsplan für separate iOS-Apps
stehen in
[`docs/mobile-cross-platform-architecture.md`](../docs/mobile-cross-platform-architecture.md).
Das Dokument ergänzt die Bestandsverträge, erstellt aber keine Produkt-API und
hebt das P0-Gate nicht auf.

Nächste Schritte: SecurityChain-P0-Nachweis und fachlich verantwortliche
Freigaben einholen; API-Datenflüsse und Ressourcenumfang mit beiden App-Teams
abgleichen; Identitätsanbieter, Schlüsselrichtlinie, Serverplattform und
Betriebsverantwortung auswählen; dann OpenAPI/Schema versionieren und
Implementierung, Negativtests und unabhängige Sicherheitsprüfung freigeben.
Bei nicht abgedeckten Sicherheitsentscheidungen hier anhalten.
