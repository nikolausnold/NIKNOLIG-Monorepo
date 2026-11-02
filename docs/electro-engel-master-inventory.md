# Elektro Engel – Bestandsaufnahme und Integrationsstand

**Stand:** 2026-11-02 · Branch `fictional-succotash` (PR #189, Basis `536af2c`).
Keine Produktionsfreigabe oder produktive Backend-Erreichbarkeit nachgewiesen;
kein KI-Zugang.

## A. Bereits vorhandene Komponenten

| Zielkomponente | Vorhanden in | Status |
| --- | --- | --- |
| Elektro Engel Core (lokal) | `modules/electro-engel/core` (`ElectroEngelAnalyzer`, `LocalAnalysisServer`), genutzt von beiden `AssistantActivity` | Lokal, KI standardmäßig `AI_DISABLED` |
| AI Gateway | `backend/ai_support.py` (`SupportService`, `Provider`-Protokoll, `CloudflareWorkersAI`, `LocalModelProvider`), `backend/workers_ai.py` (TLS-Transport, Timeouts, kein Retry/Redirect) | Vorbereitet, fail-closed |
| Conversation Engine | `POST /support`, `POST /v1/ai/support` (`asgi.py`, `support_http.py`); Einzelanfrage ohne Gesprächsverlauf | Teilweise |
| Knowledge Engine | `backend/ai_knowledge.py` (Quellenfreigabe, Versionen, Lernkandidaten, Recherche deaktiviert) | Vorbereitet, nur In-Memory |
| Security Layer | `Principal`, `Authenticator`-Protokoll, App-Scope- und `ai:<feature>`-Prüfung, `RuntimeControls`, `Limits`/`QuotaStore` | `RejectAllAuthenticator` ist Standard → alles 401/503 |
| Observability | `AuditSink` ohne Prompt/Antwort/Subject; `UnavailableAuditSink` als Standard | Kein genehmigter Sink |
| Memory Engine | **fehlte** → neu: `backend/memory_engine.py` | Neu, nicht verdrahtet |
| Tool Engine | **fehlt bewusst**; keine Shell-/Tool-Ausführung | Offen (P0-pflichtig) |
| Android-Netz | `BackendHealthClient` je App (nur `GET /health/ready`) | Kein Gateway-Client, kein Login |

`ProductionGate` existiert im Repository nicht als Code-Symbol; die Gates sind
`RuntimeControls` (alle `False` standardmäßig) und die P0-Dokumente. Es wurde
nichts geöffnet.

## Neu in diesem Paket: Memory Engine

`backend/memory_engine.py` (Tests: `backend/tests/test_memory_engine.py`):
verlangt opake Einwilligungsnachweise, die ein injizierter `ConsentVerifier`
für Zweck `long-term-memory`, Principal-Scope, Gültigkeit und aktuellen Widerruf
prüfen muss. Es gibt keinen freigegebenen produktiven Verifier; der Standard
lehnt ab. Die Test-Suite verwendet ausschließlich einen Mock-Verifier. Die Engine
ist getrennt nach
`(app, subject)`, Berechtigungen `memory:read`/`memory:write`, Zugangsdaten-
Erkennung und einfache Ablehnung erkennbarer E-Mail-, internationaler
Telefonnummern- und Luhn-gültiger Kartennummern, 500 Zeichen, max. 100 Einträge je Principal und 10.000 je
In-Memory-Store, Aufbewahrung 1–365 Tage (Standard 90),
Aktualisieren, Löschen, Gesamtlöschung. Gesprächsverläufe, Wissenseinträge und
Modelltraining bleiben getrennte Funktionen; Erinnerungen trainieren kein Modell.
Härtung (PR #189): Speichern, Aktualisieren und Abruf verlangen dieselbe
aktuelle, durch den Verifier bestätigte Einwilligung; ein Boolean genügt nicht.
Abgelehnte/veraltete/widerrufene Nachweise blockieren Operationen; autorisiertes
Löschen bleibt ohne Einwilligungsnachweis möglich. IDs müssen `UUID` sein;
abgelaufene Datensätze werden unabhängig
von weiterem Nutzerzugriff terminiert und zusätzlich bei Zugriff physisch
bereinigt; Store und Ablauf-Queue sind begrenzt. Speicher-/Löschfehler und fehlgeschlagene
Bereinigung enden als `STORE_UNAVAILABLE` (ohne Ursache/Inhalt), ein
fehlgeschlagenes Löschen wird nie als Erfolg gemeldet; fremde Datensätze eines
fehlerhaften Adapters werden ignoriert. Bei mehrdeutigem Schreibfehler wird ein
bereits persistierter Datensatz zurückgerollt; wenn das nicht sicher gelingt,
bleibt sein Ablaufjob aktiv. Es wird nichts protokolliert.
`remember()` liefert einen Beleg – nur dieser darf eine „gespeichert“-Aussage
begründen. Standard `enabled=False`; keine HTTP-Route, kein Persistenz-Adapter.

## Gemeinsame Schnittstelle und Trennung

- Beide Apps bleiben getrennte Module und Application-IDs. Sie verwenden die
  gemeinsamen, plattformneutralen Bibliotheken `:electro-engel-core` und
  `:support-core`; kein App-Modul hängt direkt vom jeweils anderen ab. Gemeinsame
  Bibliotheksnutzung überträgt weder App-Identität noch Berechtigungen.
- Der gemeinsame Contract `backend/ai-support.openapi.yaml` beschreibt zwei
  getrennte Requestformate: `POST /support` akzeptiert genau `app` und `message`
  und setzt `feature=support`; `POST /v1/ai/support` akzeptiert `app`, `feature`
  und `prompt` und kann auch `electro-engel` auswählen. Die Pfade sind keine
  Payload-Aliase. Beide erfordern serverseitig einen verifizierten
  Bearer-Principal; der Server prüft die exakte App-Übereinstimmung und
  `ai:<feature>`. Der Client-App-Wert ist kein Identitätsnachweis. ASGI und
  Caddy registrieren die Route, aber der Default-Service ist deaktiviert,
  verwendet keinen aktiven Provider und lehnt standardmäßig ab.
- Memory ist nach `(app, subject)` getrennt, erwartet aber einen durch den
  Aufrufer übergebenen `Principal`; die Engine prüft keine Tokens, Signaturen
  oder Widerrufe. Ohne Auth-Provider/API bleibt sie nicht verdrahtet. Keine
  gegenseitigen Rechte.
- Zwischen den Apps existiert keine direkte Kommunikation; beide sprechen nur
  über die gemeinsame, noch nicht in Apps integrierte Backend-Schnittstelle.
  Beide lokalen Android-Assistenten verwenden den gemeinsamen Analyzer; das ist
  keine produktive KI-Anbindung. **Produktive Authentifizierung und
  Gateway-Integration sind nicht nachgewiesen.**

## Blocker für Online-Betrieb (Priorität)

1. Kein deploytes Backend / keine freigegebene HTTPS-Origin (`NIKNOLIG_BACKEND_URL`, `NIKNOLIG_DEFENSE_BACKEND_URL`).
2. Kein Auth-Aussteller (`Authenticator`) und kein Login in den Apps.
3. Kein genehmigter Audit-Sink, keine dauerhaften/verteilten Quotas, keine Kostenkontrolle in Geld.
4. Kein Provider-Zugang (Cloudflare-Account-ID und Token-Datei serverseitig, nicht im Repo) und keine Provider-/Kostenfreigabe.
5. Android: kein KI-Gateway-Client oder Login; `AssistantActivity` nutzt
   ausschließlich den deterministischen lokalen Analyzer. `SupportActivity`
   prüft nur Health und zeigt lokale Supporthinweise.
6. SecurityChain P0 Freigabe für Persistenz der Memory Engine, Tools und Pairing.

## Externe Produktionsvoraussetzungen und Abnahmen

Die folgenden Rollen sind Verantwortungsfunktionen, keine benannten Personen.
Laut [P0-Freigaberegister](securitychain-d01-d12-abschlussstatus.md#register-offener-menschlicher-freigaben)
sind Namen und Freigaben offen. Es wird kein Anbieter, Konto, Schlüssel oder
Produktivziel vorausgesetzt.

| Fehlende Entscheidung oder Konfiguration | Betroffene Komponente | Verantwortliche Rolle (Person offen) | Erforderlicher Nachweis vor Freigabe | Auswirkung bis dahin |
| --- | --- | --- | --- | --- |
| Genehmigter Identitätsanbieter, App-getrennte Rollen, MFA/Recovery sowie Token-Aussteller, Zielgruppe, Scope, Laufzeit, Erneuerung und Widerruf | Backend-`Authenticator`/Login; je ein Android-Anmeldeclient und Credential-Ablage pro App | Produktverantwortliche je App, Betreiber/Backend-Betrieb, unabhängige Security-Prüfung | Schriftlich freigegebener Auth-Vertrag; synthetische Erfolgs- und Negativtests für fehlende, manipulierte, abgelaufene, widerrufene und falsch gescopte Tokens; keine Produktionsschlüssel in Apps | `RejectAllAuthenticator` bleibt Standard; keine geschützte Online-Operation und kein Login |
| Zweck, Datenklassen, Rechtsgrundlage, Einwilligungstext/-version, Retention und Widerrufsfolgen | Consent-UI, persistente Consent-Historie und produktiver `ConsentVerifier` | Datenschutz/Recht sowie Produktverantwortliche je App | Freigegebene Texte und Dateninventar; nachvollziehbare, app-/subjektgebundene Grant-/Deny-/Revoke-Ereignisse; geprüfte Ablauf- und Widerrufstests | Memory bleibt default-deny; der vorhandene Verifier-Vertrag und Test-Mock belegen keine echte Einwilligung |
| PostgreSQL-/Speicherfreigabe, App-getrennte DB-Berechtigungen, KMS/HSM, AEAD-/Schlüsselrotation und Backup-Löschregeln | Dauerhafter Memory-Adapter, Quoten, Retention- und Löschworker | Betreiber/Backend- und Datenbankbetrieb, unabhängige Security-Prüfung, Datenschutz | Nicht-destruktive, reviewte Migration; Berechtigungs-/Mandantentests; KMS-Schlüsselrichtlinie; Verschlüsselungs-, Retention-, Lösch-, Restore- und Fehlerfallnachweise | Vorhanden ist nur flüchtiger In-Memory-Speicher; keine produktive Memory-Persistenz oder Verschlüsselung |
| KI-Anbieter, Konto/Modell/Region, Nutzdatenfreigabe, serverseitiges Secret, Quoten und Kostenlimit | Backend-Provider/Gateway, Audit und beide App-Clients | Produktverantwortliche je App, Anbieter-Kontoverantwortliche, Betreiber/Backend-Betrieb, Datenschutz und Security | Anbieter-/Datenflussfreigabe; Secret-Konfiguration nur serverseitig; erfolgreicher Live-Aufruf in der Zielumgebung; getestete Quoten, Kostenalarmierung und datensparsame Fehler-/Auditpfade | Kein echter KI-Aufruf; Mock- oder Unit-Tests gelten nicht als Live-Nachweis |
| Produktionsziel, DNS, TLS/Trust, Firewall, Secret-Rotation, Monitoring/Alarmierung, Incident-Weg, Backup/Restore und Rollback | Backend-/Compose-Deployment, Gateway-Origin und App-Konfiguration | Benannter Betreiber/Backend-Betrieb; Release-Verantwortliche | Freigegebene Architektur, Region und Kosten; verifizierte HTTPS-Origin und Zertifikatserneuerung; Betriebs-/Alarmtests; dokumentierter Restore- und Rollback-Test | Keine produktive URL oder Laufzeit ist nachgewiesen; kein Deployment |
| Unabhängige P0-, Datenschutz-, Plattform- und Release-Abnahmen je App/Commit/Artefakt | SecurityChain D-01–D-12, beide Android-Releases und Backend | Unabhängige Security-Prüfung, Datenschutz/Recht, Produktverantwortliche je App, Plattform- und Release-Verantwortliche | Benannte Reviewer; Findings-Disposition; schriftliche, commit- und artefaktgebundene Signoffs; aktuelle Builds und Negativtests für beide App-Scope | PR #189 und Produktionsfreigabe bleiben blockiert; technische Tests ersetzen keine menschliche Freigabe |

## Phasen

- **A** externes Modell über Gateway: Code vorhanden, nicht erreichbar/ungetestet. Modell ist fest `MODEL` in `ai_support.py` – Anbieterwechsel ist per `Provider`-Protokoll möglich, aber noch nicht per Konfiguration; die Apps sind unabhängig vom Anbieter, der Transport ist derzeit an Cloudflare gebunden.
- **B** eigener Wissensspeicher/Memory: Engines vorhanden (In-Memory), Persistenz offen.
- **C** lokales Open-Source-Modell: `LocalModelProvider`-Schnittstelle vorhanden, keine Gewichte/Runtime.
- **D** automatische Modellwahl: nicht begonnen. Keine Anbieterunabhängigkeit behauptet.

## Tests und Sicherheitsnachweise (2026-11-02)

- Lokaler aktueller Arbeitsstand: Backend-Tests mit den gepinnten
  `backend/requirements.txt`-Abhängigkeiten und einem wegwerfbaren PostgreSQL-
  17.9-Container mit dem CI-Digest → **251 bestanden, 1 übersprungen**. Der
  übersprungene Test benötigt das optionale, nicht installierte `jsonschema`;
  die übrigen strukturellen Contract-Assertions liefen. Tooling: **74 bestanden**.
- Neue Regressionen prüfen abgelaufenen Principal und Widerruf nach erfolgreichem
  `put()`/`replace()`, abgelaufene Retention während `put()`/`replace()`, Rollback
  einer nach partieller Persistierung fehlgeschlagenen Aktualisierung sowie das
  fail-closed Verhalten für nicht weak-reference-fähige Store-Adapter. Die Engine
  bleibt deaktiviert und ohne HTTP-Route.
- GitHub Actions liefen für den vorherigen SHA `51f85deee2f5bb8b1c04728c94ae9884f5bca14a`
  erfolgreich: [Backend/Tooling, Versuch 2](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41382290646)
  sowie [Android und iOS-Core, Versuch 2](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41382290982).
  Diese Läufe enthalten nicht die hier dokumentierten Änderungen; erforderliche
  Checks für den Commit dieser Änderungen müssen separat auf GitHub erfolgreich
  sein.
- Backend-CI-Fehlläufe auf `72af3b0` und `962a078` bestanden jeweils den
  Backend-Testschritt, scheiterten aber in vier Tooling-Evidenztests: ein Auszug
  passte nach einer README-Verschiebung nicht mehr zu den zitierten Zeilen in
  `backend/README.md`. Der Zitierfehler wurde in `51f85de` korrigiert;
  [Backend/Tooling](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41382290646)
  bestand danach.
- Die ersten Versuche `41381585616` (Backend) und `41381585598` (Android) zeigten
  `action_required`; das sind Run-Gates, keine fehlgeschlagenen Tests.
  Das Android-Run `41381585598` wurde anschließend durch den Repository-Eigentümer
  als Versuch 2 auf demselben SHA `bc60f713` ausgeführt und bestand. Das Backend-
  Run `41381585616` sowie `41381106369` hatten beim Abfragen null Jobs und keine
  fehlgeschlagenen Jobs/Logs; ein API-Grund war nicht verfügbar. Der spätere
  Backend-Lauf auf `51f85de` bestand. Es wurden weder Prüfungen noch
  Branch-Protection umgangen.
- Für den aktuellen Änderungssatz `d2b7f7874bd9fd8ee6f1f4ba625f2910be5e350d`
  stehen [Backend](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41383960083)
  und [Android](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41383960099)
  auf `action_required`; beide Abfragen lieferten null Jobs und keine Logs. Die
  API nennt keinen Grund und bietet hier keine sichere Freigabe-/Approval-Aktion.
  Diese erforderlichen Checks sind offen, bis ein berechtigter Repository-
  Verantwortlicher sie freigibt bzw. erneut startet.
- Der aktuelle Review-Snapshot auf `51f85de` meldete einen ungültigen Rückgabewert
  bei der zweiten `store.list()`-Abfrage in `recall()`. Der neue Code weist diesen
  Fall mit `STORE_UNAVAILABLE` ab; eine gezielte Regression prüft ihn. Die
  unabhängige Security-Prüfung des Änderungssatzes fand keine hochkonfidenten
  Befunde.
- Android: Die vorherige erfolgreiche CI assemblierte beide Debug-APKs, führte
  App-Tests/Lint-/Identitätsprüfungen aus und bestand den portablen Elektro-Engel-
  iOS-Core-Job. Der aktuelle Änderungssatz enthält keine App-Quellen; CI-Nachweise
  für den neuen Commit bleiben erforderlich.
- iOS-App-/Simulator-Builds: **nicht erbracht**. Der iOS-Workflow ist auf
  Änderungen unter `apps/ios/`, den iOS-Modulen und seiner Workflowdatei
  beschränkt; für diesen Backend-/Compose-/Dokumentationssatz wurde kein
  nativer Simulator-Build ausgelöst. Frühere portable Core-Tests ersetzen ihn
  nicht. `xcodebuild` ist lokal nicht verfügbar.
- Statische Prüfung: `compileall` für die geänderten Python-Dateien bestand.
  Es gibt im Backend-Workflow keinen separaten Ruff-/Mypy-/Bandit-Lauf. Der
  unabhängige Security-Review fand keine Befunde. CodeQL und Secret-Scan werden
  für den finalen Änderungssatz vor Abschluss ausgeführt.
- Echter KI-Aufruf: **nicht erbracht**. Es fehlen Provider-Zugang,
  Datenfluss-/Kostenfreigabe und ein genehmigtes Stagingziel; kein Mock gilt
  als Live-Nachweis.

## Spätere KI-Integration: vorhandener Vertrag, keine Memory-API

Der einzige bestehende Netzwerkvertrag für KI-Vorbereitung ist
`backend/ai-support.openapi.yaml`: `POST /support` akzeptiert ausschließlich
`app` und `message`; `POST /v1/ai/support` akzeptiert `app`, `feature` und
`prompt`. Beide erwarten eine unabhängig verifizierte, aktive und nicht
abgelaufene Identität mit passender App- und Feature-Berechtigung. Sie nehmen
weder Gedächtniszugriff noch Gesprächsverlauf entgegen; die Standardruntime
bleibt deaktiviert. `MemoryService` ist weder in diesen Routen noch in einer
anderen öffentlichen Schnittstelle verdrahtet. Eine künftige Verbindung darf
nicht die hier bestehenden Contracts umdeuten oder neue Endpunkte als bereits
vorhanden ausgeben; sie benötigt eine separat freigegebene Spezifikation,
Einwilligungsnachweis und P0-Prüfung.

## Nächster Schritt

Betreiber stellt freigegebene Backend-Origin, Auth-Aussteller und serverseitigen
Provider-Zugang bereit; danach P0-Freigabe, Audit-Sink/Quotas, dann Android-
Gateway-Client je App mit eigenem Scope.

## Spezifikation für späteren dauerhaften Memory-Speicher (nicht implementiert)

`InMemoryMemoryStore` ist flüchtig und **keine** Produktionsspeicherung. Der
folgende Vorschlag ist keine Freigabe und darf erst nach separater
SecurityChain-P0- und Datenschutzfreigabe implementiert werden. Bis dahin
bleiben `enabled=False`, die Runtime-Gates geschlossen und alle produktiven
Zugänge deaktiviert.

1. **Vertrauensgrenze und Mandantenbindung:** Jede Operation erhält App und
   Subject ausschließlich aus einem unabhängig authentifizierten und
   autorisierten Principal; Request-Felder sind kein Identitätsbeweis. Datenbank-
   Primär-/Fremdschlüssel binden jeden Datensatz an `(app, subject, record_id)`.
   App-spezifische Datenbankrollen und Row-Level-Schutz ergänzen, nicht ersetzen,
   die serverseitige Prüfung. Quoten und Retention müssen transaktionssicher und
   über mehrere Prozesse hinweg wirksam sein. Kein App-zu-App-Zugriff.
2. **Verschlüsselung:** Nur TLS-geschützte Verbindungen; Nutzdaten vor dem
   Schreiben mit einem geprüften AEAD-Verfahren und zufälligem Data-Encryption-
   Key (DEK) verschlüsseln. Envelope Encryption bindet DEKs an verwaltete,
   getrennte App-Key-Scopes in einem KMS/HSM. Der Schlüssel darf nicht in Repo,
   APK, Datenbank-Logs oder Audit-Events gelangen. Associated data bindet den
   Ciphertext an App, pseudonymisierten Subject-Scope, Record-ID und
   Schema-Version. Nonce-Disziplin, Schlüsselversionierung, Rotation,
   Wiederherstellung und KMS-Ausfallverhalten müssen spezifiziert und getestet
   sein. Klartext nur so kurz wie nötig im Arbeitsspeicher; keine Payloads in
   Logs, Metriken, Crashreports oder Backups.
3. **Minimierte Metadaten und Consent:** Speichern nur explizit bestätigte
   Erinnerungsnotizen, keinen Gesprächsverlauf und keine Trainingsdaten.
   Metadaten begrenzen sich auf nötige pseudonyme App-/Subject-Scopes,
   Einwilligungszweck/-version/-zeitpunkt, Typ, Erstellungs-/Ablaufzeit und
   Schlüssel-/Schema-Version. Ein Widerruf sperrt neue Zugriffe sofort und löst
   denselben Löschablauf aus. Freitext-Filter gelten nicht als DLP.
4. **Retention:** Ein dauerhafter, überwachten Job löscht abgelaufene Datensätze
   unabhängig von Nutzeraktivität. Er arbeitet idempotent, paginiert,
   mandantengebunden und mit begrenzten Wiederholungen; ein nicht verfügbarer
   Speicher oder KMS führt fail-closed, erzeugt einen inhaltsfreien Alarm und
   lässt den Löschstatus offen, bis die Löschung verifiziert ist. Quoten- und
   Retention-Rennen werden durch Datenbanktransaktionen bzw. atomare
   Compare-and-set-Operationen verhindert.
5. **Nachweisbare Löschung:** Zuerst wird in einer Transaktion ein
   nicht rücksetzbarer Lösch-Tombstone im aktiven System gesetzt, der jeden
   Lese-/Schreibzugriff für den Scope sperrt; danach werden Datensätze, Indizes,
   Cache- und Replikatkopien idempotent entfernt. Eine nicht-sensitive
   Löschquittung enthält Request-ID, pseudonymisierten Scope, Zeitpunkt,
   betroffene Anzahl, Status und bestätigte Speicher-/Replikatziele, nie Inhalt
   oder Schlüssel. Ein unabhängiges, manipulationsgeschütztes Löschregister
   verhindert, dass Restore aus Backup gelöschte Daten wieder freischaltet.
   Kryptografische Löschung darf erst als abgeschlossen gelten, wenn die
   Zerstörung aller zur Entschlüsselung nötigen Schlüsselkopien vom KMS/HSM
   bestätigt ist. Falls KMS-Schlüssellöschung verzögert ist oder Backups noch
   wiederherstellbare DEKs enthalten, muss der Status dies offen ausweisen;
   spätestens nach definierter Backup-Aufbewahrung wird die Bereinigung
   nachgewiesen. Keine sofortige physische oder kryptografische Löschung
   behaupten, wenn der Speicheranbieter sie nicht belegen kann.
6. **Audit und Betrieb:** Audit nur mit Ereignis, App, pseudonymisiertem Scope,
   Request-ID und Ergebnis, ohne Subject-ID, Prompt, Erinnerungstext,
   Ciphertext oder Schlüsselmaterial. Audit, Quotas, Backup-/Restore-Verfahren,
   Key-Rotation sowie Alarmierung und Incident-Verantwortung brauchen
   Aufbewahrungs- und Zugriffsvorgaben.
7. **Abnahmereihenfolge:** Zunächst Bedrohungsmodell, Daten-/Löschfristen,
   KMS- und Backup-Vertrag sowie P0-Freigabe. Danach ein verschlüsselter Adapter
   samt atomaren Mandantenlimits, dauerhafter Retention und Löschregister;
   anschließend Tests für App-/Subject-Isolation, manipulierte Principal-Scopes,
   AEAD-Tampering, Key-Rotation/-Ausfall, parallele Writes/Löschungen,
   wiederholte Löschanfragen, Replikate und Restore ohne Wiederbelebung. Erst
   nach unabhängiger Prüfung und Freigabe darf eine Route erwogen werden;
   produktive KI-/Memory-Anbindung bleibt eine getrennte Freigabe.

## Offene Risiken
- Keine Persistenz, kein Audit, keine Verschlüsselung, keine Nutzer-Auth (siehe Blocker).
- Inhaltserkennung weist einige bekannte Credentials, Kontaktinformationen und
  Kartennummern zurück; sie ist ein best-effort Eingabefilter, keine DLP oder
  Datenschutzgarantie. Gesundheits-, Religions-, Identitäts- und sonstige
  sensible Freitextangaben können weiterhin durchkommen. Der `ConsentVerifier`
  ist nur ein Provider-Vertrag; es gibt keine genehmigte Implementierung, keine
  persistente Consent-Historie und keine verifizierte UI-Einwilligung. Deshalb
  bleiben Engine und Routen deaktiviert; vor jeder Freigabe sind eine engere
  Datenklassifikation, tatsächliche nutzerseitige Vorschau/Einwilligung und
  unabhängige Datenschutzprüfung erforderlich. Gesprächsverläufe werden nicht
  in Memory umgewandelt oder gespeichert.
- iOS-App-Simulator-Builds wurden nicht ausgeführt; die erfolgreichen CI-Läufe
  validieren portable Core-Tests, keine iOS-App-Targets.
- `Principal` wird von der Memory Engine als bereits authentifiziert vorausgesetzt;
  die Engine selbst prüft keine Identitäts-Signatur oder Sitzung. Diese Prüfung
  und ein persistenter Widerrufs-/Einwilligungsnachweis bleiben externe Aufgaben.
- Kein echter KI-Aufruf; P0 bleibt ungeprüft und nicht freigegeben.
