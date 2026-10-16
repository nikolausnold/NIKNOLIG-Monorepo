# Elektro-Engel: Architekturgrenzen und spätere Repository-Migration

**Status:** Architekturvorbereitung; keine Core-Runtime, keine neue Gradle-
Bibliothek und keine Freigabe zur Produktivintegration. SecurityChain-P0 bleibt
BLOCKED.

## Ziel und aktueller Stand

Elektro-Engel soll so abgegrenzt werden, dass ein späterer, eigenständiger Core
ohne Abhängigkeit von Android-Oberflächen, App-Daten oder NIKNOLIG-Code gepflegt
und gegebenenfalls in ein separates Repository übertragen werden kann. Das ist
ein zukünftiges Architekturziel und ändert den aktuellen Produktstatus nicht:
Die lokale Assistenzvorschau gehört zu NIKNOLIG; NIKNOLIG und NIKNOLIG Defense
bleiben eigenständige Apps, Sicherheitsdomänen und Releases.

Heute gibt es keine Elektro-Engel-Core-Laufzeit oder gemeinsame Android-
Bibliothek. Die JSON-Schemas unter `backend/contracts/` sind deklarative
Vertragsentwürfe; sie implementieren weder Zustimmung noch Pairing,
Sensorzugriff oder Datentransfer. Die App-Quellen liegen unter
`apps/niknolig/` und `apps/niknolig-defense/`. Es werden keine vorhandenen
Module verschoben und keine App-Runtime-Abhängigkeiten hinzugefügt.

## Vorgesehene Verantwortungsgrenzen

Diese Grenzen beschreiben den späteren Zielzuschnitt, keine heute vorhandenen
Module:

| Schicht | Verantwortung | Darf nicht enthalten |
| --- | --- | --- |
| `core` | Plattformunabhängige Domänenmodelle, deterministische Regeln und Schnittstellen für Zustimmung, Fähigkeiten und minimale Ergebnisse | Android- oder UI-Frameworks, App-Identität, Netzwerk-/Sensorzugriff, NIKNOLIG-spezifische Zustände |
| `contracts` | Versionierte, dokumentierte Austauschformate und Kompatibilitätsregeln | Laufzeitannahmen; ein valides Schema ist weder Autorisierung noch Consent |
| `sensor-adapters` | Lokale, explizit registrierte Implementierungen der Core-Schnittstellen; tatsächliche Laufzeitfähigkeiten melden | Core-Entscheidungen, implizite OS-Freigaben, remote geladener Plugin-Code |
| `multidevice` | Getrennte Protokoll-/Transportintegration für Gerätekommunikation, erst nach eigener Sicherheitsfreigabe | Allgemeine Fernsteuerung, implizite Wiederaufnahme oder Umgehung von Core-Consent-Prüfungen |
| Android-Integration / UI | Je App eigene Oberfläche, OS-Permissions, Adapterinstanziierung und Übersetzung in app-lokale Zustände | Gemeinsame App-Credentials, Zugriff auf die Daten der jeweils anderen App |
| NIKNOLIG-Integration | NIKNOLIG-spezifische Navigation, Vorschau und Produktfunktionen außerhalb des neutralen Core | NIKNOLIG-Abhängigkeiten im Core oder implizite Defense-Berechtigungen |

Die Abhängigkeitsrichtung verläuft von Integrationen und Adaptern zu eng
definierten Core-Schnittstellen. Der Core kennt keine konsumierende App und
importiert keine Android-Typen. Apps dürfen jeweils eigene Integrationen
bereitstellen; das macht sie nicht zu gegenseitigen Abhängigkeiten.

## Schnittstellen- und Kompatibilitätsregeln

- Änderungen an bestehenden `backend/contracts/*-v1.schema.json` sind
  rückwärtskompatibel zu halten. Inkompatible Änderungen erhalten eine neue
  Vertrags-/Schema-Version und behalten die alte Version, solange unterstützte
  Verbraucher davon abhängen.
- Jede Schnittstelle dokumentiert Eigentümer, Zweck, Version, erlaubte Daten,
  Fehler-/Ablehnungsverhalten und Kompatibilitätsregeln. Unbekannte Versionen,
  Felder, Fähigkeiten und Erweiterungen werden fail closed behandelt.
- Sensible Vorgänge benötigen eine konkrete, gültige und widerrufbare
  Zustimmung. Schema-Validität ersetzt niemals Installation-/Peer-Identität,
  Autorisierung, OS-Runtime-Permission oder SecurityChain-P0-Prüfung.
- Contract-Tests bleiben auf den neutralen Verträgen und Invarianten. App-
  Integrationstests prüfen zusätzlich die getrennte App-Domäne; echte Sensor-
  und Zwei-Geräte-Freigaben bleiben separate manuelle Gates.

## Abhängigkeiten, Pfade und Build-Basis

| Bereich | Aktueller Pfad | Abhängigkeit / Bedeutung für die Trennung |
| --- | --- | --- |
| Gradle-Projektdefinition | `settings.gradle.kts`, `build.gradle.kts` | Nur `:niknolig` und `:niknolig-defense` sind Android-Projekte; es gibt kein Core-Modul. |
| NIKNOLIG Android-App | `apps/niknolig/` | Eigene Oberfläche, Manifest, Ressourcen und Build-Konfiguration; keine Abhängigkeit auf die Defense-App. |
| Defense Android-App | `apps/niknolig-defense/` | Eigene Oberfläche, Manifest, Ressourcen und Build-Konfiguration; keine Abhängigkeit auf NIKNOLIG. |
| Consent-/Sensorverträge | `backend/contracts/` | Derzeit gemeinsamer, rein deklarativer Vertragsentwurf; bei späterer Extraktion gemeinsam mit den versionierten Vertragstests migrieren. |
| API-Entwurf und Backend-Tests | `backend/openapi.yaml`, `backend/tests/test_contracts.py` | Noch keine operative API; kein Produktionsendpunkt oder Laufzeitclient. |
| Geräte-/Sensor-Sicherheitsplanung | `docs/electro-engel-multidevice-sensors.md`, `docs/device-link-security-design.md` | Quelle für offene Sicherheitsentscheidungen und ausdrückliche Stop-Gates. |
| Android-Build | `gradlew`, `gradle/wrapper/gradle-wrapper.properties`, `apps/*/build.gradle.kts`, `.github/workflows/android-build.yml` | Wrapper auf Gradle 8.13, JDK 17, compile SDK/build tools 35; der Workflow baut beide Apps getrennt. |

Der bestehende Build ist versioniert, aber dadurch allein nicht vollständig
reproduzierbar. Vor einer Core-Veröffentlichung sind Wrapper-Distribution-
Checksumme, JDK-/Android-SDK- und Build-Tools-Versionen, transitive
Abhängigkeiten sowie CI-Actions nachvollziehbar festzulegen. Builds sollen
ohne geheime oder maschinenlokale Eingaben wiederholbar sein; Artefakte und
Prüfergebnisse müssen einer Commit-ID zugeordnet werden. App-Signierschlüssel
gehören nicht in das Core-Repository oder dessen Vertragstests.

Vertragstests lokal ausführen:

```sh
python3 -m unittest discover -s backend/tests
```

Der Android-CI-Workflow führt diese Tests ebenfalls aus. `jsonschema` bleibt
optional; die strukturellen Invarianten verwenden die Python-Standardbibliothek.

## Migrationsplan

1. **Vorbereitung im Monorepo:** Diese Modulgrenzen und Vertragsregeln pflegen;
   Vertragstests in CI ausführen. Keine Laufzeit oder App-Abhängigkeit allein
   aufgrund der Zielarchitektur hinzufügen.
2. **Extraktionsreife nachweisen:** Mindestens ein unabhängig nutzbarer,
   plattformneutraler Core mit stabilen Verbrauchern und dokumentierter API muss
   existieren. Verantwortliche müssen Scope, Versionierung, Lizenzierung,
   Maintainer, Release-/Supportprozess und Sicherheitsreview schriftlich
   festlegen.
3. **Security-Gates erfüllen:** Verbindliche SecurityChain-P0-Kriterien,
   Bedrohungsmodell, Consent-/Widerrufsverhalten, App-Domänen, Datenklassen,
   Identität, Transport, Aufbewahrung und Negativtests müssen freigegeben und
   überprüfbar sein. Ohne diese Nachweise findet keine operative
   Geräte-/Sensorintegration statt.
4. **Separat extrahieren:** Erst nach Freigabe nur plattformneutrale Core-
   Implementierung, ihre öffentlichen Verträge, Tests, Dokumentation und
   reproduzierbare Build-Konfiguration übertragen. Android-UIs,
   app-spezifische Ressourcen, Credentials und NIKNOLIG-Integrationen verbleiben
   in ihren App-Repositories. Sensoradapter und Multi-Device-Transport werden
   nur übernommen, falls sie separat freigegeben und unabhängig testbar sind.
5. **Verbraucher unabhängig anbinden:** Je App eine eigene, explizite Integration
   gegen eine freigegebene Core-Version reviewen. Es gibt keine gemeinsame
   Laufzeit- oder Credential-Domäne und keine automatische Änderung der
   App-Repositories durch diese Migration.
6. **Übergang verifizieren:** Vor Abschalten der Monorepo-Vertragsquelle
   kompatible Verbraucher, negative Consent-/Autorisierungstests, App-
   Paketidentitäten, Android-Builds und Release-Artefakte vergleichen. Die
   bisherige Vertragsversion bleibt verfügbar, bis alle unterstützten
   Verbraucher migriert und geprüft sind.

### Migrationsrisiken und Gegenmaßnahmen

- **Scheinbar stabile Schemas werden als Runtime-API missverstanden:** Schema-
  Dokumentation und Tests ausdrücklich als deklarativ kennzeichnen; keine
  Autorisierung daraus ableiten.
- **App- oder UI-Code sickert in den Core:** Extraktionsumfang per Pfad-/Import-
  Review begrenzen und Plattformunabhängigkeit als CI-Invariante prüfen.
- **App-Domänen oder Zustimmung werden vereinheitlicht:** App-Bereich und
  konkrete Consent-Prüfung in jedem Verbraucher erhalten; Änderungen benötigen
  eigene negative Tests und Sicherheitsreview.
- **Vertragsdrift zwischen Repositories:** Ein versionierter Vertrag ist die
  gemeinsame Referenz; Kompatibilität mit den geprüften App-Verbrauchern vor
  jedem Breaking Release nachweisen.
- **Builds hängen an lokalen Umgebungen oder Geheimnissen:** Toolchain und
  Abhängigkeiten pinnen; keine Signierdaten oder produktiven Konfigurationen für
  Core-Tests verwenden.
- **Vorzeitige Extraktion erzeugt unnötige Kopplung und Betriebslast:** Ein
  eigenes Repository ist erst sinnvoll, wenn eine echte neutrale Core-
  Implementierung unabhängig versioniert und verantwortet werden muss. Vorher
  bleiben Dokumentation und Vertragsvorbereitung im Monorepo.

Bis zur erfüllten Extraktionsreife und separaten Freigabe bleiben
SecurityChain-P0-Grenzen, Nutzerzustimmung, die getrennten Android-Apps und der
Status „keine produktive Laufzeitintegration“ unverändert.
