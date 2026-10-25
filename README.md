# NIKNOLIG-Monorepo

Dieses Repository enthält die getrennten Android-Module unter `apps/` und zwei
native iOS-Vorschauziele unter `apps/ios/`. Android- und iOS-Projekte sowie deren
Builds sind getrennt zu behandeln. Die externe Android-Quelle für NIKNOLIG ist
`nikolausnold/NIKNOLIG/app`; das owner-designierte aktive
NIKNOLIG-Defense-App-Repository ist
[`nikolausnold/-niknolig-defense`](https://github.com/nikolausnold/-niknolig-defense).
Das separate Repository
[`nikolausnold/-NIKNOLIG-Defense-Website`](https://github.com/nikolausnold/-NIKNOLIG-Defense-Website)
ist archiviert und keine aktuelle Website-Quelle. Ein separates iOS-Monorepo enthält
beide iOS-Projekte; die lokalen Vorschauziele bleiben zusätzlich hier. Websites
und Deployments bleiben in ihren Quell-Repositories.

## Android-Module

| Modul | Android `applicationId` | Quellstand |
| --- | --- | --- |
| `:niknolig` (`apps/niknolig`) | `com.niknolig.app` | [NIKNOLIG `app/`, `main` @ `2531bdfa`](https://github.com/nikolausnold/NIKNOLIG/tree/2531bdfa9a4c7e949c2778fbf515c132fed9d4d3/app) |
| `:niknolig-defense` (`apps/niknolig-defense`) | `com.niknolig.defense` | [Owner-designiertes aktives NIKNOLIG-Defense-App-Repository](https://github.com/nikolausnold/-niknolig-defense) (GitHub-API während dieses Audits nicht lesbar; daher keine Revision bestätigt) |

| Produkt | Lokales iOS-Ziel | Separates iOS-Projekt |
| --- | --- | --- |
| NIKNOLIG | [`apps/ios/NIKNOLIG.xcodeproj`](apps/ios/NIKNOLIG.xcodeproj), `NIKNOLIGApp.swift` | [`nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/apps/niknolig-ios`](https://github.com/nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/tree/afe4f5a3f0b84500437484a3bf0b3976d7b99e58/apps/niknolig-ios), `main` @ `afe4f5a3` |
| NIKNOLIG Defense | [`apps/ios/NIKNOLIG.xcodeproj`](apps/ios/NIKNOLIG.xcodeproj), `NIKNOLIGDefenseApp.swift` | [`nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/apps/niknolig-defense-ios`](https://github.com/nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/tree/afe4f5a3f0b84500437484a3bf0b3976d7b99e58/apps/niknolig-defense-ios), `main` @ `afe4f5a3` |

Die lokalen iOS-Ziele sind getrennte Targets und teilen weder Laufzeitcode noch
App-Daten mit Android oder der jeweils anderen App. Das NIKNOLIG-Quellrepository
enthält zusätzlich einen `ios/`-Ordner; ein verbindliches Verhältnis zwischen
diesen externen iOS-Ablagen ist nicht nachgewiesen.

## Offizielle Websites und App-Zuordnung

| Produkt | Offizielle Website für Android und iOS | Website-Quelle und Veröffentlichungsweg |
| --- | --- | --- |
| NIKNOLIG | [https://niknolig.com/](https://niknolig.com/) | `nikolausnold/NIKNOLIG`: `index.html`, `styles.css`, `assets/niknolig-mark.svg`; `.github/workflows/deploy-website.yml` veröffentlicht mit GitHub Pages. Lauf [#36](https://github.com/nikolausnold/NIKNOLIG/actions/runs/39954787871) war auf `main` erfolgreich und setzte die Workflow-URL auf `https://niknolig.com/`. |
| NIKNOLIG Defense | [https://defense.niknolig.com/](https://defense.niknolig.com/) | Laut aktueller Produktvorgabe wird die Website im aktiven App-Repository [`nikolausnold/-niknolig-defense`](https://github.com/nikolausnold/-niknolig-defense) gepflegt. Das separate Repository `nikolausnold/-NIKNOLIG-Defense-Website` ist archiviert; seine früheren Pages-Läufe belegen keine aktuelle Veröffentlichung. |

Beide Android-Supportseiten und beide nativen iOS-Supportansichten öffnen die
jeweilige offizielle URL extern im Browser. Es gibt keine WebView, Android-App-
Link-/Intent-Filter oder iOS-Associated-Domain-Konfiguration für diese Websites.
Die Android-Apps verwenden jeweils eine produktspezifische, fest konfigurierte
HTTPS-URL mit `ACTION_VIEW`. Browser-Ladevorgang, TLS-Fehler, Timeouts und
Wiederholungen liegen außerhalb der App; die App zeigt eine lesbare Meldung,
wenn kein Browser zum Öffnen gefunden wird. Die Live-Prüfung am 23.10.2026
scheiterte für beide Domains bereits an der DNS-Auflösung (`curl`-Fehler 6);
HTTP-Antwort, TLS-Zertifikat und Redirects konnten daher nicht geprüft werden.
Das ist kein Nachweis allgemeiner Nichterreichbarkeit.

Der [App-Web-Designabgleich](docs/app-web-design-alignment.md) dokumentiert
die gemeinsame Farbpalette und die absichtlich getrennten Produktlayouts.

Die ursprünglichen App-Verzeichnisse beider Quell-Commits hatten denselben Git-Tree-Stand.
Darum starteten die Module mit denselben Vorschau-Funktionen. Die
NIKNOLIG-App enthält zusätzlich eine lokale Elektro-Engel-Oberfläche ohne
KI-/Backend-Anbindung oder Gerätezugriff. Eigene Aufgaben bleiben lokal, werden
nicht übertragen und nicht automatisch ausgeführt. Eine gespeicherte
Sitzungskurzfassung kann nach ausdrücklicher Auswahl als lokaler Analysekontext
eingefügt werden. Die Defense-App bleibt separat; für
sie ist darüber hinaus keine Defense-spezifische Funktion belegt. Änderungen
an den Quell-Repositories wurden nicht vorgenommen.

## Elektro-Engel als Systemfunktion

Elektro-Engel ist eine Funktion des NIKNOLIG-Systems, kein eigenes Projekt,
Repository oder eine separate App. NIKNOLIG und NIKNOLIG Defense bleiben
getrennte Apps mit eigenen Identitäten und Installationen. Die NIKNOLIG-App
enthält eine lokale Assistenzvorschau, eine lokale Aufgabenliste und ein lokales
Lernprofil. Aufgaben werden nicht übertragen oder automatisch ausgeführt.
Anfragen werden nicht übertragen oder automatisch beantwortet; eine gespeicherte
Sitzungszusammenfassung wird nur nach ausdrücklicher Auswahl als lokaler
Analysekontext eingefügt. Geräteerkennung,
Verbindungen und Steuerbefehle sind nicht verfügbar. Es gibt keine gemeinsame
Laufzeit oder einen Datenaustausch mit NIKNOLIG Defense.

**Verbindliches Produktziel:** Ein kontrollierter, authentifizierter
Datenaustausch zwischen NIKNOLIG und NIKNOLIG Defense auf Android und iOS über
das gemeinsame Backend `https://api.niknolig.com`, bei weiterhin getrennten
App-Identitäten und Berechtigungen. Dieses Ziel ist noch nicht implementiert:
die vorhandenen Verbindungen prüfen ausschließlich Health-Endpunkte. Die
Sicherheits- und Produktentscheidungen für konkrete Datenflüsse, Identitäten,
Gerätekopplung und Widerruf bleiben erforderlich; bis dahin findet kein
produktiver Datenaustausch statt.

**Bestätigte Produktgrenzen (D-01, 21.10.2026):** NIKNOLIG umfasst allgemeine
Systemfunktionen; NIKNOLIG Defense zusätzliche Sicherheits- und Notfallfunktionen.
Elektro-Engels Infrastruktur-Erkennung und Reparaturhinweise gehören
ausschließlich zu Defense. Keine Infrastruktur-Erkennung in der normalen
NIKNOLIG-App; die dort vorhandene lokale Assistenzvorschau ist davon getrennt.
Das ist keine Implementierungs- oder Datenfreigabe.
[D-01-Prüfprotokoll und offene Detailentscheidungen](docs/securitychain-p0-specification.md#d-01-prüfprotokoll-bestätigte-produktgrenzen-und-offene-detailfreigaben)
dokumentieren den Funktionsumfang beider Apps und die fehlenden Bestätigungen;
D-01 ist noch nicht abgeschlossen, D-02 bis D-12 bleiben unverändert offen.

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

Voraussetzungen: JDK 17, Android SDK / compile SDK 35 und Gradle 8.14.6 (über den
mitgelieferten Wrapper).

Beide APKs unabhängig im selben Build aufbauen:

```sh
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug
```

Der Workflow
[`Android apps build`](.github/workflows/android-build.yml) baut beide Apps,
prüft ihre APK-IDs und verifiziert die APK-Signaturen. Zusätzlich laufen
die Android-Health-Client-Unit-Tests beider Module. Sie verwenden simulierte
HTTPS-Verbindungen und ersetzen keinen realen Server- oder Gerätetest.

## Read-only Audit

Der manuelle Workflow
[`Read-only Workers repository audit`](.github/workflows/audit-workers.yml)
prüft ausschließlich Dateien dieses Monorepos. Er führt keine Projekt-Workflows
oder Skripte aus und benötigt weder `WORKERS_REPOSITORY_URL` noch
`WORKERS_REPO_READ_PAT` oder andere Repository-Secrets. Er ist weder ein
Anwendungstest noch ein Nachweis für eine
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

Die plattformübergreifende Vertragsarchitektur und Android-/iOS-Sicherheitsgrenzen
stehen in [`docs/mobile-cross-platform-architecture.md`](docs/mobile-cross-platform-architecture.md).
Die lokalen iOS-Vorschauziele in `apps/ios/` implementieren nur lokale
Profil-/Vorschaufunktionen, einen konfigurierbaren Health-Check und bestätigte
E-Mail-Entwürfe. Sie enthalten keine KI-, Geräte-, Sensor- oder
Notfallintegration und benötigen weiterhin SecurityChain-P0- sowie
Plattform-/Store-Freigaben.

Der lokale, einmalig ausführbare Ideen-Priorisierer ist in
[`docs/evolution-engine.md`](docs/evolution-engine.md) beschrieben. Er bewertet
nur belegte, kuratierte Vorschläge und nimmt selbst keine Dateiänderungen,
Builds, Netzwerkzugriffe oder Deployments vor.

## Automatische Updates und Autobuild

- Bei Push und Pull Request sowie montags um 04:23 UTC und manuell laufen
  getrennte Workflows: [`Android apps build`](.github/workflows/android-build.yml)
  baut und prüft beide Android-APKs sowie ihre Health-Client-Unit-Tests;
  [`iOS app builds`](.github/workflows/ios-build.yml) baut die bestehenden
  lokalen iOS-Vorschauziele separat für das Simulator-SDK ohne Code Signing,
  wenn iOS-Quelldateien geändert werden oder manuell. Der Android-Workflow
  verwendet Gradle nur für die Android-Module und testet zusätzlich den
  portablen Swift-Analyse-Core; er baut keine nativen iOS-Apps und baut nicht
  das iOS-Projekt im separaten NIKNOLIG-Repository;
  [`Backend contracts and tooling`](.github/workflows/backend-contracts.yml)
  führt Backend-Vertrags-/Tooltests und den Systemregister-Check aus.
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
- Das Artefakt `mobile-contracts-<Commit-SHA>` wird vom Backend-Vertragsworkflow
  veröffentlicht. Es enthält OpenAPI-/JSON-Verträge für Android und spätere
  iOS-Verbraucher sowie das Systemregister. Neue Repositories müssen ausdrücklich
  im Register aufgenommen werden. Andere Repositories werden weder verändert
  noch ferngesteuert gebaut; erfolgreiche Monorepo-Workflows bestätigen nicht
  deren Builds oder Integration.
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
   benötigt. Der iOS-CI-Build ist kein Xcode-Archiv, kein signierter Build,
   kein Simulator-/Gerätetest und kein TestFlight- oder App-Store-Upload.

### App-Downloads und Defense-Testzugang (23.10.2026)

Die [vorbereitete Downloadseite](docs/download/index.html) zeigt Android-/iOS-
Verfügbarkeitszustände und Installationshinweise; ihre Einbindung auf
`niknolig.com` ist nicht umgesetzt oder live bestätigt. Es gibt keine
verifizierten Store-/Installationslinks. Defense zeigt in beiden lokalen
App-Vorschauen die geplanten fünf kostenlosen Tage, den zusätzlichen getrennten
48-Stunden-Notfallzugang und das optionale dauerhafte Upgrade für einmalig
0,75 € ohne Abo oder automatische Zahlung. Die Notfallprüfung ist noch nicht
festgelegt; Test, Notfallzugang und Kauf sind nicht verfügbar. Konto-, Trial-,
Notfall- und Storeprüfung fehlen.
[Verifizierter Bestand, kleinster sicherer Backendanschluss und Releaseblocker](docs/release-readiness.md#defense-zugang-und-app-verteilung--stand-23102026).
