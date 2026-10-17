# Sicherheits- und Release-Readiness

**Stand:** 2026-10-17  
**Gesamtstatus:** **BLOCKED** für Geräteverbindung und Produktionsfreigabe  
**Geltungsbereich:** Nachweise für Android; iOS-Bestand im Monorepo; keine
Store-Veröffentlichung, Signierung oder Schlüsselverwaltung in diesem Bericht.

## Implementierungsfortschritt (2026-10-17)

Im offenen PR wurde app-getrennte Android-Grundlogik für Verbindungssitzung,
explizite lokale Zustimmung, Peer-/Einwilligungsprüfungs-Gates, begrenzte
Control-Nachrichten, Sequenz-Replay-Abwehr, Widerruf und Fehlerzustände ergänzt.
Der neue versionierte Vertrag
[`device-link-message-v1.schema.json`](../backend/contracts/device-link-message-v1.schema.json)
definiert ausschließlich ein minimiertes Control-Envelope, keine Nutzdaten und
keinen Backend-Endpunkt. Die Android-CI führt nun Unit-Tests für beide Apps
zusätzlich zu den bisherigen Prüfungen aus.

Dies ist **keine lauffähige BLE-Verbindung**: Im Bestand gab es keinen
Connection Manager. Die neue `DeviceLinkBleTransport`-Schnittstelle besitzt
noch keinen Android-Bluetooth/GATT-Adapter; `DeviceLinkSecurityPolicy` besitzt
keine produktive kryptografische Vertrauens-, Consent- oder
Autorisierungsimplementierung. Eine explizite deny-all-Policy ist verfügbar;
es gibt keinen permissiven Produktions-Provider. Verbindungszustand wird erst
nach policy-bestätigtem, verschlüsseltem und MITM-geschütztem
Transportnachweis als verbunden gemeldet. Es gibt keine UI-/Manifest-Integration,
dauerhafte Replay-/Widerrufsspeicherung oder Geräte-Interoperabilität. Daher
bleibt Geräteauthentifizierung, BLE-Verbindung und Produktionsintegration
**BLOCKED**. Die Unit-Tests verwenden kontrollierte Fakes und belegen nur
Zustands-/Envelope-Ablehnungslogik; sie belegen keine Kryptografie oder
Sicherheit auf Geräten.

Das iOS-Quellprojekt ist in diesem Monorepo weiterhin nicht vorhanden. Der
versionierte JSON-Vertrag ist plattformneutral, aber hier ist weder eine iOS-
Implementierung noch ein zweites iOS-Backend hinzugefügt.

Dieser Bericht trennt nachgewiesene technische Prüfungen von unabhängiger
Vertrauensstellung, menschlichen Freigaben und noch nicht ausgeführten Tests.
Dokumentierte Kriterien sind ein Freigabeentwurf, keine behauptete
SecurityChain-P0-Abnahme.

## 1. Signatur-Fingerprints

Die Werte stammen aus dem Schritt **Verify package identities and release
signatures** des erfolgreichen
[Android-Release-Laufs #71](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39045747765),
Job
[`assemble-release`](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39045747765/job/117433997288).
Der Lauf baute Commit `dca6b1bd808e266b4feb9d40be44c6952d9a95d4` auf `main`;
die Build-Nummer des Workflows war 71, daraus ergab sich `versionCode` 1071.

| App / Paket-ID | SHA-256 des Keystore-Zertifikats | SHA-256 des APK-Zertifikats | Workflow-Vergleich |
| --- | --- | --- | --- |
| NIKNOLIG / `com.niknolig.app` | `59aad308bbba86fade464d15eee30edf4419e77e511dc6e4ee2cd1e01d351e92` | `59aad308bbba86fade464d15eee30edf4419e77e511dc6e4ee2cd1e01d351e92` | `PASS` |
| NIKNOLIG Defense / `com.niknolig.defense` | `a87cdd166d98f355735386d4681152b9557f5b103f5590ab09adcc2a0641c2ef` | `a87cdd166d98f355735386d4681152b9557f5b103f5590ab09adcc2a0641c2ef` | `PASS` |

Der vorherige Release-Lauf #70 auf demselben Commit protokollierte dieselben
beiden Werte und ebenfalls erfolgreiche APK-/Keystore-Vergleiche. Das ist ein
Reproduzierbarkeitsnachweis innerhalb derselben Actions-/Secret-Vertrauenskette,
**keine unabhängige Bestätigung der Schlüsselidentität**. Die geprüften
Repository-Unterlagen enthalten keine unabhängig freigegebene Referenz; die
GitHub-Release-Abfrage ergab keine Releases. Ein früheres vertrauenswürdiges
Produktions-APK oder ein außerhalb dieses Workflows verwahrter
Fingerprint-Nachweis wurde nicht bereitgestellt.

**Vertrauensstatus beider Fingerprints: `UNVERIFIED`.** Die Zahlen belegen nur,
welches Zertifikat die beiden Workflow-Läufe verwendeten und dass jeweils das
APK damit signiert wurde. Sie belegen weder die Kontinuität zu einer zuvor
veröffentlichten App noch die unabhängige Kontrolle des Keystores. Bis eine
autorisierte Person eine vertrauenswürdige Referenz bestätigt, darf dieser
Status nicht zu `VERIFIED` geändert werden. Private Schlüssel, Keystore-Dateien
und Passwörter wurden für diese Dokumentation weder ausgelesen noch verändert;
es wurde nichts signiert.

## 2. P0-Gates und Freigabeumfang

Die folgenden Kriterien bilden einen konkreten **Freigabeentwurf**, der vor
Implementierung durch Produktverantwortliche und unabhängige
Sicherheitsprüfung schriftlich zu bestätigen ist. Ein nicht erfülltes oder
nicht nachgewiesenes Kriterium bedeutet Ablehnung („fail closed“).

| Gate | Mindest-Abnahmekriterium |
| --- | --- |
| Zustandsmaschine | Explizite Zustände `idle`, `discovering`, `pairing`, `connected`, `reconnecting`, `revoked`, `failed`; nur definierte Übergänge. Abbruch, Timeout, Prozessende, Widerruf und Sicherheitsfehler führen in einen sicheren Zustand. Keine sensiblen Aktionen außerhalb einer authentisierten, autorisierten Sitzung. |
| Geräteauthentifizierung | Gegenseitiger, kryptografischer Identitätsnachweis; Gerätename, BLE-Adresse, Discovery oder OS-Pairing allein gelten nicht als App-Identität. Frische Challenge/Nonce, Sitzungsbindung und Schutz gegen Replay, Peer-Wechsel und nicht genehmigten Schlüsselwechsel. Identitätsverlust erfordert erneute beidseitige Zustimmung. |
| Autorisierung | Jede Nachricht prüft App-Bereich, Peer, Rolle, Richtung, konkrete Aktion, Sitzung, Einwilligung und Gültigkeit. NIKNOLIG und Defense bleiben getrennte Sicherheitsdomänen; keine impliziten appübergreifenden Rechte. Widerruf wirkt unmittelbar und löscht die Vertrauensbeziehung. |
| Input-/Event-Sicherheit | Versioniertes, streng validiertes Nachrichtenschema; Pflichtfelder, Kodierung, Größen-/Ratenlimits, Sequenz/Frische und erlaubte Ereignisse werden geprüft. Unbekannte Versionen, zusätzliche/fehlende Pflichtdaten, Duplikate, veraltete oder manipulierte Events werden abgelehnt. Parser-/Callback-Fehler dürfen keine Autorisierung umgehen. |
| BLE-Sicherheit | Transport bleibt bis zur formalen Entscheidung `PENDING`. Falls BLE/GATT gewählt wird: minimale Laufzeitberechtigungen je OS-Version, verschlüsselte Verbindung mit angemessenem MITM-Schutz sowie zusätzliche App-Peer-Authentifizierung und Aktionsautorisierung. Downgrade, falsches Gerät und ungeschützte Wiederverbindung werden abgelehnt. Discovery/Bonding allein ist kein Freigabenachweis. |
| Fehlerbehandlung | Berechtigungsverweigerung/-widerruf, Offlinezustand, Verbindungsabbruch, Timeout, ungültiger Peer und Integritätsfehler schließen oder sperren die Sitzung sicher. Wiederverbindung authentisiert und autorisiert erneut; keine automatische Wiederholung sensibler Aktionen und keine nicht freigegebene Offline-Warteschlange. |
| Sichere Protokollierung | Keine Tokens, Schlüssel, privaten Daten, vollständigen Payloads oder unnötigen Geräte-/Personenkennungen in Logs. Sicherheitsereignisse dürfen nur minimierte, redigierte Eventklasse, Zeit und technische Korrelations-ID erfassen; Aufbewahrung und Zugriff sind vorab festzulegen. |
| Verifikation | Automatisierte positive und negative Tests für jedes Gate, getrennte Plattform-Builds sowie dokumentierte Zwei-Geräte-Abnahme auf unterstützter Hardware. CI-Erfolg, Schema-Test oder Emulator ersetzt keinen physischen Gerätetest. |

### Zuständigkeiten und menschliche Freigaben

| Verantwortung | Erforderliche Entscheidung / Nachweis | Status |
| --- | --- | --- |
| Produktverantwortliche Person (zu benennen) | Zweck, Daten, erlaubte Aktionen, Rollen, Nutzerzustimmung, Widerruf, Offlineverhalten und Aufbewahrung für jede App | **PENDING** – verantwortliche Person und schriftliche Abnahme nicht hinterlegt |
| Unabhängige Sicherheitsprüfung (zu benennen) | Bedrohungsmodell, P0-Kriterien, Identität, Transport/BLE, Schlüssel-Lebenszyklus, Negativtests und Abbruchkriterien | **PENDING** – unabhängige prüfende Person und schriftliche Abnahme nicht hinterlegt |
| Android-Verantwortliche Person (zu benennen) | NIKNOLIG- und Defense-Änderungen getrennt implementieren, testen und zu Commits/Builds zuordnen | **PENDING** – nicht als Freigabe erteilt |
| iOS-Verantwortliche Person (zu benennen) | Je iOS-App eigenständige native Implementierung, Tests und Geräteabnahme verantworten | **PENDING** – iOS-Quellen sind nicht Bestandteil dieses Monorepo-Arbeitsstands |
| Release-Verantwortliche Person (zu benennen) | Erst nach allen Gates Fingerprintreferenz prüfen und den konkreten Commit/Build dokumentiert zur Verteilung freigeben | **PENDING** |

Vor einem Implementierungs- oder Produktions-Gate sind mindestens die
normative P0-Version, Scope-/Datenentscheidung, Bedrohungsmodell, Transport-
und Protokollentscheidung, namentliche Rollen, Datum, geprüfter Commit sowie
Testnachweise in einem versionierten Freigabenachweis festzuhalten.
Dokumentation durch den Coding Agent ist keine menschliche Abnahme.

## 3. Plattformbestand und Geräteverbindung

### Android

Die zwei Android-Module sind getrennte Apps mit den IDs `com.niknolig.app` und
`com.niknolig.defense`. Implementiert ist nur der neue app-lokale
Sitzungs-/Envelope-Manager mit kontrollierten Test-Fakes. Es gibt weiterhin
keine Android-BLE/GATT-Implementierung, Produktiv-Pairing, produktive
Kryptografie-/Autorisierungs-Policy oder Instrumented-/Zwei-Geräte-Tests. Die
vorhandenen Release- und Debug-Builds belegen daher keine Geräteverbindung.

### iOS

In diesem Monorepo-Arbeitsstand existieren weder ein iOS-Quellordner noch
Xcode-Projekte oder Swift-Tests. iOS-Quellen liegen außerhalb des hier
verfügbaren Arbeitsstands; dieses Repository enthält damit keine prüfbare
iOS-Geräteverbindungsimplementierung. Es wurden keine externen Repositories
geändert oder als getestet ausgegeben.

Android und iOS müssen später jeweils native Transport-/Berechtigungsadapter,
Zustandsintegration und Tests in ihren eigenen Plattform-Builds erhalten. Ein
gemeinsamer Vertrag darf keine gemeinsame App-Identität, impliziten Rechte oder
platformübergreifende Vertrauensannahme erzeugen.

### Zwei-Geräte-Testprotokoll (vorbereitet, nicht ausgeführt)

Für jeden Testfall sind vorab Test-ID, Datum, Tester, Gerätemodell und
OS-Version beider Geräte, App-/Build-ID, Commit, erwartetes und tatsächliches
Ergebnis sowie redigierter Nachweis zu erfassen. Keine Tokens, Schlüssel oder
unnötigen personenbezogenen Daten protokollieren.

| Testfall | Erwartung | Status |
| --- | --- | --- |
| Beidseitig bestätigtes Pairing und Peer-Verifikation | Sitzung nur nach Zustimmung beider Geräte und erfolgreicher gegenseitiger Verifikation | **NOT RUN** |
| Unbekanntes/unerwartetes Gerät oder veränderter Identitätsnachweis | Ablehnung; keine Sitzung oder Datenfreigabe | **NOT RUN** |
| Nicht autorisierte Aktion, falsche App/Rolle oder Richtung | Ablehnung und sicherer Sitzungsabbruch | **NOT RUN** |
| Ungültige, übergroße, unbekannte oder wiederholte Nachricht | Ablehnung ohne Zustands-/Rechteänderung; sicherer Fehlerzustand | **NOT RUN** |
| BLE-Schutz, Berechtigungsverweigerung und Berechtigungswiderruf | Kein unsicherer Fallback; keine Fortsetzung ohne erneute Prüfung | **NOT RUN** |
| Abbruch beim Pairing / während Sitzung, Offline und Timeout | Sicherer Abbruch, keine gepufferte sensible Aktion | **NOT RUN** |
| Wiederverbindung | Neue Peer-Authentifizierung und Autorisierung vor Fortsetzung | **NOT RUN** |
| Widerruf | Verbindung und Vertrauensstatus beendet; erneutes Pairing erforderlich | **NOT RUN** |

Dieses Protokoll ist eine Testvorbereitung, kein Testergebnis. Ein
automatisierter Simulator-/Unit-Test kann einzelne Protokoll- und
Zustandsinvarianten abdecken, ersetzt aber nicht die physische Zwei-Geräte-
Abnahme.

## 4. Statusübersicht

| Kriterium | Status | Begründung |
| --- | --- | --- |
| Fingerprints dokumentiert und Workflow-Gleichheit geprüft | **TESTED** | Release-Läufe #70 und #71 meldeten jeweils übereinstimmende APK-/Keystore-Werte. |
| Unabhängige Vertrauensstellung der Fingerprints | **PENDING** | Keine unabhängige Referenz oder menschliche Bestätigung verfügbar; beide daher `UNVERIFIED`. |
| P0-Kriterien und Testmatrix schriftlich konkretisiert | **IMPLEMENTED** | In diesem Dokument als abnahmebedürftiger Entwurf erfasst. |
| Produkt-/Security-/Release-Freigaben | **PENDING** | Keine menschlichen Abnahmen oder benannten unabhängigen Prüfer dokumentiert. |
| Android-Sitzungs-/Envelope-Grundlogik | **IMPLEMENTED** | App-lokale fail-closed Manager-Grundlage und Fake-basierte Negativtests; keine Produktivverdrahtung. |
| Android-Geräteauthentifizierung/-autorisierung/Transport | **BLOCKED** | Kein kryptografischer Security-Provider und kein BLE/GATT-Adapter; P0, Bedrohungsmodell und Transportentscheidung offen. |
| iOS-Geräteauthentifizierung/-autorisierung/Transport | **BLOCKED** | Keine iOS-Quellen in diesem Monorepo-Arbeitsstand; keine externen Änderungen. |
| Manager-Negativtests | **IMPLEMENTED** | App-getrennte Unit-Tests prüfen Ablehnung und sichere Zustandsreaktion mit Fakes; keine echte BLE-/Geräteprüfung. |
| BLE-Fehler-/Wiederverbindungstests und Zwei-Geräte-Abnahme | **BLOCKED** | Kein BLE-Adapter oder Hardwaretest; keine produktive Authentifizierungs-Policy. |
| Physische Zwei-Geräte-Abnahme | **PENDING** | Testfälle vorbereitet; kein Test ausgeführt. |
| Android Release-Build #71 | **TESTED** | Beide Release-APKs und Paketsignaturen erfolgreich geprüft; das ist keine P0-Abnahme. |
| Produktions-/Verteilungsfreigabe | **BLOCKED** | Erfordert unabhängig bestätigte Signieridentität, alle technischen Gates und dokumentierte menschliche Abnahmen. |

## 5. Geprüfte Nachweise und Grenzen

- [Release-Lauf #71](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39045747765),
  [Job-Logs](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39045747765/job/117433997288):
  Build, Paket-ID und APK-/Keystore-Vergleich erfolgreich.
- Release-Lauf #70 protokollierte dieselben Fingerprints; da er dieselbe
  Workflow-/Secret-Vertrauenskette nutzt, ist dies kein unabhängiger
  Vertrauensanker.
- Der Release-Workflow baut APKs und AABs; Artefakterstellung ist keine
  Store-Veröffentlichung. In dieser Arbeit wurde nichts veröffentlicht.
- Backend- und Geräte-Link-Verträge sind deklarativ. Sie implementieren keine
  Live-Authentifizierung, Pairing-, BLE- oder P0-Prüfung.
- Es wurden in dieser Änderung weder App-Quellcode ausgeführt noch Android-
  oder iOS-Builds/Tests gestartet. Die dokumentierten erfolgreichen Release-
  Prüfungen beziehen sich ausschließlich auf die oben genannten Actions-Läufe.
