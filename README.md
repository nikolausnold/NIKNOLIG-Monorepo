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

Nach der Erneuerung die Clone-Adresse des Ziel-Repositories als GitHub Actions
Secret `WORKERS_REPOSITORY_URL` hinterlegen und anschließend den Zugriff
freigeben: [Repository-Secrets öffnen](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/secrets/actions/new).
Den Secret-Wert nicht in Chat, Issue oder Pull Request posten. Bis der Secret
verfügbar ist, werden keine externen Repositories geklont oder integriert.

## Integrationsvorgehen

Nach Bereitstellung des geschützten Zugriffs werden die NIKNOLIG-, Defense- und
Workers-Projekte zunächst auf Dateipfade, Funktionen und Abhängigkeiten verglichen.
Übernahmen erfolgen nur für nicht kollidierende Inhalte; Konflikte und offene
Schnittstellen werden vor Änderungen dokumentiert. Tests werden nur ausgeführt,
wenn die übernommenen Projekte sie bereitstellen. Es erfolgt weder ein
automatischer Merge noch ein Deployment.
