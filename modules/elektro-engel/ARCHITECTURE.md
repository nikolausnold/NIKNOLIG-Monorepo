# Architektur

## Bestand und Wiederverwendung

Vorhanden waren Architektur- und Sicherheitsplanung in
`docs/electro-engel-architecture-and-migration.md` und
`docs/electro-engel-multidevice-sensors.md`, Backend-Fehler-/Healthverträge
sowie deklarative Consent-, Audit- und Sensorschemas in `backend/`. Es gab
keinen Core, keine Laufzeit, keinen Toolzugriff und keine gemeinsame
Android-Bibliothek. Die Android-Apps bleiben getrennt; `settings.gradle.kts`
bindet nur `:niknolig` und `:niknolig-defense` ein.

Der neue Kern übernimmt die dokumentierten Prinzipien: getrennte App-Domänen,
minimierte Logs, explizite Zustimmung, fail-closed Toolzugriff und keine
automatische Geräte-/Sensorintegration. Die Backend-Schemas werden nicht kopiert
und nicht als Runtime-Sicherheitskontrolle missverstanden.

## Komponenten und Datenfluss

```text
Host / optionale NIKNOLIG-Integration
              │ TaskRequest
              ▼
       CoreEngine ───────────────► InMemoryAuditLog
          │     │                         ▲
          │     ├── BoundedPlanner ─► TaskPlan (nur Vorschlag)
          │     ├── ContextStore (explizite, flüchtige Werte)
          │     ├── LearningSandbox (inaktive Vorschläge)
          │     └── ToolRegistry ───► registriertes Tool
          │                              ▲
          └──────────────────── ToolApproval
```

`TaskRequest` wird auf Nicht-Leere und Eingabelänge geprüft. Der Planner erzeugt
genau einen Review-Schritt; kein Plan wird automatisch ausgeführt. Eine
Toolausführung benötigt einen registrierten Namen sowie eine explizite
Freigabestruktur, die Request-ID und Tool-Namen exakt bindet. Der Aufrufer bleibt
für die tatsächliche Authentifizierung und Autorisierung verantwortlich.

Context und Lernvorschläge sind nur im Arbeitsspeicher des Prozesses und haben
Kapazitätsgrenzen. Audit-Metadaten sind ebenfalls flüchtig und auf maximal 1000
Ereignisse begrenzt. Es gibt weder Persistenz noch Netzwerk- oder
Plattformzugriff.

## Grenzen und Lücken

- Keine LLM-/KI-Inferenz, Gedächtnispersistenz oder Lern-/Evaluierungslogik.
- Kein NIKNOLIG-Adapter als App-Code, kein Defense-Adapter und keine App-Build-
  oder Runtime-Abhängigkeit.
- Keine authentisierte Freigabeprüfung: `ToolApproval` allein ist nicht
  vertrauenswürdig und darf nie die Host-Autorisierung ersetzen.
- Kein Sensor-, LiDAR-, Gerätewechsel-, Netzwerk-, Backend- oder
  Produktionszugriff.
- Kein SecurityChain-P0-Nachweis; die produktive Integration bleibt BLOCKED.
- Keine JSON-Schema-Laufzeitvalidierung für Backend-Verträge.

## Abhängigkeiten

Python 3.10 oder neuer; ausschließlich Python-Standardbibliothek. Es gibt keine
Monorepo-Pfadreferenz in der Laufzeit und keine NIKNOLIG-App-Importe. Build-,
Release- und Produktionsdeployment sind nicht eingerichtet.
