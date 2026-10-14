# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Diese Arbeitskopie enthält Dokumentation, einen manuellen Read-only-Audit-
Workflow sowie einen getesteten OpenAI-Gateway-Vertrag für Cloudflare Workers.
Die Produktquellen und Clients von NIKNOLIG, Elektro-Engel und NIKNOLIG Defense
fehlen weiterhin. Daher wurde noch kein Projekt aus einem anderen Repository
übernommen und es ist keine Überschneidungsprüfung auf Dateiebene möglich.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | `README.md`, `.github/workflows/audit-workers.yml`, `workers/openai-gateway/` |
| Abhängigkeiten | Keine Drittanbieter-Abhängigkeiten |
| Tests | Node.js-Built-in-Test für den Worker-Gateway-Vertrag |
| Schnittstellen | `POST /v1/assist`; Produktclients und kontrollierter Datenaustausch fehlen |

## OpenAI-Gateway (Cloudflare Workers)

`workers/openai-gateway` enthält einen serverseitigen Gateway-Vertrag für
NIKNOLIG, Elektro-Engel und NIKNOLIG Defense. Die drei Systemkennungen verwenden
getrennte Cloudflare-Access-Audiences und getrennte Systemanweisungen. Der
Gateway akzeptiert ausschließlich `system` und `input`; er speichert keine
Konversationen, sendet `store: false` an OpenAI und gibt keine Upstream-Fehler
oder API-Schlüssel zurück. Ein explizites `shareWith`-Feld wird abgelehnt. Ein
systemübergreifender Datenaustausch ist derzeit nicht implementiert, da keine
Projektquellen oder Schnittstellen vorhanden sind.

Eingaben sind auf 4.000 Zeichen, OpenAI-Ausgaben auf 300 Tokens und Aufrufer auf
10 Anfragen pro Minute begrenzt. Netzwerk-, Upstream- und Konfigurationsfehler
liefern einen allgemeinen Offline-Fallback. Das Rate-Limit und die Tokenlimits
begrenzen einzelne Aufrufe, sind aber kein monatliches Ausgabenbudget; dafür
muss zusätzlich ein Ausgabenlimit im OpenAI-Projekt konfiguriert werden.

Für den Betrieb sind eine Cloudflare-Access-Anwendung pro System, die zugehörigen
Audiences, eine Rate-Limit-Namespace-ID und das Worker-Secret `OPENAI_API_KEY`
erforderlich. Die Werte für die Platzhalter in
`workers/openai-gateway/wrangler.toml` werden nicht im Repository hinterlegt:

- `ACCESS_TEAM_DOMAIN`: ausschließlich der Access-Team-Hostname, ohne
  `https://` und Pfad. Der bestehende Worker akzeptiert nur Hostnamen unter
  `cloudflareaccess.com`; den exakten Team-Hostname im Cloudflare Zero Trust
  Dashboard unter **Settings → General → Team domain** übernehmen.
- `SYSTEM_AUDIENCES`: JSON-Objekt mit genau den Schlüsseln `niknolig`,
  `elektro-engel` und `niknolig-defense`. Jeder Wert muss unverändert die
  Audience-Tag-Zeichenkette (`aud`) der jeweils zugehörigen Cloudflare-Access-
  Anwendung sein. Die konkreten Tags unter **Access → Applications → jeweilige
  Anwendung → Overview → Application Audience (AUD) Tag** ablesen; keine Tags
  aus Systemnamen ableiten. Aktuell ist der konfigurierte Wert `{}` und reicht
  nicht zur Authentifizierung.
- `OPENAI_API_KEY`: ausschließlich als geschütztes Worker-Secret, nicht als
  `vars`-Eintrag, speichern. Den Schlüssel ausschließlich mit
  `wrangler secret put OPENAI_API_KEY` setzen
  ([Worker-Secrets-Dokumentation](https://developers.cloudflare.com/workers/configuration/secrets/)).

Die Access-Anwendungen müssen jeweils nur die vorgesehenen Benutzer/Clients des
zugehörigen Systems zulassen. Secret-Werte werden nicht ausgelesen oder
ausgegeben. Die Verfügbarkeit des Cloudflare-Secrets ließ sich in dieser
Umgebung nicht prüfen; ein Deployment fand nicht statt.

Das vorhandene GitHub-Secret `OPENAI_API_KEY` wird von GitHub Actions nicht
automatisch an einen Worker übertragen. Der Read-only-Audit-Workflow verwendet
es bewusst nicht: Er benötigt ausschließlich `WORKERS_REPOSITORY_URL` und
`WORKERS_REPO_READ_PAT`, klont nur das Quellrepository und führt keinen
Cloudflare-Aufruf aus. Für den Worker-Laufzeitbetrieb muss derselbe Schlüssel
einmal als Cloudflare-Worker-Secret `OPENAI_API_KEY` hinterlegt werden. Eine
spätere, ausdrücklich freigegebene Deployment-Pipeline könnte das vorhandene
GitHub-Secret als Quelle dafür verwenden; dafür wären zusätzlich ein eng
begrenztes Cloudflare-Deployment-Token und ein eigener, geprüfter Deploy-Job
erforderlich. Eine solche Pipeline wird hier nicht angelegt und es erfolgt
keine Übertragung.

Die vorhandenen Repositorys enthalten keine Frontends oder Backends der drei
Systeme; deshalb kann dieser Gateway-Vertrag noch von keinem Produktivsystem
aufgerufen werden. Tests lokal ausführen:
`node --test workers/openai-gateway/src/index.test.mjs`.

## Sicherer Integrationszugriff

Vor einem Klon oder Vergleich müssen betroffene Zugangsdaten erneuert werden,
falls sie offengelegt wurden. Zugangsdaten und Clone-Adressen gehören nicht in
Quellcode, Dokumentation, Logs oder Commits.

Nach der Erneuerung folgende Repository-Secrets einrichten:

- `WORKERS_REPOSITORY_URL`: HTTPS-Clone-Adresse von `niknolig-workers`.
- `WORKERS_REPO_READ_PAT`: separat gespeichertes, nur leseberechtigtes Token für
  dieses Repository (Inhalte lesen; kein Schreib-, Merge- oder Deploy-Zugriff).

[Repository-Secrets öffnen](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/secrets/actions/new).
Secret-Werte nicht in Chat, Issues, Pull Requests, Logs oder Dateien einfügen.
Der Workflow `Read-only Workers repository audit` prüft beim manuellen Start,
ob beide Secrets verfügbar sind, entfernt optionale Zugangsdaten aus der
Clone-Adresse und verwendet ausschließlich das separate PAT für den lesenden Klon.

Die aktuelle Agentensitzung kann Repository-Secrets weder auflisten noch deren
Verfügbarkeit in GitHub Actions verifizieren. Secret-Werte werden nicht
ausgelesen. Ohne eingerichtete Secrets kann der manuelle Audit-Workflow nicht
auf das externe Repository zugreifen.
Die verfügbaren Audit-Läufe vom 13.10.2026 brachen vor dem Klonen bei der
Prüfung einer URL mit eingebetteten Zugangsdaten ab. Der Workflow wurde danach
angepasst; ein erfolgreicher Lauf mit der Korrektur liegt nicht vor. Der Inhalt
des externen `niknolig-workers`-Repositorys ist deshalb weiterhin ungeprüft.
Der aktuelle Workflow erlaubt eingebettete URL-Zugangsdaten, entfernt sie vor
dem Klon und authentifiziert stattdessen ausschließlich mit
`WORKERS_REPO_READ_PAT`. Query-Parameter und Fragmente werden abgelehnt; Clone-
Diagnosen bleiben unterdrückt. Ein erneuter Workflow-Dispatch war aus dieser
Sitzung nicht verfügbar.

## Integrationsvorgehen

Nach Bereitstellung des geschützten Zugriffs zunächst den Audit-Workflow manuell
starten und dessen Strukturbericht, README-Überschriften und vorhandene
Workflow-Dateien prüfen. Der Workflow führt keine externen Skripte aus und
ändert keine Dateien. Danach NIKNOLIG-, Defense- und Workers-Projekte auf
Dateipfade, Funktionen und Abhängigkeiten vergleichen. Übernahmen erfolgen nur
für nicht kollidierende Inhalte; Konflikte und offene Schnittstellen werden vor
Änderungen dokumentiert. Tests werden nur ausgeführt, wenn die übernommenen
Projekte sie bereitstellen. Es erfolgt weder ein automatischer Merge noch ein
Deployment.
