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

## Release-Zertifikate: unabhängige Freigabe ausstehend

Der manuelle [Release-Workflow](.github/workflows/android-release.yml) verwendet
das Environment `android-release` und unverändert sechs Signing-Secrets. Die
PKCS12-Dateien werden daraus temporär bereitgestellt; im Repository und in der
Audit-Umgebung sind weder diese Keystores noch ihre Passwörter verfügbar.

Die folgenden **beobachteten APK-Zertifikat-Fingerprints sind keine freigegebenen
Vertrauensanker**. Sie stammen aus den bereits vorhandenen, mit `apksigner verify
--print-certs` erfolgreich geprüften APKs des
[Release-Laufs 38644626589](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38644626589)
vom 14.10.2026, Commit `89895e73b656631ace6cdc8bf4374b7e96016295`. Die
Archiv-Digests wurden gegen die Actions-Artefaktmetadaten geprüft; sie sind
nicht die Zertifikat-Fingerprints.

| App | Beobachteter Zertifikat-SHA-256 (APK) | Konfigurierte PKCS12-Datei / Alias | Unabhängige Referenz / Status |
| --- | --- | --- | --- |
| NIKNOLIG (`com.niknolig.app`) | `59aad308bbba86fade464d15eee30edf4419e77e511dc6e4ee2cd1e01d351e92` | `niknolig-release.p12` / `niknolig` | Nicht belegt; Freigabe blockiert |
| NIKNOLIG Defense (`com.niknolig.defense`) | `a87cdd166d98f355735386d4681152b9557f5b103f5590ab09adcc2a0641c2ef` | `niknolig-defense-release.p12` / `niknolig-defense` | Nicht belegt; Freigabe blockiert |

Eine direkte Messung der **aktuellen Keystore-Zertifikate und Prüfung der
tatsächlich enthaltenen Aliases** war ohne Zugriff auf die bestehenden
Environment-Secrets nicht möglich. Die Dateinamen, Alias- und Paket-ID-Referenzen
passen zur Gradle-Konfiguration beider Apps. Die alten APKs belegen weder den
aktuellen Secret-Inhalt noch dessen unabhängige Freigabe. Der genannte Lauf
liegt vor der Keystore/APK-Vergleichsprüfung aus
[PR #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/13);
auch diese Prüfung allein stellt keinen unabhängigen Vertrauensnachweis dar.
Im untersuchten Repository und den geprüften Release-Nachweisen wurde keine
unabhängig dokumentierte Freigabe gefunden; die aktuellen Environment-Variablen
konnten hier nicht eingesehen werden.

**Genau zwei Referenzwerte sind noch manuell zu bestätigen und freizugeben:**

1. Für **NIKNOLIG** den SHA-256 des genehmigten Release-Zertifikats aus einer
   unabhängig authentifizierten Quelle bestätigen, mit dem Zertifikat des
   vorhandenen Keystores unter Alias `niknolig` vergleichen und nach Freigabe
   als Environment-Variable `NIKNOLIG_RELEASE_CERT_SHA256` hinterlegen.
2. Für **NIKNOLIG Defense** denselben unabhängigen Abgleich für Alias
   `niknolig-defense` durchführen und den freigegebenen Wert als
   `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256` hinterlegen.

Die zuständige Person muss Quelle, Prüfer, Datum und Freigabe nachvollziehbar
festhalten. Geeignet ist beispielsweise ein bereits unabhängig bestätigter
Zertifikatsnachweis oder ein authentifiziertes Signing-Inventar; ein Export
aus dem gerade verwendeten Keystore oder die obigen APK-Messwerte allein
reichen nicht. Nicht ungeprüft übernehmen und keine neuen Keystores erzeugen.
Die Variablen sind öffentliche Zertifikat-Referenzen, keine Passwörter.
Verwaltung und Freigabeschutz:
[Environment android-release](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/environments).
Bestehende Secrets, Passwörter, Aliases und Paket-IDs bleiben unverändert.

Der Workflow bricht bei fehlender oder ungültiger Referenz **vor dem Build**
ab. Vor beiden getrennten Uploads müssen Paket-ID, genau eine APK pro App,
genau ein APK-Signer, gültige APK-Signatur, Keystore/APK-Gleichheit und der
Abgleich beider Zertifikate mit der jeweiligen Referenz erfolgreich sein.
Es gibt keine automatische Erzeugung oder Übernahme von Referenzwerten.

**Separater offener Befund:** Der bekannte Android-Security-Scan-Fehler
**HTTP 403** ist durch diese Signaturprüfung nicht behoben. Eine nachgewiesene
Behebung liegt hier nicht vor; erfolgreiche APK-Builds oder Zertifikatsprüfungen
ersetzen diesen Security-Scan nicht. Es wurde für diese Untersuchung kein
Release-Build, keine Veröffentlichung und kein Merge ausgelöst.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und ist weder ein Anwendungstest noch ein Nachweis für eine
Cloudflare-Verbindung. Sein begrenzter Credential-Musterscan beweist nicht, dass
keine Geheimnisse vorhanden sind.

Weitere Inventur- und Cloudflare-Nachweise stehen im
[Master-Integrationsplan](docs/MASTER-INTEGRATION-PLAN.md).
