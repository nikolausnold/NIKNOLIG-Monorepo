# SecurityChain-P0-Reparaturbericht

**Stand: 01.11.2026. Ergebnis: technische Datenschutzreparatur umgesetzt; SecurityChain-P0 nicht freigegeben oder erfüllt.** Bearbeitet wurde der vorhandene Branch `copilot/naechster-produktiver-schritt`. Die App-IDs, getrennten Scopes und bestehenden Sperren blieben unverändert.

## 1. Befund und Reparatur

| Befund | Betroffene Dateien | Reparatur und Nachweis |
| --- | --- | --- |
| Bei einer ungelösten Supportfrage wurde der vollständige Freitext verschlüsselt in der lokalen Ticketablage gespeichert, obwohl die App ihn weder entschlüsselt noch verwendet. Auch beim Öffnen eines E-Mail-Entwurfs wurde er vorgemerkt. Das geschah vor der Bestätigung zum Öffnen des Entwurfs und war für den bestehenden festen E-Mail-Text nicht erforderlich. | `apps/niknolig/src/main/java/com/niknolig/app/SupportActivity.kt`; `apps/niknolig-defense/src/main/java/com/niknolig/defense/SupportActivity.kt`; `apps/ios/NIKNOLIGApp.swift`; `apps/ios/NIKNOLIGDefenseApp.swift` | Alle vier Oberflächen verschlüsseln für lokale Tickets nur noch den leeren Platzhalter. Die lokale Ticket-Metadaten-/Idempotenzfunktion und der feste, nutzerbestätigte E-Mail-Entwurf bleiben bestehen. Keine Frage wird dadurch übertragen. |
| Es fehlte eine Regression gegen die erneute Speicherung des Freitexts durch eine der vier Supportoberflächen. | `backend/tests/test_contracts.py` | `test_support_queues_do_not_persist_free_text` prüft die Argumente aller Payload-Verschlüsselungsaufrufe der Android- und iOS-Oberflächen. |
| Die Support-Dokumentation beschrieb den festen E-Mail-Entwurf, nicht aber die Minimierung des lokal gespeicherten Ticket-Payloads. | `docs/app-web-design-alignment.md` | Dokumentiert nun ausdrücklich den leeren verschlüsselten Platzhalter. |

Die Reparatur löscht **keine** vorhandenen lokalen Tickets aus früheren App-Versionen. Deren verschlüsselter Payload kann bis zum Löschen des Tickets oder der App-Daten auf dem Gerät verbleiben; siehe verbleibende Risiken.

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
