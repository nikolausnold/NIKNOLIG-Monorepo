# Zielarchitektur

Diese Übersicht beschreibt Modulgrenzen für künftige Implementierungen. Sie
bestätigt nicht, dass die unten aufgeführten Komponenten bereits vorhanden sind.

## Vorgeschlagene Struktur

```text
apps/
  niknolig-android/       # Android-Einstiegspunkt und Plattformintegration
modules/
  niknolig-core/          # plattformunabhängige Hauptplattform-Funktionen
  elektro-engel/          # isoliertes Assistenzmodul
  defense-integration/    # eng begrenzter Adapter in Richtung Defense
packages/
  api-contracts/          # versionierte Austauschverträge
  shared-models/          # nur ausdrücklich gemeinsam genutzte Datentypen
  security/               # gemeinsame Sicherheitsbausteine ohne Trust-Übernahme
docs/
tests/
```

Die Struktur ist ein Vorschlag; Technologie und konkrete Paketgrenzen hängen
von den zu verifizierenden Quellprojekten ab.

## Verantwortlichkeiten und Grenzen

- **NIKNOLIG** besitzt die Haupt-App und ihre Plattformintegrationen. Android-
  und BLE-Verhalten sowie vorhandene Connection-Manager- und SecurityChain-
  Mechanismen müssen vor Änderungen am jeweiligen Quellcode erfasst werden.
- **Elektro-Engel** kapselt Geräte-, Sensor- und Assistenzlogik. Es erhält keine
  direkten impliziten Zugriffe auf Defense oder Core-interne Daten.
- **Defense** bleibt eine eigenständige Sicherheitsdomäne. Nur ein explizit
  konfigurierter Adapter darf freigegebene Daten über den dokumentierten Vertrag
  austauschen; gemeinsame Verträge heben diese Grenze nicht auf.
- **Gemeinsame Modelle und API-Verträge** enthalten nur benötigte, versionierte
  Daten. Sie sind kein Ort für Geschäftslogik, Zugangsdaten oder
  sicherheitsrelevante Entscheidungshoheit.
- **Tests** sollen Modulgrenzen, Autorisierung, Fehlerfälle, Synchronisation,
  Geräteintegration und Lokalisierung separat prüfen.

## Offline und Synchronisation

Lokale Nutzung und spätere Synchronisation sind Anforderungen, aber noch nicht
implementiert. Vor einer Implementierung müssen Datenklassifizierung,
Speicherung, Verschlüsselung, Konfliktregeln, Wiederholungsverhalten,
Widerruf/Löschung und Schutz vor doppelter Ausführung festgelegt werden.
Synchronisation muss authentifiziert und autorisiert sein, darf keine
Berechtigungsgrenzen umgehen und muss Fehler sicher behandeln. Bis dahin wird
keine konkrete Offline-Sicherheitsgarantie behauptet.

## Mehrsprachigkeit und RTL

Zielsprachen: Deutsch, Englisch, Russisch, Japanisch, Chinesisch, Koreanisch,
Hindi, Französisch, Spanisch und Arabisch. Übersetzungen sollen aus
sprachneutralen Ressourcen geladen werden; Layouts müssen RTL unterstützen und
mit arabischem Text geprüft werden. Übersetzungsabdeckung, Pluralregeln,
Schriftarten, Datums-/Zahlenformate und Accessibility sind bei der Umsetzung zu
validieren. Derzeit existiert keine Lokalisierungsimplementierung.

## Integrationsablauf

1. Quellrepository, Revision, Buildsystem und vorhandene Tests verifizieren.
2. Vorhandene Funktionen und Sicherheitsgrenzen dokumentieren, bevor Dateien
   übernommen oder ersetzt werden.
3. Moduladapter und versionierte Verträge definieren; jede Datenfreigabe
   ausdrücklich autorisieren.
4. Integration zunächst lokal und mit Testdaten verifizieren.
5. Release, Merge, Deployment oder externe Aktionen erst nach erforderlicher
   menschlicher Freigabe durchführen.
