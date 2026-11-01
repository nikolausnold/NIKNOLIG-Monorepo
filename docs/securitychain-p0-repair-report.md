# SecurityChain-P0-Reparaturbericht

**Stand: 01.11.2026. Ergebnis: technische Datenschutzreparatur umgesetzt; SecurityChain-P0 nicht freigegeben oder erfüllt.** Bearbeitet wurde der vorhandene Branch `copilot/naechster-produktiver-schritt`. Die App-IDs, getrennten Scopes und bestehenden Sperren blieben unverändert.

Abschnitte 1–5 dokumentieren die frühere Reparatur und deren damalige Testergebnisse. Abschnitt 6 beschreibt den ersten PR-#178-Nachtrag. Die aktuelle Prüfung aller 12 PR-Commits und 19 geänderten Dateien steht in Abschnitt 7; ältere Aussagen zu fehlender Migration oder fehlenden CI-Ergebnissen sind keine Beschreibung des aktuellen Stands.

## 1. Befund und Reparatur

| Befund | Betroffene Dateien | Reparatur und Nachweis |
| --- | --- | --- |
| Bei einer ungelösten Supportfrage wurde der vollständige Freitext verschlüsselt in der lokalen Ticketablage gespeichert, obwohl die App ihn weder entschlüsselt noch verwendet. Auch beim Öffnen eines E-Mail-Entwurfs wurde er vorgemerkt. Das geschah vor der Bestätigung zum Öffnen des Entwurfs und war für den bestehenden festen E-Mail-Text nicht erforderlich. | `apps/niknolig/src/main/java/com/niknolig/app/SupportActivity.kt`; `apps/niknolig-defense/src/main/java/com/niknolig/defense/SupportActivity.kt`; `apps/ios/NIKNOLIGApp.swift`; `apps/ios/NIKNOLIGDefenseApp.swift` | Alle vier Oberflächen verschlüsseln für lokale Tickets nur noch den leeren Platzhalter. Die lokale Ticket-Metadaten-/Idempotenzfunktion und der feste, nutzerbestätigte E-Mail-Entwurf bleiben bestehen. Keine Frage wird dadurch übertragen. |
| Es fehlte eine Regression gegen die erneute Speicherung des Freitexts durch eine der vier Supportoberflächen. | `backend/tests/test_contracts.py` | `test_support_queues_do_not_persist_free_text` prüft die Argumente aller Payload-Verschlüsselungsaufrufe der Android- und iOS-Oberflächen. |
| Die Support-Dokumentation beschrieb den festen E-Mail-Entwurf, nicht aber die Minimierung des lokal gespeicherten Ticket-Payloads. | `docs/app-web-design-alignment.md` | Dokumentiert nun ausdrücklich den leeren verschlüsselten Platzhalter. |

Die Reparatur löscht **keine** vorhandenen lokalen Tickets aus früheren App-Versionen. Deren verschlüsselter Payload kann bis zum Löschen des Tickets oder der App-Daten auf dem Gerät verbleiben; siehe verbleibende Risiken.

### Nachtrag: Datenschutzhinweise an tatsächliches Verhalten angepasst

Die Oberflächentexte (Android DE/EN beider Apps, iOS beider Apps) und `modules/support/README.md` behaupteten weiterhin, ungeklärte Fragen blieben lokal verschlüsselt. Tatsächlich wird der Fragetext gar nicht gespeichert; verschlüsselt wird nur ein leerer Platzhalter (AES-GCM, Android Keystore bzw. iOS-Keychain-Schlüssel). Lokal verbleiben unverschlüsselt Vorgangs-UUID, App, zufälliger Request-Key, feste Issue-/Diagnosecodes, Zeitpunkt, Versuchszähler und Übergabestatus (Android: app-private SharedPreferences, iOS: `UserDefaults`). Es gibt keinen Backend-Ticketspeicher; Fragetext wird weder an das Backend noch in E-Mail-Entwürfe übertragen. Das Verhalten wurde nicht geändert; Texte, README, Backend-README und Design-Dokumentation wurden korrigiert. Neuer Test: `test_support_privacy_texts_do_not_claim_encrypted_questions`. Nicht belegt bzw. nicht geprüft: Löschung oder Verhalten alter, vor der Reparatur erzeugter Tickets mit verschlüsseltem Freitext; Verhalten von iOS-Backups für `UserDefaults`. D-01–D-12 bleiben unverändert, da diese Korrektur keine Entscheidung klärt.

## 2. Bestandsgrenzen

- Backend-Login, produktive Tokenvalidierung, Geräte-/Pairing-Laufzeit und Produktdaten-APIs sind nicht implementiert. `RejectAllAuthenticator` und deaktivierte Standard-Gates bleiben bestehen.
- Consent-, Sensor- und Auditdateien sind deklarative Verträge, keine Laufzeitdurchsetzung. Der Standard-Auditsink verweigert Schreibzugriffe.
- Android und iOS behalten getrennte Produktidentitäten und lokale App-Daten. Health-Clients sind keine Produktdatenverbindung.
- Die Reparatur aktiviert weder KI, Netzwerk-Support, BLE, Discovery, Pairing, Sensorzugriff noch Datentransfer.
- Es wurden keine kryptografischen Parameter, Anbieter, Rollen, Retention-Regeln oder sonstigen offenen P0-Entscheidungen festgelegt.

## 3. Tatsächlich ausgeführte Prüfungen

| Befehl/Prüfung | Ergebnis |
| --- | --- |
| `python3 -m unittest discover -s backend/tests` vor Abhängigkeitsinstallation | Fehlgeschlagen: vier Testmodule konnten wegen fehlendem `psycopg` nicht importiert werden. |
| `python3 -m pip install -r backend/requirements.txt` | Erfolgreich; vorhandene, gepinnte Backend-Abhängigkeiten installiert. |
| `python3 -m unittest discover -s backend/tests` erneut | **188 Tests ausgeführt, 19 übersprungen, keine Fehler.** Die übersprungenen Tests benötigen eine explizit konfigurierte Wegwerf-PostgreSQL-Datenbank (`BACKEND_TEST_DATABASE_URL`); hier wurde keine bereitgestellt. |
| `python3 -m unittest discover -s tools/tests` | **73 Tests bestanden.** |
| `swift test --package-path modules/support/ios` | **9 Tests bestanden** unter Linux. |
| `swift test --package-path modules/electro-engel/ios` | **8 Tests bestanden** unter Linux. |
| `./gradlew :electro-engel-core:test :support-core:test :niknolig:assembleDebug :niknolig-defense:assembleDebug :niknolig:testDebugUnitTest :niknolig-defense:testDebugUnitTest :niknolig:lintDebug :niknolig-defense:lintDebug --no-daemon` | Fehlgeschlagen, bevor Projektaufgaben liefen: Gradle konnte `com.android.application:9.4.1` in den konfigurierten Repositories nicht auflösen. Versionen wurden deshalb nicht geändert. |
| `command -v xcodebuild` | Kein `xcodebuild` auf diesem Linux-Runner; native iOS-Appziele konnten nicht gebaut werden. Die erfolgreichen Swift-Pakettests ersetzen diesen Build nicht. |
| GitHub Actions für den Reparaturcommit | [Android](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41263787624), [Backend/Tooling](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41263787707), [iOS](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41263787764): jeweils `action_required`; die Joblisten enthielten null Jobs. Daher gibt es aus diesen Läufen weder CI-Ergebnisse noch Joblogs. |
| CodeQL | Python: keine Alerts. Für Swift konnte keine Datenbank erstellt werden (fehlende Buildabhängigkeiten oder nicht unterstützte Projektkonfiguration). Die Ausgabe enthielt kein Kotlin-Ergebnis; Android-Code ist damit nicht durch diesen Lauf abgedeckt. |

Es wurden keine Produktionsdienste, echten Konten, Geräte, Store-Uploads oder Deployments verwendet. Die PostgreSQL-Integration und native iOS-Appprüfung bleiben ausstehend.

## 4. Verbleibende Risiken

- Früher gespeicherte Freitext-Payloads werden durch dieses Update nicht automatisch entfernt.
- Neue lokale Tickets behalten weiterhin minimale Metadaten wie App-Bereich, Diagnosecode, Ticket-ID und Zustand. Aufbewahrung, Löschung und Audit-Zugriff sind nicht vollständig durch eine freigegebene Policy festgelegt.
- Die Android-/iOS-Appquellen wurden wegen fehlender Buildwerkzeuge bzw. nicht auflösbarem Gradle-Plugin nicht als native App-Artefakte validiert. Es gab keinen physischen Geräte- oder Zwei-Geräte-Test.
- Es existieren weiterhin keine produktiven Authentifizierungs-, Widerrufs-, Consent-, Gerätevertrauens- oder Betriebsnachweise. Ein erfolgreicher Unit-Test oder Build würde diese Nachweise nicht ersetzen.

## 5. Offene Entscheidungen und Entscheidungsvorlagen

Die folgenden Punkte bleiben gemäß [SecurityChain-P0, Abschnitt 10](securitychain-p0-specification.md#10-offene-entscheidungen-und-menschliche-freigaben) offen. Die Rollen sind Entscheidungsfunktionen; Personen oder Zustimmungen werden nicht unterstellt.

| Punkt / Status | Erforderliche Entscheidung und zuständige Funktion | Zentrales Risiko bei ungeklärtem Punkt |
| --- | --- | --- |
| D-01 – Entscheidung erforderlich | Je App Akteure, Ressourcen, Datenfelder, Aktionen, Richtung und Zielinstallation als Allowlist festlegen; Produktverantwortliche je App, Security und Datenschutz. | Unbeabsichtigter Cross-App-Zugriff oder nicht freigegebene Funktionen. |
| D-02 – Entscheidung erforderlich | Identitätsanbieter, Issuer/Audience, getrennte App-Rollen, MFA, Recovery und Tokenvertrag wählen; Produkt, Security, Identität, Datenschutz und Betrieb. | Gefälschte oder falsch gescopte Identität. |
| D-03 – blockiert / Nachweis fehlt | Bindung von Nutzer, Installation, App-Bereich und Schlüssel sowie Besitznachweis und Recovery festlegen; Security, Plattform und Backend. | Geräte-Spoofing oder unberechtigter Installationszugriff. |
| D-04 – Entscheidung erforderlich | Etabliertes Sitzungs-/Transportprotokoll, Version und Parameter auswählen und unabhängig kryptografisch prüfen lassen; Security und technische Plattformverantwortliche. | MITM, Replay, Downgrade oder fehlerhafte Eigenkryptografie. |
| D-05 – Entscheidung erforderlich | Getrennte Keychain-/Keystore-Policy, Hardware-Backing, Rotation, Verlust und Recovery entscheiden; Security, Identität und Plattform. | Schlüsselkopie, Vertrauensübernahme nach Verlust oder appübergreifende Schlüsselverwendung. |
| D-06 – Entscheidung erforderlich | Sitzungs-TTL, erneute Authentifizierung, Widerrufs-SLA, Offlineverhalten und Recovery festlegen; Security, Identität, Betrieb und Produkt. | Fortbestehende Rechte nach Widerruf oder unsichere Offlineaktionen. |
| D-07 – nur Ist-Zustand technisch nachgewiesen | Transport und Geräte-/OS-Matrix entscheiden. BLE bleibt deaktiviert; BLE braucht eine gesonderte schriftliche Freigabe. Produkt, Security und Plattform. | Ungeprüfte oder nicht ausreichend geschützte Verbindung. |
| D-08 – Entscheidung erforderlich | Unterstützte OS-/Geräte-/Hardwarematrix und notwendige Berechtigungen pro App festlegen; Produkt und Android-/iOS-Verantwortliche, Security. | Nicht getestete Plattformen oder unnötige Berechtigungen. |
| D-09 – Entscheidung erforderlich | Consent-Texte, Zweck, Datenumfang, Ziel, Gültigkeit, Widerruf und Löschfolgen freigeben; Produkt, Datenschutz/Recht und Technik. | Schema wird fälschlich als wirksame Zustimmung behandelt. |
| D-10 – Entscheidung erforderlich | Rechtsgrundlage, Region, Auditfelder, Zugriff, Manipulationsschutz, Retention und Löschung genehmigen; Datenschutz/Recht und Betrieb. | Unzulässige oder nicht nachvollziehbare Protokollierung. |
| D-11 – blockiert / Nachweis fehlt | Betreiber, Zielumgebung, DNS/TLS, Monitoring, Secret-Rotation, Backup/Restore, Incident und Rollback nachweisen; Betrieb, Security und Datenschutz/Recht. | Unverantwortbarer Ausfall oder fehlende Vorfallreaktion. |
| D-12 – Entscheidung erforderlich | Unabhängige Reviewer, Prüfplan, physische Geräteabnahme und commit-/versionsgebundene Signoffs benennen; Security, Produkt, Plattform und Release. | CI-Erfolg wird mit unabhängiger Sicherheitsabnahme verwechselt. |

**Abschluss:** Die technische Reparatur dieses Berichts beseitigt nur die beschriebene unnötige lokale Freitextspeicherung. Sie schließt keine D-01–D-12-Entscheidung und erklärt SecurityChain-P0 weder für genehmigt noch erfüllt.

## 6. Nachtrag: PR #178 Abschlussprüfung der Support-Tickets

**Stand: 01.11.2026. Ergebnis: Legacy-Bereinigung und iOS-Backup-Schutz implementiert; keine Sicherheitsfreigabe.**

- **Alt-Tickets:** Frühere Ticket-Payloads konnten verschlüsselten Freitext enthalten. Beim ersten Öffnen des Supports entschlüsselt die App jeden gespeicherten Payload. Nicht-leerer oder nicht lesbarer Inhalt wird durch neu verschlüsselten Leerinhalt ersetzt; Ticket-ID, App, Request-Key, Fehler-/Diagnosecodes, Zeit, Versuche und Übergabestatus bleiben erhalten. Ist Verschlüsselung oder Speicherung nicht möglich, wird die Warteschlange nicht zur Nutzung freigegeben. Tests prüfen Metadatenerhalt, Wiederholbarkeit und fehlgeschlagene Migrationen. Android Keystore/Keychain-Migration wurde nicht auf physischen Geräten ausgeführt.
- **iOS-Ablage:** Neue Ticketdaten liegen in einer dedizierten Application-Support-Datei. Datei und Verzeichnis setzen die Backup-Ausnahme; der Dateischutz ist `completeUntilFirstUserAuthentication`. Beim ersten Laden wird ein früherer `UserDefaults`-Wert in die Datei überführt und anschließend aus `UserDefaults` entfernt. Der Swift-Pakettest prüft Umzug und Nutzdatenmigration. Ein echtes iCloud-Backup/Restore wurde nicht ausgeführt. Vor der Migration erstellte Backups können alte verschlüsselte Payloads weiterhin enthalten; die App kann historische Backups nicht ändern oder widerrufen.
- **Android-Backup:** Beide Manifeste setzen weiterhin `allowBackup=false`. Android dokumentiert mögliche herstellerspezifische Geräteübertragungen trotz dieser Einstellung. Es gab keinen Gerätetest; ein solcher Transfer kann nicht ausgeschlossen werden.
- **Datenschutzhinweise:** Android DE/EN beider Apps und die deutschsprachigen iOS-Hinweise benennen jetzt Legacy-Migration, verbleibende Metadaten und Backup-Grenzen. Der E-Mail-Entwurf enthält weiterhin keine Frage oder Payload.

### Ausgeführte Prüfungen für diesen Nachtrag

| Prüfung | Ergebnis |
| --- | --- |
| `python3 -m unittest backend.tests.test_contracts` | **16 Tests bestanden.** |
| `python3 -m unittest tools.tests.test_support_flow` | **10 Tests bestanden.** |
| `swift test --package-path modules/support/ios` | **13 Tests bestanden** unter Linux; kein iOS-App-Build. |
| `kotlinc modules/support/core/src/main/kotlin/org/niknolig/support/SupportEscalationQueue.kt modules/support/core/src/main/kotlin/org/niknolig/support/SupportCore.kt -d /tmp/support-core-check.jar` | **Kotlin-Supportkern kompiliert.** Kein Android-App-Build. |
| `./gradlew :support-core:test --no-daemon` | **Vor Taskausführung fehlgeschlagen:** Gradle konnte `com.android.application:9.4.1` nicht auflösen; Projektaufgaben starteten nicht. |
| Android-XML-Prüfung | **Vier** deutsche/englische Support-XML-Dateien geparst. |
| `xcodebuild` / physischer iOS-Backup-Test | `xcodebuild` ist nicht installiert; iCloud-Backup/Restore und File-Protection auf iOS-Gerät daher nicht verifiziert. |
| CodeQL | Python: keine Alerts. Für Swift konnte keine Datenbank erstellt werden; Kotlin/Android wurde von diesem Lauf nicht abgedeckt. Kein vollständiger CodeQL-Nachweis. |

Die verfügbaren Tests belegen keine Freigabe der P0-Sicherheitskette. D-01 bis D-12 bleiben separat offen; es erfolgte keine produktive, kryptografische oder geräteübergreifende Sicherheitsabnahme.

## 7. PR #178: Gesamtprüfung nach 12 Commits

**Prüfstand: 01.11.2026, Commit `29b28942f55d44d3ec4c3850387db22d1fae8f13`.** Die GitHub-PR-Daten bestätigen 12 Commits und 19 geänderte Dateien. Die unabhängige, lesende Sicherheitsprüfung fand in diesem Änderungssatz **keinen nachgewiesenen Datenschutz- oder Sicherheitsfehler**. Das ist keine Aussage, dass sämtliche Geräte-, Absturz- oder Backup-Szenarien sicher funktionieren. Deshalb wurde kein Laufzeitcode vorsorglich geändert; korrigiert wird nur der veraltete Prüfstatus dieses Berichts.

### Migration, Datenminimierung und Schutz

- **Alt-Tickets:** Kotlin und Swift ersetzen nur nicht-leere oder nicht entschlüsselbare Payloads; bereits leer entschlüsselte Payloads bleiben unverändert. ID, App, Request-Key, feste Codes, Zeitpunkt, Versuche und Übergabestatus bleiben erhalten. Alle Ersatz-Payloads werden vor dem Speichern erzeugt. Bei Verschlüsselungsfehlern erfolgt kein Migrations-Speichervorgang; bei Migrationsfehlern geben die Oberflächen die Warteschlange nicht für Ticketanlage oder E-Mail-Übergabe frei.
- **Fehlerfälle:** Unit-Tests prüfen unveränderte Originaltickets nach injizierten Verschlüsselungs- und Speicherfehlern. Der iOS-Dateistore schreibt zuerst eine Staging-Datei, wendet deren Schutz an und ersetzt erst danach die maßgebliche Datei mittels `rename`. Erst nach erfolgreichem Ersetzen wird der alte `UserDefaults`-Wert entfernt. Der Test für einen injizierten Schutzfehler prüft unveränderte Zieldaten, erhaltene Tickets und den erhaltenen Legacy-Wert bei fehlgeschlagenem Import. Diese Tests belegen die modellierten Fehlerpfade, nicht die Dauerhaftigkeit bei Stromverlust oder echten Speicherfehlern.
- **Unterbrochene Schreibvorgänge:** Vor Laden und Speichern werden zurückgelassene, UUID-förmig benannte Support-Staging-Dateien bereinigt. Ein Test legt eine solche Datei gezielt an und prüft Bereinigung sowie anschließende Ticketlöschung. Ein realer Prozessabbruch oder Neustart während des Schreibens wurde nicht ausgeführt.
- **Neue Tickets:** Alle Ticket-Erzeugungspfade der vier App-Oberflächen verschlüsseln ausschließlich `""`. Die Backend-Vertragstests prüfen diese Aufrufargumente. Das gilt für die aktuellen App-Aufrufpfade; die wiederverwendbare Queue-API erzwingt selbst keinen Leerinhalt. Neue lokale Tickets enthalten weiterhin unverschlüsselte Metadaten, aber keinen eingegebenen Fragetext.
- **Übertragung:** E-Mail-Entwürfe verwenden nur Ticket-ID, App und feste, allowlist-geprüfte Fehler-/Diagnosecodes. Fragetext, Ciphertext und Request-Key werden nicht eingefügt. Der Health-Aufruf erhält keinen Fragetext. Das Öffnen eines Entwurfs ist kein Versand- oder Zustellnachweis; eine echte E-Mail wurde nicht versandt.
- **iOS:** Verzeichnis und Ticketdatei setzen `URLResourceValues.isExcludedFromBackup = true` und `completeUntilFirstUserAuthentication`; der Payload-Schlüssel ist gerätegebunden. Der Schutz `completeUntilFirstUserAuthentication` bedeutet nicht, dass Daten nach jedem erneuten Sperren des Geräts unzugänglich werden. Die Backup-Assertions im Swift-Test sind ausschließlich unter `os(iOS)` aktiv und laufen daher weder im Linux-Test noch beim macOS-Pakettest. Simulator-Kompilation bestätigt die API-Nutzung, nicht Backup-/Restore- oder Sperrverhalten auf einem Gerät.
- **Android:** App-private `SharedPreferences` und `allowBackup=false` bleiben bestehen. Herstellerabhängige Geräteübertragungen und echte Keystore-/Speicherfehler sind nicht getestet. Historische Backups können alte verschlüsselte Payloads behalten; das Update kann sie nicht rückwirkend löschen.

### Abdeckung aller 19 Dateien

Alle folgenden Dateien wurden im aktuellen PR-Diff und ihrem jeweiligen Aufruf-/Nachweiskontext geprüft:

| Datei im Prüfcheckout | Prüfumfang / Ergebnis |
| --- | --- |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/ios/NIKNOLIGApp.swift` | Migration-Gate, Leer-Payloads, Hinweise und E-Mail-Allowlist; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/ios/NIKNOLIGDefenseApp.swift` | Entsprechender Defense-Flow und App-Scope; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/src/main/java/com/niknolig/app/SupportActivity.kt` | Initialisierung nach Migration, Fehler-Gates, Leer-Payloads und E-Mail; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/src/main/java/com/niknolig/defense/SupportActivity.kt` | Entsprechender Defense-Flow und App-Scope; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/src/main/res/values/support_strings.xml` | Deutsche Hinweise zu Legacy-Tickets, Metadaten und Backup-Grenzen. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/src/main/res/values-en/support_strings.xml` | Entsprechende englische Hinweise. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/src/main/res/values/support_strings.xml` | Entsprechende deutsche Defense-Hinweise. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/src/main/res/values-en/support_strings.xml` | Entsprechende englische Defense-Hinweise. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/README.md` | Unterscheidung Metadaten/Leer-Payload und Migration-/Backup-Grenzen. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/tests/test_contracts.py` | Assertions für Leer-Payloads, Hinweise, Manifeste und Dateischutz; keine Abschwächung der Schutzanforderungen. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/docs/app-web-design-alignment.md` | Hinweise zu Legacy-Bereinigung und Backup-Grenzen. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/docs/device-link-security-design.md` | Entscheidungspaket erteilt keine Laufzeit- oder P0-Freigabe. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/docs/securitychain-p0-repair-report.md` | Historische Testergebnisse als solche gekennzeichnet; aktuelle Nachweise und Grenzen hier ergänzt. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/evolution/ideas.json` | Exakter Evidence-Auszug stimmt mit Zeilen 247–249 des Sicherheitsdesigns überein; kein Laufzeitverhalten geändert. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/modules/support/README.md` | Speicherung, Migration, Backups, E-Mail, Löschung und Testgrenzen. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/modules/support/core/src/main/kotlin/org/niknolig/support/SupportEscalationQueue.kt` | Nur Payload ersetzt, Speichern nach Ersatzbildung, Metadata-Allowlist; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/modules/support/core/src/test/kotlin/org/niknolig/support/SupportCoreTest.kt` | Metadatenerhalt, Wiederholbarkeit, injizierte Verschlüsselungs-/Speicherfehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/modules/support/ios/Sources/SupportCore/SupportCore.swift` | Migration, geschütztes Datei-Ersetzen, Staging-Bereinigung und Allowlist; kein nachgewiesener Fehler. |
| `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/modules/support/ios/Tests/SupportCoreTests/SupportCoreTests.swift` | Alle 15 Tests einschließlich Schutzfehler und Staging-Bereinigung geprüft; echte Plattformfehler nicht simuliert. |

### Ausgeführte Tests und vorhandene CI-Nachweise

Die lokalen Python-Läufe verwendeten `PYTHONDONTWRITEBYTECODE=1`; Swift-Builddaten und der Gradle-Projektcache lagen unter `/tmp`. Es wurden keine destruktiven Git-Operationen verwendet.

| Prüfung | Ergebnis am geprüften Stand |
| --- | --- |
| Backend lokal, erster Versuch | Vier Importfehler wegen fehlendem `psycopg`; kein Produktfehler. |
| Installation vorhandener gepinnter Backend-Abhängigkeiten | Erfolgreich, keine Abhängigkeitsdatei geändert. |
| Backend lokal, erneut | **190 Tests erkannt: 171 bestanden, 19 PostgreSQL-Integrationstests übersprungen**, da lokal keine Wegwerf-Datenbank konfiguriert wurde. |
| Tooling lokal | **73 Tests bestanden**, einschließlich Support-Flow und strenger Evidence-Validierung. |
| Swift-Support lokal mit temporärem Scratch-Verzeichnis | **15 Tests bestanden** unter Linux. Keine Ausführung der `os(iOS)`-Assertions. |
| Kotlin lokal: `:support-core:test` | **Nicht ausgeführt:** Gradle scheiterte vor Taskausführung an der Auflösung von `com.android.application:9.4.1`. Kein Versionswechsel oder Ersatz-Testwerkzeug. |
| [Backend/Tooling-CI](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41271734531/job/124746046609) | Auf demselben Commit: **190 Backend-Tests ohne Skips und 73 Tooling-Tests bestanden**, einschließlich PostgreSQL-Integration. Joblogs geprüft. |
| [Android-/Kotlin-CI](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41271734437/job/124746045027) | Auf demselben Commit: `:support-core:test`, Elektro-Engel-Kerntests, Unit-Tests beider Apps, Debug-APKs und Lint erfolgreich. Die Logs belegen die tatsächlich ausgeführte Support-Testtask; keine unbelegte Kotlin-Testanzahl angegeben. |
| [iOS-CI](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41271734445) | Auf demselben Commit: **15 Swift-Supporttests auf macOS bestanden**; beide Apps für iOS-Simulator in Debug und Release erfolgreich kompiliert, ohne Signierung. Release-Origins sind Fixtures, keine freigegebenen Produktionsziele. |

**Nicht ausgeführt:** lokale Kotlin-Testtask, lokale iOS-App-Builds, iOS-Runtime-Backup-Assertions, echte iCloud-Backup-/Restore-Tests, Sperr-/Entsperrtests auf Geräten, echte Keystore-/Keychain-Fehler, Stromverlust-/Crash-Recovery, herstellerspezifische Android-Geräteübertragung und physische Zwei-Geräte-Abnahme. Die lokalen PostgreSQL-Skips sind durch vorhandene erfolgreiche CI-Tests desselben Commits abgedeckt; die Geräteprüfungen nicht.

**Freigabeentscheidung:** keine P0-Freigabe, keine produktive Bereitstellung, kein Merge und keine Änderung der D-01–D-12-Status. Relevante Plattform-/Backup-/Durabilitätsnachweise sowie genehmigte Aufbewahrungs-, Lösch- und Betriebsregeln bleiben offen. Erfolgreiche CI-Läufe ersetzen diese Nachweise nicht.
