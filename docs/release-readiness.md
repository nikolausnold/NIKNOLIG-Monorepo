# NIKNOLIG Release-Readiness-Bericht

**Ergebnis: BLOCKED**

**Audit-Baseline:** 2026-10-15, Bestandsaufnahme ab 15:03 UTC
**Letzte Aktualisierung:** 2026-10-23 (Verteilung und Defense-Zugang)

**Repository:** `nikolausnold/NIKNOLIG-Monorepo`

**Baseline-Prüfstand:** Commit `37b2f163312bc9611ed1bf4d2fa2056b4108777d` (erfolgreicher `main`-Build)

**Audit-Branch:** `copilot/audit-release-integration`

## Defense-Zugang und App-Verteilung – Stand 23.10.2026

**Teilumsetzung, nicht betriebsbereit.** Die nachfolgenden Angaben sind aktuell
für diesen Auftrag; die älteren Auditabschnitte darunter bleiben historische
Nachweise. Insbesondere existieren inzwischen App-Testquellen, ein lokales
iOS-Projekt und Health-/Support-Laufzeiten, aber keine Konto-/Entitlement-API.
Die neue Fünf-Tage-Regel ersetzt die frühere 48-Stunden-Härtefallregel; der
Test verlangt keinen Nachweis einer Notlage.

### Geänderte Bereiche und Veröffentlichungsnachweise

- `docs/download/index.html`: vorbereitete statische Downloadseite mit getrennten
  Android-/iOS-Verfügbarkeitszuständen für beide Apps, Installationshinweisen,
  Trial-/Einmalkaufbedingungen und Links zu den beiden offiziellen Websites.
  Keine Store-, APK-, IPA- oder TestFlight-Installationslinks erfunden.
- `apps/niknolig-defense/src/main/res/layout/activity_main.xml` und
  `res/values{,-en}/strings.xml`: lesbarer, nicht interaktiver Zugangshinweis
  in der Android-Defense-Vorschau, ohne Zeitstempel oder lokalen Grant.
- `apps/ios/NIKNOLIGDefenseApp.swift`: inhaltlich gleicher deutscher Hinweis.
  Das iOS-Projekt verwendet bisher deutsche Inline-Texte; die Android-Vorschau
  enthält zusätzlich Englisch. Keine Kaufbuttons ohne funktionierende Anbindung.
- `README.md`, `backend/README.md`, `docs/BUSINESSPLAN.md`,
  `docs/AGB-ENTWURF.md` und `docs/LEGAL-CHECKLIST.md`: Status und neue Produktregel
  vereinheitlicht. Rechtliche Texte bleiben ungeprüfte Entwürfe.
- `tools/tests/test_app_design.py`: statische Regressionen für Verfügbarkeit,
  sichere Linkziele und übereinstimmende deutsche Vorschauhinweise.

| Prüfung am 23.10.2026 | Befund / Grenze |
| --- | --- |
| https://niknolig.com/ und https://defense.niknolig.com/ | Live-Abruf scheitert in dieser Umgebung an DNS-Auflösung. HTTP/TLS, Redirects und produktive Links nicht geprüft; kein Beweis allgemeiner Nichterreichbarkeit. |
| NIKNOLIG-Website-Quelle | GitHub-API liest `nikolausnold/NIKNOLIG/index.html`, SHA `27534569b14b951910b0602a3abbf8b199c60ced`: keine Store-/Installationslinks vorhanden. Die Website liegt nicht in diesem Monorepo. |
| Aktive Defense-Quelle | GitHub-API für `nikolausnold/-niknolig-defense` liefert 404: Inhalt, Releases und Veröffentlichungsweg nicht verifizierbar, keine Aussage über Nichtexistenz. |
| Monorepo-Releases | GitHub-API liefert eine leere Release-Liste. CI-Artefakte sind keine öffentlichen Installationslinks. |
| NIKNOLIG-Quellrepository | [Prerelease `13.10.2026`](https://github.com/nikolausnold/NIKNOLIG/releases/tag/13.10.2026) existiert, enthält aber **keine Assets**. Source-ZIP/Tarball ist keine installierbare App. |
| Google Play / App Store | Keine verifizierte öffentliche Produkt-URL für beide Produkte gefunden. Websuche ohne relevante Treffer ist kein Nachweis, dass weltweit keine Veröffentlichung existiert. Keine geratenen Paket-/Store-URLs verlinkt. |
| iOS | Lokale SwiftUI-Vorschauziele, kein verifiziertes signiertes Archiv, App-Store-Listing oder TestFlight-Link. Simulator-Build ist kein installierbarer Release. |

**Website-Blocker:** Dieses Monorepo veröffentlicht die offizielle Website nicht.
Die vorbereitete Downloadseite ist weder als `https://niknolig.com/download/`
noch als andere Live-URL nachgewiesen. Nach separater Freigabe muss der
Website-Verantwortliche die Seite in der tatsächlichen Website-Quelle integrieren,
von Hauptnavigation/Startseite verlinken und den Live-Pfad prüfen. Dieser Auftrag
ändert keine anderen Repositories, DNS, Serverkonfigurationen oder Deployments.
Die Website-Verteilung ist daher **nicht abgeschlossen**.

**Freigabe von Installationslinks:** Pro Produkt und Plattform erst das echte
öffentliche Storelisting einschließlich Anbieter, App-Identität, Region und
Installierbarkeit verifizieren. Android-APK nur als zusätzlich freigegebenes
signiertes Release auf stabilem HTTPS-Pfad, mit SHA-256, Version, unabhängig
genehmigtem Zertifikat-Fingerprint, nicht-debuggable Manifest und dokumentiertem
Updatepfad; kein Verweis auf kurzlebige CI-Artefakte. Für APK-Updates müssen
Paketname, kompatible Signatur und höhere Versionscodes erhalten bleiben.
Sideloading und eigene Updateverantwortung erklären. iOS nur App Store oder
konkret freigegebene Apple-Verteilung (z. B. bestätigte TestFlight-Einladung,
ausdrücklich als Beta); kein direkter IPA-Download als Installation.

### Fehlende Komponenten und kleinster sicherer Anschluss

`backend/ai_support.py` besitzt `Principal`/`Authenticator` als austauschbare
Schnittstellen, standardmäßig aber `RejectAllAuthenticator`. Die ASGI stellt
Health-/Projekt-/Datenbankdiagnose und gesperrten Support bereit. Es fehlen
Login, Konto-Verknüpfung, Eligibility, Trialtabellen, Billingadapter, Storeprodukte
und Receipt-/Transaction-Verifikation. Migration `001_initial_contract.sql`
ist ein gesperrter Gerätevertragsentwurf, kein Konten- oder Lizenzmodell.
Weder Health-Readiness, Supportberechtigung noch Geräte-Linkstatus gewähren Defense.
In Android fehlt Play Billing, in iOS StoreKit; kein Kauf wurde getestet.

Der sichere Mindestumfang nach Identitäts-/SecurityChain-P0-Freigabe ist:

1. **Gemeinsame Identität, getrennte App-Autorisierung:** An die vorhandene
   Authenticator-Grenze eine verifizierte Kontoidentität anschließen, statt
   Client-Konto-IDs, E-Mail-Strings oder Installationskennungen zu vertrauen.
   Aussteller, Signatur, Audience/App-Scope, Ablauf und Widerruf prüfen;
   Android/iOS müssen bewusst dasselbe berechtigte Konto verknüpfen können.
   Eligibility fachlich festlegen (z. B. verifiziertes, aktives NIKNOLIG-Konto).
   Ein gemeinsames Konto gibt weder Sensorrechte noch Zugriff auf andere Appdaten.
2. **Persistenter Trial-Ledger:** Neue separat freizugebende Migration mit
   eindeutiger `(account_id, defense_product)`-Zuordnung, `trial_started_at`
   und `trial_expires_at` als UTC-Zeitstempel. Aktivierung erst nach expliziter
   Nutzerbestätigung in einer atomaren Servertransaktion: einmaliges Einfügen
   mit Datenbankzeit, Ablauf exakt **432000 Sekunden** später. Gleichzeitige
   oder wiederholte Requests liefern denselben Datensatz, auch nach Timeout
   mit unklarer Antwort. Kein Reset bei Reinstall, Logout oder Plattformwechsel.
   Aktivierung und Statusabfrage dürfen keine Zahlung auslösen; eine reine
   Statusabfrage startet niemals einen Test.
3. **Accountbezogene Status-API und Enforcement:** Authentifizierte Lese-API
   liefert Serverzeit, Aktivierungszeit, Ablauf, Restsekunden und Zustand
   `not_started`, `trial_active`, `expired` oder `permanent`; bei fehlender
   Synchronisierung separat `unavailable`, niemals fälschlich `expired`.
   Trialzugriff gilt bei `started_at <= server_now < expires_at`, Restzeit
   mindestens null; Zeitzonen/Sommerzeit ändern die Dauer nicht.
   Bezahlte Defense-Operationen prüfen die Berechtigung serverseitig bei jeder
   Ausführung. Gerätedatum und lokale Flags dürfen nur Darstellung beeinflussen.
4. **Storeprodukte und Verifikation:** Play als nicht konsumierbares
   Einmalkaufprodukt, Apple als Non-Consumable-In-App-Purchase konfigurieren,
   keine Subscription und kein externes Payment-Checkout als Umgehung.
   Produkt-IDs sind noch nicht vergeben. Zielpreis **0,75 € Gesamtpreis** je
   freigegebenem EUR-Storefront bestätigen; Store-Preisstufen, Steuern und
   Länder können das verhindern. Keine eigenmächtige Preisänderung: bei
   fehlendem passenden Produkt/Preis Kauf deaktiviert lassen.
   Vor dem Storedialog aktuelle lokalisierte Produktdaten mit endgültigem
   Preis und „einmalig, dauerhaft“ anzeigen; ausdrückliche Bestätigung verlangen.
5. **Vertrauenswürdiger Kauf-Ledger:** Backend validiert Play-Purchase-Token
   über die Google Play Developer API und Apples signierte Transaktion mit
   vertrauenswürdiger Signatur-/Zertifikatsprüfung und App Store Server API.
   Paket-/Bundle-ID, Produkt, Umgebung, Kaufstatus, Kontobindung
   (`obfuscatedAccountId`/`appAccountToken`) sowie Erstattung/Widerruf prüfen.
   Sandbox bleibt strikt von Produktionsrechten getrennt.
   `(store, environment, transaction_id/purchase_token)` global eindeutig
   binden: derselbe Kauf darf weder doppelt noch für ein anderes Konto gelten.
   Alte Nachrichten niemals einen späteren Widerruf überschreiben lassen;
   relevante Zustände bei der Plattform erneut abgleichen.
6. **Atomarer Grant und Wiederherstellung:** Nur ein verifizierter abgeschlossener
   Kauf gewährt dauerhaftes `defense_product`-Entitlement. Android-Käufe nicht
   konsumieren; erst nach durablem Grant fristgerecht bestätigen, Apple-
   Transaktionen nach Verarbeitung abschließen. Timeouts/Wiederholungen sind
   idempotent und dürfen weder Verlust noch Doppelgrant erzeugen.
   „Käufe wiederherstellen“ ruft vorhandene Käufe ab, prüft serverseitig erneut
   und synchronisiert für dasselbe Konto auf beiden unterstützten Plattformen.
   Bereits Berechtigte bekommen keinen erneuten Kauf angeboten.
7. **Lifecycle, Offline und Datenschutz:** Verifizierte Play-Notifications und
   App Store Server Notifications V2 authentifizieren; deduplizieren und bei
   Empfang sowie regelmäßig mit Storezustand abgleichen. Geheimnisse nur in
   genehmigter Server-Secretverwaltung. Minimale pseudonyme Kontoreferenz,
   Trialzeiten, Storetransaktionsreferenz, Prüf-/Widerrufsstatus und begrenztes
   Audit speichern; keine Karten-, Notlagen-, Gesundheits- oder Standortdaten.
   Receipt-/Tokenwerte nicht protokollieren, notwendigen Speicher schützen.
   Rechtsgrundlage, Aufbewahrung und Kontolöschung einschließlich minimalem
   Verbrauchsnachweis gegen Neuanlage-Missbrauch vorab klären; keine verdeckte
   ewige Personenverfolgung. Bis zu einem separat geprüften signierten,
   zeitlich begrenzten Offlineverfahren keine neuen geschützten Aktionen bei
   fehlender verifizierbarer Berechtigung; kein lokaler Trialreset oder
   dauerhafter Offline-Grant. NIKNOLIG und lokale Vorschau bleiben nutzbar.

### Zustände und plattformgleiche Nutzerführung

| Ereignis | Erwartetes Verhalten nach Implementierung |
| --- | --- |
| Noch nicht aktiviert | „Fünf Tage kostenlos aktivieren“, Laufzeit/keine Zahlungsmethode erklären; nur bewusste Bestätigung startet serverseitig. |
| Aktiver Test | Aktivierungszeit, Endzeit mit Zeitzone, Restdauer aus Serverzeit; Geräteuhränderung verlängert nichts. |
| Exakt am Ablauf / abgelehntes Upgrade | „Dein kostenloser Defense-Test ist beendet.“ Optional „Dauerhaft für einmalig 0,75 € freischalten“ nur bei bestätigtem Storepreis; kein automatischer Dialog, keine Zahlung bei Ablehnung. NIKNOLIG bleibt nutzbar. |
| Erfolgreicher verifizierter Kauf / Restore | Dauerhaft freigeschaltet, Konto synchronisieren, keinen erneuten Kauf anbieten. |
| Abgebrochen / fehlgeschlagen | Kein neuer Grant, keine automatische Wiederholung; bestehender gültiger Test/Kauf bleibt unverändert. |
| Pending / Verifikation nicht erreichbar | „Kauf ausstehend“ bzw. „Prüfung nicht verfügbar“, kein vorzeitiger Grant, keinen zweiten Kauf anstoßen; später synchronisieren. |
| Erstattet / widerrufen | Betroffenen Kaufgrant entziehen, keine neue Trialaktivierung; andere unabhängig gültige Kaufgrants oder ein noch laufender Originaltest bleiben maßgeblich. Kein Neuverkauf ohne neue ausdrückliche Entscheidung. |
| Offline / Serverfehler | „Berechtigung nicht synchronisierbar“, nicht „Test beendet“ behaupten; keine erfundenen Zeitwerte und keine neuen Grants. Nach Verbindung neu prüfen. |

Ohne Test/Upgrade bleiben die freizugebenden Defense-Sicherheits-,
Notfall-, Infrastruktur-Erkennungs- und Reparaturhinweisfunktionen gesperrt.
**Aktuell sind diese Funktionen ohnehin nicht implementiert**, auch nicht gegen
Zahlung. Konkreter freigegebener Funktionskatalog ist ein Veröffentlichungsblocker.
Ein kostenpflichtiges Upgrade garantiert keine Notfallhilfe. Bei akuter Gefahr
örtliche Notrufnummer verwenden; keine Zahlung oder Nachweisprüfung vor Notruf
suggerieren. Verbraucherrechte, Storebedingungen, GDPR-Rechtsgrundlagen und
Datenschutzhinweise müssen vor Einführung fachlich geprüft werden.

### Tests und Abnahme

- Statische Vorschauprüfungen sind keine Entitlement- oder Zahlungstests.
- Lokaler erster Lauf: 9 vorhandene Design-/Theme-Tests erfolgreich.
  Nach Ergänzung der statischen Regressionen: `python3 -m unittest discover -s tools/tests`
  mit **61 Tests erfolgreich**, einschließlich der zwei neuen Vorschau-/Downloadtests;
  `git diff --check` erfolgreich. Der erste Gesamtlauf hatte vier Fehler durch
  verschobene README-Zeilenbelege; durch Anhängen statt Einschieben des neuen
  README-Abschnitts behoben, ohne die bestehenden Belegtests abzuschwächen.
  Ein Android-Build-/Lint-/Unit-Testversuch scheitert **vor Taskausführung**:
  `com.android.application:9.4.1` kann aus den konfigurierten Repositories nicht
  aufgelöst werden. Keine Wiederholung oder Änderung der Buildversionen.
  Xcode/iOS-SDK ist in dieser Linux-Umgebung nicht vorhanden.
- Baseline-CI vor diesen Änderungen: [Backend #317 erfolgreich](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39993489397)
  und [Android #975 erfolgreich](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39993489393),
  beide auf `31d61b4119f1505bb443e23badd2934fa4ab6d19`. Kein Nachweis dieser Änderungen.
- Branch-CI für Implementierungscommit `7e48eba`:
  [Android #976](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39994528545),
  [iOS #38](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39994528307)
  und [Backend #318](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39994528281)
  stehen auf **`action_required`**, jeweils null Jobs laut Logabfrage.
  Keine ausgeführten Build-/Testjobs und kein CI-Erfolg für diese Änderungen;
  keine Wiederholung angefordert.
- Secret-Scan aller zwölf geänderten Dateien ohne Treffer.
  Parallele Validierung aufgerufen: automatischer Reviewer konnte wegen
  fehlendem Modell nicht initialisieren (trotz „Success“-Hülle kein bestandener
  Review). Separater read-only Code-Review fand keine signifikanten Probleme.
  CodeQL überspringt diese ausschließlich informativen UI-/Dokumentations- und
  Teständerungen als trivial; kein durchgeführter CodeQL-Scan behauptet.
  Keine offene Reviewbeanstandung, technische Freigaben bleiben ausstehend.
  Bei der abschließenden Abfrage kein Pull Request für den Branch gefunden.
- Noch **nicht ausführbar/abgenommen**: erstmalige Aktivierung; Grenze eine
  Sekunde vor, exakt bei und nach 432000 Sekunden; parallele/duplizierte
  Aktivierung einschließlich verlorener Antwort; Reinstall/Logout/Gerätewechsel;
  Android→iOS und iOS→Android; Restore für dasselbe/falsches Konto;
  fremde/ungültige/replayte Transaktionen; Erfolg/Abbruch/Pending/Fehler;
  Refund/Widerruf und verspätete doppelte Notifications; Offline, Uhrmanipulation
  und erneute Synchronisierung; fehlende Storepreise; reale Website-Installation
  und Updatepfad. Diese Fälle erfordern die fehlenden Komponenten und
  Play-Lizenztester-/Apple-Sandboxkonten, keine echten Käufe.
- Keine neuen Dienste gekauft, keine Secrets/Signierschlüssel angelegt, keine
  Stores beschrieben oder veröffentlicht, kein Merge und kein Produktionsrollout.
  Vollständige Betriebsbereitschaft darf erst nach dieser Abnahme behauptet werden.

## Aktualisierung 2026-10-16

Diese Aktualisierung ergänzt den historischen Auditstand; sie ersetzt weder
SecurityChain-P0-Nachweise noch einen Zwei-Geräte-Test.

- Arbeitsbranch: `copilot/download-apps-without-zip`; letzter geprüfter Stand
  vor dieser Berichtsergänzung: `79b627a87a2be4e242587ac72337f72982d0daf2`.
  Der Ausgangsstand `3920e30` war sauber. Seit `main` `b28a19b` enthält der
  Branch ausschließlich Sicherheitsdesign-/Auditdokumentation, keine App- oder
  Workflow-Implementierung.
- Der erfolgreiche Android-Debug-Lauf #94 baute und prüfte beide APKs auf
  `main` bei `b28a19b`:
  [Actions-Lauf #94](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928).
  Er belegt keinen Geräte-Link und führt keine App-Unit-/Instrumentierungstests
  aus.
- Der letzte Branch-Push löste Android-Lauf #98 auf dem geprüften Stand aus,
  Ergebnis `action_required`, **null Jobs und keine fehlgeschlagenen Jobs**:
  [Actions-Lauf #98](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38861769602).
  Lauf #96 und #97 endeten gleichfalls mit `action_required`. Somit fand für
  diese Branch-Pushes kein CI-Build statt; es gibt keine Job-Logs, die einen
  Codefehler belegen.
- Ein lokaler Versuch von
  `./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug :niknolig:testDebugUnitTest :niknolig-defense:testDebugUnitTest --no-daemon`
  brach vor der Build-/Testausführung ab: Gradle konnte das Android-Gradle-
  Plugin `com.android.application:8.11.1` aus den konfigurierten Plugin-
  Repositories nicht auflösen. Das ist ein Abhängigkeitsauflösungsfehler der
  Umgebung; ein App-Kompilierfehler oder Testergebnis wurde nicht erreicht.
  Pluginversionen wurden nicht geändert.
- Letzter erfolgreicher Release-Workflow in den abgefragten Ergebnissen ist
  Lauf #14 auf `main`, Commit `37b2f163312bc9611ed1bf4d2fa2056b4108777d`:
  [Release-Lauf #14](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38759170886).
  Der Lauf erzeugte signierte APK-Artefakte; dies ist kein Store-Release und
  kein aktueller P0-Integrationsnachweis.
- Es wurden keine Android-Testquellen im Arbeitsstand gefunden. Automatisierte
  App-Tests und physische Zwei-Geräte-Abnahme bleiben offen.
- Der freigegebene Autobuild bezieht sich auf Debug-Builds bei Push/PR. Er
  autorisiert keine produktive Veröffentlichung und hebt die P0-Sperre nicht
  auf. Konkrete SecurityChain-P0-Kriterien, Transport und Protokoll sind in
  den geprüften Dateien weiterhin nicht freigegeben. Transportkandidaten und
  ihre offenen Prüfungen sind in
  [`device-link-security-design.md`](device-link-security-design.md)
  dokumentiert.

## Zusammenfassung

Vorhandene Actions-Nachweise belegen erfolgreiche Debug- und Release-Builds auf
den in der Aktualisierung oben genannten Commits. Der Branch-Build #96 wurde
nicht ausgeführt (`action_required`); der lokale Prüfversuch scheiterte bereits
bei der Auflösung des Android-Gradle-Plugins. Damit ist kein Build-/Testergebnis
für den aktuellen Dokumentationscommit behauptet.

Das ist kein Nachweis für die geforderte Verbindung zwischen zwei Smartphones:
In den vorhandenen Apps sind Geräteerkennung, Pairing, Authentifizierung,
verschlüsselte Kommunikation, Abbruchbehandlung und Wiederverbindung nicht
implementiert. Es gibt außerdem keine Android-Testquellen. Ein realer
Zwei-Geräte-Test wurde nicht durchgeführt. Daher sind die vorhandenen Builds
technisch erfolgreich, die geforderte Release-Funktion aber nicht release-ready.

## Repository- und Workflow-Bestand

- Das Arbeitsverzeichnis war vor dieser Aktualisierung sauber. Der lokale
  Branch und der geprüfte Ausgangscommit stehen oben; es erfolgte kein
  Branchwechsel, Merge oder Deployment.
- Der Klon ist flach. Der Release-Commit
  `c8d152f4dff28f452e768b2379ebedf6ae4688e4` wurde gezielt nachgeladen.
  Der Git-Vergleich gegen den Prüfstand zeigt: App- und Gradle-Dateien sowie
  Release- und Audit-Workflow sind unverändert. Geändert wurden zwei
  Dokumentationsdateien und der Debug-Workflow ausschließlich um den
  Bericht-Upload. Die frühere Aussage „keine Workflow-Dateien geändert“
  war daher zu weitgehend.
- Vorhandene Projektworkflows: `Android apps build` (Push, Pull Request,
  manuell), `Preparing release APKs` (manuell, nur `main`) und
  `Read-only Workers repository audit` (manuell). Es gibt keinen
  Store-Publishing-Workflow.
- Die Android-Module `:niknolig` und `:niknolig-defense` sind unabhängige Apps
  mit `com.niknolig.app` beziehungsweise `com.niknolig.defense`. Das Monorepo
  ändert die beiden separaten Quell-Repositories nicht.
- Werkzeugkonfiguration: JDK 17, Gradle-Wrapper 8.13, Android-Gradle-Plugin
  8.11.1, Kotlin 2.2.21, compile/target SDK 35, Build Tools 35.0.0,
  min SDK 26. Beide Apps deklarieren Version `0.1.0`, `versionCode = 1`.
  Das ist kein Nachweis einer freigegebenen produktiven Version.
- Gemeinsame Dateien sind insbesondere Gradle-Settings, Root-Build,
  Wrapper und CI-Workflows. Sie bleiben in diesem Auftrag unverändert.
  Neue gemeinsame APIs, Transportbibliotheken oder Berechtigungen benötigen
  zuerst eine Entscheidung über Zuständigkeiten und Sicherheitsgrenzen.

## CI- und Testergebnisse

| Prüfung | Ergebnis und Nachweis |
| --- | --- |
| Aktuellster geprüfter Android-Debug-Build | **Erfolgreich** auf `main`, Commit `37b2f163312bc9611ed1bf4d2fa2056b4108777d`; [Actions-Lauf #83](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38756192188). Jobschritte und Upload-Logs bestätigen beide APKs und den damaligen Bericht; Paket-ID-/Signaturprüfung erfolgreich. |
| Release-Build | **Erfolgreich** auf `main`, Commit `c8d152f4dff28f452e768b2379ebedf6ae4688e4`; [Actions-Lauf #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201). Keystores wurden validiert, beide Release-APKs gebaut, Paket-IDs geprüft und APK-Zertifikate mit den jeweiligen Keystore-Zertifikaten verglichen. |
| Read-only-Repository-Audit | **Erfolgreich**, [Actions-Lauf #16](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736489156). Dies ist kein Android-, Integrations- oder Gerätetest. |
| Automatisierte App-Tests | **Nicht vorhanden/nicht ausgeführt.** Im geprüften Stand gibt es keine `src/test`- oder `src/androidTest`-Quellen. Der Android-Build-Workflow führt Build- und APK-Prüfungen, aber keine Android-Testtasks aus. |
| Lint, Emulator- und Navigationstests | **Kein Nachweis aus diesen Läufen.** Die Workflows rufen keine entsprechenden Prüf-Tasks auf. Die Navigation wurde ausschließlich im Quellcode geprüft. |
| Test auf zwei physischen Geräten | **Nicht durchgeführt.** Kein CI-Lauf kann diesen manuellen Test ersetzen. |

Der frühere [Debug-Lauf #79](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38754078450)
wird inzwischen als `failure` geführt; die Jobs-/Logabfrage lieferte null Jobs
und keine fehlgeschlagenen Joblogs. Eine technische Ursache ist dadurch nicht
belegt. Der erfolgreiche spätere Lauf #83 belegt den inzwischen vorhandenen
Bericht-Upload. Eine erneute Freigabe von #79 ist dafür nicht erforderlich.

Es wurden keine zusätzlichen Builds oder Workflow-Retries manuell gestartet.
Bestehende Ergebnisse wurden wiederverwendet; für die reine Berichtsänderung
ist kein erneuter lokaler Android-Build erforderlich. Der bestehende
Debug-Workflow reagiert allerdings auf jeden Push und Pull Request, auch auf
Dokumentation, und kann dadurch automatisch nochmals bauen. Dieses
Effizienzrisiko wird berichtet, nicht durch ungefragte CI-Umbauten behoben.
Das Buildlog von #83 enthält außerdem eine Node-20-Migrationswarnung für
Checkout/Java-Setup; der Lauf war dennoch erfolgreich.

## Vorhandene APK-Artefakte

Die folgenden Artefaktarchive waren zum Berichtszeitpunkt nicht abgelaufen.
Die Download-URLs sind die von GitHub Actions zurückgegebenen echten
Artefakt-URLs; für den Zugriff ist eine entsprechende GitHub-Berechtigung
erforderlich.

| Artefakt | Zugehöriger Lauf | Größe | Ablauf | Download |
| --- | --- | ---: | --- | --- |
| `niknolig-debug-apk` | [Debug #94](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928), Commit `b28a19b` | 866.594 Byte | 2026-10-22 16:56:23 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928/artifacts/11992227705) |
| `niknolig-defense-debug-apk` | [Debug #94](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928), Commit `b28a19b` | 862.674 Byte | 2026-10-22 16:56:32 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928/artifacts/11991628637) |
| `niknolig-release-apk` | [Release #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201), Commit `c8d152f` | 662.828 Byte | 2026-10-16 12:43:07 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201/artifacts/11974091975) |
| `niknolig-defense-release-apk` | [Release #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201), Commit `c8d152f` | 659.853 Byte | 2026-10-16 12:43:08 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201/artifacts/11974306823) |
| `niknolig-release-apk` | [Release #14](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38759170886), Commit `37b2f16` | 662.828 Byte | 2026-10-16 15:19:55 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38759170886/artifacts/11984518236) |
| `niknolig-defense-release-apk` | [Release #14](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38759170886), Commit `37b2f16` | 659.851 Byte | 2026-10-16 15:19:57 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38759170886/artifacts/11984757701) |
| `release-readiness-report` (vorherige Berichtsfassung) | [Debug #94](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928), Commit `b28a19b` | 6.543 Byte | 2026-10-22 16:56:34 UTC | [Download](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38772997928/artifacts/11991593684) |

Die Release-APKs stammen aus dem vorherigen Commit `c8d152f`; die App-,
Gradle-Dateien und der Release-Workflow sind zwischen diesem Commit und dem
Prüfstand unverändert; nur der Debug-Workflow erhielt den Bericht-Upload.
Die Release-Pipeline lädt Artefakte hoch, veröffentlicht sie aber nicht in
einem App-Store. Die Tabelle beschreibt Actions-Archivgrößen, nicht die Größe
entpackter APKs. Verfügbarkeit wurde über Artefaktmetadaten (`expired: false`)
und erfolgreiche Upload-Schritte geprüft, nicht durch erneuten Download,
Installation oder eigene Binäranalyse.

### Bericht als Actions-Artefakt

Der bestehende Android-Build-Workflow lädt den Bericht bereits als
`release-readiness-report` mit sieben Tagen Aufbewahrung hoch. Lauf #83 stellt
die **vorherige Fassung** tatsächlich bereit; er enthält nicht die
Aktualisierungen dieses Auftrags. Der nächste erfolgreiche Lauf auf dem
aktualisierten Commit kann diese Fassung über denselben Upload bereitstellen.
Bis dessen erfolgreicher Upload nachgewiesen ist, wird dafür kein neuer
Download behauptet oder eine Run-ID vorweggenommen. Zusätzliche APK-, PDF-
oder Infrastruktur-Builds sind für diesen Audit nicht nötig.

Der erste Push dieses Audits (`c047566949e682cac4c92ddce41af5871f6465bf`)
hat inzwischen den realen [Debug-Lauf #84](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38757410552)
ausgelöst: `action_required`, null Jobs, null Artefakte laut Actions-Abfrage.
Die Bereitstellung dieser aktualisierten Audit-Fassung ist damit noch
**offen**. Ein berechtigter Repository-Nutzer muss den erforderlichen
Freigabeschritt auf der Laufseite prüfen; bei einem späteren Berichtscommit
ist stattdessen dessen neuester Lauf auf der
[Branch-Workflowseite](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/android-build.yml?query=branch%3Acopilot%2Faudit-release-integration)
maßgeblich. Freigaben werden nicht umgangen; zusätzliche manuelle Builds
oder Retries werden nicht gestartet.

## Integrationsprüfung und Zwei-Geräte-Anforderung

### Tatsächlich konfigurierte Komponenten und Navigation

| Integrationspunkt | Statischer Befund und Grenze |
| --- | --- |
| Modulgrenzen | Zwei Android-Applications ohne gegenseitige `project`-Abhängigkeit oder gemeinsame Runtime. Gleiche Profil-Schlüsselnamen bedeuten wegen unterschiedlicher App-Sandboxes keinen Datenaustausch. |
| NIKNOLIG-Navigation | Startseite → Lernprofil bzw. Elektro-Engel-Assistent; Assistent → Lernprofil oder Schließen (`finish`). Explizite interne Activity-Intents stimmen mit den Manifestdeklarationen überein. |
| Defense-Navigation | Startseite → eigenes Lernprofil; kein Intent zur anderen App oder zum zweiten Smartphone. |
| Support | Beide Startseiten öffnen per `ACTION_SENDTO`/`mailto` eine externe E-Mail-App; fehlende App wird abgefangen. Dies ist keine Backend- oder Defense-Verbindung. Versand wurde nicht getestet. |
| Elektro-Engel | Anfrage wird nur als lokaler Status angezeigt. Profil, Stil und Feedback liegen lokal in `MODE_PRIVATE`-SharedPreferences; keine KI-Antwort, Synchronisation oder Geräteaktion. |
| APIs und Verträge | Keine API-Clientimplementierung, Endpoint-Konfiguration, OpenAPI-/Swagger-Spezifikation oder versioniertes App-zu-App-Nachrichtenmodell im geprüften Dateibestand. Datenformate, Rollen, Autorisierung, Fehlercodes, Timeouts, Replay-Schutz und Widerruf sind nicht vereinbart. |
| Websites/Cloudflare | Website-Quellen und GitHub-Pages-Deployments wurden am 23.10.2026 read-only geprüft: NIKNOLIG-Lauf [#36](https://github.com/nikolausnold/NIKNOLIG/actions/runs/39954787871) auf `6eec28f` und Defense-Lauf [#35](https://github.com/nikolausnold/-NIKNOLIG-Defense-Website/actions/runs/39912347042) auf `2692285` erfolgreich; deren Workflow-Logs nennen `https://niknolig.com/` bzw. `https://defense.niknolig.com/`. DNS-Auflösung scheiterte in der Prüfungsumgebung, daher kein Live-Erreichbarkeitsnachweis. Keine Wrangler-Konfiguration oder Cloudflare-Verbindung im Monorepo nachgewiesen; externe Repositories wurden nicht verändert. |

Quellnachweise am unveränderlichen Prüfstand:
[Modulzuordnung](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/37b2f163312bc9611ed1bf4d2fa2056b4108777d/settings.gradle.kts#L21-L24),
[NIKNOLIG-Navigation](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/37b2f163312bc9611ed1bf4d2fa2056b4108777d/apps/niknolig/src/main/java/com/niknolig/app/MainActivity.kt#L16-L40),
[Defense-Navigation](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/37b2f163312bc9611ed1bf4d2fa2056b4108777d/apps/niknolig-defense/src/main/java/com/niknolig/defense/MainActivity.kt#L16-L36),
[lokaler Assistent](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/37b2f163312bc9611ed1bf4d2fa2056b4108777d/apps/niknolig/src/main/java/com/niknolig/app/AssistantActivity.kt#L15-L31),
[lokales Profil](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/37b2f163312bc9611ed1bf4d2fa2056b4108777d/apps/niknolig/src/main/java/com/niknolig/app/LearningProfileActivity.kt#L12-L15).
Diese Quellprüfung ist kein ausgeführter UI- oder Ende-zu-Ende-Test.

### Verbindung auf zwei Smartphones

Die Android-Manifeste enthalten keine Netzwerk-, Bluetooth- oder
Nearby-Device-Berechtigungen. Die App-Quellen enthalten keinen Transport-,
Geräteerkennungs-, Pairing-, Authentifizierungs-, Verschlüsselungs- oder
Wiederverbindungscode. Bluetooth-Erwähnungen in den Oberflächen sind
Vorschautexte, keine Gerätefunktionen. Zwischen den beiden Modulen gibt es
keine gemeinsame Laufzeitbibliothek oder App-zu-App-Schnittstelle.

| Anforderung | Befund |
| --- | --- |
| Geräteerkennung und Pairing | Nicht implementiert |
| Authentifizierung/Vertrauensaufbau | Nicht implementiert |
| Verschlüsselte Verbindung | Nicht implementiert |
| Verbindungsabbruch und Wiederverbindung | Nicht implementiert |
| Automatisierte Integrationstests | Nicht vorhanden |
| Test mit den zwei Smartphones des Nutzers | Nicht durchgeführt |

Ein späterer echter Gerätetest benötigt zwei physische Smartphones mit
zugeordneten App-Versionen, APK-/Signaturidentitäten und Android-Versionen.
Zu protokollieren sind beidseitige Zustimmung/Pairing, erlaubter Datenaustausch,
Ablehnung eines fremden Geräts, verweigerte Berechtigungen, Offlinebetrieb,
Abbruch/Wiederverbindung und Widerruf. Ergebnis, Zeitpunkt und redigierte
Nachweise müssen den getesteten Builds zugeordnet werden. Das ist ein offenes
Abnahmekriterium, kein hier erzieltes Testergebnis. Ein Emulatorlauf oder
automatisierter Vertragstest würde diesen physischen Nachweis nicht ersetzen.

## Offene Blocker und kleinste nächste Schritte

1. **P0 – Zwei-Geräte-Verbindung fehlt (Release-Blocker).** Zuerst müssen Umfang,
   Transport, Identität/Pairing, Berechtigungen und Sicherheitsanforderungen
   freigegeben werden. Danach ist die Funktion zu implementieren und durch
   automatisierte Fehlerfalltests sowie einen dokumentierten Test auf beiden
   Smartphones zu prüfen. Dieser Bericht nimmt keine solche Implementierung
   vor.
2. **P1 – Keine automatisierten App-Tests oder Geräteabnahme.** Sobald der Funktionsumfang freigegeben
   ist, automatisierte Tests für Pairing, Authentifizierung, Verschlüsselung,
   Abbruch und Wiederverbindung ergänzen und in CI ausführen.
3. **P1 – Keine unabhängig freigegebene Signaturreferenz.** Der Release-Workflow
   vergleicht den APK-Fingerabdruck mit dem Keystore desselben Laufs, aber
   nicht mit einem unabhängig freigegebenen erwarteten Fingerabdruck. Vor
   einem produktiven Release muss die Signieridentität unabhängig geprüft und
   eine Referenz für den Release-Prozess freigegeben werden.
4. **P1 – Release-Freigabekriterien nicht belegt.** Store-/Produktivfreigabe,
   Review-Gates und Rollback sind durch die vorhandenen Artefakt-Builds nicht
   belegt. Kleinster Schritt: diese Kriterien vor einer Store-Veröffentlichung
   festlegen und nachweisen.
5. **P2 – Nachweisaufbewahrung und CI-Effizienz.** Release-Artefakte laufen
   nach einem Tag ab, Debug-APKs/Berichte nach sieben Tagen. Dauerhafte
   Aufbewahrung, Versionsfortschreibung und dokumentationsbezogene
   Build-Vermeidung sind vor einem Release abzustimmen. Der Bericht-Download
   an sich ist durch #83 belegt und kein offener Funktionsblocker mehr;
   die aktualisierte Fassung benötigt ihren eigenen Upload-Nachweis.

## Änderungen und Prüfgrenzen dieses Auftrags

- Aktualisiert wurde ausschließlich dieser bestehende Markdown-Bericht.
  Apps, gemeinsame Konfigurationen und alle Workflows bleiben unverändert.
- Keine Secrets ausgelesen oder geändert, keine Signierung angestoßen,
  keine separaten App-Repositories bearbeitet, kein Merge und kein Deployment.
- Nachweise: sauberer Ausgangsstatus, vollständiges App-/Konfigurationsinventar,
  Quellprüfung der fünf Activities und Manifeste, Git-Differenz gegen den
  Release-Commit sowie GitHub-Actions-Run-, Job-, Log- und Artefaktabfragen.
- Die wiederverwendeten CI-Ergebnisse gelten für die oben genannten Commits,
  nicht als neue Funktions-, Penetrations- oder Zwei-Smartphone-Tests.
  Der begrenzte Credential-Musterscan des Workers-Audits ist ebenfalls kein
  vollständiger Sicherheitsnachweis. Externe Environment-Reviewerregeln und
  Branchschutz sind aus den Workflow-Dateien allein nicht belegbar.
- Der geänderte Bericht bestand den separaten Secret-Scan und
  `git diff --check`. Die kombinierte Validierung wurde aufgerufen:
  CodeQL wurde wegen reiner Dokumentationsänderungen übersprungen; das
  integrierte Code-Review-Werkzeug meldete fehlende Verfügbarkeit.
  Ein zusätzliches read-only Review des Berichtsdiffs fand keine wesentlichen
  Probleme.
  Das ist kein erfolgreicher Sicherheits- oder Anwendungstest.

**Freigabeentscheidung:** **BLOCKED** bis mindestens die geforderte
Zwei-Geräte-Funktion implementiert und auf beiden Smartphones erfolgreich
getestet ist. Ein erfolgreicher APK-Build allein hebt diesen Blocker nicht auf.
