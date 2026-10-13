# NIKNOLIG Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Status

Dieses Repository ist derzeit ein Dokumentations- und Architekturgrundgerüst. Es
enthält noch keinen importierten Anwendungscode, keine Module, keine API-Server,
keine Build-Konfiguration und keine Tests. Bestehende BLE-, Connection-Manager-
oder SecurityChain-Implementierungen konnten daher nicht geprüft oder verändert
werden.

Eine Bestandsaufnahme mit den bekannten Repository- und Branchinformationen
steht in [docs/inventory.md](docs/inventory.md). Die vorgeschlagenen Modulgrenzen
stehen in [docs/architecture.md](docs/architecture.md); die Schnittstellenregeln
stehen in [docs/interface-contracts.md](docs/interface-contracts.md).

## Architekturüberblick

- **NIKNOLIG Core / Android-App:** Hauptplattform; bestehende Android- und BLE-
  Funktionen sind bei einer späteren Integration zu erhalten.
- **Elektro-Engel:** Eigenständiges Assistenzmodul für elektrische Geräte,
  Sensoren und unterstützende Automatisierung.
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

Vor der Implementierung müssen die Quellrepositorys und die gewünschte
Technologie-/Build-Basis benannt und zugänglich gemacht werden. Danach können
Bestandscode und Berechtigungen verifiziert, Modulverträge konkretisiert und
passende Tests eingerichtet werden. Bis dahin werden keine Quellcodes oder
laufenden Funktionen erfunden.
