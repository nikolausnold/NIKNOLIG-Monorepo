# NIKNOLIG Mobile Backend Connection Status

**Prüfdatum:** 2026-10-22  
**Status: TEILWEISE IMPLEMENTIERT, PRODUKTIONSVERBINDUNG BLOCKIERT** – Beide
Android-Apps enthalten jetzt getrennte HTTPS-Clients für `GET /health/ready`.
Nachtrag 2026-10-24: `https://api.niknolig.com` ist auftragsgemäß als Standard-
Origin für die bestehenden Health-Clients und im OpenAPI-Vertrag eingetragen;
Android-App-Umgebungsvariablen und iOS-Build-Einstellungen bleiben getrennt
überschreibbar. Eine erfolgreiche Verbindung zu einem deployten Backend,
DNS-/TLS-Zuordnung oder Produkt-API ist nicht nachgewiesen.

## Tatsächlicher Netzwerkpfad

| Plattform/App | Befund |
| --- | --- |
| Android NIKNOLIG (`:niknolig`) | Eigener `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Standard-Origin `https://api.niknolig.com`, überschreibbar über `NIKNOLIG_BACKEND_URL` oder Gradle-Property. Die Support-Ansicht ruft nach Nutzeraktion ausschließlich `GET /health/ready` ab. |
| Android NIKNOLIG Defense (`:niknolig-defense`) | Separater `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Dieselbe Standard-Origin, separat überschreibbar über `NIKNOLIG_DEFENSE_BACKEND_URL` oder Gradle-Property. Keine geteilten App-Clients, Credentials oder Defense-Funktionen. |
| iOS NIKNOLIG und Defense | Zwei native Targets in `apps/ios/NIKNOLIG.xcodeproj` enthalten getrennte Health-Clients und getrennte Build-Einstellungen mit derselben Standard-Origin. Der Check läuft nur nach Nutzeraktion, akzeptiert nur HTTPS ohne Redirect und sendet keine Credentials oder Nutzdaten. Xcode-Build, Simulator-, Geräte- oder echter Servertest wurden nicht ausgeführt. |

Die Android-Clients verwenden `HttpsURLConnection` mit System-Zertifikatsprüfung,
ohne Redirects, mit 5-Sekunden-Verbindungs-/Lese-Timeout, begrenzter JSON-Antwort,
Health-Vertragsprüfung und typisierten Statusfehlern. Sie protokollieren weder
URL, Antwortinhalt noch Exceptions und senden keine Credentials oder Nutzdaten.
Für Health-Checks wird keine Authentifizierung benötigt; dies implementiert
keinen Login oder Zugriff auf geschützte Funktionen.

Beide Manifeste verbieten Klartextverkehr ausdrücklich. Die Verbindung kann
nach Fehlern oder Netzwerkwechsel erneut geprüft werden; während einer Anfrage
ist die Prüftaste deaktiviert. Die getrennten Variablen
`NIKNOLIG_BACKEND_URL` und `NIKNOLIG_DEFENSE_BACKEND_URL` überschreiben den
Standard-Origin für app-spezifische Umgebungen. Es wird kein anderer
Ersatzserver gewählt.

## URL-Konfiguration und vorhandene Routen

- [`backend/openapi.yaml`](../backend/openapi.yaml) ist der Health-Vertrag,
  kein Nachweis für einen deployten oder freigegebenen Produktionsserver.
- [`backend/.env.example`](../backend/.env.example) setzt den lokalen
  Health-Server auf `127.0.0.1:8000`.
- [`backend/ai-support.openapi.yaml`](../backend/ai-support.openapi.yaml) nennt
  `http://127.0.0.1:8000` ausschließlich als lokales Vorbereitungsbeispiel.
- Die Standard-Origin ist auftragsgemäß `https://api.niknolig.com`; dies belegt
  weder DNS-/TLS-Erreichbarkeit noch einen deployten oder freigegebenen
  Produktdienst.
- Android NIKNOLIG nimmt `NIKNOLIG_BACKEND_URL` oder
  `-PniknoligBackendUrl=...`; Defense nimmt getrennt
  `NIKNOLIG_DEFENSE_BACKEND_URL` oder `-PniknoligDefenseBackendUrl=...`.
  Release-Aufgaben verwenden standardmäßig die offizielle Origin und erlauben
  getrennte Overrides. Nicht-HTTPS-, lokale, Loopback- und `.invalid`-Hosts
  werden abgelehnt.
  Manuelle und automatische Android-Releases verwenden dieselbe URL-Prüfung,
  bevor Signiergeheimnisse bereitgestellt oder Release-Artefakte gebaut werden.

### Android-Release-URLs in GitHub konfigurieren

Die aktuellen Repository-/Environment-Variablen können in diesem Arbeitslauf
nicht über die verfügbaren GitHub-Schnittstellen ausgelesen werden. Der letzte
fehlgeschlagene Release-Lauf protokollierte beide Werte leer; ihr jetziger
Konfigurationsstand ist damit nicht bestätigt. Es wurde keine Produktions-URL
angenommen oder ergänzt.

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
| `GET /health/ready` | Lokal in `backend/app.py`; liefert `200` mit `{"status":"ready"}`. Prüft keine Produktabhängigkeiten. |
| `GET /health/live`, `GET /health/ready` in Produktion | `backend/asgi.py`: FastAPI-Liveness und echte PostgreSQL-/Betriebsschema-Prüfung. Readiness liefert bei fehlender Konfiguration, Datenbank oder passender Migration `503 SERVICE_UNAVAILABLE`, nicht `ready`. |
| `POST /support` | Gemeinsame lokale Vorbereitungsroute mit exakt `app` und `message` (maximal 2.048 UTF-8-Bytes); verwendet die bestehende Authentifizierung, App-Scope-Prüfung und Limits. Der Standardstart ist gesperrt und liefert `503 AI_DISABLED`. Nicht im Produktions-ASGI registriert; kein produktiver Auth-Aussteller, Provider-Transport oder deployter Dienst. |
| `POST /v1/ai/support` | Lokale Kompatibilitätsroute mit bisherigem Request-Format; bleibt unverändert gesperrt und nutzt denselben Support-Service. |
| Produkt-, Login-, Geräte-, Profil- und Pairing-Routen | Nicht implementiert bzw. nicht freigegeben; nicht vorhandene Pfade liefern lokal `404`. |

Der unveränderte lokale Vorbereitungsserver verwendet `http.server` ohne TLS;
`backend/compose.yaml` bleibt ausschließlich für lokale Datenbankentwicklung.
Der zusätzliche Produktionsweg in `backend/compose.production.yaml` umfasst
FastAPI, PostgreSQL, eine separate Betriebs-Migration und TLS-Terminierung.
Die vorgeschlagene Geräte-/Pairing-Migration `001_initial_contract.sql` wird
nicht automatisch ausgeführt. Deployment-Anleitung und Betriebsgrenzen stehen
in [`backend/README.md`](../backend/README.md).

**Separater HTTPS-Nachweis: NICHT ERBRACHT.** Eine bestätigte Serveradresse,
Serverzugang und verwaltete TLS-Zertifikate wurden nicht bereitgestellt. Weder
ein lokaler HTTP-Test noch ein Containerstart oder Build gilt als Ersatz.
Es wurde kein fremder Host als Produktionsziel angenommen oder kontaktiert.

## Prüfung und Aussagekraft

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

1. Der Serverbetreiber muss für jede App eine kanonische, freigegebene
   Produktions-HTTPS-Basis-URL,
   verwaltetes DNS, gültige TLS-Zertifikatskette und einen erreichbaren
   Test-/Staging-Endpunkt bereitstellen. Die Release-Builds bleiben ohne diese
   konkreten app-scoped URLs absichtlich gesperrt.
2. Ein deployter API-Dienst fehlt weiterhin; die zuvor fehlende technische
   Deployment-Konfiguration ist jetzt implementiert. Der Betreiber muss einen
   freigegebenen Docker-Compose-Server, DNS, Zertifikatskette samt privatem
   Schlüssel, getrennte Datenbank-Secrets und Serverzugang bereitstellen.
   Es werden keine kostenpflichtigen Ressourcen erstellt. Erst nach Deployment
   und externer HTTPS-Prüfung können die bestehenden Android-Clients die echten
   Health-Routen nachweisbar erreichen.
3. SecurityChain-P0 sowie die Produkt-/Security-Entscheidungen zu App-Bereichen,
   Identitäten, Authentifizierung, Widerruf und Datenumfang bleiben gemäß
   [`backend/README.md`](../backend/README.md) Freigabevoraussetzungen. Dieser
   Bericht ändert oder schließt keine SecurityChain-D01–D12-Anforderung ab.
4. Für iOS müssen die neuen Targets auf macOS/Xcode gebaut und auf Simulator
   und Geräten getestet werden. Apple-Team, endgültige Plattformmatrix,
   Signierung, Datenschutzangaben und Storefreigabe sind nicht vorhanden.
5. Erst nach Bereitstellung und Freigabe dieser Voraussetzungen können die
   Android-Health-Clients gegen den echten HTTPS-Server getestet werden. Für
   Produktfunktionen müssen später separat freigegebene API-Routen, Authentisierung
   und app-scoped Autorisierung implementiert werden; die iOS-Targets enthalten
   ausschließlich nicht-sensitive Health-/Vorschauflüsse, keine Produkt-API.

Bis dahin bleibt die Produktionsverbindung **BLOCKIERT**. Die implementierten
Android- und iOS-Clients können ausschließlich den Health-Endpunkt abfragen; weder
Anmeldung noch KI-, Profil-, Geräte- oder geschützte Funktionen sind verbunden
oder geprüft. Der Health-Endpunkt liefert keine Aussage über diese Funktionen.
