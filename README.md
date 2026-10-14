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

## Read-only Audit

Der Workflow `Read-only Workers repository audit` prüft beim manuellen Start
ausschließlich die Dateien dieses Monorepos. Er erstellt einen Überblick über
Dateien, README-Überschriften und Workflows sowie einen einfachen Scan nach
credential-ähnlichen Mustern. Werte, Quellinhalte und Clone-Diagnosen werden
nicht ausgegeben. Der Workflow benötigt keine Repository-Secrets, klont kein
externes Repository und führt keine Projekt-Workflows oder Skripte aus.

## Integrationsvorgehen

Den Audit-Workflow manuell starten und den Bericht über die vorhandenen
Repository-Dateien, README-Überschriften und Workflows prüfen. Da die
Projektquellen derzeit fehlen, ist ein Vergleich mit NIKNOLIG-, Defense- oder
Workers-Projekten erst möglich, wenn deren Inhalte tatsächlich in diesem
Monorepo vorhanden sind. Es erfolgt weder ein automatischer Merge noch ein
Deployment.
