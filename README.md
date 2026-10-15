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

### Release-Signaturen: unabhängige Freigabe fehlt

Der [Release-Workflow](.github/workflows/android-release.yml) verwendet das
Environment `android-release` und zwei bestehende PKCS12-Keystores aus den
jeweiligen `NIKNOLIG_RELEASE_*`- bzw. `NIKNOLIG_DEFENSE_RELEASE_*`-Secrets.
Passwörter, Aliases, Keystores und Paket-IDs bleiben unverändert.

Die folgenden **beobachteten Zertifikat-Fingerprints sind keine freigegebenen
Vertrauensanker**:

| App / Paket-ID | Konfigurierter Keystore / Alias | Beobachteter Zertifikat-SHA-256 | Unabhängige Referenz / Status |
| --- | --- | --- | --- |
| NIKNOLIG / `com.niknolig.app` | `niknolig-release.p12` / `niknolig` | `59aad308bbba86fade464d15eee30edf4419e77e511dc6e4ee2cd1e01d351e92` | Keine im Repository oder geprüften Release-Nachweisen gefunden; Freigabe offen |
| NIKNOLIG Defense / `com.niknolig.defense` | `niknolig-defense-release.p12` / `niknolig-defense` | `a87cdd166d98f355735386d4681152b9557f5b103f5590ab09adcc2a0641c2ef` | Keine im Repository oder geprüften Release-Nachweisen gefunden; Freigabe offen |

Nachweis: vorhandener erfolgreicher
[Release-Lauf 38644626589](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38644626589)
vom 14.10.2026, Commit `89895e73b656631ace6cdc8bf4374b7e96016295`.
Die beiden APK-Artefakte wurden ohne Neubuild heruntergeladen, ihre Archiv-Digests
mit den Actions-Metadaten verglichen und ihre Signaturen mit
`apksigner verify --print-certs` geprüft. Die Tabelle enthält die
**Zertifikat-Digests**, nicht die Archiv- oder APK-Datei-Digests.
Die aktuellen Secret-Keystores und Passwörter sind in dieser Arbeitsumgebung
nicht verfügbar; ihre heutigen Fingerprints und Aliases konnten deshalb nicht
direkt ausgelesen werden. Der historische Lauf belegt die damals erfolgreiche
Signierung mit den konfigurierten Aliases, nicht die unveränderte Identität
heutiger Secrets. Auch [PR #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/13)
benennt die fehlende unabhängige Referenz ausdrücklich als offenen Blocker.

**Zwei manuell zu bestätigende Referenzwerte:**

1. Für NIKNOLIG den Zertifikat-SHA-256 der freigegebenen Release-Identität
   unabhängig bestätigen und als `NIKNOLIG_RELEASE_CERT_SHA256` hinterlegen.
2. Für NIKNOLIG Defense den Zertifikat-SHA-256 ihrer eigenen freigegebenen
   Release-Identität unabhängig bestätigen und als
   `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256` hinterlegen.

Beide Werte erst nach dokumentierter manueller Freigabe unter
[Settings → Environments → android-release → Environment variables](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/environments)
eintragen (64 Hex-Zeichen, optional mit Doppelpunkten). Als unabhängigen Nachweis
eine bereits freigegebene Zertifikat-Dokumentation bzw. eine separat verwahrte,
vertrauenswürdig zugeordnete Signaturidentität verwenden; Quelle und Freigabe
nachvollziehbar dokumentieren. Die oben beobachteten Werte dürfen nicht allein
wegen dieses Workflow-Laufs übernommen werden. Es gibt keinen automatischen
Fallback auf den gerade verwendeten Keystore und keine automatische Freigabe.

Fehlende oder formal ungültige Referenzen blockieren vor Keystore-Staging und
Build. Vor den getrennten Uploads müssen sowohl Keystore-Zertifikat als auch
APK-Signer der jeweiligen freigegebenen Referenz entsprechen. Die Prüfungen auf
genau eine APK und genau ein Signerzertifikat pro App, Paket-ID und gültige
APK-Signatur bleiben erhalten. Bis zur unabhängigen Bestätigung und erfolgreichen
Prüfung gegen die aktuellen Keystores bleibt der Release-Blocker offen.

**Separater Blocker:** Der gemeldete Android-Security-Scan-Fehler **HTTP 403**
ist hier nicht behoben und wird nicht durch erfolgreiche APK-Signaturprüfungen
entkräftet. Im aktuellen Repository ist kein eigener Android-Security-Scan-Workflow
vorhanden; ein nachweislich erfolgreicher Wiederholungslauf dieses Scans liegt
dieser Prüfung nicht vor.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und ist weder ein Anwendungstest noch ein Nachweis für eine
Cloudflare-Verbindung. Sein begrenzter Credential-Musterscan beweist nicht, dass
keine Geheimnisse vorhanden sind.

Weitere Inventur- und Cloudflare-Nachweise stehen im
[Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md).
