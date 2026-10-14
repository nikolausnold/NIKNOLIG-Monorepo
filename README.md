# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Dieses Repository enthält diese README, einen manuellen Read-only-Audit-Workflow
und den [Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md). Es sind
keine Anwendungsquellen oder Projekt-Integrationsschnittstellen vorhanden.
Die separaten Quell-Repositories sind inzwischen lesbar, wurden aber nicht in
dieses Monorepo übernommen; eine Integration ist nicht belegt.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | `README.md`, `.github/workflows/audit-workers.yml`, `docs/MASTER-INTEGRATION-PLAN.md` |
| Funktionen | Nur der unten beschriebene Repository-Audit; keine Anwendungsfunktionen |
| Schnittstellen | `workflow_dispatch` zum manuellen Start; keine Anwendungs-API |
| Abhängigkeiten | Workflow nutzt `actions/checkout@v4` und Python-Standardbibliothek; keine Projekt-Manifeste |
| Tests | Keine Testkonfiguration oder Tests vorhanden |

## Integrationsinventur

| Komponente | Dateien und Funktionen im Monorepo | Schnittstellen / Abhängigkeiten | Fehlende Voraussetzungen und Risiken |
| --- | --- | --- | --- |
| NIKNOLIG | Keine Komponentendateien im Monorepo; getrennte Quelle enthält ein Android-Entwicklungsgerüst und statische Website | Keine Integration oder Projekt-API im Monorepo nachgewiesen | App-Vorschau und GitHub-Pages-Deployment sind keine bestätigte produktive Systemintegration |
| Elektro-Engel | Keine Komponentendateien im Monorepo; in NIKNOLIG als Assistenz-/Lernziel beschrieben | Keine separate API oder Runtime nachgewiesen | Funktionsumfang und Einbaupunkt bleiben an den nachgewiesenen App-Stand gebunden |
| NIKNOLIG Defense | Keine Komponentendateien im Monorepo; getrennte Quelle enthält Android-Gerüst und statische Website | Keine Austausch-API oder Integration im Monorepo nachgewiesen | Sicherheitsgrenzen, Datenaustausch und Cloudflare-Verbindung sind nicht verifiziert |

Die verfügbaren Dateien belegen keine Implementierungen in diesem Monorepo.
Die getrennten Quellstände und die nachgewiesenen Workflow-/Build-Ergebnisse
sind im [Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md)
dokumentiert. Cloudflare-Verbindungen und produktive Integrationen bleiben
ungeprüft.

## Read-only Audit

Der Workflow `Read-only Workers repository audit` prüft beim manuellen Start
ausschließlich die Dateien dieses Monorepos. Er erstellt einen Überblick über
Dateien, README-Überschriften und Workflows sowie einen einfachen Scan nach
credential-ähnlichen Mustern. Werte, Quellinhalte und Clone-Diagnosen werden
nicht ausgegeben. Der Workflow benötigt keine Repository-Secrets, klont kein
externes Repository und führt keine Projekt-Workflows oder Skripte aus.
Der Muster-Scan ist eine begrenzte Prüfung und kein Nachweis, dass keine
Geheimnisse vorhanden sind.

## Integrationsvorgehen

Den Audit-Workflow manuell starten und den Bericht über die vorhandenen
Repository-Dateien, README-Überschriften und Workflows prüfen. Der Audit
untersucht nur dieses Monorepo; er ersetzt nicht die Prüfung der getrennten
Quell-Repositories. Es erfolgt weder ein automatischer Merge noch ein
Deployment.
