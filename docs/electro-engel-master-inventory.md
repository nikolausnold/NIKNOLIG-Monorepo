# Elektro Engel – Bestandsaufnahme und Integrationsstand

**Stand:** 2026-11-01 · Branch `fictional-succotash` (Basis `536af2c`).
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

## Phasen

- **A** externes Modell über Gateway: Code vorhanden, nicht erreichbar/ungetestet. Modell ist fest `MODEL` in `ai_support.py` – Anbieterwechsel ist per `Provider`-Protokoll möglich, aber noch nicht per Konfiguration; die Apps sind unabhängig vom Anbieter, der Transport ist derzeit an Cloudflare gebunden.
- **B** eigener Wissensspeicher/Memory: Engines vorhanden (In-Memory), Persistenz offen.
- **C** lokales Open-Source-Modell: `LocalModelProvider`-Schnittstelle vorhanden, keine Gewichte/Runtime.
- **D** automatische Modellwahl: nicht begonnen. Keine Anbieterunabhängigkeit behauptet.

## Tests (tatsächlich)

- Backend lokal: `python -m unittest discover -s backend/tests` mit den gepinnten
  `backend/requirements.txt`-Abhängigkeiten und einem kurzlebigen PostgreSQL-
  17.9-Container nach CI-Konfiguration → **232 Tests bestanden, keine
  übersprungen**. Damit wurden auch die PostgreSQL-Integrationen ausgeführt.
  Regressionen decken Authentifizierung/Einwilligung, App-/Subject-Isolation,
  parallele Principal- und globale Quoten, sensible Eingaben, Löschung,
  Retention und Speicherfehler ab.
- Tooling lokal: `python -m unittest discover -s tools/tests` → **74 Tests OK**.
- GitHub Actions auf Code-Commit `e5a7bf7`: [Backend Contracts/Tooling](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41316873061)
  und [Android Build](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41316873042)
  erfolgreich (Retry, Versuch 2). Backend-Vertrags- und Tooling-Tests liefen
  erfolgreich mit PostgreSQL-Service. Android assemblierte beide Debug-APKs und
  bestand Client-Tests, Lint sowie Paket-/Signaturprüfungen; auch der portable
  Elektro-Engel-iOS-Core-Testjob bestand. Das ist kein iOS-App-Simulator-Build.
- Der Backend-Contracts/Tooling-Workflow auf `562b765` ist nach Retry
  erfolgreich und nutzte den CI-PostgreSQL-Service. Die aktuellen
  Memory-Engine-Änderungen wurden lokal mit derselben gepinnten PostgreSQL-
  Imageversion verifiziert; ein Android-Build wurde dafür nicht erneut
  ausgeführt.
- Für den Backend-Code-Stand `981f884` melden [Backend](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41326654020)- und
  [Android-Workflow](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41326648599)
  `action_required`; für diesen SHA wurden noch keine CI-Jobs ausgeführt. Die
  vollständigen lokalen Backend-Tests oben bestehen, ersetzen aber keinen
  Android-Build auf diesem Commit.
- Swift-Pakettests lokal unter Linux: `modules/support/ios` **15 bestanden**;
  `modules/electro-engel/ios` **8 bestanden**. Das sind portable Core-Tests,
  keine iOS-App-Builds. `xcodebuild`/Simulator-Builds waren unter Linux nicht
  ausführbar; der iOS-Build-Workflow war für den aktuellen backend-only
  Code-Commit nicht triggerbar. Android lokaler Gradle-Build scheiterte zuvor
  beim Auflösen des Android-Gradle-Plugins `9.5.0`; der erfolgreiche
  Android-CI-Lauf oben ist der belegte Buildnachweis für den Vorgängerstand.
- Echter KI-Test: **nicht erbracht**; Definition of Done für „online“ nicht erfüllt.

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
