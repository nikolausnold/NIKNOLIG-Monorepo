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
ausdrückliche Einwilligung (`user_confirmed is True`), getrennt nach
`(app, subject)`, Berechtigungen `memory:read`/`memory:write`, Zugangsdaten-
Erkennung, 500 Zeichen, max. 100 Einträge je Principal und 10.000 je
In-Memory-Store, Aufbewahrung 1–365 Tage (Standard 90),
Aktualisieren, Löschen, Gesamtlöschung. Gesprächsverläufe, Wissenseinträge und
Modelltraining bleiben getrennte Funktionen; Erinnerungen trainieren kein Modell.
Härtung (PR #189): Gespeichert wird nur mit `user_confirmed is True` (auch beim
Aktualisieren); IDs müssen `UUID` sein; abgelaufene Datensätze werden unabhängig
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

- Beide Apps bleiben getrennte Module/Application-IDs ohne gemeinsame Abhängigkeit.
- Die bestehende Schnittstelle ist `POST /v1/ai/support` (Kompatibilitätsalias
  `/support`) aus `backend/ai-support.openapi.yaml`. Sie akzeptiert einen
  Request mit `app`, `feature` und `prompt`, erfordert serverseitig einen
  verifizierten Bearer-Principal, prüft die exakte App-Übereinstimmung und
  `ai:<feature>`; der Client-App-Wert ist kein Identitätsnachweis. ASGI und
  Caddy registrieren die Route, aber der Default-Service ist deaktiviert,
  verwendet keinen aktiven Provider und lehnt standardmäßig ab.
- Beide Apps bleiben getrennte Module/Application-IDs ohne gemeinsame
  Abhängigkeit. Memory ist nach `(app, subject)` getrennt, erwartet aber einen
  durch den Aufrufer übergebenen `Principal`; die Engine prüft keine Tokens,
  Signaturen oder Widerrufe. Ohne Auth-Provider/API bleibt sie nicht verdrahtet.
  Keine gegenseitigen Rechte.
- Zwischen den Apps existiert keine direkte Kommunikation; beide sprechen nur
  über die gemeinsame, noch nicht in Apps integrierte Backend-Schnittstelle.
  **Produktive Authentifizierung und App-Integration sind nicht nachgewiesen.**

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

- Backend lokal: `python -m unittest discover -s backend/tests` mit
  `backend/requirements.txt` → **216 Tests OK, 19 übersprungen** (lokal nicht
  verfügbares PostgreSQL). Contract-/App-Isolationsprüfungen liefen in der Suite;
  Regressionstests decken persistierte Schreibfehler und nicht bestätigte
  Rückgabewerte ab.
- GitHub Actions auf Code-Commit `31c1519`: [Backend Contracts/Tooling](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41315957822)
  und [Android Build](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41315957682)
  erfolgreich (Retry, Versuch 2). Backend lief mit PostgreSQL-Service. Android
  assemblierte beide Debug-APKs und bestand Client-Tests, Lint sowie
  Paket-/Signaturprüfungen; auch der portable Elektro-Engel-iOS-Core-Testjob
  bestand. Die ersten Versuche endeten mit `action_required` und starteten keine
  Jobs; die erfolgreichen Wiederholungen validieren den Code-Commit.
- Swift-Pakettests lokal unter Linux: `modules/support/ios` **15 bestanden**;
  `modules/electro-engel/ios` **8 bestanden**. Das sind portable Core-Tests,
  keine iOS-App-Builds. `xcodebuild`/Simulator-Builds waren unter Linux nicht
  ausführbar; der iOS-Build-Workflow war für den aktuellen backend-only
  Code-Commit nicht triggerbar. Android lokaler Gradle-Build scheiterte zuvor
  beim Auflösen des Android-Gradle-Plugins `9.5.0`; der erfolgreiche
  Android-CI-Lauf oben ist der belegte Buildnachweis für den Vorgängerstand.
- Echter KI-Test: **nicht erbracht**; Definition of Done für „online“ nicht erfüllt.

## Nächster Schritt

Betreiber stellt freigegebene Backend-Origin, Auth-Aussteller und serverseitigen
Provider-Zugang bereit; danach P0-Freigabe, Audit-Sink/Quotas, dann Android-
Gateway-Client je App mit eigenem Scope.

## Spezifikation für späteren dauerhaften Memory-Speicher (nicht implementiert)

`InMemoryMemoryStore` ist flüchtig und **keine** Produktionsspeicherung. Vor
einer Aktivierung sind mit separater P0-Freigabe erforderlich:

1. Verschlüsselung at rest (verwaltete Schlüssel, nicht im Repo/APK/Logs) und TLS.
2. Mandanten-Trennung auf Datenbankebene: Schlüssel `(app, subject)`, getrennte Rollen je App; Zugriff nur über den authentifizierten `Principal`.
3. Atomares Limit (100 Einträge) und Retention per Datenbank-Job; Löschung nachprüfbar (Lösch-Quittung, keine Soft-Deletes ohne Frist; Backups mit definierter Löschfrist).
4. Audit-Sink ohne Inhalte (nur Ereignis, App, pseudonymisierte ID, Ergebnis), mit Aufbewahrungsregel.
5. DSGVO: Auskunft, Berichtigung, Löschung, Widerruf der Einwilligung, Verzeichnis der Verarbeitung, Löschpfad bei Konto-Löschung.
6. Erst danach: HTTP-Route mit serverseitiger Auth, Rate-Limit und Kostenkontrolle. Bis dahin bleiben `enabled=False` und `RuntimeControls` geschlossen.

## Offene Risiken
- Keine Persistenz, kein Audit, keine Verschlüsselung, keine Nutzer-Auth (siehe Blocker).
- Erkennung von Zugangsdaten ist nur ein Muster-Filter, keine DLP; sensible Inhalte in freiem Text sind möglich.
- iOS-App-Simulator-Builds wurden nicht ausgeführt; die erfolgreichen CI-Läufe
  validieren portable Core-Tests, keine iOS-App-Targets.
- `Principal` wird von der Memory Engine als bereits authentifiziert vorausgesetzt;
  die Engine selbst prüft keine Signatur, Sitzung oder Widerruf. `user_confirmed`
  ist ein API-Boolean, kein eigenständiger Nachweis einer UI-Einwilligung.
- Kein echter KI-Aufruf; P0 bleibt ungeprüft und nicht freigegeben.
