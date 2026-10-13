# Zielarchitektur

Diese Übersicht beschreibt Modulgrenzen für künftige Implementierungen. Sie
bestätigt nicht, dass die unten aufgeführten Komponenten bereits vorhanden sind.
Die im Repository angelegten `README.md`-Dateien unter diesen Pfaden sind
bewusst nur Platzhalter. Sie ersetzen oder überdecken keinen Quellcode.

## Vorgeschlagene Struktur

```text
apps/
  niknolig-android/       # vorgesehener App-Einstiegspunkt; genaue Plattform offen
    features/
      elektro-engel/      # logische NIKNOLIG-Funktion, kein eigenständiges Projekt
modules/
  niknolig-core/          # logische Core-Grenze; Zuschnitt nach Quellcodeprüfung
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

- **NIKNOLIG** ist die zivile Hauptplattform. Der Eigentümer nennt
  `https://github.com/nikolausnold/NIKNOLIG`, Branch `main`; beides konnte in
  dieser Umgebung nicht gelesen/verifiziert werden. Android-, BLE-,
  Connection-Manager- und SecurityChain-Verhalten müssen vor Änderungen im
  Quellcode erfasst werden.
- **Elektro-Engel** ist gemäß Projektgrundlage eine Funktion innerhalb von
  NIKNOLIG, kein separates Repository, eigenständiges Deployment oder zusätzliche
  Vertrauensdomäne. Umfang, Einbaupunkt und Geräteschnittstellen dürfen erst
  anhand des NIKNOLIG-Quellcodes festgelegt werden.
- **Defense** bleibt eine eigenständige Sicherheitsdomäne. Nur ein explizit
  konfigurierter Adapter darf freigegebene Daten über den dokumentierten Vertrag
  austauschen; gemeinsame Verträge heben diese Grenze nicht auf. Der angegebene
  Quellstand ist `https://github.com/nikolausnold/NIKNOLIG-Defense`, Branch
  `main`; auch dieses Repository war nicht lesbar/verifizierbar.
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

1. Lesenden Zugriff auf beide angegebenen Quellrepositorys verifizieren.
2. Revision, Buildsystem, vorhandene Tests und tatsächliche Modulstruktur prüfen.
3. Vorhandene Funktionen und Sicherheitsgrenzen dokumentieren, bevor Dateien
   übernommen oder ersetzt werden.
4. Elektro-Engel innerhalb der zivilen NIKNOLIG-Plattform einordnen und den
   Defense-Adapter getrennt definieren; versionierte Verträge und jede
   Datenfreigabe ausdrücklich autorisieren.
5. Integration zunächst lokal und mit Testdaten verifizieren.
6. Release, Merge, Deployment oder externe Aktionen erst nach erforderlicher
   menschlicher Freigabe durchführen.
