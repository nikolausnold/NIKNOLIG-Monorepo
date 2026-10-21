# NIKNOLIG Mobile Backend Connection Status

**Prüfdatum:** 2026-10-21  
**Ergebnis: BLOCKIERT** – Eine Verbindung beider Apps zu einem deployten Backend
über HTTPS ist nicht nachgewiesen und mit der vorliegenden Konfiguration nicht
möglich. Es wurde keine Produktionsadresse angenommen oder erfunden.

## Tatsächlicher Netzwerkpfad

| Plattform/App | Befund |
| --- | --- |
| Android NIKNOLIG (`:niknolig`) | Kein API-Client, keine Backend-Basis-URL und keine `INTERNET`-Berechtigung. Die Assistentenanfrage wird lokal angezeigt; die Support-Prüfung markiert den KI-Dienst lokal als nicht verfügbar. Die E-Mail-Funktion öffnet nach Nutzerbestätigung einen E-Mail-Entwurf (`ACTION_SENDTO`), sie sendet keine App-Anfrage an ein Backend. |
| Android NIKNOLIG Defense (`:niknolig-defense`) | Kein API-Client, keine Backend-Basis-URL und keine `INTERNET`-Berechtigung. Der Support-Ablauf ist lokal; eine bestätigte E-Mail-Aktion öffnet einen Entwurf und ist kein Backend-Aufruf. |
| iOS | In diesem Repository gibt es keine Swift-Dateien, Xcode-Projekte/-Workspaces oder `Info.plist`. Daher sind weder ein iOS-Netzwerkpfad noch iOS-Release-Konfiguration oder eine iOS-Verbindung prüfbar bzw. implementierbar. |

Beide Android-Release-Buildskripte konfigurieren Paketkennung und optionales
Signing, aber keine URL oder Netzwerkvariante. Für keine Plattform sind ein
Backend-Transport, TLS-Vertrauen, Authentifizierung, Client-Timeouts oder
Netzwerkfehlerbehandlung konfiguriert. Die Apps stellen derzeit keine Verbindung
her.

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

`python3 -m unittest discover -s backend/tests` **bestanden** (73 Tests). Die
Health-Servertests starten einen temporären lokalen HTTP-Server; sie prüfen
Vertrags- und lokale Laufzeitfunktionen, nicht HTTPS, ein Deployment, Android,
iOS oder ein physisches Gerät. Es wurde kein Android-/iOS-Build durchgeführt.
Ein erfolgreicher lokaler Test ist kein Build- und kein Verbindungsnachweis.

## Konkrete Blocker und nächste Voraussetzungen

1. Der Serverbetreiber muss eine kanonische, freigegebene HTTPS-Basis-URL,
   verwaltetes DNS, gültige TLS-Zertifikatskette und einen erreichbaren
   Test-/Staging-Endpunkt bereitstellen.
2. Für diese Adresse fehlt ein deployter API-Dienst. Vor einer App-Integration
   müssen die freigegebenen Routen und Fehlerverträge implementiert, der Dienst
   sicher betrieben und seine HTTPS-Erreichbarkeit nachgewiesen werden.
3. SecurityChain-P0 sowie die Produkt-/Security-Entscheidungen zu App-Bereichen,
   Identitäten, Authentifizierung, Widerruf und Datenumfang bleiben gemäß
   [`backend/README.md`](../backend/README.md) Freigabevoraussetzungen. Dieser
   Bericht ändert oder schließt keine SecurityChain-D01–D12-Anforderung ab.
4. Für iOS fehlt zusätzlich die iOS-App samt Projekt- und Release-Konfiguration;
   sie muss innerhalb der dafür zuständigen App-Quellen ergänzt und separat
   geprüft werden.
5. Erst nach Bereitstellung und Freigabe dieser Voraussetzungen können die
   getrennten Android-Clients und der iOS-Client mit plattformspezifischem
   TLS-, Auth-, Timeout- und Fehlerverhalten integriert und gegen den
   deployten Server getestet werden.

Bis dahin bleibt der Verbindungsstatus **BLOCKIERT**. Anmeldung und geschützte
Funktionen wurden nicht geprüft und dürfen aus den lokalen Health-Tests nicht
abgeleitet werden.
