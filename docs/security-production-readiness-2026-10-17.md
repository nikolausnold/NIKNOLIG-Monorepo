# NIKNOLIG – Security & Production Readiness Gates

- **Prüfdatum:** 2026-10-17
- **Prüfstand:** `copilot/android-build-checks`, Commit `692e44d02f55afc90bab6288aba5aeee24f314b7`
- **Gesamtergebnis:** **BLOCKED – keine technische Produktionsfreigabe**

Dieser Bericht trennt technische Prüfergebnisse von einer abschließenden
Gründerentscheidung. Er erteilt weder eine Produktionsfreigabe noch eine
Veröffentlichungserlaubnis. Ein erfolgreicher Build belegt nur die tatsächlich
ausgeführten Build-/Prüfschritte.

## Statusdefinition

- **PASS:** Der konkret genannte Prüfpunkt wurde für den genannten Commit und
  Umfang nachgewiesen. Das ist keine pauschale Sicherheitsfreigabe.
- **FAIL:** Eine ausgeführte Prüfung ist fehlgeschlagen.
- **BLOCKED:** Die Funktion oder Voraussetzung fehlt, ist nicht genehmigt oder
  kann ohne eine erforderliche Freigabe nicht sicher geprüft werden.
- **NOT TESTED:** Es liegt kein entsprechender Prüflauf oder Nachweis vor.

## Ergebnismatrix

| Prüfpunkt | NIKNOLIG Android | NIKNOLIG iOS | NIKNOLIG Defense Android | NIKNOLIG Defense iOS | Backend / Supabase |
| --- | --- | --- | --- | --- | --- |
| App-/Plattformgrenzen | **PASS** – eigenes Gradle-Modul und `com.niknolig.app` | **BLOCKED** – iOS-Prototyp nur im ungemergten PR #26 | **PASS** – eigenes Gradle-Modul und `com.niknolig.defense` | **BLOCKED** – iOS-Prototyp nur im ungemergten PR #26 | **PASS (Umfang)** – deklarative gemeinsame Verträge, keine gemeinsame Laufzeit oder Rechte |
| Debug-/Simulator-Build | **PASS, nur `main`-SHA `dca6b1b`** (#246); aktueller Branch-Lauf #249: **BLOCKED** (`action_required`, null Jobs) | **BLOCKED** – iOS-Läufe #1/#2 `action_required`, null Jobs | **PASS, nur `main`-SHA `dca6b1b`** (#246); aktueller Branch-Lauf #249: **BLOCKED** | **BLOCKED** – iOS-Läufe #1/#2 `action_required`, null Jobs | **NOT TESTED in aktuellem Actions-Lauf** – Backend-Run #15 `action_required`, null Jobs; lokale Regressionstests siehe unten |
| Unit-/Negativtests und Lint | **NOT TESTED** – keine Android-App-Testquellen; Android-Workflow ruft weder App-Unit-Tests noch Lint auf | **BLOCKED** – kein ausgeführter iOS-Testlauf; PR-Prototyp hat nur Identitätstests | **NOT TESTED** – keine Android-App-Testquellen; kein App-Lint-Nachweis | **BLOCKED** – kein ausgeführter iOS-Testlauf; PR-Prototyp hat nur Identitätstests | **PASS, begrenzt** – 13 lokale Backend-Regressionstests bestanden; keine Auth-/RLS-/Replay-Negativtests |
| Release-Build, Signatur, Artefakte | **PASS, technisch begrenzt** – APK/AAB-Build und Signaturvergleich in #58; kein Store-Upload | **NOT TESTED** – kein signierter Archive-/Export-Build | **PASS, technisch begrenzt** – APK/AAB-Build und Signaturvergleich in #58; kein Store-Upload | **NOT TESTED** – kein signierter Archive-/Export-Build | **BLOCKED** – kein produktiver Backend-Betrieb oder Deployment geprüft |
| SecurityChain P0, Authentifizierung, Autorisierung, Zustandsmaschine | **BLOCKED** – nicht implementiert/freigegeben | **BLOCKED** – nicht implementiert/freigegeben | **BLOCKED** – nicht implementiert/freigegeben | **BLOCKED** – nicht implementiert/freigegeben | **BLOCKED** – nur Health-Routen; kein Produkt-Auth/API |
| BLE/Geräteverbindung, Fehler, Widerruf, Wiederverbindung | **BLOCKED** – keine Laufzeitimplementierung oder Berechtigungen | **BLOCKED** – nicht implementiert | **BLOCKED** – keine Laufzeitimplementierung oder Berechtigungen | **BLOCKED** – nicht implementiert | **BLOCKED** – keine Geräte-/Pairing-API |
| Zwei-Geräte-Abnahme | **NOT TESTED** | **NOT TESTED** | **NOT TESTED** | **NOT TESTED** | **NOT TESTED** |
| Store-Voraussetzungen, Datenschutz-/Restore-Nachweise | **NOT TESTED** | **NOT TESTED** | **NOT TESTED** | **NOT TESTED** | **BLOCKED / NOT TESTED** – kein Supabase, kein produktiver Dienst, keine RLS-/Restore-Prüfung |

## Getrennte Plattformbefunde

### NIKNOLIG Android

- Die Modul- und Paketidentität ist getrennt: `:niknolig`,
  `com.niknolig.app`; Android-Konfiguration setzt `minSdk 26`, `targetSdk 35`,
  JDK 17, Version `0.1.0` und lokalen Standard-`versionCode 1`.
- Manifest: Backup deaktiviert; Launcher-Activity exportiert, interne Activities
  nicht exportiert. Keine Netzwerk-, Bluetooth- oder Sensorberechtigungen. Das
  ist eine minimale Vorschau-Berechtigungsfläche, kein Nachweis einer
  Gerätefunktion.
- [Android-Lauf #246](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39021888482)
  war auf `main`, SHA `dca6b1bd808e266b4feb9d40be44c6952d9a95d4`, erfolgreich:
  Backend-/Tooling-Regressionstests, beide Debug-APK-Builds, Paket-ID- und
  Signaturprüfung sowie Uploads. Der Lauf beweist keine Release-Funktion.
- [Release-Lauf #58](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39021989663)
  auf demselben `main`-SHA war erfolgreich. APKs und AABs wurden gebaut,
  Paket-IDs geprüft und APK-Zertifikate mit den Zertifikaten der in diesem Lauf
  verwendeten Keystores verglichen. Der manuelle Contract-Test-Schritt wurde
  bei diesem `workflow_run` **übersprungen**. Die Artefakte wurden in Actions
  hochgeladen; sie wurden nicht in einen Store veröffentlicht. Der Vergleich
  mit dem Keystore desselben Laufs ist **keine unabhängige Freigabe** eines
  erwarteten Signatur-Fingerabdrucks.
- Für den aktuellen Audit-Branch ist [Lauf #249](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39022543193)
  `action_required`; die Jobabfrage ergab **null Jobs**. Daher ist der hier
  geprüfte Commit nicht durch diesen Workflow gebaut.
- Keine Android-App-Unit-/Instrumentierungstests, Lint-, Emulator- oder
  Zwei-Geräte-Abnahme sind nachgewiesen. Die Workflow-Schritte und die
  Manifest-/Buildkonfiguration sind unter
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/.github/workflows/android-build.yml`,
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/build.gradle.kts`
  und
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/src/main/AndroidManifest.xml`
  nachvollziehbar.

### NIKNOLIG iOS

- Im Audit-Checkout gibt es kein iOS-Projekt. Ein einfacher iOS-Prototyp mit
  Bundle-ID `com.niknolig.app.ios` liegt im **offenen, nicht gemergten**
  [PR #26](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/26), Commit
  `3a5ef6d39c987363f0d050c6130764214df04391`. Das ist kein Bestandteil des
  geprüften Audit-Commits oder des `main`-Build-Nachweises.
- Die PR-Workflowläufe [#1](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39020183412)
  und [#2](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39020186170)
  endeten `action_required`; beide hatten **null Jobs**. Kein macOS/Xcode-Build
  oder XCTest-Ergebnis wird behauptet.
- Der PR-Workflow sieht einen Debug-Simulatorlauf mit
  `CODE_SIGNING_ALLOWED=NO` vor. Das ist ausdrücklich kein Geräte- oder
  Release-Signing-Nachweis. Im Xcode-Projekt steht zwar automatischer
  Signierstil für Release, aber Zertifikat, Provisioning Profile, signiertes
  Archiv und Export/Store-Validierung wurden nicht nachgewiesen.
- Der Prototyp enthält eine lokale SwiftUI-Vorschau und Identitätstests, aber
  keine Assistenz-, Geräte-, Backend- oder P0-Sicherheitsfunktion.

### NIKNOLIG Defense Android

- Separates Modul und getrennte Paketidentität `:niknolig-defense` /
  `com.niknolig.defense`; die Android-Build- und Release-Läufe #246/#58
  enthalten beide Apps und weisen Debug-/Release-Paketidentität und
  Signaturprüfung für die Defense-APK nach.
- Auch hier gilt: Die Nachweise beziehen sich auf `main`-SHA
  `dca6b1bd808e266b4feb9d40be44c6952d9a95d4`, nicht auf den Audit-Branch. Der
  Branch-Lauf #249 hatte null Jobs.
- Keine App-Unit-/Instrumentierungstests oder Lint-Prüfung; keine
  Zwei-Geräte-/Defense-Autorisierungsprüfung. Manifest, Versionierung und
  übrige Grenzen entsprechen den separat geprüften Dateien unter
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/`.

### NIKNOLIG Defense iOS

- Ein eigenständiger Prototyp mit Bundle-ID `com.niknolig.defense.ios` und
  eigener Identitätstestdatei ist nur im offenen PR #26 vorhanden. Das Xcode-
  Projekt ist in `ios/niknolig-defense/` vom NIKNOLIG-Xcode-Projekt getrennt.
- PR-iOS-Läufe #1/#2 sind `action_required` mit null Jobs. Simulator-Build,
  XCTest, Signierung, Release-Archiv, Berechtigungs-/Entitlements- und
  Store-Prüfung sind nicht ausgeführt.
- Es gibt keine implementierte Defense-Geräteverbindung, Authentifizierung,
  Autorisierung oder SecurityChain-P0-Funktion. Der Prototyp allein ist keine
  Produktions-App.

## Backend, Supabase und gemeinsame Sicherheitsgates

- `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/app.py` stellt
  nur `/health/live`, `/health/ready` und generische 404-Antworten bereit.
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/openapi.yaml`
  bezeichnet Bearer-Auth ausdrücklich als zukünftige, nicht implementierte
  Anforderung. Es gibt keine produktiven Endpunkte, Tokenausgabe/-validierung,
  App-Bereich-Autorisierung oder produktive Serverkonfiguration.
- Die Migration
  `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/migrations/001_initial_contract.sql`
  ist als Vorschlag markiert und gesperrt. Sie definiert **keine**
  Row-Level-Security-Policies. Die Compose-Datenbank ist eine lokale
  PostgreSQL-Entwicklungsumgebung, loopback-gebunden und ohne API-Service.
- Im geprüften Repository wurden keine Supabase-Konfiguration, Supabase-Clients
  oder RLS-Policies gefunden. Folglich sind RLS-, Rollen-, API-Zugriffs-,
  Datenschutz-, Backup-/Restore- und Produktionskonfigurationsprüfungen
  **BLOCKED** oder **NOT TESTED**, nicht bestanden.
- Die SecurityChain-P0-Vorgaben und Produkt-/Sicherheitsentscheidungen sind
  laut `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/README.md`
  noch nicht genehmigt. Das Sicherheitsdesign verbietet Implementierung bis zu
  diesen Freigaben. Es gibt keine implementierte Geräte-State-Machine,
  Authentifizierung, Pairing, Replay-Abwehr, Widerruf oder Wiederverbindung.
- [Backend-Workflow #15](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39020186142)
  für PR #26 endete `action_required` mit **null Jobs**. Die lokalen
  Regressionstests des aktuellen Audit-Branches liefen zuvor erfolgreich:
  13 Backend- und 32 Tooling-Tests. Sie decken Verträge, Health-Routen und
  Tooling ab, nicht Authentifizierung, Berechtigungen, BLE, State-Machine-
  Negativtests, RLS oder echte Geräte.

## Supply Chain, Secrets und Workflow-Nachweise

- Eine Advisory-Datenbankabfrage für Android Gradle Plugin `8.11.1`,
  Kotlin-Gradle-Plugin `2.2.21`, `actions/checkout` `7.0.0`,
  `actions/setup-java` `5.0.0` und `actions/upload-artifact` `7.0.2` meldete
  keine bekannten Advisories für diese angegebenen Versionen. Das ist kein
  vollständiger transitive dependency-, SBOM-, Container- oder Lizenzscan.
- Dependabot ist für Gradle und GitHub Actions wöchentlich konfiguriert.
  Die Gradle-Wrapper-Konfiguration pinnt Gradle `8.13`, enthält aber keine
  Distribution-Checksumme. Gradle-Dependency-Lockfiles/SBOM- und
  Schwachstellen-Scans sind im vorhandenen Workflow nicht nachgewiesen.
- Es wurden keine produktiven Secrets gelesen und keine Server-/Store-Aktion
  ausgeführt. GitHub Secret- und Code-Scanning-Alert-APIs antworteten in dieser
  Prüfung mit `403 Resource not accessible by integration`; ihr Alert-Status
  ist deshalb **NOT TESTED**, nicht „keine Alerts“. Eine Quelltextprüfung
  ersetzt keinen Zugriff auf Secret-Scopes oder GitHub-Sicherheitseinstellungen.
- Die letzten erfolgreichen Android-Läufe gehören zu `main`-SHA
  `dca6b1bd808e266b4feb9d40be44c6952d9a95d4`. Branch-/PR-Läufe mit
  `action_required` und null Jobs wurden nicht als fehlgeschlagen oder bestanden
  umgedeutet.

## Blocker und notwendige nächste Nachweise

1. **P0:** SecurityChain-P0-Anforderungen, Daten-/Aktionsumfang,
   Nutzerzustimmung, Vertrauensmodell, Identitäts-/Schlüssel-Lebenszyklus und
   Fehler-/Widerrufsverhalten schriftlich genehmigen.
2. **P0:** Erst danach produktive Authentifizierung und per-App-/Ressourcen-/
   Aktionsautorisierung implementieren; Negativtests für falsche Identität,
   Scope, abgelaufene/widerrufene Zustimmung, Replay, manipulierte Eingaben,
   ungültige Zustandsübergänge und Ausfälle ergänzen.
3. **P0:** Transport (einschließlich BLE, falls gewählt), Berechtigungen,
   gegenseitige Authentifizierung, Verschlüsselung und Wiederverbindung nach
   unabhängiger Sicherheitsprüfung implementieren. Auf beiden Android-Apps und
   beiden iOS-Apps plattformspezifisch testen; Zwei-Geräte-Abnahme dokumentieren.
4. **P1:** iOS-Prototyp-PR #26 freigeben/mergen, bevor daraus ein
   `main`-Buildnachweis abgeleitet wird; danach macOS/Xcode-Tests tatsächlich
   ausführen. Für iOS Release Signing und Archive/Export einen separaten
   genehmigten Prozess nachweisen.
5. **P1:** Android-App-Unit-/Instrumentierungstests und Lint für beide Module
   hinzufügen und ausführen. Unabhängig freigegebene Signatur-Fingerabdrücke
   sowie Store-Metadaten, Datenschutzangaben und Rollback-Verfahren prüfen.
6. **P1:** Falls Supabase oder eine andere Datenbank gewählt wird,
   Zugriffskontrollen/RLS, Rollen, Isolation zwischen beiden Apps, Migrationen,
   Datenaufbewahrung/-löschung, Backup und Restore gegen Negativfälle testen.
7. **P2:** Vollständigen Dependency-/Container-/SBOM- und Secret-Alert-Status
   mit ausreichenden Repository-Berechtigungen nachweisen; Gradle-Wrapper-
   Distribution verifizieren/pinnen.
8. Erst nach technischen Nachweisen entscheidet die Gründerseite separat über
   eine Produktionsfreigabe. Dieser Bericht und erfolgreiche Builds ersetzen
   diese Entscheidung nicht.

## Durchgeführte / nicht durchgeführte Aktionen

Die bestehende Workflow-Historie und Job-/Artefaktmetadaten wurden ausgewertet;
erfolgreiche Läufe wurden nicht wiederholt. Die lokalen Backend-/Tooling-
Regressionstestergebnisse wurden aus dem aktuellen Commit wiederverwendet.
Keine Workflows wurden erneut gestartet oder wiederholt; keine echten Secrets,
Deployments, Migrationen, Store-Uploads, Veröffentlichungen oder externen
API-Freigaben wurden ausgeführt. Die technische Freigabereife bleibt
**BLOCKED**; die Gründerentscheidung ist **nicht erteilt**.
