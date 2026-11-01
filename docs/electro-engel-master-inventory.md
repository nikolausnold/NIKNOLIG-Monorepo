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
Härtung (PR #189): Gespeichert wird nur mit `user_confirmed is True` (auch beim
Aktualisieren); IDs müssen `UUID` sein; abgelaufene Datensätze werden bei jedem
Zugriff physisch gelöscht; Speicher-/Löschfehler und fehlgeschlagene
Bereinigung enden als `STORE_UNAVAILABLE` (ohne Ursache/Inhalt), ein
fehlgeschlagenes Löschen wird nie als Erfolg gemeldet; fremde Datensätze eines
fehlerhaften Adapters werden ignoriert. Es wird nichts protokolliert.
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

- Backend: `python -m unittest discover -s backend/tests` im venv mit `requirements.txt` → 205 Tests OK, 20 übersprungen (benötigen PostgreSQL). Ausgangsstand 190 OK. Darin 15 Memory-Tests, u. a. App-/Nutzertrennung, Einwilligung, Ablauf, Löschfehler und Regression „keine HTTP-Route, `RuntimeControls` geschlossen, Modul nicht in `asgi.py`/`app.py` eingebunden“.
- Die bestehenden Contract-Tests zur Isolation der beiden Android-Module liefen mit.
- Android-Gradle-Build/Unit-Tests: **nicht ausführbar** (kein Android SDK in dieser Umgebung). iOS, CI-Lauf, echter KI-Aufruf: **nicht ausgeführt**.
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
- Android-Builds und CI-Läufe dieser Änderung nicht verifiziert (Änderung betrifft nur Backend/Docs).
