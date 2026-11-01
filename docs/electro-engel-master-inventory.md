# Elektro Engel – Bestandsaufnahme und Integrationsstand

**Stand:** 2026-11-01 · Branch `fictional-succotash` (Basis `536af2c`).
Keine Produktionsfreigabe, kein erreichbares Backend, kein KI-Zugang.

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
Erkennung, 500 Zeichen, max. 100 Einträge, Aufbewahrung 1–365 Tage (Standard 90),
Aktualisieren, Löschen, Gesamtlöschung. Gesprächsverläufe, Wissenseinträge und
Modelltraining bleiben getrennte Funktionen; Erinnerungen trainieren kein Modell.
`remember()` liefert einen Beleg – nur dieser darf eine „gespeichert“-Aussage
begründen. Standard `enabled=False`; keine HTTP-Route, kein Persistenz-Adapter.

## Kommunikation und Trennung

- Beide Apps bleiben getrennte Module/Application-IDs ohne gemeinsame Abhängigkeit.
- Serverseitig trennt `principal.app != payload.app` → `403 APP_AREA_MISMATCH`;
  Memory ist pro App und Subjekt isoliert. Keine gegenseitigen Rechte.
- Zwischen den Apps existiert keine direkte Kommunikation; beide sprechen nur
  (künftig) mit dem Backend. **Nicht getestet, nicht nachgewiesen.**

## Blocker für Online-Betrieb (Priorität)

1. Kein deploytes Backend / keine freigegebene HTTPS-Origin (`NIKNOLIG_BACKEND_URL`, `NIKNOLIG_DEFENSE_BACKEND_URL`).
2. Kein Auth-Aussteller (`Authenticator`) und kein Login in den Apps.
3. Kein genehmigter Audit-Sink, keine dauerhaften/verteilten Quotas, keine Kostenkontrolle in Geld.
4. Kein Provider-Zugang (Cloudflare-Account-ID und Token-Datei serverseitig, nicht im Repo) und keine Provider-/Kostenfreigabe.
5. Android: kein Client für `/support`; Offline-/Login-Fehlertexte nur für das lokale Analysemodul.
6. SecurityChain P0 Freigabe für Persistenz der Memory Engine, Tools und Pairing.

## Phasen

- **A** externes Modell über Gateway: Code vorhanden, nicht erreichbar/ungetestet. Modell ist fest `MODEL` in `ai_support.py` – Anbieterwechsel ist per `Provider`-Protokoll möglich, aber noch nicht per Konfiguration; die Apps sind unabhängig vom Anbieter, der Transport ist derzeit an Cloudflare gebunden.
- **B** eigener Wissensspeicher/Memory: Engines vorhanden (In-Memory), Persistenz offen.
- **C** lokales Open-Source-Modell: `LocalModelProvider`-Schnittstelle vorhanden, keine Gewichte/Runtime.
- **D** automatische Modellwahl: nicht begonnen. Keine Anbieterunabhängigkeit behauptet.

## Tests (tatsächlich)

- Backend: `python -m unittest discover -s backend/tests` im venv mit `requirements.txt` → 198 Tests OK, 20 übersprungen (benötigen PostgreSQL). Vorher 190 OK.
- Android-Gradle-Build/Unit-Tests, iOS, CI-Lauf, echter KI-Aufruf: **nicht ausgeführt**.
- Echter KI-Test: **nicht erbracht**; Definition of Done für „online“ nicht erfüllt.

## Nächster Schritt

Betreiber stellt freigegebene Backend-Origin, Auth-Aussteller und serverseitigen
Provider-Zugang bereit; danach P0-Freigabe, Audit-Sink/Quotas, dann Android-
Gateway-Client je App mit eigenem Scope.
