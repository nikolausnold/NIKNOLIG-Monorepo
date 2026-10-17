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
KI-/Backend-Anbindung oder Gerätezugriff. Die Defense-App bleibt separat; für
sie ist darüber hinaus keine Defense-spezifische Funktion belegt. Änderungen
an den Quell-Repositories wurden nicht vorgenommen.

## Elektro-Engel als Systemfunktion

Elektro-Engel ist eine Funktion des NIKNOLIG-Systems, kein eigenes Projekt,
Repository oder eine separate App. NIKNOLIG und NIKNOLIG Defense bleiben
getrennte Apps mit eigenen Identitäten und Installationen. Die NIKNOLIG-App
enthält eine lokale Assistenzvorschau und ein lokales Lernprofil. Anfragen
werden nicht übertragen oder automatisch beantwortet; Geräteerkennung,
Verbindungen und Steuerbefehle sind nicht verfügbar. Es gibt keine gemeinsame
Laufzeit oder einen Datenaustausch mit NIKNOLIG Defense.

## Sicherheits- und Integrationsgrenzen

- Kein App-Modul hängt vom jeweils anderen ab; es gibt keine gemeinsame
  Laufzeitbibliothek und keine App-zu-App-Schnittstelle.
- Die eindeutigen `applicationId`s erlauben die parallele Installation und
  separate Android-App-Daten. Es werden keine Berechtigungen hinzugefügt.
- Die vorhandene Vorschau verwendet keine Netzwerk- oder Bluetooth-Berechtigung.
  Das Launcher-Activity ist exportiert; das Lernprofil-Activity bleibt nicht
  exportiert. Backups sind in beiden Manifesten deaktiviert.
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
[`Android preview APK checks (not release approval)`](.github/workflows/android-build.yml) baut beide Apps,
prüft ihre APK-IDs und verifiziert die APK-Signaturen. In den importierten
Quellständen sind keine Android-Testquellen vorhanden; deshalb wird kein
Android-Testtask behauptet. Ein grüner Lauf belegt diese Prüfungen und den
Artefakt-Upload, aber keine vollständige Funktion, Geräteverbindung,
Geräteabnahme oder Release-Freigabe.

Der separate Workflow
[`Sign Android artifacts (not store publication)`](.github/workflows/android-release.yml)
erstellt und prüft signierte APK-/AAB-Artefakte. Er lädt nichts in einen App
Store hoch und erteilt keine Veröffentlichungsfreigabe.

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
Konfiguration und statischen Vertragstests. Es gibt noch keinen API-Server oder
eine App-Anbindung. Die operative Geräteintegration bleibt bis zur dokumentierten
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

## Automatische Updates und Autobuild

- Bei Push und Pull Request sowie montags um 04:23 UTC und manuell laufen
  gemeinsame Vertrags-/Tooltests und der Build beider getrennten Android-Apps.
  Der Zeitplan wird erst nach Übernahme auf den Default-Branch aktiv; GitHub
  kann geplante Läufe verzögern oder bei inaktiven öffentlichen Repositories
  deaktivieren.
- [Dependabot](.github/dependabot.yml) schlägt wöchentlich Updates für Gradle
  und GitHub Actions als Pull Requests vor. Diese durchlaufen den Autobuild;
  es gibt keinen automatischen Merge und keine ungeprüfte Quellcodeübernahme.
- Das [Systemregister](config/system-repositories.json) erfasst dieses
  Monorepo, die bekannten NIKNOLIG-/Defense-Quellen und den noch offenen
  iOS-Anschluss. Auf `main` prüft der Autobuild die registrierten Repositories
  lesend über die GitHub-API. Der commitbezogene `system-update-report` zeigt
  Änderungen gegenüber den eingetragenen Quellständen; er importiert sie nicht.
  Nicht erreichbare/private Quellen ohne Leserecht lassen die Prüfung
  fehlschlagen, statt vollständige Systemkompatibilität vorzutäuschen.
- Das Artefakt `mobile-contracts-<Commit-SHA>` enthält dieselben OpenAPI- und
  JSON-Verträge für Android und spätere iOS-Verbraucher sowie das Systemregister.
  Neue Repositories müssen ausdrücklich im Register aufgenommen werden.
  Andere Repositories werden weder verändert noch ferngesteuert gebaut;
  ein erfolgreicher Monorepo-Build bestätigt nicht deren Builds oder Integration.
- Nach einem erfolgreichen `main`-Autobuild aus Push, Zeitplan oder manuellem
  Start erzeugt [Preparing release APKs](.github/workflows/android-release.yml)
  automatisch signierte APKs **genau des geprüften Commits**. PR-Builds und
  fehlgeschlagene Builds lösen keine Signierung aus. Die vorhandenen Freigaben
  des Environments `android-release` und seine sechs Signiergeheimnisse bleiben
  erforderlich; fehlende Geheimnisse stoppen den Release-Build.
- Release-Builds verwenden für beide Apps `versionCode = 1000 +` fortlaufende
  Release-Workflow-Laufnummer und `versionName = 0.1.<versionCode>`.
  Wiederholungen desselben Laufs behalten dieselbe Version; lokale Builds
  bleiben ohne `NIKNOLIG_VERSION_CODE` bei `0.1.0`/Code `1`.
  Der Release-Workflow darf nicht mit zurückgesetztem Versionszähler ersetzt
  werden. Vor einem Store-Anschluss muss der nächste Code über allen bereits
  verteilten Codes liegen; App-IDs und jeweilige Signierschlüssel bleiben stabil.

**Geräteseitige Updates sind noch nicht aktiviert.** APK-Artefakte sind keine
Store-Veröffentlichung; Debug-APKs sind kein Updatepfad für signierte Releases.
Für automatische Android-Updates braucht es einen freigegebenen Play-Store-
oder verwalteten Verteilungsweg. iOS benötigt eigene App-Repositories, Apple-
Signierung und einen TestFlight-/App-Store-Verteilungsweg. Ein stiller eigener
Installer oder die Umgehung von Plattformfreigaben wird nicht eingerichtet.
SecurityChain-P0 und die produktive Releasesperre bleiben bestehen.

Ergebnisse: [Autobuilds](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/android-build.yml)
und [signierte Builds](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/android-release.yml).

### Vorbereitung der Storeanbindung

Der Release-Workflow baut zusätzlich zu den bisherigen APKs zwei getrennte,
signierte Android App Bundles (`:niknolig:bundleRelease` und
`:niknolig-defense:bundleRelease`). JDK `jarsigner -verify -strict` prüft jedes
Bundle gegen den jeweiligen Keystore-Alias; fehlende, mehrere, unsignierte
oder nicht passend signierte Bundles stoppen den Lauf vor den Uploads.
Die commitbezogenen Artefakte `niknolig-store-aab-<Commit-SHA>` und
`niknolig-defense-store-aab-<Commit-SHA>` werden 14 Tage aufbewahrt. Sie sind
Vorbereitungsartefakte, keine Store-Freigabe oder vollständige Bundlevalidierung.
Vor einer späteren Einreichung ist ein frischer, erfolgreich geprüfter Build
mit noch nicht verwendeter Versionsnummer zu verwenden.

**Es gibt keinen Store-Upload, keine Store-Zugangsdaten und keine zeitgesteuerte
Aktivierung in einer Woche.** Die tatsächliche Anbindung benötigt anschließend:

1. Zwei getrennte App-Einträge in der
   [Google Play Console](https://play.google.com/console/) mit den unveränderten
   Paketnamen `com.niknolig.app` und `com.niknolig.defense`. Pro App sind
   Storetexte, Screenshots, Support-/Datenschutz-URL, Inhaltsbewertung,
   Zielgruppe und wahrheitsgemäße Angaben zur Datensicherheit vorzubereiten.
   Die dann geltenden Ziel-API-, Konto- und Testanforderungen sind vor Upload
   zu prüfen; das aktuelle `targetSdk = 35` ist keine Zusage der Storeannahme.
2. Vor dem ersten Upload pro App die
   [Play-App-Signing-Entscheidung](https://support.google.com/googleplay/android-developer/answer/9842756)
   dokumentieren: App-Signierschlüssel und Upload-Schlüssel sind unterschiedliche
   Rollen. Die vorhandenen Keystores werden nicht automatisch ersetzt. Falls
   bestehende APK-Installationen künftig Storeupdates erhalten sollen, muss
   die gewählte App-Signieridentität mit deren Updatepfad kompatibel sein.
   Freigegebene Zertifikat-Fingerprints und höchste bereits verteilte
   `versionCode`s sind unabhängig vom jeweiligen Build festzuhalten.
3. Erst nach SecurityChain-P0-/Produktfreigabe einen internen Test-Track
   einrichten und das geprüfte Bundle zunächst manuell hochladen.
   Paketname, Upload-Zertifikat und Versionsnummer durch Play prüfen lassen;
   Installation und Update einer Vorversion auf Geräten je App testen.
   Ein erfolgreicher Signaturcheck ersetzt weder diese Tests noch die
   Storeprüfung. Ein Rollback der Funktionalität benötigt im Store ebenfalls
   einen neuen, höheren Versionscode.
4. Für einen späteren automatisierten Upload einen eigenen, minimal berechtigten
   Zugang nach der
   [Google-Play-API-Einrichtung](https://developers.google.com/android-publisher/getting_started)
   vorsehen, auf die benötigten Apps und Test-Tracks begrenzen und in einem
   separat geschützten GitHub-Environment mit manueller Freigabe verwalten.
   Keine Zugangsschlüssel in Git oder Artefakte aufnehmen. Eine künftige
   Veröffentlichung muss den exakt geprüften Commit und seine Bundles verwenden;
   kein automatischer Produktions-Rollout als Folge eines normalen Autobuilds.
5. iOS bleibt ein separater Anschluss: In
   [Apple Developer](https://developer.apple.com/account/) und
   [App Store Connect](https://appstoreconnect.apple.com/) werden eigene
   App-Identitäten, Signierung, Datenschutzangaben und TestFlight-Prüfungen
   benötigt. Da hier kein iOS-App-Projekt existiert, erzeugt dieser Workflow
   weder ein iOS-Archiv noch einen iOS-Storeupload.
