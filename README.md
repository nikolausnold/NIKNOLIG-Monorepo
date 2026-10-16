# NIKNOLIG-Monorepo

Monorepo für zwei getrennte Android-Apps: NIKNOLIG und NIKNOLIG Defense. Die
Apps bleiben eigenständige Installationen und Sicherheitsdomänen. Die Websites
und ihre Deployments bleiben in den jeweiligen Quell-Repositories.

## Android-Module

| Modul | Android `applicationId` | Quellstand |
| --- | --- | --- |
| `:niknolig` (`apps/niknolig`) | `com.niknolig.app` | [NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG/tree/3c4d6618a61604f6433639151e741371491a5f0d), Commit `3c4d6618a61604f6433639151e741371491a5f0d` |
| `:niknolig-defense` (`apps/niknolig-defense`) | `com.niknolig.defense` | [NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense/tree/5f0f385089bc27347eacd282c13a546eb4511da2), Commit `5f0f385089bc27347eacd282c13a546eb4511da2` |

Der [App-Web-Designabgleich](docs/app-web-design-alignment.md) dokumentiert
die gemeinsame Farbpalette und die absichtlich getrennten Produktlayouts.

Die App-Verzeichnisse beider Quell-Commits hatten denselben Git-Tree-Stand.
Darum starteten die Module mit denselben Vorschau-Funktionen. Die
NIKNOLIG-App enthält zusätzlich eine lokale Elektro-Engel-Oberfläche ohne
KI-/Backend-Anbindung oder Gerätezugriff. Beide Apps bieten jetzt getrennte
lokale Elektro-Engel-Designvorschauen: NIKNOLIG über die Assistenzseite,
Defense über die Startseite. Die neue Defense-Vorschau ist rein visuell,
keine operative Assistenz oder Sicherheitsfunktion. Änderungen an den
Quell-Repositories wurden nicht vorgenommen.

## Elektro-Engel als Systemfunktion

Elektro-Engel ist eine Funktion des NIKNOLIG-Systems, kein eigenes Projekt,
Repository oder eine separate App. NIKNOLIG und NIKNOLIG Defense bleiben
getrennte Apps mit eigenen Identitäten und Installationen. Die NIKNOLIG-App
enthält eine lokale Assistenzvorschau und ein lokales Lernprofil. Anfragen
werden nicht übertragen oder automatisch beantwortet; Geräteerkennung,
Verbindungen und Steuerbefehle sind nicht verfügbar. Es gibt keine gemeinsame
Laufzeit oder einen Datenaustausch mit NIKNOLIG Defense.

Die Designvorschauen zeigen fünf ausdrücklich beispielhafte Situationen,
simulierte Telefon-/Tablet-Zielgrößen und App-/Web-inspirierte Muster.
Zielwechsel übertragen nichts; echte Websites bleiben unverändert. Engel,
Statussymbol und Beschreibung bleiben statisch, ohne Blinken oder erfundenen
Fortschritt. Die drei Auswahlen werden bei Activity-Neuerstellung erhalten.

## Sicherheits- und Integrationsgrenzen

- Kein App-Modul hängt vom jeweils anderen ab; es gibt keine gemeinsame
  Laufzeitbibliothek und keine App-zu-App-Schnittstelle.
- Die eindeutigen `applicationId`s erlauben die parallele Installation und
  separate Android-App-Daten. Es werden keine Berechtigungen hinzugefügt.
- Die vorhandene Vorschau verwendet keine Netzwerk- oder Bluetooth-Berechtigung.
  Das Launcher-Activity ist exportiert; das Lernprofil-Activity bleibt nicht
  exportiert; auch beide Designvorschau-Activities sind nicht exportiert.
  Backups sind in beiden Manifesten deaktiviert.
- Websites, GitHub-Pages-Workflows und Cloudflare-Einstellungen wurden nicht
  verschoben oder verändert. Dieses Monorepo führt kein Website- oder
  Cloudflare-Deployment aus.

## Build und Prüfung

Voraussetzungen: JDK 17, Android SDK / compile SDK 35 und Gradle 8.13 (über den
mitgelieferten Wrapper).

Beide APKs unabhängig im selben Build aufbauen:

```sh
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug
```

Der Workflow
[`Android apps build`](.github/workflows/android-build.yml) baut beide Apps,
prüft ihre APK-IDs und verifiziert die APK-Signaturen. In den importierten
Quellständen sind keine Android-Testquellen vorhanden; deshalb wird kein
Android-Testtask behauptet.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und ist weder ein Anwendungstest noch ein Nachweis für eine
Cloudflare-Verbindung. Sein begrenzter Credential-Musterscan beweist nicht, dass
keine Geheimnisse vorhanden sind.

Weitere Inventur- und Cloudflare-Nachweise stehen im
[Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md).

## Gemeinsame Backend-Verträge

[`backend/`](backend/README.md) enthält einen lokalen, nicht produktionsfreigegebenen
Vertragsentwurf mit getrennten App-Bereichen, OpenAPI-Health-/Fehlerverträgen,
provisorischer Datenbankmigration, loopback-isolierter PostgreSQL-Compose-
Konfiguration und Tests. Eine lokale FastAPI-Laufzeit bedient nur Health-Routen;
es gibt keine App-Anbindung. Die operative Geräteintegration bleibt bis zur dokumentierten
SecurityChain-P0-Freigabe gesperrt.

Die Gerätewechsel-, Sensor- und Android-Abnahmeplanung ist in
[`docs/electro-engel-multidevice-sensors.md`](docs/electro-engel-multidevice-sensors.md)
dokumentiert; versionierte, deklarative Consent-/Sensorverträge liegen unter
[`backend/contracts/`](backend/contracts/). Es wurden keine Sensoren aktiviert
oder Geräte gekoppelt; die Laufzeitintegration bleibt P0-blockiert.

Die vorbereiteten Core-/Adapter-/App-Grenzen, Vertragsregeln und ein möglicher
späterer Extraktionspfad sind in
[`docs/electro-engel-architecture-and-migration.md`](docs/electro-engel-architecture-and-migration.md)
dokumentiert. Das ist keine Freigabe, ein Core-Modul, eine Runtime oder ein
separates Repository anzulegen.

Das Soll-Konzept für getrennte Gründerrollen und app-spezifische Konten steht in
[`docs/founder-roles-and-account-requirements.md`](docs/founder-roles-and-account-requirements.md).
Es wurden keine Konten angelegt; die produktive Rollenvergabe bleibt bis zur
SecurityChain-P0-Freigabe gesperrt.

Die plattformübergreifende Vertragsarchitektur, Android-/iOS-Grenzen und der
Integrationsplan für spätere separate iOS-Repositories stehen in
[`docs/mobile-cross-platform-architecture.md`](docs/mobile-cross-platform-architecture.md).
Es werden keine iOS-Repositories oder produktiven APIs angelegt.

Der lokale, einmalig ausführbare Ideen-Priorisierer ist in
[`docs/evolution-engine.md`](docs/evolution-engine.md) beschrieben. Er bewertet
nur belegte, kuratierte Vorschläge und nimmt selbst keine Dateiänderungen,
Builds, Netzwerkzugriffe oder Deployments vor.
