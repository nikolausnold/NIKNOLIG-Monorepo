# NIKNOLIG Mobile Backend Connection Status

**Prüfdatum:** 2026-10-25
**Status: API-KONFIGURATION VERBUNDEN, PRODUKTFUNKTIONEN NICHT FREIGEGEBEN.**
Die vier App-Konfigurationen verwenden standardmäßig die vom Betreiber genannte
bestehende API `https://api.niknolig.com`, mit getrennten Overrides je Produkt.
Die Health-Clients rufen nur `GET /health/ready` ab. Die Websites bleiben
`https://niknolig.com/` und `https://defense.niknolig.com/`.
Ein öffentlicher HTTPS-Versuch aus dieser Umgebung scheiterte an DNS
(`curl: (6) Could not resolve host`). Ein aktueller Live-Funktionsnachweis ist
deshalb nicht erbracht; die vom Betreiber gemeldeten Healthchecks sind keine
hier wiederholten Messungen. Es wurde kein Ersatzbackend eingerichtet oder
Produktivserver verändert.

## Tatsächlicher Netzwerkpfad

| Plattform/App | Befund |
| --- | --- |
| Android NIKNOLIG (`:niknolig`) | Eigener `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Die Support-Ansicht ruft nach Nutzeraktion ausschließlich `GET /health/ready` ab. Die Assistentenanfrage bleibt lokal; E-Mail öffnet nach Bestätigung nur einen Entwurf. |
| Android NIKNOLIG Defense (`:niknolig-defense`) | Separater `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Die Support-Ansicht ruft nach Nutzeraktion ausschließlich `GET /health/ready` ab. Keine geteilten App-Clients, Credentials oder Defense-Funktionen. E-Mail öffnet nur einen Entwurf. |
| iOS NIKNOLIG und Defense | Zwei native Targets in `apps/ios/NIKNOLIG.xcodeproj` enthalten getrennte Health-Clients und je eine eigene Build-URL-Einstellung mit der bestehenden API als Standard. Der Check läuft nur nach Nutzeraktion, akzeptiert nur HTTPS ohne Redirect und sendet keine Credentials oder Nutzdaten. Die frühere Basisrevision `44aac38` wurde in CI für beide Targets in Debug/Release für den Simulator gebaut; die neue Konfiguration ist damit noch nicht nativ gebaut oder auf einem Gerät getestet. |

Die Android-Clients verwenden `HttpsURLConnection` mit System-Zertifikatsprüfung,
ohne Redirects, mit 5-Sekunden-Verbindungs-/Lese-Timeout, begrenzter JSON-Antwort,
Health-Vertragsprüfung und typisierten Statusfehlern. Sie protokollieren weder
URL, Antwortinhalt noch Exceptions und senden keine Credentials oder Nutzdaten.
Für Health-Checks wird keine Authentifizierung benötigt; dies implementiert
keinen Login oder Zugriff auf geschützte Funktionen.

Beide Manifeste verbieten Klartextverkehr ausdrücklich. Die Verbindung kann
nach Fehlern oder Netzwerkwechsel erneut geprüft werden; während einer Anfrage
ist die Prüftaste deaktiviert. Debug-CI übernimmt jetzt wie Release-CI die
getrennten Repository-Variablen `NIKNOLIG_BACKEND_URL` und
`NIKNOLIG_DEFENSE_BACKEND_URL`. Ohne nichtleeren Override gilt die bestehende
API als Standard; es wird kein Ersatzserver gewählt. Die gemeinsamen Origins
teilen weder App-Daten noch Credentials oder Autorisierung.

## URL-Konfiguration und vorhandene Routen

- [`backend/openapi.yaml`](../backend/openapi.yaml) ist der Health-Vertrag,
  kein Nachweis für einen deployten oder freigegebenen Produktionsserver.
- [`backend/.env.example`](../backend/.env.example) setzt den lokalen
  Health-Server auf `127.0.0.1:8000`.
- [`backend/ai-support.openapi.yaml`](../backend/ai-support.openapi.yaml) nennt
  `http://127.0.0.1:8000` ausschließlich als lokales Vorbereitungsbeispiel.
- Die vom Betreiber vorgegebene Produktions-API ist `https://api.niknolig.com`.
  Beide Produkte verwenden sie unabhängig voneinander als Konfigurationsstandard.
- Android NIKNOLIG nimmt `NIKNOLIG_BACKEND_URL` oder
  `-PniknoligBackendUrl=...`; Defense nimmt getrennt
  `NIKNOLIG_DEFENSE_BACKEND_URL` oder `-PniknoligDefenseBackendUrl=...`.
  Nichtleere Overrides werden weiterhin validiert. Nicht-HTTPS-, lokale,
  Loopback- und `.invalid`-Hosts werden abgelehnt. Eine eigene leere
  iOS-Release-Einstellung bleibt unzulässig; Android nutzt bei fehlendem oder
  leerem Override die vorgegebene API.
  Manuelle und automatische Android-Releases verwenden dieselbe URL-Prüfung,
  bevor Signiergeheimnisse bereitgestellt oder Release-Artefakte gebaut werden.

### Android-Release-URLs in GitHub konfigurieren

Die aktuellen Repository-/Environment-Variablen können in diesem Arbeitslauf
nicht über die verfügbaren GitHub-Schnittstellen ausgelesen werden. Der letzte
fehlgeschlagene Release-Lauf protokollierte beide Werte leer; ihr jetziger
Konfigurationsstand ist damit nicht bestätigt. Die hier vorgegebene API-Origin ersetzt nicht die unveränderten
Environment-/Signierfreigaben des Release-Workflows.

1. Ein Repository-Administrator öffnet
   [Settings → Environments](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/environments)
   und wählt das Environment `android-release` (oder legt es exakt so an).
2. Unter **Environment variables** werden zwei getrennte Variablen eingetragen:
   `NIKNOLIG_BACKEND_URL` für NIKNOLIG und
   `NIKNOLIG_DEFENSE_BACKEND_URL` für NIKNOLIG Defense. Beide Werte müssen
   jeweils die vom zuständigen Betreiber ausdrücklich für Produktion
   freigegebene HTTPS-Origin sein. Keine Beispiel-, lokale oder erfundene
   Adresse eintragen; die URLs sind keine Secrets.
3. Unter **Deployment protection rules** wird mindestens ein erforderlicher
   Reviewer festgelegt. Der Reviewer bestätigt vor Freigabe des Environment-
   Deployments, dass beide eingetragenen Origins für Produktion freigegeben
   sind. Das Workflow-Environment `android-release` erzwingt diese Schutzregel
   für manuelle und automatische Release-Ausführungen.
4. Danach prüft der Release-Workflow beide Werte vor der Prüfung der Build-
   Nachweise, vor dem Zugriff auf Signiergeheimnisse und vor dem Release-Build.
   Fehlende Werte erhalten eine konkrete GitHub-Fehlermeldung; ungültige
   HTTPS-Origins, Credentials, Pfade, Query-/Fragmentbestandteile sowie
   Loopback- und `.invalid`-Hosts werden durch die Gradle-Validierung abgelehnt.

Ohne die beiden vom Betreiber bereitgestellten und vom Environment-Reviewer
bestätigten Werte bleiben signierte Releases blockiert. Die Prüfung bestätigt
URL-Format und Freigabeprozess, aber weder DNS/TLS-Erreichbarkeit noch einen
deployten Produktionsdienst. Debug-Builds bleiben von dieser Release-Prüfung
unabhängig.

| Route | Implementierung und tatsächlicher Status |
| --- | --- |
| `GET /health/live` | Lokal in `backend/app.py`; liefert `200` mit `{"status":"live"}`. |
| `GET /health/ready` | Beide Laufzeiten verwenden die echte PostgreSQL-/Migrations- und Least-Privilege-Prüfung; ohne passende Datenbankkonfiguration HTTP 503. Prüft keine Produktabhängigkeiten. |
| `GET /health/live`, `GET /health/ready` in Produktion | `backend/asgi.py`: FastAPI-Liveness und echte PostgreSQL-/Betriebsschema-Prüfung. Readiness liefert bei fehlender Konfiguration, Datenbank oder passender Migration `503 SERVICE_UNAVAILABLE`, nicht `ready`. |
| `GET /health`, `GET /projects`, `GET /db/health` | Bestehende ASGI-Kompatibilitätsrouten; jetzt in OpenAPI dokumentiert und von Caddy mit exakten GET-Matchern an `api:8000` geleitet. Katalog = statische Metadaten; DB-Prüfung = echte begrenzte `SELECT 1`-Abfrage, nicht Readiness. |
| `GET /projects/{name}/health` | Vom Betreiber als live gemeldet; nicht im Repository implementiert. Upstream-Ziele/Konfigurationsvertrag fehlen hier. Kein Ersatz durch Scheinerfolg oder beliebigen Proxy. |
| `POST /support` | In lokaler Laufzeit und ASGI registriert, über Caddy erreichbar. Exakt `app` und `message` (maximal 2.048 UTF-8-Bytes); App-Scope-Prüfung und Limits. Standardstart bleibt `503 AI_DISABLED`; kein produktiver Auth-Aussteller oder aktivierter Anbieter. |
| `POST /v1/ai/support` | In beiden Laufzeiten registrierte, gesperrte Kompatibilitätsroute mit bisherigem Request-Format und demselben Support-Service. |
| Produkt-, Login-, Geräte-, Profil- und Pairing-Routen | Nicht implementiert bzw. nicht freigegeben; nicht vorhandene Pfade liefern lokal `404`. |

Der unveränderte lokale Vorbereitungsserver verwendet `http.server` ohne TLS;
`backend/compose.yaml` bleibt ausschließlich für lokale Datenbankentwicklung.
Der zusätzliche Produktionsweg in `backend/compose.production.yaml` umfasst
FastAPI, PostgreSQL, eine separate Betriebs-Migration und TLS-Terminierung.
Die vorgeschlagene Geräte-/Pairing-Migration `001_initial_contract.sql` wird
nicht automatisch ausgeführt. Deployment-Anleitung und Betriebsgrenzen stehen
in [`backend/README.md`](../backend/README.md).

**Separater Live-HTTPS-Nachweis: NICHT ERBRACHT.** Die bestehende Serveradresse
ist vorgegeben, aber aus dieser Umgebung nicht per DNS auflösbar. Serverzugang
und Produktions-Upstream-Konfiguration liegen hier nicht vor. Weder lokale
HTTP-/Datenbanktests noch Containerstarts oder Builds gelten als Live-Nachweis.

## Prüfung und Aussagekraft

### Integrationsprüfung 25.10.2026

Repository-Wurzel für die folgenden Befehle:
`/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo`.
Die Runtime-Abhängigkeiten wurden unverändert aus `backend/requirements.txt`
in `/tmp/niknolig-validation-venv` installiert; keine neuen Projektabhängigkeiten.

- `PYTHONDONTWRITEBYTECODE=1 BACKEND_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:54329/ci_backend_test PGPASSWORD=ci-only-disposable /tmp/niknolig-validation-venv/bin/python -m unittest discover -s backend/tests`:
  **186 Tests, kein Fehler**. Die Instanz war ein isolierter, anschließend
  entfernter PostgreSQL-17.9-Testcontainer mit dem bestehenden CI-Image-Digest,
  keine Betriebsdatenbank. Enthalten sind Migration/Checksumme/Rollback,
  Least-Privilege-/Read-only-Prüfungen, Datenbankausfall und HTTP-Tests.
  Ein optionaler JSON-Schema-Test wurde in der isolierten Python-Umgebung
  übersprungen und anschließend mit dem bereits installierten System-`jsonschema`
  gezielt ausgeführt:
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest backend.tests.test_contracts.BackendContractTests.test_schemas_accept_valid_contracts_and_reject_negative_cases`
  – **bestanden**, einschließlich negativer Fälle.
- `PYTHONDONTWRITEBYTECODE=1 /tmp/niknolig-validation-venv/bin/python -m unittest tools.tests.test_evolution_engine`:
  **11 Tests bestanden**; bestehende Evidence-Zeilen bleiben gültig.
- `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` im
  unverändert gepinnten Caddy-2.10.2-Container: **Valid configuration**.
  Verwendet wurden ausschließlich kurzlebige lokale Testzertifikate.
- Zusätzlich realer lokaler HTTPS-Pfad: Caddy mit dem Repository-Caddyfile →
  `asgi:app` → PostgreSQL mit der migrierten `backend_health`-Rolle.
  `/health/live`, `/health/ready`, `/health`, `/projects` und `/db/health`
  lieferten **HTTP 200**, einschließlich echter Datenbankabfrage.
  Die ersten beiden Abrufe unmittelbar beim Proxy-Start scheiterten transient
  beim TLS-Verbindungsaufbau; die gezielte Wiederholung nach Start war erfolgreich.
  `POST /support` blieb für beide App-Bereiche **HTTP 503 / AI_DISABLED**;
  `POST /projects` und `/projects/niknolig/health` blieben **HTTP 404**.
  Testdienste wurden danach beendet. Kein Live-/Produktivnachweis.
- Tooling: Die vorhandenen **70 Bestandstests** liefen erfolgreich innerhalb
  der zwischenzeitlichen 78-Test-Suite; die anschließend konsolidierten,
  korrigierten Regressionstests liefen separat mit
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.tests.test_backend_defaults -v`
  – **2 Tests bestanden**. Sie prüfen die Android-Override-/Leerwert-Reihenfolge
  und extrahieren beide echten iOS-Debug-/Release-Einstellungen; jede Einstellung
  wird durch den bestehenden iOS-Validator geprüft.
- `swift test --package-path modules/electro-engel/ios` und
  `swift test --package-path modules/support/ios`: **8 + 9 Tests bestanden**.
  Das sind portable Coretests unter Linux, keine iOS-Simulator-/Gerätetests.
  Generierte Änderungen an bereits versionierten Swift-Buildartefakten wurden
  zurückgesetzt; keine Buildausgaben gehören zum Änderungsumfang.
- Android-Versuch:
  `./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug -x test`.
  Bereits die Root-Konfiguration scheiterte an der Auflösung von
  `com.android.application:9.4.1` aus den konfigurierten Plugin-Repositories.
  Damit sind lokale APK-Builds, JVM-App-/Coretests und Lint auf dem neuen Stand
  **nicht nachgewiesen**. Die unveränderten Versionen wurden nicht willkürlich
  ersetzt. Ein konkreter DNS- oder Versionsfehler ist aus dieser Gradle-Meldung
  allein nicht ableitbar.
- Native iOS-Compilation und interaktive Simulatorprüfungen der neuen
  Konfiguration: **nicht ausgeführt**, da macOS/Xcode hier fehlen.

Vorhandene, erfolgreiche CI-Nachweise der **Basisrevision `44aac38`**, nicht
der neuen Änderungen:
[Android-Builds, Clienttests, Coretests und Lint beider Apps](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/40171571761)
und [iOS-Debug-/Release-Simulator-Compilation beider Targets](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/40171568252).
Sie wurden geprüft und nicht erneut gestartet. Das ist keine Aussage über
signierte Releases, Gerätebetrieb oder die neue Produktionskonfiguration.

Die Authentifizierungs-/Autorisierungsnachweise stammen aus den vorhandenen
negativen Service-/HTTP-Tests: Standard-Authenticator verweigert Zugriff,
falscher App-Bereich/fehlende Berechtigungen werden abgelehnt, Auditfehler
verhindern Anbieteraufrufe. Das beweist die Sperren, **keinen produktiven Login**.
D-02 (IdP, Rollen, MFA, Tokenvertrag), D-03–D-06 (Gerätevertrauen,
Schlüsselprotokoll, Sitzungen/Widerruf), D-09/D-10 (Einwilligung und dauerhafte
Auditablage) sowie D-11/D-12 (Betriebs- und unabhängige Abnahme) enthalten hier
weiterhin keine ausreichend konkrete genehmigte Implementierungsentscheidung.
Es wurden deshalb keine Krypto-/Identitätsverfahren erfunden und keine
Produkt-/Gerätemigrationen freigeschaltet.

Die folgenden Abschnitte zu PR #118 und `837c404` sind historische Nachweise,
nicht die Testergebnisse dieser Revision.

### PR #118: erneute Ausführungsprüfung

Die PR-Workflows [Android #765](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39586752214)
und [Backend #110](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39586752108)
haben `action_required`, nicht einen ausgeführten Buildfehler. Die Actions-API
meldet jeweils **null Jobs**; deshalb existieren dort noch keine Test-/Buildlogs.
Eine Betreiberfreigabe ist erforderlich, bevor diese Checks Nachweise liefern.

Die lokale Diagnose grenzt den Android-Fehler auf den Repositoryzugriff ein:

```sh
curl --head --location --max-time 20 \
  https://maven.google.com/com/android/tools/build/gradle/8.11.1/gradle-8.11.1.pom
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug \
  :niknolig:testDebugUnitTest :niknolig-defense:testDebugUnitTest --no-daemon --info
```

Der offizielle Google-Maven-Endpunkt antwortet mit `301` auf
`https://dl.google.com/dl/android/maven2/...`; der Zielhost ist in der
Agent-Umgebung nicht auflösbar (`curl: (6) Could not resolve host: dl.google.com`).
Maven Central liefert für Kotlin `2.2.21` dagegen HTTP `200`, die
Gradle-Distribution `8.14.6` ist über ihre offizielle Downloadkette erreichbar.
Der frühere main-Build #762 hatte AGP bereits aufgelöst und erreichte die
Modulskript-Kompilierung. Zusätzlich bestätigt der erfolgreiche
[main-Build #761](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39581246830)
auf `3b60d62` beide Debug-APKs samt Paket-/Signaturprüfung mit genau AGP
`8.11.1`, Kotlin `2.2.21` und Gradle `8.14.6`. Das belegt die Verfügbarkeit
dieser Versionen, **nicht** einen erfolgreichen Build des aktuellen PR-Stands.
Deshalb ist kein Versionswechsel als vermeintliche
Behebung dieses Zugriffsfehlers vorgenommen worden. Keine fremden Mirrors,
DNS-/Firewall-Umgehungen oder abgeschwächte TLS-Prüfungen werden eingeführt.
Die Freigabe von Google Maven beziehungsweise ein freigegebener CI-Lauf bleibt
für Android-Nachweise erforderlich; dies ist unabhängig vom Produktionsserver.

Der erneute kombinierte Build-/Unit-Test-Aufruf endete nach 28 Sekunden mit
dem nicht auflösbaren AGP-Plugin, bevor eine App kompiliert wurde. Die CI
archiviert jetzt vorhandene JUnit-XML-/HTML-Berichte beider Health-Clients mit
Commit-SHA für sieben Tage, auch bei Testfehlern. Fehlende Berichte werden
nicht als bestandene Tests gewertet. Die aktualisierte Tooling-Suite besteht
mit **48 Tests**; daraus folgt kein bestandener Android-Build.

**Externe Produktionsbereitstellung:** Ein vom Betreiber bestätigtes,
zugängliches Serverziel einschließlich Domain, DNS und vertrauenswürdiger
TLS-Konfiguration wurde weiterhin nicht bereitgestellt. Ohne dieses konkrete
Ziel sind DNS-, Zertifikats-, HTTPS-Health- und echte Android-Server-Prüfungen
nicht ausführbar. Der vorhandene Deploymentweg wird weiterverwendet; eine
zusätzliche Implementierung oder eine erfundene Serveradresse ersetzt diese
Voraussetzung nicht.

### PR #118: behobene Backend-Review-Befunde

- Beide inline definierten Primärschlüssel des vorgeschlagenen Produktschemas
  werden nach dessen separat freigegebener Anwendung ebenfalls geprüft.
- Katalogprüfungen vergleichen Tabellenzuordnung, Typ und Definition der
  Constraints sowie Tabellenzuordnung, Eindeutigkeit, Spalten und Prädikat der
  Indizes. Gleichnamige `CHECK (true)`-/Index-Ersatzobjekte bestehen nicht mehr.
- Die Health-Rolle darf nicht das effektive libpq-Migratorpasswort verwenden,
  auch nicht bei Konfiguration über `DATABASE_URL` oder `PGPASSWORD`.
- Bereits vorhandene überprivilegierte Health-Rollen werden bei unerwarteten
  Rechten, Eigentum oder Rollenmitgliedschaften abgelehnt, nicht stillschweigend
  zu einer vermeintlich schreibgeschützten Rolle erklärt.
- Die asynchrone Readiness besitzt eine clientseitige Gesamtfrist von vier
  Sekunden. Eine nach Verbindungsaufbau nicht mehr antwortende Datenbank führt
  zu `503`; die lokale Verbindung wird vor der Aufgabenstornierung geschlossen.
  Die Liveness bleibt unabhängig ausführbar.

**Neue Nachweise:** 108 Backend-Tests gegen PostgreSQL 17.9 bestanden;
zusätzlich 34 Laufzeit-/Datenbanktests gegen PostgreSQL 16.15 bestanden.
Enthalten sind echte blockierte, bereits aufgebaute Datenbankverbindungen,
gleichzeitige Liveness sowie Primärschlüssel-, Definitions-, Index-,
Passwortquellen- und überprivilegierte Rollenregressionen. Diese lokalen
Prüfungen belegen weiterhin keine öffentliche HTTPS-Produktionsverbindung.
Die zuvor genannten 95 Tests sind die ältere Prüfung vor diesen Review-Fixes.
Die abschließende zusätzliche Passwortregression weist auch einen nicht
verfügbaren effektiven Migratorpasswort-Nachweis vor jeder Rollenänderung zurück.

Die gezielten Android-Client-Unit-Tests verwenden simulierte HTTPS-Verbindungen
und prüfen Pfad, HTTPS-Vorgabe, Timeouts, Redirect-Ablehnung und Fehlerantworten.
Sie belegen keine echte TLS-Verbindung. `python3 -m unittest discover -s
backend/tests` prüft den Backendvertrag und startet für Health-Tests einen
temporären lokalen HTTP-Server; ein bestandener Test ist weder HTTPS- noch
Deploymentnachweis. Der gezielte gemeinsame Aufruf der beiden Android-Debug-
Builds und Unit-Tests in dieser Umgebung scheiterte vor der Projektkonfiguration:
Android-Gradle-Plugin 8.11.1 wurde aus Google/Maven/Plugin Portal nicht aufgelöst.
Deshalb wird hier kein erfolgreicher Android-Build oder APK behauptet. Die
CI führt die vorhandenen Client-Unit-Tests nun ausdrücklich zusätzlich aus.
Für iOS wurde kein Build durchgeführt.

Aktuelle Backend-Prüfung: **95 Tests bestanden**, einschließlich echter,
isolierter PostgreSQL-Integration für Migrationen, Rollback, Drift und
eingeschränkte Datenbankrechte. Docker-Image-Build, Compose- und Caddy-
Konfiguration sowie HTTP-Readiness-Ausfall/Wiederherstellung im Container
wurden geprüft. Die **47 Tooling-Regressionstests** bestehen ebenfalls.
Das sind lokale Backend-Nachweise, keine öffentliche HTTPS- oder
SecurityChain-Freigabe. Die Android-Client-Tests für Redirects, `503`,
Antwortgrößen, Timeout und TLS-Fehler sind ergänzt, aber lokal wegen der
genannten AGP-Auflösung nicht ausgeführt.

### Tatsächliche CI-Fehler auf dem gemergten Stand `837c404`

- [Android #762](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39584444860):
  `java.net.URI` und `java.net.InetAddress` wurden in beiden Gradle-Kotlin-Skripten
  vom `java`-DSL-Namen überschattet (`Unresolved reference: net` und Folgefehler).
  Explizite Imports beheben diese Ursache; Release-URL-Prüfungen bleiben bestehen.
- [Backend/Tooling #107](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39584444630):
  sechs veraltete Support-Assertions erwarteten keine Netzwerkberechtigung,
  den alten `aiUnavailable`-Zustand und alte Texte. Vier Evolution-Testfehler
  entstanden durch verschobene README-Belegzeilen. Die Tests prüfen jetzt
  ausschließlich INTERNET, Klartextverbot, echte Health-Abfrage, weiter gesperrte
  KI und bestätigte E-Mail-Entwürfe; die Belege sind aktualisiert.
  Der anschließend fehlende Systemreport war ein Folgefehler des vorzeitig
  abgebrochenen Jobs, keine fehlgeschlagene Serverprüfung.
- Die automatisch nachfolgenden Release-Läufe wurden wegen der fehlgeschlagenen
  Voraussetzungen übersprungen. Signierung oder Sicherheitsfreigaben wurden
  nicht umgangen.

## Konkrete Blocker und nächste Voraussetzungen

1. Live-DNS/TLS und die tatsächlichen API-Antworten müssen aus einer Umgebung
   mit Zugriff auf `https://api.niknolig.com` geprüft werden. Die vorgegebene
   Origin ist implementiert; deren Erreichbarkeit ist hier nicht nachgewiesen.
2. Das bestehende Hetzner-Backend wird nicht ersetzt. Zum Abgleich der
   Repository-Konfiguration mit dem laufenden `backend-nold-api-1` fehlen
   die bestätigte Image-/Commit-Identität und die nicht geheimen
   Projekt-Upstream-Verträge. Deshalb kein Servereingriff, keine Migration in
   Produktion und kein neuer `/projects/{name}/health`-Scheinerfolg.
3. SecurityChain-P0 sowie die Produkt-/Security-Entscheidungen zu App-Bereichen,
   Identitäten, Authentifizierung, Widerruf und Datenumfang bleiben gemäß
   [`backend/README.md`](../backend/README.md) Freigabevoraussetzungen. Dieser
   Bericht ändert oder schließt keine SecurityChain-D01–D12-Anforderung ab.
4. Für die geänderte iOS-Konfiguration fehlen hier macOS/Xcode und ein
   Simulator; die Basisrevision hat erfolgreiche CI-Simulator-Compilations.
   Interaktive Simulator-/Gerätetests, Apple-Team, endgültige Plattformmatrix,
   Signierung, Datenschutzangaben und Storefreigabe sind nicht vorhanden.
5. Erst nach Bereitstellung und Freigabe dieser Voraussetzungen können die
   Android-Health-Clients gegen den echten HTTPS-Server getestet werden. Für
   Produktfunktionen müssen später separat freigegebene API-Routen, Authentisierung
   und app-scoped Autorisierung implementiert werden; die iOS-Targets enthalten
   ausschließlich nicht-sensitive Health-/Vorschauflüsse, keine Produkt-API.

Bis dahin bleibt der Live-Funktionsnachweis **OFFEN**. Die implementierten
Android- und iOS-Clients können ausschließlich den Health-Endpunkt abfragen; weder
Anmeldung noch KI-, Profil-, Geräte- oder geschützte Funktionen sind verbunden
oder geprüft. Der Health-Endpunkt liefert keine Aussage über diese Funktionen.
