# NIKNOLIG-Monorepo

Monorepo für zwei getrennte Android-Apps: NIKNOLIG und NIKNOLIG Defense. Die
Apps bleiben eigenständige Installationen und Sicherheitsdomänen. Die Websites
und ihre Deployments bleiben in den jeweiligen Quell-Repositories.

## Android-Module

| Modul | Android `applicationId` | Quellstand |
| --- | --- | --- |
| `:niknolig` (`apps/niknolig`) | `com.niknolig.app` | [NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG/tree/3c4d6618a61604f6433639151e741371491a5f0d), Commit `3c4d6618a61604f6433639151e741371491a5f0d` |
| `:niknolig-defense` (`apps/niknolig-defense`) | `com.niknolig.defense` | [NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense/tree/5f0f385089bc27347eacd282c13a546eb4511da2), Commit `5f0f385089bc27347eacd282c13a546eb4511da2` |

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
[`Android apps build`](.github/workflows/android-build.yml) baut beide Apps,
prüft ihre APK-IDs und verifiziert die APK-Signaturen. In den importierten
Quellständen sind keine Android-Testquellen vorhanden; deshalb wird kein
Android-Testtask behauptet.

## Release-Signaturen und offene Freigabe

Der manuelle Release-Workflow verwendet das Environment `android-release`.
Er benötigt zusätzlich zu den unveränderten sechs Signing-Secrets zwei
unabhängig bestätigte SHA-256-Zertifikat-Fingerprints als Actions-Variablen:
`NIKNOLIG_RELEASE_CERT_SHA256` und `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256`.
Fehlende oder ungültige Werte blockieren bereits vor dem Build. Nach dem Build
müssen freigegebene Referenz, Zertifikat des ausgewählten Keystore-Alias und
APK-Signer übereinstimmen. Genau eine APK und genau ein Signer pro App,
Paket-ID-Prüfungen sowie getrennte Uploads bleiben vorgeschrieben.

### Befund vom 15.10.2026: beide Identitätsfreigaben noch offen

Im Repository und in der geprüften Release-Dokumentation ist keine unabhängig
freigegebene Zertifikatreferenz belegt.
[PR #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/13)
benennt diese Vertrauenslücke ausdrücklich. Der erfolgreiche
[Release-Lauf 38644626589](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38644626589)
verwendete bereits beide PKCS12-Secrets und die unten genannten Aliases,
protokollierte jedoch keine Zertifikat-Fingerprints.

Die vorhandenen APK-Artefakte dieses Laufs wurden ohne Neubuild mit
`apksigner verify --print-certs` erfolgreich geprüft; ihre Paket-IDs wurden mit
`aapt` bestätigt. Folgende Werte sind **nur beobachtete APK-Signer-Zertifikate,
keine unabhängig freigegebenen Vertrauensanker**:

| App | Beobachteter Zertifikat-SHA-256 | Workflow-Zuordnung | Unabhängige Referenz / Status |
| --- | --- | --- | --- |
| NIKNOLIG | `59aad308bbba86fade464d15eee30edf4419e77e511dc6e4ee2cd1e01d351e92` | `NIKNOLIG_RELEASE_KEYSTORE_BASE64` → `niknolig-release.p12`, Alias `niknolig`, Paket `com.niknolig.app` | Nicht belegt; Freigabe blockiert |
| NIKNOLIG Defense | `a87cdd166d98f355735386d4681152b9557f5b103f5590ab09adcc2a0641c2ef` | `NIKNOLIG_DEFENSE_RELEASE_KEYSTORE_BASE64` → `niknolig-defense-release.p12`, Alias `niknolig-defense`, Paket `com.niknolig.defense` | Nicht belegt; Freigabe blockiert |

Die tatsächlichen Release-Keystores und Passwörter waren in dieser
Arbeitsumgebung nicht verfügbar. Eine direkte erneute Messung der beiden
Keystore-Aliases ist deshalb hier **nicht erfolgt**; die historischen APKs
beweisen auch nicht den heutigen Inhalt der Secrets. Die Gradle-Konfigurationen
verwenden jeweils die passenden app-spezifischen Umgebungsvariablen und PKCS12.
ZIP-/APK-Datei-Hashes aus Upload-Logs sind keine Zertifikat-Fingerprints.

**Verbleibende manuelle Aktionen, jeweils getrennt auszuführen:**

1. Für NIKNOLIG den Zertifikat-SHA-256 des bestehenden Release-Alias `niknolig`
   über einen unabhängig vertrauenswürdigen Nachweis bestätigen und freigeben.
   Herkunft des Nachweises, freigebende Person und Datum dokumentieren; bei
   Abweichung vom beobachteten Wert zunächst die Identität klären.
   Erst danach `NIKNOLIG_RELEASE_CERT_SHA256` setzen.
2. Für NIKNOLIG Defense dieselbe unabhängige Bestätigung für den bestehenden
   Release-Alias `niknolig-defense` einholen und dokumentieren.
   Erst danach `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256` setzen.

Die beiden Werte sind jeweils 64 Hexzeichen (Groß-/Kleinschreibung und
Doppelpunkte werden normalisiert). Sie werden nach Freigabe unter den
[Environment-Einstellungen für android-release](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/environments)
als Variablen gepflegt; Environment-Zugriff und Freigaben müssen entsprechend
geschützt sein. Ein bloßes Kopieren aus diesen APKs oder aus dem gerade
verwendeten Keystore stellt **keine** unabhängige Freigabe dar. Es gibt keine
automatische Übernahme und keinen Fallback auf abgeleitete Werte.
Secrets, Passwörter, Aliases und Paket-IDs werden dafür nicht geändert.

### Separater offener Befund: Android-Security-Scan HTTP 403

Der bekannte HTTP-403-Fehler des Android-Security-Scans ist durch diese
Zertifikatsprüfung weder behoben noch als behoben nachgewiesen. Er bleibt
separat offen; erfolgreiche APK-Signaturprüfungen oder Workflow-Syntaxprüfungen
ersetzen keinen erfolgreichen Android-Security-Scan.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und ist weder ein Anwendungstest noch ein Nachweis für eine
Cloudflare-Verbindung. Sein begrenzter Credential-Musterscan beweist nicht, dass
keine Geheimnisse vorhanden sind.

Weitere Inventur- und Cloudflare-Nachweise stehen im
[Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md).
