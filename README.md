# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Dieses Repository enthält derzeit diese README und einen manuellen
Read-only-Audit-Workflow. Es sind keine Anwendungsquellen oder
Projekt-Integrationsschnittstellen vorhanden. Daher wurde kein Projekt aus
einem anderen Repository übernommen und es ist keine Überschneidungsprüfung auf
Dateiebene möglich.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | `README.md`, `.github/workflows/audit-workers.yml` |
| Funktionen | Nur der unten beschriebene Repository-Audit; keine Anwendungsfunktionen |
| Schnittstellen | `workflow_dispatch` zum manuellen Start; keine Anwendungs-API |
| Abhängigkeiten | Workflow nutzt `actions/checkout@v4` und Python-Standardbibliothek; keine Projekt-Manifeste |
| Tests | Keine Testkonfiguration oder Tests vorhanden |

## Integrationsinventur

| Komponente | Dateien und Funktionen im Monorepo | Schnittstellen / Abhängigkeiten | Fehlende Voraussetzungen und Risiken |
| --- | --- | --- | --- |
| NIKNOLIG | Nur als Projektname in dieser README erwähnt; keine Komponentendateien oder Anwendungsfunktionen | Keine Projekt-API oder Projekt-Abhängigkeiten nachweisbar | Quellcode und tatsächliche Modulgrenzen müssen geprüft werden; vorhandene Funktionen könnten ohne diese Prüfung übersehen oder beschädigt werden |
| Elektro-Engel | Nur als Projektname in dieser README erwähnt; keine Komponentendateien oder Anwendungsfunktionen | Keine Projekt-API oder Projekt-Abhängigkeiten nachweisbar | Einordnung und Einbaupunkt sind nicht belegt; keine eigenständige Schnittstelle annehmen |
| NIKNOLIG Defense | Nur als Projektname in dieser README erwähnt; keine Komponentendateien oder Anwendungsfunktionen | Keine Projekt-API oder Projekt-Abhängigkeiten nachweisbar | Datenaustausch, Autorisierung und Vertrauensgrenze sind nicht spezifiziert; keine Verbindung oder Berechtigung annehmen |

Die verfügbaren Dateien belegen weder Implementierungen noch die Abwesenheit
von Funktionen in den privaten Quellrepositories. Buildsystem, unterstützte
Plattformen, Datenflüsse, Authentifizierung und Tests der Projekte sind hier
nicht verifizierbar. Vor einer Integration müssen diese Punkte anhand
freigegebener Quellstände geklärt werden.

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
Repository-Dateien, README-Überschriften und Workflows prüfen. Da die
Projektquellen derzeit fehlen, ist ein Vergleich mit NIKNOLIG-, Defense- oder
Workers-Projekten erst möglich, wenn deren Inhalte tatsächlich in diesem
Monorepo vorhanden sind. Es erfolgt weder ein automatischer Merge noch ein
Deployment.
