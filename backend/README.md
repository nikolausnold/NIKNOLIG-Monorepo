# Gemeinsame Backend-Grundlage

**Status: lokal testbare, standardmäßig gesperrte API-Referenzintegration.
SecurityChain-P0 und Produktivfreigabe bleiben BLOCKED. Kein Deployment erfolgt.**

Dieses Verzeichnis definiert gemeinsame, versionierte Verträge für die getrennten
Apps `com.niknolig.app` und `com.niknolig.defense`. `app.py` bleibt der bisherige
abhängigkeitsfreie Health-Testserver. `api.py` ergänzt eine getrennte Flask-/WSGI-
Laufzeit für Authentifizierungsprüfung, Autorisierung und eigene Installationen;
Anmeldung und Tokenausstellung bleiben beim noch zu bestätigenden bestehenden
Identitätsanbieter. Pairing-, Consent-, Sensor- und Produkt-APIs bleiben aus.
NIKNOLIG und NIKNOLIG Defense bleiben getrennte
Sicherheits- und Release-Domänen; gemeinsame Verträge verleihen keine Rechte.
Elektro-Engel ist eine NIKNOLIG-Systemfunktion, keine dritte App.

## Artefakte

- [`openapi.yaml`](openapi.yaml): OpenAPI 3.1 für Health und die gesperrte
  `/v1`-Referenz-API. Keine produktive Freigabe.
- [`app.py`](app.py): lokale Health-only-HTTP-Laufzeit ohne externe
  Python-Abhängigkeiten. Sie ist kein produktionsgeeigneter API-Server.
- [`api.py`](api.py), [`store.py`](store.py): WSGI-API mit PostgreSQL-Persistenz.
  [`requirements.txt`](requirements.txt) pinnt die benötigten Abhängigkeiten;
  [`Dockerfile`](Dockerfile) startet Gunicorn als nicht privilegierter Benutzer.
- [`migrations/001_initial_contract.sql`](migrations/001_initial_contract.sql):
  vorgeschlagenes relationales Modell für App-Bereiche, Installationen,
  Geräteidentitätsstatus und spätere Zwei-App-Link-Beziehungen. Das Anwenden der
  Migration ist bis zur Architektur-/Security-Freigabe gesperrt.
- [`migrations/002_backend_api.sql`](migrations/002_backend_api.sql):
  additive API-Tabellen, öffentliche Geräteschlüssel und Schema-Versionsmarker.
  Kein automatischer Migrationslauf beim Start.
- [`compose.yaml`](compose.yaml): PostgreSQL und optionaler `api`-Profilservice,
  beide im internen DB-Netz; API zusätzlich im Edge-Netz und nur auf Loopback
  veröffentlicht. PostgreSQL besitzt keine Host-Portfreigabe.
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
2. **Authentifizierung:** Die Referenz prüft RS256-Access-JWTs (`typ=at+jwt`)
   eines konfigurierten HTTPS-Ausstellers anhand dessen vorhandenen öffentlichen
   RSA-Schlüssels. Pflichtclaims: `iss`, `aud`, `sub`, `iat`, `exp`, `jti`,
   `app_area`, `scope`; maximale Laufzeit 900 Sekunden. Pro App ist eine andere
   Zielgruppe zwingend. `X-App-Area`, signierter Bereich und Zielgruppe müssen
   übereinstimmen. Logout widerruft genau dieses Token persistent bis zum Ablauf,
   nicht den Refresh-Token beim Aussteller. Kein Passwortlogin, Token-Endpunkt,
   Founder-/Admin-Konto oder neuer Anbieter wird erfunden. Ohne passenden
   bestehenden Aussteller bleibt die API gesperrt. Schlüsselwechsel verlangt
   kontrollierten Austausch der öffentlichen Datei und Neustart; kein
   ungeprüftes Nachladen von Token-URLs.
3. **Geräteidentität:** Eine Installations-ID oder ein Android-Gerätename ist
   kein Authentizitätsnachweis. Vorgesehen ist eine registrierte
   App-Installation mit implementierter Challenge-basierter Besitzprüfung eines
   installationsgebundenen öffentlichen Schlüssels. Hardware-Backing,
   Attestierung, Neuinstallation, Backup/Restore und Rotation benötigen
   weiterhin eine freigegebene Richtlinie. Widerruf ist endgültig, keine
   Reaktivierung durch Verifizieren. Private Schlüssel werden nie an das Backend
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
6. **Healthchecks:** `/health/live` meldet nur Prozessverfügbarkeit. In `api.py`
   verlangt `/health/ready` Aktivierung, gültige Auth-Konfiguration,
   DB-Verbindung und erwartetes API-Schema; sonst 503. Der alte `app.py`
   bleibt Health-only und weist keine API-Bereitschaft nach. Antworten legen
   keine Umgebungsvariablen, internen Hosts, Stacktraces oder Datenbankdetails
   offen.

## Lokale Datenbankumgebung

Docker Compose veröffentlicht PostgreSQL nicht auf dem Host, nutzt ein
erforderliches lokales Passwort, ein internes DB-Netz und benanntes Volume. Es
gibt mit `--profile api` einen optionalen API-Container; ohne Profil bleibt
es beim bisherigen DB-Service. `.env` wird lokal aus `.env.example` erstellt und nicht
eingecheckt. Das Compose-Setup ist nicht für Deployment oder sensible Daten
bestimmt. Produktivbetrieb verlangt die unten beschriebenen Freigaben und
Anpassungen an den tatsächlich vorhandenen Server.

Erforderlich: Docker Compose ≥2.33.1 für `gw_priority`. Das API-Edge-Netz
besitzt explizit den Standardgateway. Compose setzt
`BACKEND_ALLOW_INSECURE_LOCAL=true` ausschließlich für den privaten HTTP-Hop
vom TLS-Proxy zur Loopback-veröffentlichten API. Ohne dieses explizite Opt-in
verlangt die WSGI-Anwendung HTTPS. Das erlaubt **kein HTTP in mobilen Clients**:
öffentlicher Traffic muss am bestehenden HTTPS-Proxy terminieren; die
Compose-Portbindung darf nicht auf `0.0.0.0` geändert werden.

### Compose-DNS: Containername ist kein Hostname des Ubuntu-Hosts

Im Ausgangsstand gab es **keinen API-Service und keine PostgreSQL-Verbindung im
Python-Code**. Ein früherer Server-Stacktrace liegt nicht vor. Lokal mit Docker
28.0.4 reproduziert: Ein Client ausschließlich im internen Netzwerk scheiterte
bei `postgres` mit `Temporary failure in name resolution`; direkter TCP-Zugriff
im selben Netz funktionierte. Außerdem wurde die bisherige Host-Portfreigabe
des ausschließlich internen DB-Containers nicht angelegt. Ein Client mit
zusätzlichem normalen Edge-Netz löste `postgres` korrekt auf und erreichte
PostgreSQL. Deshalb besitzt nur die API zusätzlich `api-edge`; die Datenbank
bleibt intern, die irreführende DB-Host-Portfreigabe entfällt.

| Aufrufort | DB-Host | DB-Port |
| --- | --- | --- |
| `api` im gleichen Compose-Projekt/Netzwerk | `postgres` | `5432` |
| DB-Werkzeuge | `docker compose exec postgres psql …` | kein Host-Port; lokale Python-API ebenfalls im Compose-Profil starten |
| separat freigegebene Host-/externe DB, nicht dieser Stack | explizit konfigurierte Hostadresse | tatsächlicher DB-Port, niemals Compose-Namen auf dem Host voraussetzen |
| Android/iOS | **kein DB-Zugriff** | nur freigegebene HTTPS-API |

`localhost` im API-Container bezeichnet nicht PostgreSQL. `postgres` wird nur
über das gemeinsame `backend-internal` aufgelöst. Kein öffentlicher DNS-Eintrag,
`extra_hosts`, Host-Netzwerk oder öffentlicher DB-Port ist nötig. Compose setzt
`PGHOST=postgres`, `PGPORT=5432`; Healthcheck und `depends_on: service_healthy`
ordnen den Start. Das API-Edge-Netz ermöglicht die Loopback-Veröffentlichung
und den funktionierenden Docker-Resolver; PostgreSQL wird nicht daran
angeschlossen. Spätere DB-Ausfälle werden weiter fail closed behandelt.
Immer dieselben `-p`, `-f`, `--env-file` verwenden; kein zweites Projekt
versehentlich mit einem anderen Volume starten.

### Referenz-API und mobile Anbindung

| Methode/Pfad | Scope | Wirkung |
| --- | --- | --- |
| `GET /v1/auth/session` | `auth:read` | geprüfte eigene Sitzung |
| `POST /v1/auth/logout` | `auth:revoke` | aktuelles Token sperren |
| `GET /v1/devices`, `GET /v1/devices/{id}` | `devices:read` | eigene Installationen im Token-Bereich |
| `POST /v1/devices` | `devices:write` | UUID + öffentlicher P-256-Schlüssel als `pending` registrieren |
| `POST /v1/devices/{id}/challenge` | `devices:write` | einmalige, kurzlebige Besitz-Challenge |
| `POST /v1/devices/{id}/verify` | `devices:write` | ECDSA-SHA256-Besitznachweis prüfen |
| `DELETE /v1/devices/{id}` | `devices:write` | endgültig widerrufen |

Fremde Ressourcen → 404, Bereichsabweichungen → 403. JSON-Felder bestimmen
weder Principal, Rolle, Bereich noch Verifikationsstatus. Begrenzte Requests
und persistente Ratenlimits schützen die Referenz; zusätzliche TLS-Proxy-
Limits müssen vor JWT-/DB-Verarbeitung greifen.
`verified` beweist Schlüsselbesitz, **nicht** Hardware-Attestierung,
Peer-Pairing, Consent oder Sensor-/Defense-Aktionsrechte.
Die Verwaltungs-Access-Tokens sind principal- und appgebunden, noch nicht
installationsgebunden. Gerätewiderruf sperrt den Geräte-/Challenge-Zustand,
nicht automatisch das Account-Token; dafür separat Token-Logout bzw.
Aussteller-Sessionwiderruf verwenden. Keine gerätegebundenen Produktaktionen
auf dieser Grundlage freigeben.

Android und iOS verwenden denselben Vertrag, aber je App eigene OAuth-
Clientregistrierung, Redirect-URI, API-Zielgruppe, Tokenablage und Installation.
Der vorhandene Aussteller muss Authorization Code mit PKCE S256 und Systembrowser
unterstützen; keine Client-Secrets in Apps. Ohne bestätigte vorhandene
Clientregistrierungen keine Live-Anbindung und keine neuen Zugangsdaten anlegen.
Private P-256-Schlüssel bleiben im Android Keystore bzw. Apple Keychain/
Secure Enclave. Exakte `message` als UTF-8 mit ECDSA-SHA256 signieren;
`signature` ist Standard-Base64 der ASN.1-DER-Signatur, nicht JOSE-Raw-`r||s`.
Challenge und sensible Aktionen nicht automatisch wiederholen.
Details: [`mobile-cross-platform-architecture.md`](../docs/mobile-cross-platform-architecture.md).

## Lokaler Health-Server

Mit Python 3 starten:

```sh
python3 backend/app.py
```

Die Standardbindung ist `127.0.0.1:8000`. `BACKEND_HOST` und `BACKEND_PORT`
können als Umgebungsvariablen gesetzt werden. Die Anwendung lädt `.env` nicht
automatisch. `/health/live` und `/health/ready` liefern die vereinbarten
Statusantworten; andere GET-Pfade geben eine generische 404-Antwort zurück.
In diesem alten Einstiegspunkt gibt es keine Anmeldung, DB-Verbindung oder
Gerätefunktion; diese Tests bleiben unverändert als Regression erhalten.
Die Standardbibliotheks-HTTP-Laufzeit ist nur für lokale Entwicklung und
Vertragstests gedacht: nicht öffentlich exponieren oder als produktiven
Internetserver verwenden. Serverplattform, TLS, Authentifizierung, Betrieb und
Deployment bleiben separat zu konfigurieren und freizugeben.

## SecurityChain-P0 und Freigabe

Im geprüften Repository liegt keine normative SecurityChain-P0-Fassung mit
prüfbaren Muss-/Abbruchkriterien. Daher wird keine P0-Konformität behauptet.
**Produktive Geräteintegration und Aktivierung der operativen API bleiben BLOCKED**, bis
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

`python3 -m unittest discover -s backend/tests` prüft Vertragsinvarianten,
Health-only-Laufzeit und, mit installierten API-Abhängigkeiten, API-Negativfälle.
DB-Integrationstests benötigen eine isolierte Wegwerf-Testdatenbank; niemals
eine produktive DSN verwenden. Sofern Docker Compose installiert ist, kann die lokale
Compose-Konfiguration mit diesem lokalen Platzhalter syntaktisch geprüft werden:

```sh
POSTGRES_PASSWORD=local-only-check docker compose \
  --env-file backend/.env.example -f backend/compose.yaml config --quiet
```

Der Datenbankstart verlangt bewusst ein gesetztes lokales Passwort und ist nicht
Teil der abhängigkeitfreien Tests. Keine lokale Prüfung belegt eine
P0-Freigabe, echte OAuth-Anmeldung oder Verbindung zweier physischer Geräte.

Gerätewechsel-, Sensorverträge, Android API-/Berechtigungsanforderungen und
Geräteabnahmeplan stehen in
[`docs/electro-engel-multidevice-sensors.md`](../docs/electro-engel-multidevice-sensors.md).
Sie genehmigen keine Implementierung und lockern das P0-Gate nicht.

Die Android-/iOS-übergreifende Vertrags- und Backend-Architektur, vorhandene
Vertragslücken, Testparität und der Integrationsplan für separate iOS-Apps
stehen in
[`docs/mobile-cross-platform-architecture.md`](../docs/mobile-cross-platform-architecture.md).
Das Dokument beschreibt zusätzlich die gesperrte Referenzintegration, aber
keine Produkt-/Pairing-/Sensor-API und hebt das P0-Gate nicht auf.

Nächste Schritte: SecurityChain-P0-Nachweis und fachlich verantwortliche
Freigaben einholen; API-Datenflüsse und Ressourcenumfang mit beiden App-Teams
abgleichen; Identitätsanbieter, Schlüsselrichtlinie, Serverplattform und
Betriebsverantwortung auswählen; dann OpenAPI/Schema versionieren und
produktive Implementierung und unabhängige Sicherheitsabnahme freigeben.
Bei nicht abgedeckten Sicherheitsentscheidungen hier anhalten.

## SecurityChain-P0: konkrete Lücken und Grenzen dieser Änderung

Bestandsprüfung, **keine erfundene normative P0-Zertifizierung**:

| Bereich | Lokal ergänzt | Vor Freigabe weiter erforderlich |
| --- | --- | --- |
| Authentifizierung | Signatur, Issuer, Lebenszeit, App-Zielgruppe, Revocation | bestehenden Anbieter/Claim-Mapping, PKCE-/Refresh-/Recovery-Flow und Schlüssel bestätigen |
| Autorisierung | Scope + Principal + App + eigene Ressource, fail closed | fachliches Rollenmodell; keine Founder-/Admin-/Cross-App-Rechte implementiert |
| Geräte | öffentlicher Schlüssel, Challenge, Ablauf, Replay-Ablehnung, Widerruf | Hardware-/Attestierungs-, Neuinstallations-, Recovery-/Rotationspolitik |
| Consent/Daten | keine neuen Produkt-/Sensor-/Pairing-Routen | beidseitige Zustimmung und aktuelle serverseitige Consent-Prüfung vor solchen Funktionen |
| Betrieb | internes Netz, Loopback, WSGI, DB-Readiness | TLS-Proxy, Host-Inventar, Restore-Probe, Least Privilege, Monitoring, Retention |
| Nachweise | gezielte lokale Tests | normative P0-Version, Threat Model, unabhängige und physische Android-/iOS-Abnahme |

`BACKEND_API_ENABLED=false` ist Standard. Ein Schalter ersetzt keine Freigabe.
Keine Änderungen an laufenden Serverdiensten, Produktionsdaten, DNS, TLS,
Konten oder App-Identitäten wurden durchgeführt.

## Hetzner Ubuntu: sichere Deployment-Anleitung für den Betreiber

**Nicht ausgeführt.** IP, Ubuntu-Version, Domain, Proxy, Compose-Projekt,
DB-Rollen und Pfade des Servers sind nicht bekannt. Die folgenden Pfade
sind eine vorgeschlagene Struktur, keine Behauptung über den Ist-Zustand.
Bestehende Konfigurationen nicht ersetzen. Direkte Einstiege:
[Hetzner Console](https://console.hetzner.com/),
[Backend-Quellcode](https://github.com/nikolausnold/NIKNOLIG-Monorepo/tree/main/backend),
[Compose Networking](https://docs.docker.com/compose/how-tos/networking/).

### 1. Stop-Gates und lesende Bestandsaufnahme

Zuerst P0-/Produktfreigabe, Wartungsfenster, Verantwortlichen, bestehenden
Aussteller samt öffentlichem RSA-Schlüssel und getrennte Zielgruppen bestätigen.
Keine neuen Dienste buchen oder Zugangsdaten erzeugen. Fehlt eine geeignete
vorhandene DB-Rolle oder OAuth-Clientregistrierung: **stoppen**, nicht durch
Superuser, Dummy-Token oder neue Registrierung umgehen.
Nach Anmeldung über den bereits freigegebenen SSH-Zugang zunächst nur lesen:

```sh
lsb_release -ds
df -h
free -h
timedatectl status
docker version
docker compose version
docker compose ls
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
sudo ss -lntp
sudo systemctl is-active nginx caddy
sudo ufw status verbose
```

Nicht `docker inspect`, vollständige Environments, Logs oder `compose config`
ohne `--quiet` unredigiert teilen: möglicherweise bestehende Secrets.
Kollisionen zuerst separat prüfen. Keine pauschale Firewalländerung, kein
Docker-Neustart, kein `compose down`, `down -v` oder `prune`.
Zeitsynchronisation muss funktionieren; Token-/Challenge-Frische nicht durch
größere Toleranzen als Ersatz für eine fehlerhafte Serveruhr abschwächen.

### 2. Release und Konfiguration vorbereiten, noch kein Start

Reviewed Commit in neues Release-Verzeichnis
`/srv/niknolig/releases/<COMMIT>/` bereitstellen, nicht über laufende Dateien
kopieren. Vorhandenen Compose-Projektnamen und Datenvolume beibehalten.
Bei Erstinstallation unbenutzten Projektnamen festlegen und dokumentieren.
Image einmal als `niknolig-backend:<COMMIT>` bauen; vorheriges Image und
Konfiguration behalten. Commit, Image-ID/Digest und Schema-Stand protokollieren.

Konfiguration außerhalb Git unter `/srv/niknolig/config/backend.env`,
Verzeichnis 0700, Datei 0600. Vorhandene Secrets sicher übertragen, nie in
Shell-History, Chat oder Kommandozeilenargumenten einfügen.

| Variable | Bestätigung / Wert |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | vorhandene DB und Bootstrap-/Migrationszugang; kein Runtime-Superuser |
| `BACKEND_DB_USER`, `BACKEND_DB_PASSWORD` | bestehende separate Least-Privilege-Runtime-Rolle |
| `BACKEND_PORT` | freier Loopback-Upstream-Port, Standard `8000` |
| `BACKEND_API_ENABLED` | zunächst `false`; erst nach Abnahme bewusst `true` |
| `AUTH_ISSUER` | exakte bestehende HTTPS-Issuer-URL |
| `AUTH_AUDIENCE_NIKNOLIG`, `AUTH_AUDIENCE_DEFENSE` | zwei verschiedene vorhandene API-Zielgruppen |
| `AUTH_PUBLIC_KEY_FILE` | absoluter Hostpfad zum öffentlichen RSA-PEM, lesbar für UID 10001; nie privaten Schlüssel mounten |

Container-`PGHOST=postgres`/`PGPORT=5432` sind festgelegt. Änderungen an
`POSTGRES_*` initialisieren ein bestehendes Volume **nicht** neu und rotieren
keine Passwörter. Bestehende Zugangsdaten nicht zum „Reparieren“ überschreiben.
Produktion benötigt lokal geprüften Override außerhalb Git:
`api.image: niknolig-backend:<COMMIT>`, Start mit `--no-build`.
PostgreSQL bleibt ohne Host-Port, nur im internen Netz. Bei externer bestehender DB nicht
parallel diesen DB-Service starten; Netzwerk/Serviceadresse separat anpassen.

Die Befehle setzen **erst nach Bestandsaufnahme** voraus:

```sh
RELEASE=/srv/niknolig/releases/GEPRUEFTER_COMMIT
ENV=/srv/niknolig/config/backend.env
PROJECT=BESTEHENDER_ODER_FREIGEGEBENER_PROJEKTNAME
OVERRIDE=/srv/niknolig/config/production.yaml
docker compose -p "$PROJECT" --env-file "$ENV" -f "$RELEASE/backend/compose.yaml" \
  -f "$OVERRIDE" --profile api config --quiet
docker build -t niknolig-backend:GEPRUEFTER_COMMIT "$RELEASE/backend"
```

Platzhalter zuerst ersetzen. Diese Anleitung ist kein Auftrag zur sofortigen
Ausführung; ein Build startet noch keinen Dienst.

### 3. Backup, Migrationen und Least Privilege im Wartungsfenster

**Nur nach separater Betreiberfreigabe.** Zuerst konsistentes Backup mit dem
bereits bestehenden Compose-PostgreSQL in geschützten vorhandenen Backup-Speicher:

```sh
umask 077
BACKUP=/srv/niknolig/backups/VORHERIGER_STAND.dump
docker compose -p "$PROJECT" --env-file "$ENV" -f "$RELEASE/backend/compose.yaml" \
  -f "$OVERRIDE" exec -T postgres \
  sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$BACKUP"
test -s "$BACKUP"
```

Rückgabecode von `pg_dump` prüfen; nichtleere Datei allein ist kein Nachweis.
Restore mit `pg_restore --exit-on-error --no-owner` in isolierter **Test-DB**,
nie gegen laufende DB, verifizieren. Passende PostgreSQL-Major-Version,
genügend Speicher, Zugriffsschutz und vorhandene verschlüsselte Backupablage
sicherstellen. Ohne erfolgreiche Probe stoppen. Bei Erstinstallation stattdessen
den bestätigten Leerzustand dokumentieren.

Schreiber stoppen, Ist-Stand mit Owner/Migrationszugang prüfen:

```sql
SELECT to_regclass('public.device_installations'),
       to_regclass('public.backend_schema_migrations');
```

001 ausschließlich bei bestätigtem leeren Zielschema anwenden. Vorhandene
Tabellen zuerst gegen 001 abgleichen, **nicht** erneut ausführen oder mit
`IF NOT EXISTS` Abweichungen verstecken. 002 nur bei passender 001 und fehlendem
Marker `002_backend_api` in `backend_schema_migrations`. Bei Teilzuständen oder
unbekanntem Schema stoppen.
Migrationen nie beim App-Start ausführen.

```sh
# Nur wenn die Zustandsprüfung die jeweilige Migration erlaubt:
docker compose -p "$PROJECT" --env-file "$ENV" -f "$RELEASE/backend/compose.yaml" \
  -f "$OVERRIDE" exec -T postgres \
  sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$RELEASE/backend/migrations/001_initial_contract.sql"
docker compose -p "$PROJECT" --env-file "$ENV" -f "$RELEASE/backend/compose.yaml" \
  -f "$OVERRIDE" exec -T postgres \
  sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$RELEASE/backend/migrations/002_backend_api.sql"
```

Runtime benötigt nur `CONNECT`, Schema-`USAGE` und benötigte DML-Rechte
auf API-Tabellen, einschließlich bereinigender `DELETE`-Operationen; nur
`SELECT` auf dem Versionsmarker. Keine Schema-/DDL-Rechte, kein Owner,
Superuser, `BYPASSRLS`, `CREATEDB`, `CREATEROLE` oder Zugriff auf fremde
Produktdaten. Grants separat mit bestehendem Owner durchführen, öffentliche
Schema-/PUBLIC-Rechte prüfen, nicht unbesehen clusterweit ändern.

Beispiel ausschließlich mit **bestehender**, zuvor geprüfter Runtime-Rolle
im Owner-`psql` der richtigen Datenbank (Rollennamen ersetzen):

```sql
\set runtime_role 'BEREITS_VORHANDENE_RUNTIME_ROLLE'
SELECT format('GRANT CONNECT ON DATABASE %I TO %I',
              current_database(), :'runtime_role') \gexec
GRANT USAGE ON SCHEMA public TO :"runtime_role";
GRANT SELECT ON device_installations TO :"runtime_role";
GRANT INSERT (id, app_area, principal_reference, installation_reference,
              public_key, public_key_fingerprint)
    ON device_installations TO :"runtime_role";
GRANT UPDATE (identity_state, verified_at, revoked_at)
    ON device_installations TO :"runtime_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON backend_device_challenges,
    backend_token_revocations, backend_rate_limits TO :"runtime_role";
GRANT SELECT ON backend_schema_migrations TO :"runtime_role";
```

Keine Rechte auf `device_links` erforderlich. Bestehende weitergehende Rechte
und Rollenmitgliedschaften separat prüfen; diese Grants entziehen sie nicht.
Hilfsdatenbereinigung erfolgt bei authentifizierten Aufrufen in begrenzten
Paketen. Für Stillstandszeiten/hohes Volumen zusätzlich genehmigten
Wartungslauf vorsehen; niemals noch gültige Revocations vorzeitig löschen.

### 4. Aktivierung, TLS und Healthchecks

Bestehenden TLS-Proxy wiederverwenden, nicht ersetzen: freigegebene Domain,
gültige Kette, TLS ≥1.2, nur Health und definierte `/v1/*` zum Loopback-Upstream.
Bodylimit 16 KiB, begrenzte Header, kurze Read-/Upstream-Timeouts und
vorgelagertes IP-Ratenlimit. Keine Auth-Header, Querystrings oder Bodies loggen.
API vertraut keinen `X-Forwarded-*`-Headern; keine Cookies/CORS-Freigabe.
8000/5432 nicht öffentlich freigeben; Docker kann UFW umgehen, daher
Loopback-Bindung und fehlende DB-Portfreigabe nicht ersetzen.
Ein containerisierter Proxy kann nicht über sein eigenes Loopback zum Host:
benötigtes gemeinsames Proxy-Netzwerk dann erst separat prüfen.

Falls der Bestand **Nginx auf dem Host** verwendet, diese Direktiven nach
Review in dessen bestehende Konfiguration integrieren, nicht eine zweite
Konfiguration darüberkopieren. Im vorhandenen `http`-Block:

```nginx
limit_req_zone $binary_remote_addr zone=niknolig_api:10m rate=5r/s;
log_format niknolig_minimal '$time_iso8601 $status $request_id';
```

Im bereits vorhandenen TLS-`server` mit bestätigter Domain/Zertifikaten, nur
wenn er ausschließlich der Backend-API dient:

```nginx
client_max_body_size 16k;
client_body_timeout 10s;
client_header_timeout 10s;
access_log /var/log/nginx/niknolig-api.log niknolig_minimal;

location / {
    limit_req zone=niknolig_api burst=10 nodelay;
    limit_req_status 429;
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_connect_timeout 3s;
    proxy_read_timeout 10s;
    proxy_send_timeout 10s;
}
```

Nicht zusätzlich auf einen gemeinsam genutzten Website-`location /` legen.
Header-/Verbindungslimits und Log-Rotation an den vorhandenen Nginx-Bestand
anpassen. Fehlerlogs können Requestzeilen enthalten: keine Query-Parameter für
Tokens/Personendaten verwenden und bestehende Fehlerlog-Aufbewahrung prüfen.
Nach Betreiberfreigabe zuerst `sudo nginx -t`, nur bei Erfolg gezielt reloaden,
kein blinder Service-Neustart. Bei Caddy/anderem Proxy äquivalent im vorhandenen
System konfigurieren, keinen zweiten Proxy installieren.

Nach Freigabe `BACKEND_API_ENABLED=true` setzen und nur API aktualisieren:

```sh
docker compose -p "$PROJECT" --env-file "$ENV" -f "$RELEASE/backend/compose.yaml" \
  -f "$OVERRIDE" --profile api up -d --no-deps --no-build api
curl --fail --max-time 5 http://127.0.0.1:8000/health/live
curl --fail --max-time 5 http://127.0.0.1:8000/health/ready
```

Port an Konfiguration anpassen. Erstinstallation benötigt vor Migrationen
separat freigegebenen PostgreSQL-Start; oben wird absichtlich keine DB gestartet.
Liveness 200 genügt nicht: Readiness muss 200 liefern, bei deaktivierter API,
DB-Ausfall/falschem Schema 503. Zusätzlich über bestätigte HTTPS-Domain
**ohne `curl -k`** prüfen. Kein produktiver Endpunkt ist hier erfunden.
Geschützt ohne Token → 401, Bereich falsch → 403, fremde Ressource → 404.
Positiven Zugriff/Widerruf nur mit vorhandenem freigegebenem Testkonto testen;
keine Tokens in History/Logs, keine Founder-Konten dafür anlegen.

Nachweis: Commit, Image-ID, Konfigurationsrevision ohne Secrets, Migrationsstand,
Backup-/Restore-Probe, UTC-Zeit, Status, Korrelations-ID. Readiness, Speicher,
DB, TLS-Ablauf und Ratenlimits überwachen. Retention und Bereinigung der
Hilfsdaten vor Traffic schriftlich festlegen.

### 5. Rollback ohne Datenverlust

Bei Health-/Auth-/Integritätsfehlern keinen Traffic freigeben. API am bestehenden
Proxy sperren und API stoppen, DB weiterlaufen lassen. Vorherigen getesteten
Image-Tag und zugehörige Konfiguration wiederherstellen; nur `api` mit denselben
Compose-Dateien/Projektnamen und `up -d --no-deps --no-build api` starten,
Readiness/Negativfälle erneut prüfen. Health-only-Vorgänger nicht als Produkt-API
veröffentlichen.

002 ist additiv: beim App-Rollback bestehen lassen, kein automatisches Down/DROP,
kein Volumewechsel. DB-Restore nur separat freigegeben: alle Schreiber stoppen,
zuerst isolierte neue Ziel-DB wiederherstellen und prüfen, dann kontrolliert
umschalten. Backup kann jüngste Widerrufe verlieren; bis Wiederherstellung
dieser Sperren bzw. Ablauf aller betroffenen Tokens/Challenges bleibt die API
gesperrt. Nie `pg_restore --clean` gegen laufende DB, nie `down -v`.

## Tatsächliche lokale Prüfergebnisse

Prüfung im isolierten Arbeitscheckout, nicht auf Hetzner:

- Ausgangsstand `dca6b1b`: keine uncommitteten Änderungen und keine vorhandene
  Python-PostgreSQL-Verbindung. Keine früheren Serverlogs verfügbar.
- Vertragsregression: **10 Tests erfolgreich**, einschließlich App-Isolation
  und Schema-Negativfällen; nach Änderung der Netzwerkgrenze erneut geprüft.
- Compose-Konfiguration mit synthetischem lokalem Testwert:
  `config --quiet` erfolgreich.
- Docker 28.0.4 / Compose 2.38.2: DNS-Ausfall bei rein internem Client
  reproduziert; mit API-Edge-Netz im tatsächlichen Compose-API-Container
  `postgres` aufgelöst und TCP-Verbindung zu Port 5432 erfolgreich.
- PostgreSQL ohne Host-Port; API-Port ausschließlich `127.0.0.1:8000`.
  Container-interne Liveness 200 und deaktivierte Readiness 503 beobachtet.
  Hostseitiger HTTP-Aufruf lief im Sandbox-Test in einen Timeout; ein
  vollständiger Host-/TLS-Proxy-Healthcheck ist damit **nicht nachgewiesen**.
- Initialer Containerbuild erfolgreich; API-/DB-Testzahlen und finaler
  Reviewstand werden nach Abschluss unten ergänzt.
- Advisory-Prüfung der direkten und beim Containerbuild aufgelösten
  transitiven Python-Abhängigkeiten: keine gemeldeten Schwachstellen.

Nicht durchgeführt: Serverzugriff, Deployment, produktive
Migrationen, mobile Builds, echte OAuth-Anmeldung, physische Android-/iOS-
Gerätetests, DNS-/TLS-Umschaltung oder Erstellung realer Zugangsdaten.
