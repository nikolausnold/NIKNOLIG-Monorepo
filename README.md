# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Diese Arbeitskopie enthält derzeit diese README und einen manuellen
Read-only-Audit-Workflow. Es sind keine Projektquellen, Abhängigkeiten, Tests
oder Integrationsschnittstellen vorhanden. Daher wurde noch kein Projekt aus
einem anderen Repository übernommen und es ist keine Überschneidungsprüfung auf
Dateiebene möglich.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | `README.md`, `.github/workflows/audit-workers.yml` |
| Abhängigkeiten | Keine Manifestdateien vorhanden |
| Tests | Keine Testkonfiguration oder Tests vorhanden |
| Offene Schnittstellen | Noch nicht ermittelbar; Quellprojekte fehlen |

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

Für einen später ausdrücklich freigegebenen Betrieb sind eine Cloudflare-Access-
Anwendung je System mit eigener Audience, die passende Audience-Konfiguration,
eine Rate-Limit-Namespace-ID und das geschützte Worker-Secret `OPENAI_API_KEY`
erforderlich. Den Schlüssel ausschließlich über `wrangler secret put
OPENAI_API_KEY` im Cloudflare-Konto hinterlegen. Nicht im Repository, Frontend,
Workflow oder in Logs speichern. Es wurde kein Secret angelegt oder ausgelesen,
und es erfolgte kein Deployment. Das Vorhandensein des Secrets konnte mit den
verfügbaren Repository-/Actions-Schnittstellen nicht geprüft werden.

Die vorhandenen Repositorys enthalten keine Frontends, Backends oder
Workers-Integrationen der drei Systeme; deshalb kann dieser Gateway-Vertrag noch
von keinem Produktivsystem aufgerufen werden. Tests lokal ausführen:
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
