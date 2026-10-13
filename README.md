# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Diese Arbeitskopie enthält derzeit nur diese README. Es sind keine Projektquellen,
Abhängigkeiten, Tests oder Integrationsschnittstellen vorhanden. Daher wurde noch
kein Projekt aus einem anderen Repository übernommen und es ist keine
Überschneidungsprüfung auf Dateiebene möglich.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | Nur `README.md` |
| Abhängigkeiten | Keine Manifestdateien vorhanden |
| Tests | Keine Testkonfiguration oder Tests vorhanden |
| Offene Schnittstellen | Noch nicht ermittelbar; Quellprojekte fehlen |

## Sicherer Integrationszugriff

Vor einem Klon oder Vergleich müssen betroffene Zugangsdaten erneuert werden,
falls sie offengelegt wurden. Zugangsdaten und Clone-Adressen gehören nicht in
Quellcode, Dokumentation, Logs oder Commits.

Nach der Erneuerung folgende Repository-Secrets einrichten:

- `WORKERS_REPOSITORY_URL`: HTTPS-Clone-Adresse von `niknolig-workers`.
- `WORKERS_READ_TOKEN`: separat erstelltes, nur leseberechtigtes Token für
  dieses Repository (Inhalte lesen; kein Schreib-, Merge- oder Deploy-Zugriff).

[Repository-Secrets öffnen](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/secrets/actions/new).
Secret-Werte nicht in Chat, Issues, Pull Requests, Logs oder Dateien einfügen.
Der Workflow `Read-only Workers repository audit` prüft beim manuellen Start,
ob beide Secrets verfügbar sind, und verwendet sie nur für den lesenden Klon.

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
