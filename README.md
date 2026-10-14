# NIKNOLIG-Monorepo

Monorepo für zwei getrennte Android-Apps: NIKNOLIG und NIKNOLIG Defense. Die
Apps bleiben eigenständige Installationen und Sicherheitsdomänen. Die Websites
und ihre Deployments bleiben in den jeweiligen Quell-Repositories.

## Android-Module

| Modul | Android `applicationId` | Quellstand |
| --- | --- | --- |
| `:niknolig` (`apps/niknolig`) | `com.niknolig.app` | [NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG/tree/3c4d6618a61604f6433639151e741371491a5f0d), Commit `3c4d6618a61604f6433639151e741371491a5f0d` |
| `:niknolig-defense` (`apps/niknolig-defense`) | `com.niknolig.defense` | [NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense/tree/5f0f385089bc27347eacd282c13a546eb4511da2), Commit `5f0f385089bc27347eacd282c13a546eb4511da2` |

Die App-Verzeichnisse beider Quell-Commits haben denselben Git-Tree-Stand.
Darum enthalten die Module derzeit dieselben Vorschau-Funktionen. Für die
Defense-App wurden Android-Namespace, Kotlin-Paket, `applicationId` und
Anzeigename getrennt; eine darüber hinausgehende Defense-Funktion ist im
Quellstand nicht belegt. Änderungen an den Quell-Repositories wurden nicht
vorgenommen.

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
[`Android apps build`](.github/workflows/android-build.yml) baut beide Apps,
prüft ihre APK-IDs und verifiziert die APK-Signaturen. In den importierten
Quellständen sind keine Android-Testquellen vorhanden; deshalb wird kein
Android-Testtask behauptet.

Für signierte Release-APK-Builds kann der Workflow manuell auf `main` mit
`release_candidate` aktiviert werden. Er benötigt getrennte, sicher gespeicherte
GitHub-Actions-Secrets für beide App-Keystores:

- NIKNOLIG: `NIKNOLIG_RELEASE_KEYSTORE_BASE64`,
  `NIKNOLIG_RELEASE_STORE_PASSWORD`, `NIKNOLIG_RELEASE_KEY_ALIAS` und
  `NIKNOLIG_RELEASE_KEY_PASSWORD`
- NIKNOLIG Defense: `NIKNOLIG_DEFENSE_RELEASE_KEYSTORE_BASE64`,
  `NIKNOLIG_DEFENSE_RELEASE_STORE_PASSWORD`, `NIKNOLIG_DEFENSE_RELEASE_KEY_ALIAS`
  und `NIKNOLIG_DEFENSE_RELEASE_KEY_PASSWORD`

Die Keystores werden nur während des CI-Laufs in einem zugriffsbeschränkten
temporären Verzeichnis abgelegt. Ohne diese Secrets bricht der Release-Workflow
vor dem Build ab; Secrets oder Keystores gehören nicht ins Repository. Die
signierten Artefakte werden geprüft und für 30 Tage als Workflow-Artefakte
gespeichert; der Workflow veröffentlicht oder deployed sie nicht.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und ist weder ein Anwendungstest noch ein Nachweis für eine
Cloudflare-Verbindung. Sein begrenzter Credential-Musterscan beweist nicht, dass
keine Geheimnisse vorhanden sind.

Weitere Inventur- und Cloudflare-Nachweise stehen im
[Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md).
