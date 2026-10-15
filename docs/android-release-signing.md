# Android-Release-Signaturen

## Aktueller Stand

Der Release-Workflow verwendet im GitHub-Environment `android-release` getrennte
PKCS12-Keystores und Aliases:

| App | Paket-ID | Alias | Konfiguration des unabhängigen Referenzwerts |
| --- | --- | --- | --- |
| NIKNOLIG | `com.niknolig.app` | `niknolig` | Environment-Variable `NIKNOLIG_RELEASE_CERT_SHA256` |
| NIKNOLIG Defense | `com.niknolig.defense` | `niknolig-defense` | Environment-Variable `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256` |

Die Release-Prüfung vergleicht weiterhin Paket-ID, genau eine APK pro App,
APK-Signatur und Keystore-Zertifikat. Zusätzlich müssen jetzt Keystore und APK
jeweils mit dem separat freigegebenen SHA-256-Referenzwert übereinstimmen.
Fehlende oder ungültige Referenzwerte stoppen den Workflow vor dem Keystore-
Staging und vor dem Build.

## Manuelle Freigabe erforderlich

Im Repository-Checkout sind keine Release-Keystore-Dateien vorhanden. Die
Fingerprints lassen sich daher hier nicht sicher aus den unter GitHub Actions
verwahrten Keystores auslesen. Die verfügbaren früheren Release-Logs enthalten
keine Zertifikat-Fingerprints. Ein aus einem aktuell verwendeten Keystore
ermittelter Wert wäre außerdem kein unabhängiger Vertrauensanker.

Für beide Apps sind daher die folgenden Werte noch manuell aus einer
unabhängigen, vertrauenswürdigen Dokumentation zu bestätigen und freizugeben;
jeweils als SHA-256-Zertifikat-Fingerprint mit 64 Hex-Zeichen:

- **NIKNOLIG / Alias `niknolig`:** Wert für `NIKNOLIG_RELEASE_CERT_SHA256` —
  **manuell zu bestätigen und freizugeben**.
- **NIKNOLIG Defense / Alias `niknolig-defense`:** Wert für
  `NIKNOLIG_DEFENSE_RELEASE_CERT_SHA256` — **manuell zu bestätigen und
  freizugeben**.

Die bestätigten Werte sind als Environment-Variablen im Environment
[`android-release`](https://github.com/nikolausnold/NIKNOLIG-Monorepo/settings/environments)
einzutragen. Nicht aus dem für denselben Release verwendeten Keystore oder
dessen Workflow-Ausgabe ableiten. Bis beide Werte vorhanden und unabhängig
freigegeben sind, bleibt der Release-Workflow absichtlich blockiert.

## Separater Android-Security-Scan-Fehler

Der bekannte HTTP-403-Fehler des Android-Security-Scans ist ein separater,
weiterhin offener Punkt. Er wurde durch diese Signaturänderung nicht behoben
und in diesem Task nicht als behoben verifiziert.
