# NIKNOLIG Monorepo

Zentrale Integrationsplattform für NIKNOLIG und die getrennt bleibende
NIKNOLIG-Defense-Integration. Elektro-Engel ist als Funktion innerhalb der
zivilen NIKNOLIG-Plattform vorgesehen, nicht als separates Quellrepository.

## Status

Dieses Repository enthält ein Dokumentations- und Architekturgrundgerüst mit
leeren Modul-Platzhaltern. Es enthält noch keinen importierten Anwendungscode,
keine implementierten Module oder API-Server, keine Build-Konfiguration und
keine Tests. Bestehende BLE-, Connection-Manager- oder SecurityChain-
Implementierungen konnten daher nicht geprüft oder verändert werden.

Eine Bestandsaufnahme mit den angegebenen Quellrepositorys und den tatsächlich
festgestellten Zugriffshindernissen steht in [docs/inventory.md](docs/inventory.md).
Die vorgeschlagenen Modulgrenzen stehen in [docs/architecture.md](docs/architecture.md);
die Schnittstellenregeln stehen in [docs/interface-contracts.md](docs/interface-contracts.md).
Die Platzhalter dokumentieren nur vorgesehene Grenzen; sie enthalten keine
ausführbaren Funktionen.

## Architekturüberblick

- **NIKNOLIG Core / Android-App:** Hauptplattform; bestehende Android- und BLE-
  Funktionen sind bei einer späteren Integration zu erhalten.
- **Elektro-Engel:** Zivile NIKNOLIG-Funktion für elektrische Geräte, Sensoren
  und unterstützende Automatisierung; keine separate Plattform oder
  Vertrauensdomäne.
- **NIKNOLIG Defense:** Logisch und sicherheitstechnisch getrenntes Schutzsystem.
  Kommunikation erfolgt ausschließlich über ausdrücklich freigegebene Adapter.
- **Gemeinsame Verträge und Modelle:** Versionierte, technologie-neutrale
  Schnittstellen; sie erteilen keinem Modul implizit Berechtigungen.

Diese Beschreibungen sind Zielarchitektur, keine Aussage über bereits
implementierte Funktionalität.

## Sicherheit und Betrieb

- Keine Secrets, echten Zugangsdaten oder sensiblen Nutzdaten in Konfiguration,
  Dokumentation oder Logs ablegen.
- Module gewähren einander kein implizites Vertrauen. Authentifizierung,
  Autorisierung und minimale Berechtigungen sind für jeden Austausch erforderlich.
- Offline-Änderungen dürfen nur über einen später zu spezifizierenden,
  abgesicherten Synchronisationsablauf übertragen werden.
- Keine produktiven externen Aktionen oder kostenpflichtigen API-Aufrufe in der
  Entwicklung.
- Merge, Veröffentlichung und Deployment erfolgen nur nach menschlicher Freigabe.

## Weiterarbeit

Die angegebenen Quellrepositorys und Branches sind in
[docs/inventory.md](docs/inventory.md) dokumentiert. Die Quellcodezugriffe
lieferten derzeit HTTP 404; vor Quellcodeprüfung, Import oder Festlegung der
Build-Basis muss der lesende Zugriff auf beide Repositories funktionieren.
Bis dahin werden keine Quellcodes oder laufenden Funktionen behauptet.
