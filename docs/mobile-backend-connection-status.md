# NIKNOLIG Mobile Backend Connection Status

**Prüfdatum:** 2026-10-21  
**Status: TEILWEISE IMPLEMENTIERT, PRODUKTIONSVERBINDUNG BLOCKIERT** – Beide
Android-Apps enthalten jetzt getrennte HTTPS-Clients für `GET /health/ready`.
Eine erfolgreiche Verbindung zu einem deployten Backend ist nicht nachgewiesen;
es wurde keine Produktionsadresse angenommen oder erfunden.

## Tatsächlicher Netzwerkpfad

| Plattform/App | Befund |
| --- | --- |
| Android NIKNOLIG (`:niknolig`) | Eigener `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Die Support-Ansicht ruft nach Nutzeraktion ausschließlich `GET /health/ready` ab. Die Assistentenanfrage bleibt lokal; E-Mail öffnet nach Bestätigung nur einen Entwurf. |
| Android NIKNOLIG Defense (`:niknolig-defense`) | Separater `BackendHealthClient`, eigene `INTERNET`-Berechtigung und eigene Build-Konfiguration. Die Support-Ansicht ruft nach Nutzeraktion ausschließlich `GET /health/ready` ab. Keine geteilten App-Clients, Credentials oder Defense-Funktionen. E-Mail öffnet nur einen Entwurf. |
| iOS | In diesem Repository gibt es keine Swift-Dateien, Xcode-Projekte/-Workspaces oder `Info.plist`. Daher sind weder ein iOS-Netzwerkpfad noch iOS-Release-Konfiguration oder eine iOS-Verbindung prüfbar bzw. implementierbar. |

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
`NIKNOLIG_DEFENSE_BACKEND_URL`. Ohne bestätigte Werte bleibt der Zustand
„nicht konfiguriert“; es wird kein Ersatzserver gewählt.

## URL-Konfiguration und vorhandene Routen

- [`backend/openapi.yaml`](../backend/openapi.yaml) enthält als Server
  `https://backend.invalid`; die Datei kennzeichnet das ausdrücklich als
  Platzhalter, nicht als deployten oder freigegebenen Endpunkt.
- [`backend/.env.example`](../backend/.env.example) setzt den lokalen
  Health-Server auf `127.0.0.1:8000`.
- [`backend/ai-support.openapi.yaml`](../backend/ai-support.openapi.yaml) nennt
  `http://127.0.0.1:8000` ausschließlich als lokales Vorbereitungsbeispiel.
- Es gibt keine Produktions-URL in den Android-Release-Konfigurationen und
  keine iOS-Release-Konfiguration in diesem Repository.
- Android NIKNOLIG nimmt `NIKNOLIG_BACKEND_URL` oder
  `-PniknoligBackendUrl=...`; Defense nimmt getrennt
  `NIKNOLIG_DEFENSE_BACKEND_URL` oder `-PniknoligDefenseBackendUrl=...`.
  Release-Aufgaben schlagen ohne eigene App-URL fehl. Nicht-HTTPS-, lokale,
  Loopback- und `.invalid`-Hosts werden abgelehnt. Debug-Builds ohne Konfiguration
  bleiben möglich und melden im UI klar, dass kein Verbindungsversuch stattfand.

| Route | Implementierung und tatsächlicher Status |
| --- | --- |
| `GET /health/live` | Lokal in `backend/app.py`; liefert `200` mit `{"status":"live"}`. |
| `GET /health/ready` | Lokal in `backend/app.py`; liefert `200` mit `{"status":"ready"}`. Prüft keine Produktabhängigkeiten. |
| `POST /v1/ai/support` | Lokale Vorbereitungsroute. Der Standardstart ist gesperrt und liefert `503 AI_DISABLED`; der Standardauthenticator weist Credentials ab. Kein produktiver Auth-Aussteller, Transport oder deployter Dienst. |
| Produkt-, Login-, Geräte-, Profil- und Pairing-Routen | Nicht implementiert bzw. nicht freigegeben; nicht vorhandene Pfade liefern lokal `404`. |

Der lokale Server bindet standardmäßig an `127.0.0.1:8000` und verwendet
`http.server` ohne TLS. [`backend/compose.yaml`](../backend/compose.yaml)
definiert nur eine lokale PostgreSQL-Entwicklungsdatenbank, keinen API-Service.
Eine produktive Serverplattform, öffentliche DNS-Adresse, TLS-Zertifikatskette
oder Deployment-Konfiguration ist hier nicht vorhanden. Deshalb gibt es keine
echte Produktions-URL, deren DNS, TLS oder Erreichbarkeit geprüft werden könnte.

## Prüfung und Aussagekraft

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
2. Ein deployter API-Dienst fehlt. Der vorhandene Python-Server verwendet
   `http.server`, bindet lokal und ist ausdrücklich nicht produktionsgeeignet;
   Compose enthält nur eine lokale Datenbank. Ein Produktionsserver,
   TLS-Terminierung, Betriebs-/Rollbackkonzept und Deploymentkonfiguration
   müssen durch den Betreiber freigegeben und bereitgestellt werden. Die Apps
   können gegen die vorhandenen Health-Routen erst nach diesem Deployment
   verbunden werden.
3. SecurityChain-P0 sowie die Produkt-/Security-Entscheidungen zu App-Bereichen,
   Identitäten, Authentifizierung, Widerruf und Datenumfang bleiben gemäß
   [`backend/README.md`](../backend/README.md) Freigabevoraussetzungen. Dieser
   Bericht ändert oder schließt keine SecurityChain-D01–D12-Anforderung ab.
4. Für iOS fehlt zusätzlich die iOS-App samt Projekt- und Release-Konfiguration;
   sie muss innerhalb der dafür zuständigen App-Quellen ergänzt und separat
   geprüft werden.
5. Erst nach Bereitstellung und Freigabe dieser Voraussetzungen können die
   Android-Health-Clients gegen den echten HTTPS-Server getestet werden. Für
   Produktfunktionen müssen später separat freigegebene API-Routen, Authentisierung
   und app-scoped Autorisierung implementiert werden; hier wird keine iOS-
   Implementierung behauptet.

Bis dahin bleibt die Produktionsverbindung **BLOCKIERT**. Die implementierten
Android-Clients können ausschließlich den Health-Endpunkt abfragen; weder
Anmeldung noch KI-, Profil-, Geräte- oder geschützte Funktionen sind verbunden
oder geprüft. Der Health-Endpunkt liefert keine Aussage über diese Funktionen.
