# Gemeinsame Backend-Grundlage

**Status: lokale Vorbereitung und deploybare Health-ASGI-Laufzeit, nicht produktionsfreigegeben.**

Dieses Verzeichnis definiert gemeinsame, versionierte Verträge für die getrennten
Apps `com.niknolig.app` und `com.niknolig.defense`. `app.py` dient lokal;
`asgi.py` prüft echte PostgreSQL- und Migrationsbereitschaft. Android-Module
enthalten getrennte Clients ausschließlich für `GET /health/ready`.
Produkt-, Login-, Geräte- und Pairing-APIs bleiben gesperrt. Eine separate
Deployment-Konfiguration existiert; kein Produktionsziel ist nachgewiesen. NIKNOLIG und
NIKNOLIG Defense bleiben getrennte Sicherheits- und Release-Domänen; gemeinsame
Verträge verleihen keine Rechte.
Elektro-Engel ist eine NIKNOLIG-Systemfunktion, keine dritte App.

## Artefakte

- [`openapi.yaml`](openapi.yaml): OpenAPI 3.1-Vertrag für nicht-sensitive
  Liveness-/Readiness-Prüfungen und einheitliche Fehlerantworten. Es sind bewusst
  noch keine operativen Geräte-, Profil- oder Pairing-Endpunkte freigegeben.
- [`app.py`](app.py): lokale stdlib-Health-/gesperrte KI-Vorbereitungs-Laufzeit;
  [`asgi.py`](asgi.py): zusätzliche FastAPI-Health-Laufzeit mit PostgreSQL-Prüfung.
- [`migrations/001_initial_contract.sql`](migrations/001_initial_contract.sql):
  vorgeschlagenes relationales Modell für App-Bereiche, Installationen,
  Geräteidentitätsstatus und spätere Zwei-App-Link-Beziehungen. Das Anwenden der
  Migration ist bis zur Architektur-/Security-Freigabe gesperrt.
- [`compose.yaml`](compose.yaml): lokale PostgreSQL-Entwicklung, Loopback-only;
  [`compose.production.yaml`](compose.production.yaml): separates Health-Deployment.
- [`.env.example`](.env.example): Variablennamen ohne eingetragene Credentials.
- [`contracts/`](contracts/): versionierte, deklarative Entwürfe für
  Gerätewechsel-Zustimmung, minimierte Audit-Ereignisse, Sensor-Capabilities und
  abgeleitete Sensorzusammenfassungen. Sie sind nicht an eine Laufzeit-API
  angeschlossen.
- [`tests/test_contracts.py`](tests/test_contracts.py): Python-Standardbibliothek-
  Regressionstests für kritische Vertrags- und Isolationsinvarianten. Sie sind
  keine vollständige JSON-Schema-Validierung, Integration-, Sicherheits- oder
  Gerätetests.

Fehlercodes werden auf Implementierungsebene einheitlich zugeordnet:
`AUTHENTICATION_REQUIRED`/`AUTHENTICATION_INVALID` → 401;
`AUTHORIZATION_DENIED`/`APP_AREA_MISMATCH` → 403;
`DEVICE_IDENTITY_UNVERIFIED`/`PAIRING_REQUIRED`/`PAIRING_EXPIRED`/
`REPLAY_DETECTED` → 403 (Integritäts-/Sicherheitsereignisse beenden die Sitzung);
`VALIDATION_FAILED` → 400; `RATE_LIMITED` → 429; `CONFLICT` → 409;
`NOT_FOUND` → 404; `SERVICE_UNAVAILABLE` → 503; `INTERNAL_ERROR` → 500.
Antworten enthalten nur den stabilen Code, eine nicht-sensitive Nachricht und
eine Korrelations-ID; interne Details sind nicht offenzulegen.

## Grenzen und Sicherheitsanforderungen

1. **App-Bereiche:** Jeder Token und jede Ressource muss einem einzelnen
   `app_area` (`niknolig` oder `niknolig-defense`) zugeordnet sein.
   Autorisierung prüft bei jeder Operation App-Bereich, Akteur, Ressource und
   konkrete Aktion. Bereichsabweichungen werden abgelehnt; Defense erhält keine
   Rechte aus NIKNOLIG, einem gemeinsamen Konto, einer gemeinsamen API oder
   einem Linkstatus.
2. **Authentifizierung:** Geschützte API-Aufrufe benötigen künftig kurzlebige,
   widerrufbare Zugriffsnachweise mit festgelegtem Aussteller, Zielgruppe,
   Ablaufzeit, App-Bereich und minimalen Aktionsrechten. Tokenformat, Aussteller,
   Login-/Registrierungsfluss, Schlüsselrotation und Durchsetzung sind offen;
   aus dem Bearer-Schema des OpenAPI-Vertrags folgt keine implementierte oder
   freigegebene Authentifizierung.
3. **Geräteidentität:** Eine Installations-ID oder ein Android-Gerätename ist
   kein Authentizitätsnachweis. Vorgesehen ist eine registrierte
   App-Installation mit Challenge-basierter Besitzprüfung eines
   installationsgebundenen öffentlichen Schlüssels. Hardware-Backing,
   Attestierung, Neuinstallation, Backup/Restore, Rotation und Widerruf benötigen
   eine freigegebene Richtlinie. Private Schlüssel werden nie an das Backend
   übertragen; SQL speichert keinen privaten Schlüssel.
4. **Protokollgrenze:** Geräte sprechen ausschließlich eine versionierte API
   über TLS an; Apps erhalten keinen Datenbankzugriff. Für zukünftige
   Zwei-Geräte-Nachrichten sind Gegenseitigkeit, Frische/Replay-Schutz,
   explizite Nutzerzustimmung, erlaubte Aktionen, Grenzen für Payloads,
   Abbruch/Widerruf und erneute Peer-Authentifizierung festzulegen. Es gibt
   keinen stillschweigenden Offline-Queue-/Retry-Mechanismus.
5. **Datensparsamkeit:** Keine Finanztransaktionen, Zahlungsdaten, unnötigen
   Profildaten, Tokens, Schlüssel oder vollständigen Request-Payloads in Logs.
   Aufbewahrung, Löschung, Benutzeridentität und konkrete Nutzdaten sind noch
   nicht fachlich freigegeben.
6. **Healthchecks:** `/health/live` meldet nur Prozessverfügbarkeit;
   `/health/ready` prüft bei `app.py` und `asgi.py` PostgreSQL sowie die
   Migrations-Invarianten und liefert bei fehlender Konfiguration, Ausfall oder
   Schemaabweichung 503. Antworten legen keine Umgebungsvariablen, internen Hosts,
   Stacktraces oder Datenbankdetails offen.

## Lokale Datenbankumgebung

Docker Compose veröffentlicht PostgreSQL ausschließlich auf
`127.0.0.1:54329` (konfigurierbar), nutzt ein erforderliches lokales Passwort,
ein isoliertes internes Compose-Netzwerk und ein lokales benanntes Volume. Es
gibt in dieser lokalen Datei keinen API-Container und keine Internetfreigabe.
`.env` wird lokal aus `.env.example` erstellt und nicht
eingecheckt. Das Compose-Setup ist nicht für Deployment oder sensible Daten
bestimmt.

## Lokaler Health-Server

Mit Python 3 starten:

```sh
python3 backend/app.py
```

Die Standardbindung ist `127.0.0.1:8000`. `BACKEND_HOST` und `BACKEND_PORT`
können als Umgebungsvariablen gesetzt werden. Die Anwendung lädt `.env` nicht
automatisch. `/health/live` meldet Prozessverfügbarkeit. `/health/ready` erfordert
eine explizite PostgreSQL-Konfiguration und eine gültige, geprüfte Migration;
andernfalls antwortet es mit einer generischen 503-Antwort. Andere GET-Pfade geben
eine generische 404-Antwort zurück. Es gibt keine Anmeldung, Gerätefunktion oder
freigegebene Produkt-API.
Die Standardbibliotheks-HTTP-Laufzeit ist nur für lokale Entwicklung und
Vertragstests gedacht: nicht öffentlich exponieren oder als produktiven
Internetserver verwenden. Die separate ASGI-Konfiguration ersetzt keine
Produktions-, TLS-, Authentifizierungs- oder Betriebsfreigabe.

## SecurityChain-P0 und Freigabe

Der Reviewentwurf
[`docs/securitychain-p0-specification.md`](../docs/securitychain-p0-specification.md)
fasst vorgeschlagene Muss-/Abbruchkriterien zusammen. Er ist nicht genehmigt
oder normativ wirksam; daher wird keine P0-Konformität behauptet.
**Produktive Geräteintegration und die operative API bleiben BLOCKED**, bis
mindestens die verbindlichen P0-Kriterien, Bedrohungsmodell, Daten-/Aktionsumfang,
Rollen, Identitäts-/Authentifizierungsverfahren, Transport, Widerruf,
Aufbewahrung und Abnahmekriterien schriftlich von den Verantwortlichen
freigegeben und überprüfbar getestet sind. Die SQL-Modelle und zukünftigen
Routen in dieser Grundlage sind Vorschläge, keine Freigabe dieser offenen
Entscheidungen. Bei fehlender Prüfung gilt fail closed. Der Reviewentwurf
überschreibt keine bestehenden Sicherheitsregeln.

## Integration in den separaten App-Repositories

Die Quell-Repositories `nikolausnold/NIKNOLIG` und
`nikolausnold/NIKNOLIG-Defense` wurden nicht geändert. Nach Freigabe müssen
Änderungen getrennt und unabhängig reviewed werden:

| App-Repository | Vorgesehene Dateien / Schnittstellen | Abhängigkeit / Gate |
| --- | --- | --- |
| `nikolausnold/NIKNOLIG` | `app/build.gradle.kts` (geprüfte HTTP-/TLS-Clientabhängigkeit), `app/src/main/AndroidManifest.xml` (nur freigegebene Netzwerkrechte), `app/src/main/java/com/niknolig/app/` (eigener API-Client und app-spezifische Authentifizierung), `app/src/main/res/values/strings.xml` (Zustimmungs-/Fehlertexte), `app/src/test/` und `app/src/androidTest/` (Vertrag, Ablehnung, Widerruf) | Eigener App-Bereich `niknolig`; API-Client aus dem freigegebenen Vertrag generieren oder dagegen testen. Keine Defense-Credentials oder gemeinsamen Laufzeitrechte. |
| `nikolausnold/NIKNOLIG-Defense` | `app/build.gradle.kts` (separat geprüfte Clientabhängigkeit), `app/src/main/AndroidManifest.xml` (nur freigegebene Netzwerkrechte), `app/src/main/java/com/niknolig/defense/` (eigener API-Client und app-spezifische Authentifizierung), `app/src/main/res/values/strings.xml` (Zustimmungs-/Fehlertexte), `app/src/test/` und `app/src/androidTest/` (Vertrag, Ablehnung, Widerruf) | Eigener App-Bereich `niknolig-defense`; niemals das NIKNOLIG-Token oder dessen Installationsidentität wiederverwenden. |

Für beide Apps müssen zusätzlich Backend-Basis-URL pro Build-Variante, TLS-
Vertrauensregeln, Authentifizierung/Tokenbezug, Datenschutztexte und
Fehler-/Timeoutverhalten beschlossen werden. Diese Werte dürfen nicht aus
diesem lokalen Compose-Setup als Produktionskonfiguration übernommen werden.
Keine App-Repositories, URLs, Berechtigungen, Abhängigkeiten oder Workflows
werden durch dieses Monorepo automatisch geändert.

## Hetzner-Verbindung: offene Voraussetzungen

In diesem Repository gibt es weder eine bestätigte Hetzner-Adresse noch
DNS-/TLS-Konfiguration, einen produktiv betriebenen API-Endpunkt oder ein
Deployment. Beide Android-Module können nach expliziter Build-Konfiguration
ausschließlich den nicht-sensitiven Health-Endpunkt über HTTPS prüfen. Die
separaten Umgebungsvariablen `NIKNOLIG_BACKEND_URL` und
`NIKNOLIG_DEFENSE_BACKEND_URL` werden für Release-Builds verlangt; HTTPS ist
Pflicht, Loopback- und `.invalid`-Hosts werden abgelehnt. Es sind keine
Produktionsadressen oder Zugangsdaten hinterlegt. Eine Adresse oder ein Endpunkt
wird nicht angenommen oder erfunden.

Vor einer Android-Verbindung müssen die Verantwortlichen mindestens liefern und
freigeben:

1. Die kanonische HTTPS-Basis-URL des Hetzner-Servers, verwaltete DNS-Auflösung,
   TLS-Zertifikatskette/-Erneuerung und die festgelegten Client-
   Vertrauensregeln; kein HTTP-Fallback.
2. Eine bereitgestellte, versionierte Produkt-API mit freigegebenen OpenAPI-
   Operationen, Datenumfang und Fehlerantworten. Die vorhandenen Health-Routen
   implementieren keine Produktfunktion.
3. Die normative SecurityChain-P0-Fassung, Bedrohungsmodell und schriftliche
   Produkt-/Security-Freigabe, einschließlich App-Bereich, Nutzer-/Installations-
   Identität, widerrufbarer Token-Ausgabe/-Erneuerung und Schlüsselrichtlinie.
4. Einen freigegebenen Test-/Staging-Endpunkt und nicht-produktive Testidentitäten
   für Negativ-, Ablauf-, Widerrufs-, TLS- und Timeouttests; keine produktiven
   Tokens in Builds oder Tests.
5. Pro Android-App die genehmigte, zur Build-Variante passende Serveradresse,
   Token-Bezugs-/Speicherregeln (OS-geschützt und getrennt je App) sowie
   verbindliche Verbindungs-/Lese-Timeoutwerte und Abbruch-/Fehlerverhalten.
6. Betriebsverantwortung beim Serverbetreiber: Deployment-/Rollbackverfahren,
   Monitoring, Zertifikats- und Schlüsselrotation sowie erreichbarer
   Incident-Kontakt.

Erst danach können Produktoperationen der Apps unabhängig und gegen den
freigegebenen Vertrag integriert und getestet werden. Bis dahin bleibt jede
Produktverbindung fail closed; Health-Abfragen geben keine geschützten Rechte.

## Verifikation und nächste Schritte

`python3 -m unittest discover -s backend/tests` prüft Vertragsinvarianten,
Healthchecks und die gesperrte lokale Support-Route. KI-Mocks werden ebenfalls
geprüft. Die lokale
Compose-Konfiguration kann mit diesem Platzhalter syntaktisch geprüft werden:

```sh
POSTGRES_PASSWORD=local-only-check docker compose \
  --env-file backend/.env.example -f backend/compose.yaml config --quiet
```

Der Datenbankstart verlangt bewusst ein gesetztes lokales Passwort und ist nicht
Teil der automatischen Tests. Keine der Prüfungen belegt eine operative API,
sichere Authentifizierung, P0-Freigabe oder Verbindung zwischen zwei physischen
Geräten.

Gerätewechsel-, Sensorverträge, Android API-/Berechtigungsanforderungen und
Geräteabnahmeplan stehen in
[`docs/electro-engel-multidevice-sensors.md`](../docs/electro-engel-multidevice-sensors.md).
Sie genehmigen keine Implementierung und lockern das P0-Gate nicht.

Die Android-/iOS-übergreifende Vertrags- und Backend-Architektur, vorhandene
Vertragslücken, Testparität und der Integrationsplan für separate iOS-Apps
stehen in
[`docs/mobile-cross-platform-architecture.md`](../docs/mobile-cross-platform-architecture.md).
Das Dokument ergänzt die Bestandsverträge, erstellt aber keine Produkt-API und
hebt das P0-Gate nicht auf.

Nächste Schritte: SecurityChain-P0-Nachweis und fachlich verantwortliche
Freigaben einholen; API-Datenflüsse und Ressourcenumfang mit beiden App-Teams
abgleichen; Identitätsanbieter, Schlüsselrichtlinie, Serverplattform und
Betriebsverantwortung auswählen; dann OpenAPI/Schema versionieren und
Implementierung, Negativtests und unabhängige Sicherheitsprüfung freigeben.
Bei nicht abgedeckten Sicherheitsentscheidungen hier anhalten.

## KI-Support: vorbereitete Schnittstelle, keine Betriebsfreigabe

`ai_support.py` trennt die Provider-Schnittstelle vom lokalen HTTP-Endpunkt
`POST /support` und von Authentifizierung, Autorisierung und Kontingenten. Die
gemeinsame Route nimmt genau `app` (`niknolig` oder `niknolig-defense`) und
`message` entgegen; die Nachricht ist auf 2.048 UTF-8-Bytes begrenzt. Die
bisherige Route `POST /v1/ai/support` bleibt als lokale Kompatibilitätsroute
mit ihrem bisherigen Request-Format verfügbar.
Der separate Vertrag `ai-support.openapi.yaml` ist eine lokale Vorbereitung,
kein veröffentlichter Dienst. `openapi.yaml` bleibt der unveränderte
Health-Vertrag. Der Standardstart aktiviert keinen Provider; Umgebungsvariablen
können weder einen Provider noch einen kostenpflichtigen Dienst freischalten.
Tests injizieren ausschließlich lokale Mocks. Es gibt keine echten
Provider-Aufrufe, neuen Tokens, Konten, Deployments oder Abonnements.

### Architektur und Sicherheitsgrenzen

- Ein gemeinsames Provider-Protokoll erlaubt später den Austausch des Anbieters,
  ohne einen Provider-Schlüssel oder dessen SDK in die Apps aufzunehmen.
- Ein späterer Anbieter wird ausschließlich serverseitig als Adapter des
  `Provider.generate(prompt) -> ProviderResult`-Protokolls eingebunden und
  explizit in `SupportService` injiziert. Ein freigegebener Adapter muss einen
  festen Anbieter/Host, begrenzte Timeouts und Ausgaben, sichere Credential-
  Ablage sowie Datenschutz-, Lizenz-, Kosten-, Authentifizierungs-, Quota- und
  Audit-Freigaben umsetzen. Bis dahin gibt es weder Netzwerktransport noch
  kostenpflichtige Provider-Aufrufe; die Standardkonfiguration bleibt gesperrt.
- Der vorbereitete Cloudflare-Adapter verwendet ausschließlich einen injizierten
  Transport. Ein authentifizierter Netzwerktransport wird **nicht** mitgeliefert.
  Anbieter, Modell und Provider-Ziel sind keine frei wählbaren Request-Felder.
- Der Authenticator muss eine serverseitig verifizierte, aktive, nicht
  abgelaufene Identität mit App-Bereich und minimalen Berechtigungen liefern.
  Der Standard verweigert Zugriff; Test-Authentifizierung ist kein Login-System
  und darf nicht als Produktivauthentifizierung übernommen werden.
- NIKNOLIG und Defense haben getrennte Autorisierung und Kontingente.
  Elektro-Engel ist eine Funktion innerhalb von `niknolig`, kein dritter
  App-Bereich und kein Weg zu Defense-Rechten.
- Anbieter- und Kostenfreigabe sind getrennte Gates. Offline-Modus und Kill
  Switch sperren neue Aufrufe. Ein Kill Switch kann bereits beim Anbieter
  laufende Verarbeitung nicht rückwirkend ungeschehen machen.
- Größenbegrenzungen, Output-Limit, begrenzte Aufrufe und vorab reservierte
  Tokenkontingente begrenzen Missbrauch. Fehlgeschlagene beziehungsweise unklare
  Provider-Aufrufe dürfen kein unbegrenztes kostenloses Wiederholen ermöglichen.
- Audit-Ereignisse enthalten nur minimierte Betriebsmetadaten; keine Prompts,
  Antworten, Bearer-Tokens, Profile oder E-Mail-Adressen. Ein ausgefallener
  verpflichtender Audit-Sink darf keine neuen Provider-Aufrufe erlauben.
- Modelltext ist nicht vertrauenswürdig: als reiner Text anzeigen, keine
  HTML-Ausführung, Tools, Steuerbefehle, Berechtigungsentscheidungen oder
  autonome Aktionen daraus ableiten.

Die lokalen In-Memory-Limits und Mock-Audits sind **kein verteilter, persistenter
Abrechnungsschutz**: Neustarts und weitere Instanzen erfordern vor Freigabe
einen atomaren, gemeinsamen Kontingentspeicher, persistente Tages-/Monatsbudgets,
Audit-Retention und überwachte Betriebsgrenzen. Token sind nicht pauschal
Neurons oder USD. Ein Modellwechsel verlangt neue Preis-/Budgetprüfung.
Der Standardbibliotheksserver ist kein produktionsfähiger Internetserver.

Konfiguration erfolgt derzeit nur durch explizite Python-Abhängigkeitsinjektion
im lokalen Testaufbau, nicht durch ein Dashboard oder einen aktivierbaren
Produktionsschalter:

| Baustein | Lokale Konfiguration / Grenze |
| --- | --- |
| `RuntimeControls` | `enabled`, `provider_approved`, `cost_approved` müssen wahr sein; `offline` oder `killed` sperren; Standard verweigert |
| `Authenticator` / `Principal` | Verifizierter `subject`, `app`, `permissions`, Ablaufzeit und aktiver Status; `ai:support` bzw. `ai:electro-engel` separat und jeweils an dieselbe App gebunden |
| `Provider` / `CloudflareWorkersAI` | Austauschbares `generate`-Protokoll; Cloudflare nur mit injiziertem `WorkersAITransport`, ohne mitgelieferten Netzwerkzugang |
| `AuditSink` | Verpflichtender injizierter Metadaten-Sink; Standard nicht verfügbar und damit sperrend |
| `Limits` / `QuotaStore` / `LocalQuotas` | Austauschbarer Kontingentspeicher; lokal Standard 5 Aufrufe je Minute/Principal/App, 20.000 reservierte Tokens und 50 Aufrufe je App/UTC-Tag, global 80/Tag, 2 gleichzeitige Aufrufe; maximal 1.024 aktive Principal-Einträge |
| Größen / Timeout | Maximal 2.048 UTF-8-Bytes Prompt, 1.024 UTF-8-Bytes Antwort, 256 Output-Tokens; HTTP-Body maximal 8.192 Bytes mit 2 Sekunden Lesefrist; Adapter fordert 5 Sekunden Transporttimeout an |

Der Input wird konservativ nach UTF-8-Bytes einschließlich Systemtext und
Framing reserviert, nicht nach der unsicheren Faustregel „vier Zeichen je
Token“. Lokale Limits sind Test-/Vorbereitungswerte und **keine genehmigten
Produktionsbudgets**. Der injizierte echte Transport muss Timeout,
Antwortgrößen, festen Provider-Host und Abbruch später selbst erzwingen; der
Protokollparameter allein unterbricht keinen beliebigen blockierenden Code.
Lokale Audit-Ereignisse erfassen akzeptierte Reservierungen, Provider-Ergebnisse
und nachträgliche Gate-Sperren. Frühe Ablehnungen wegen Authentifizierung,
Validierung, Autorisierung, Rate/Budget oder anfänglicher Deaktivierung sind
noch nicht im Audit erfasst. Das ist keine vollständige produktive
Security-Überwachung. Vor Freigabe sind diese Ablehnungen, Proxy-/WAF-Signale
und Manipulationsschutz ohne Inhalte/Secrets verbindlich festzulegen.

### Cloudflare Workers AI: bevorzugter Kandidat, noch nicht freigegeben

Workers AI passt als austauschbarer serverseitiger Textprovider. Zwei spätere
Betriebsvarianten sind zu unterscheiden:

| Variante | Benötigt nach ausdrücklicher Freigabe | Nicht in dieser Änderung |
| --- | --- | --- |
| Bestehendes Python-Backend → Workers AI REST | Cloudflare-Konto, Account-ID, accountbeschränkter API-Token mit Workers AI Read/Edit, serverseitiger Secret Store, fester HTTPS-Transport mit Timeout und ohne Redirects | Kein Token erstellt, kein echter Transport oder REST-Aufruf |
| Separater Cloudflare Worker mit AI-Binding | Freigegebener Worker und `AI`-Binding; Modellaufruf serverseitig über `env.AI.run` ohne Provider-Token im Mobilclient | Kein Worker-Gerüst, Binding, Wrangler-Deployment oder Dienst aktiviert |

Ein neuer Worker ist keine Voraussetzung für die Vorbereitung des vorhandenen
Python-Backends. Authentifizierung, atomare Limits und Audit gelten für beide
Varianten. Cloudflare-Konto/Account-ID beweisen nicht die Identität eines
App-Nutzers. Nötig bleibt ein eigener freigegebener Identity-Provider mit
Aussteller-/Audience-Prüfung, kurzen Laufzeiten und Widerruf.

Datenschutzfreigabe muss Datenarten, Einwilligung/Rechtsgrundlage, Region,
Auftragsverarbeitung, Modelllizenz und Löschfristen festlegen. Cloudflare
beschreibt für normale zustandslose Workers-AI-Inferenz keine Nutzung der
Inhalte zum Training und keine dauerhafte Inhaltsaufbewahrung; Ausnahmen für
gesetzliche Pflichten und zustandsbehaftete Funktionen bleiben bestehen.
AI-Gateway-Logging/Caching, eigene Logs und Speicher können Inhalte gesondert
speichern und bleiben ohne gesonderte Freigabe aus.

### Kosten: Quellenstand 19.10.2026, USD

Offizielle Dokumentation wurde aus dem öffentlichen Repository
[`cloudflare/cloudflare-docs`](https://github.com/cloudflare/cloudflare-docs)
gelesen, da die direkte Dokumentationsdomain in dieser Umgebung nicht
auflösbar war. Dies ist eine Tarifrecherche, kein Zugriff auf ein Betreiberkonto
oder eine Rechnung. Preise können sich ändern; vor Freigabe erneut bestätigen.

| Posten | Verifizierter veröffentlichter Tarif | Bedeutung |
| --- | --- | --- |
| Workers AI Free | 10.000 Neurons pro Tag ohne Gebühr; Reset 00:00 UTC | Keine Übertragung ungenutzter Tagesfreimengen; Konto-Freimenge nicht pro App einplanen |
| Workers AI Paid | 0,011 USD je 1.000 Neurons oberhalb der täglichen Freimenge | Paid-Plan für Überschreitung erforderlich; manche Modelle benötigen gesondert eine Zahlungsmethode |
| Modellbeispiel `@cf/meta/llama-3.1-8b-instruct-fp8-fast` | 0,045 USD/Million Input-Tokens; 0,384 USD/Million Output-Tokens | Nur Rechenbeispiel, keine Modellfreigabe oder Qualitätszusage |
| Workers Paid | Mindestens 5 USD/Monat je Account | Zusätzlich zur KI-Nutzung; kein neues Abonnement abgeschlossen |
| Worker Standard Requests/CPU | 10 Mio. Requests und 30 Mio. CPU-ms/Monat enthalten; danach 0,30 USD/Mio. Requests und 0,02 USD/Mio. CPU-ms | Nur relevant bei gewähltem Worker-Betrieb; Logs/Speicher/andere Dienste separat kalkulieren |

Beispiel ohne Freimengenabzug: 1.000 Anfragen mit jeweils 1.000 Input- und
300 Output-Tokens beim genannten Beispielmodell ergeben rechnerisch
0,045 + 0,1152 = **0,1602 USD reine Inferenz**. Das ist keine Gesamtrechnung:
Tagesverteilung, tatsächliche Tokens, Neuronabrechnung, Grundgebühren,
Betriebsdienste, Steuern und Währungsumrechnung sind zusätzlich zu beachten.
Die Tagesfreimenge darf nicht als garantiertes kostenloses Produktionsbudget
verstanden werden.

**Durch diese Vorbereitung verursachte Provider-Nutzung: 0 Aufrufe,
0 neu aktivierte kostenpflichtige Dienste, 0 USD neue Inferenzkosten.**
Bestehende Betreiberkosten sind ohne Konto-/Rechnungszugriff unbekannt; sie
werden nicht als null behauptet. Betreiber muss ein konkretes Tages- und
Monatsbudget in Währung sowie Schwellen/Abbruchregeln ausdrücklich genehmigen.
Billing-Alarme allein ersetzen keine harte Anwendungssperre.

Quellen und abgerufene Datei-SHAs:

- [Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/),
  [Quelldatei](https://github.com/cloudflare/cloudflare-docs/blob/main/src/content/docs/workers-ai/platform/pricing.mdx),
  `2c2059a4388ff25082f590e1430adad229a16d90`.
- [Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/),
  [Quelldatei](https://github.com/cloudflare/cloudflare-docs/blob/main/src/content/docs/workers/platform/pricing.mdx),
  `c512de77f0f3af922f568949feb67d5a40a3e56a`.
- [REST-Voraussetzungen](https://developers.cloudflare.com/workers-ai/get-started/rest-api/),
  `d686c618f11ab679ce6d6404d634022a515a1f18`;
  [AI-Binding](https://developers.cloudflare.com/workers-ai/configuration/bindings/),
  `51750be8e394b6810f6845ed2b22d2356ebc5647`.
- [Data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/),
  `8e6772ef74d2c123213f42954fa056026476efdb`.

### Konten, Konfiguration und Freigabefolge

1. Betreiber prüft vorhandenes [Cloudflare-Konto](https://dash.cloudflare.com/)
   und [Workers-AI-Bereich](https://dash.cloudflare.com/?to=/:account/ai/workers-ai),
   ohne jetzt Tarif, Credits oder Modelle zu aktivieren. Ein Apple- oder
   Google-Konto ist für die serverseitigen Mock-Tests nicht erforderlich.
2. Anbieter, konkrete Modellversion, Lizenz/Datenschutz und Datenfluss
   schriftlich genehmigen. Kosten separat mit Preisstand, Tages-/Monatslimit,
   verantwortlicher Person und Abbruchverfahren genehmigen.
3. Serverhosting/TLS, Identity-Provider, getrennte App-Audiences/Berechtigungen,
   Secret Store, verteilte Kontingente und verpflichtenden Audit-Sink freigeben.
   Die Test-Injektionen ersetzen keine dieser Betriebsentscheidungen.
4. Erst nach dieser Freigabe den echten Transport implementieren und prüfen;
   Account-ID, Secret-Referenz oder Binding, Modell-Allowlist, Timeout,
   Payload-/Output-Grenzen, Rate Limits und Budget explizit konfigurieren.
   Keine Secrets in Git, Apps, URLs oder Logs. Keine globale Admin-Berechtigung.
5. Kill Switch und Offline-Verhalten testen; Last-/Negativtests zunächst mit
   Mock. Echte kostenpflichtige Smoke-Tests nur nach zusätzlicher ausdrücklicher
   Ausgabenfreigabe, niemals automatisch in CI.
6. P0-/Security-/Produktabnahme abschließen, danach kontrollierten Rollout und
   Monitoring erlauben. Rücknahme: neue Aufrufe sperren, Provider-Zugang
   widerrufen, unbekannte In-Flight-Kosten konservativ verbuchen.

### Android, iOS und Offline-Fallback

Android behält zwei getrennte Module, Installationen und app-scoped Clients.
Die vorhandene `SupportActivity` prüft ausschließlich `GET /health/ready`; damit
wird keine KI-, Login- oder Produktfunktion verfügbar. Die bestätigte E-Mail-
Alternative funktioniert unabhängig von diesem Health-Check. Dabei werden keine
Credentials oder Supportanfragen an das Backend übertragen. Release-Builds
bleiben ohne freigegebene, app-spezifische HTTPS-URL gesperrt. Elektro-Engel
verwendet später ausschließlich explizite NIKNOLIG-Berechtigungen.

Native SwiftUI-Vorschauen für beide Apps existieren unter `apps/ios/`. Ihre
Supportansichten prüfen ebenfalls ausschließlich `GET /health/ready` und öffnen
nach Bestätigung einen nutzergeprüften E-Mail-Entwurf; sie rufen keinen KI-
Endpunkt auf. Es gibt keine gemeinsamen Android-Tokens oder App-Schlüssel.
Siehe [plattformübergreifende Architektur](../docs/mobile-cross-platform-architecture.md)
und [iOS-Vorschau](../apps/ios/README.md).

Bei offline/gesperrt/nicht freigegeben/Timeout/Anbieterausfall zeigen die
Android- und iOS-Supportansichten verständlich, dass KI-Support nicht verfügbar
oder freigegeben ist. Die E-Mail-Alternative bleibt unabhängig vom Health-Check
verfügbar. Keine erfundene Antwort, keine Offline-Warteschlange oder automatischen
Wiederholungen.
Eine unklare Modellantwort ist kein Beweis für Lösung oder Sicherheit.
`escalationRequired=false` bedeutet nur, dass kein technischer Eskalationsgrund
erkannt wurde, nicht „gelöst“ oder „hilfreich“. Eine semantische Erkennung
„KI weiß nicht weiter“ ist noch nicht implementiert; eine Nutzeroption für
ungelöste Fälle bleibt vor der mobilen Integration festzulegen.
Persönliche Hilfe bleibt eine bewusste Eskalation mit Empfänger-/Datenprüfung;
kein automatischer E-Mail-Versand und kein ungefragtes Mitsenden von Verlauf,
Profilen oder sensiblen Daten. Verfügbarkeits- und Kostenfehler sind kein Anlass,
Authentifizierung oder Berechtigungen zu umgehen.

## Ergänzung: deploybare Health-ASGI-Laufzeit (ohne Produktionsfreigabe)

`app.py` ist eine lokale Vorbereitungslaufzeit; `asgi.py` ist der
containerisierte FastAPI-Einstiegspunkt. Beide implementieren die Health-Routen:
Liveness benötigt keine Datenbank; Readiness prüft eine echte PostgreSQL-
Verbindung mit `SELECT 1`, bekannte Migrationen samt SHA-256 und Schema-
Invarianten. Fehlende Verbindung, Migration oder Schema-Drift liefern eine
nicht-sensitive 503-Antwort. Alle Antworten erhalten `Cache-Control: no-store`
und `X-Content-Type-Options: nosniff`. Die ASGI-Laufzeit registriert ausschließlich
Health-Routen; FastAPI Swagger/ReDoc und `/openapi.json` sind ausdrücklich
deaktiviert, und der Caddy-Reverse-Proxy leitet ausschließlich die Health-Pfade
weiter. [`openapi.yaml`](openapi.yaml) ist ein versionierter Vertrag, kein
bereitgestellter HTTP-Endpunkt. KI-Support, Login, Pairing und Produkt-Routen
werden dort nicht aktiviert, auch nicht durch Umgebungsflags.
Die asynchrone Readiness-Prüfung hat eine gemeinsame clientseitige Frist von
4 Sekunden für Verbindungsaufbau und sämtliche Abfragen. Bei Fristablauf wird
die Verbindung lokal geschlossen, bevor die Abfrage abgebrochen wird; auch eine
bereits aufgebaute, danach stumme TCP-Verbindung blockiert Liveness nicht.
Constraints werden samt zugehöriger Tabelle, Typ und Definition geprüft
(einschließlich beider Produkt-Primärschlüssel), Indizes samt Tabelle,
Eindeutigkeit, Schlüsselspalten und Teilindex-Prädikat.

```sh
python3 -m pip install -r backend/requirements.txt
# DATABASE_URL oder PGHOST, PGDATABASE, PGUSER und separat bereitgestelltes
# PGPASSWORD_FILE konfigurieren; keine Credentials in Git oder Shell-History.
python3 backend/migrate.py
python3 -m uvicorn asgi:app --app-dir backend --host 127.0.0.1 --port 8000 \
  --no-proxy-headers --no-server-header --no-access-log
python3 -m unittest discover -s backend/tests
```

`migrate.py` initialisiert standardmäßig **nur** das Infrastruktur-Ledger
`000_health_runtime`; es erstellt keine Produkt-Tabellen. Transaktion, advisory
lock und Prüfsummen machen Wiederholungen sicher; unbekannte/abweichende
Versionen und unverbuchte bestehende Produkt-Schemata werden abgelehnt.
Die vorhandene `001_initial_contract.sql` bleibt unverändert und gesperrt:
`--approve-contract-schema` darf ausschließlich **nach tatsächlicher separater
Architektur-/Security-/Datenmodell-Freigabe** verwendet werden. Das Flag ist
kein Freigabenachweis und wird im Produktions-Compose nicht gesetzt.
Kein automatisches Downgrade oder Löschen vorhandener Daten wird durchgeführt.
Integrationstests laufen zusätzlich bei `BACKEND_TEST_DATABASE_URL`; sie
löschen das `public`-Schema und verlangen deshalb ausdrücklich eine wegwerfbare
Testdatenbank mit Namenssuffix `_backend_test`, niemals eine Betriebsdatenbank.
Da auch Rollenregressionen geprüft werden, muss die gesamte PostgreSQL-Instanz
isoliert und wegwerfbar sein. Ein lokaler TCP-Proxy simuliert nach erfolgreicher
Datenbankanmeldung einen vollständigen Antwortausfall; der Test prüft 503,
Verbindungsschließung und gleichzeitig weiterhin erfolgreiche Liveness-Abfragen.

`compose.yaml` bleibt lokal unverändert. `compose.production.yaml` ist eine
**eigenständige**, nicht damit zu kombinierende Konfiguration:

```sh
docker compose -f backend/compose.production.yaml config --quiet
docker compose -f backend/compose.production.yaml up --build -d
```

### Falsches oder veraltetes Container-Image sicher ersetzen

Der vorliegende ASGI-Einstiegspunkt registriert `GET /health/live` und
`GET /health/ready`; das Backend-Image kopiert `asgi.py` und startet
`uvicorn asgi:app`. Zusätzlich übernimmt diese Laufzeit aus den vom Betreiber
bereitgestellten Produktionsausschnitten die Antwortformate von `GET /health`
(`status: ok`, `service: NOLD API`, `version: 0.2.0`), `GET /projects`
(`projects: [niknolig, defense, monorepo]`) und `GET /db/health`
(`status: ok`, `service: NOLD PostgreSQL`; bei Fehler HTTP 503 mit
`{"detail":"database_unavailable"}`). Der Projektkatalog ist statische Metadaten,
keine Produkt-API oder Freigabe. Die Datenbankroute führt ausschließlich `SELECT 1`
über die vorhandene zeitbegrenzte PostgreSQL-Verbindung und deren externe
Konfiguration aus; Produktions-Verbindungswerte werden nicht übernommen.

**Verbleibende Unterschiede zur beschriebenen Produktion:** `/health/live` und
`/health/ready` behalten den bestehenden Vertrag (`live` beziehungsweise `ready`);
Readiness prüft weiterhin PostgreSQL und Migrationsinvarianten statt konstant
`ok` zu melden. `/projects/{name}/health` und der zugehörige Konfigurationsleser
sind nicht übernommen; es gibt keine neuen externen Anbieteraufrufe, Secret-Mounts
oder Authentifizierungsfreigaben. Der versionierte OpenAPI-Vertrag bleibt der
Health-Vertrag; die drei Kompatibilitätsrouten sind hier beschrieben und separat
getestet. Caddy bleibt unverändert auf die beiden bisherigen Health-Pfade begrenzt:
die neuen Routen sind in dieser Compose-Konfiguration nicht öffentlich erreichbar.
Das Repository-Image ist daher **kein funktionsgleicher Produktionsersatz**.
Die vom Betreiber genannte Produktion startet `app.main:app`; weder deren
Image-Identität noch eine Synchronisierung oder ein Deployment werden hier bestätigt.
PR #123 prüfte die Registrierung der Health-Routen, nicht die Identität eines
entfernten Containers.

Nach Merge dieser Korrektur darf ein autorisierter Betreiber auf dem Server
zuerst nur Zustand und laufenden Befehl prüfen. Zugangsdaten, vollständige
Umgebungen oder Secret-Inhalte nicht ausgeben:

```sh
cd /opt/nold/backend
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Command}}'
docker compose -f compose.production.yaml ps --all
container=$(docker compose -f compose.production.yaml ps -q api)
test -n "$container"
docker inspect --format '{{.Config.Image}} {{.Image}} {{json .Config.Cmd}}' "$container"
```

Die folgenden Befehle setzen voraus, dass `/opt/nold/backend` der saubere
Checkout auf `main` ist, die Korrektur bereits gemergt wurde, die nötigen
Security-/Betriebsfreigaben vorliegen und die bestätigten Host-/Secret-Variablen
sowie Dateien bereits geschützt provisioniert sind. Andernfalls hier stoppen;
keine Werte erfinden oder Secrets neu erzeugen. Der autorisierte Betreiber
aktualisiert die Revision fast-forward-only und verwendet das **definierte
Compose-Projekt**. Nicht `docker compose down`, `down --volumes` oder ein
alternatives Projekt/Service-Namen verwenden:

```sh
cd /opt/nold/backend
test "$(git branch --show-current)" = main
test -z "$(git status --porcelain)"
git pull --ff-only origin main
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml build api
docker compose -f compose.production.yaml up --no-build -d
docker compose -f compose.production.yaml ps
```

Die tatsächlichen Compose-Services heißen `preflight`, `postgres`, `migrate`,
`api` und `proxy`. `api` baut das Backend-Image; `up --no-build -d` startet die notwendigen
Abhängigkeiten und ersetzt Container bei geändertem Image, ohne das
`postgres-data`-Volume zu löschen. Bei fehlgeschlagenem Preflight oder
Migrationsjob nicht fortfahren oder Datenbank-/Rollenänderungen manuell
erzwingen. Vorherige Images und das Datenbankvolume für einen autorisierten
Rollback erhalten.

Anschließend die Routen direkt im API-Container gegen dessen Loopback-Port
prüfen; das veröffentlicht weder PostgreSQL noch Port 8000:

```sh
docker compose -f compose.production.yaml exec -T api python -c '
import json
from urllib.request import urlopen
for path, expected in (("/health/live", {"status": "live"}),
                       ("/health/ready", {"status": "ready"})):
    with urlopen("http://127.0.0.1:8000" + path, timeout=6) as response:
        body = json.load(response)
        print(f"{path}: HTTP {response.status} {body}")
        if response.status != 200 or body != expected:
            raise SystemExit(1)
'
```

Danach `/health/live` und `/health/ready` zusätzlich mit dem unten beschriebenen
zertifikatsprüfenden HTTPS-Aufruf vom freigegebenen Clientnetz prüfen. Ein
externes 404 nach erfolgreichen direkten API-Checks weist auf Proxy-/DNS-
Zuordnung oder einen anderen öffentlichen Dienst hin; nicht durch Freigabe von
Port 8000 oder PostgreSQL umgehen. Kein Deployment wurde mit dieser Anleitung
ausgeführt oder als erfolgreich bestätigt.

Vorher müssen Betreiber `BACKEND_HOSTNAME` auf ihren tatsächlich bestätigten
öffentlichen DNS-Namen und `BACKEND_HOSTNAME_CONFIRMED` ausdrücklich auf
denselben Namen setzen. Es gibt keinen Default; IPs, lokale und reservierte
Beispielnamen werden abgelehnt. Außerdem sind ausschließlich lokale Pfade zu
separat provisionierten Secret-Dateien anzugeben:
`POSTGRES_PASSWORD_SECRET_FILE`, `HEALTH_PASSWORD_SECRET_FILE`,
`TLS_CERTIFICATE_FILE` (echte Zertifikatskette mit exaktem Host-SAN) und
`TLS_PRIVATE_KEY_FILE`. Diese Dateien niemals einchecken; für Container-UID
10001 lesbar bereitstellen und außerhalb von Git angemessen schützen.
Passwörter müssen verschieden, nicht leer und einzeilig sein. Compose-Secrets
auf einem einzelnen Docker-Host sind Dateimounts, kein verschlüsselter Vault.
Bei dateibasierten Compose-Secrets ist auf `uid`/`gid`/`mode`-Remapping kein
Verlass: die tatsächlichen Host-Dateirechte müssen bereits UID/GID `10001`
im nicht privilegierten API-/Migrations-/Preflight-/Proxy-Container Lesezugriff
geben. Auf einer normalen rootful Docker-Engine eignen sich beispielsweise
root-eigene Dateien mit Gruppe `10001` und Modus `0640`, ausschließlich in
einem geschützten Betreiberverzeichnis außerhalb von Git. Das
PostgreSQL-Image liest sein Secret beim privilegierten Einstieg vor dem
Benutzerwechsel. Bei rootless Docker oder User-Namespace-Remapping gelten
andere Host-UIDs/GIDs: die tatsächlich gemappte ID oder eine eng begrenzte ACL
verwenden und den Lesezugriff vor Deployment im jeweiligen Container prüfen.
Dateien nicht als Abhilfe weltlesbar machen; private Schlüssel niemals in
Diagnoselog-Ausgaben ausgeben. Die Container laufen mit numerischer UID/GID
`10001`, die Docker-Engine muss deshalb nicht im Rootless-Modus laufen.

Der vorgeschaltete Preflight prüft Hostbestätigung, Zertifikatszeitraum,
exakten SAN und passende Schlüsseldatei; er ersetzt **keine** öffentliche
Vertrauenskette-/DNS-/Erreichbarkeitsprüfung. Danach laufen der einmalige
Migrationsjob, die ASGI-API und der HTTPS-Proxy abhängig von erfolgreichen
Vorprüfungen. PostgreSQL und API veröffentlichen keinen Host-Port; nur HTTPS
443 wird angeboten. `127.0.0.1:8000` ist daher kein Host-Ziel des
Produktions-Compose; auf dem Server ist die API intern über den Proxy erreichbar,
extern ausschließlich über den bestätigten HTTPS-Host. Ein 404 von einem
Hostdienst auf Port 8000 belegt keinen Fehler der API-Routen und darf nicht durch
eine öffentliche Portfreigabe umgangen werden. Der Health-Datenbanknutzer hat ausschließlich Leserechte
am Migrations-Ledger, keine Produkt-Datenrechte. Der Proxy verwendet TLS
1.2/1.3, HSTS und ausschließlich Health-GET-Routen. Zertifikatserneuerung,
Secret-Rotation (bei bestehendem Volume einschließlich PostgreSQL-Rollen),
Backups/Wiederherstellung, Host-Härtung und Monitoring bleiben Betreiberaufgaben.
Die Migration verweigert bereits vorhandene Health-Rollen mit unerwarteten
Grants (auch Spalten-/Grant-Option-Rechten), Objektbesitz, Rollenmitgliedschaften
oder privilegierten Rollenattributen, statt deren Rechte stillschweigend zu
übernehmen. Betreiber müssen solche Abweichungen gesondert bereinigen.
Der Passwortvergleich nutzt das tatsächlich von libpq aufgelöste
Migrationspasswort, auch bei `DATABASE_URL` oder `PGPASSWORD`, nicht nur die
Secret-Datei.
Image-Digests und sämtliche Python-Versionen sind festgeschrieben und müssen
kontrolliert auf Sicherheitsupdates geprüft werden.

**Extern weiterhin BLOCKED:** bestätigter Produktionshostname, Serverzugang,
DNS-Einrichtung, vertrauenswürdige TLS-Ausstellung und externe TLS-/Firewall-
Nachweise sowie SecurityChain-P0-/Produkt-/Betriebsfreigaben. Es wurde weder ein
Produktionsziel angenommen noch ein produktives Deployment nachgewiesen.

### Betreiberprüfung über echtes HTTPS (noch nicht durchgeführt)

Erst nach bestätigter Hostzuordnung, DNS, Firewall und Installation einer
öffentlich vertrauenswürdigen Zertifikatskette vom vorgesehenen Clientnetz aus
prüfen. Der folgende Aufruf verwendet ausschließlich den explizit gesetzten
Betreiberhost, prüft Zertifikatskette und Hostnamen mit dem System-Truststore,
folgt keinen Weiterleitungen und verlangt exakt HTTP 200:

```sh
status=$(curl --fail --silent --show-error --no-location \
  --proto '=https' --max-redirs 0 --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out '%{http_code}' \
  "https://${BACKEND_HOSTNAME:?Set the confirmed real production hostname}/health/ready") \
  && test "$status" = 200
```

Analog `/health/live` prüfen. Niemals `-k`/`--insecure`, einen erfundenen Host
oder eine HTTP-Ausweichadresse verwenden. Ein 200-Ergebnis belegt ausschließlich
die geprüfte Health-Verbindung zum Prüfzeitpunkt, keine Authentifizierung,
Geräteintegration, KI- oder P0-Freigabe. Prüfzeitpunkt, Netz, Hostname und
nicht-sensitive Resultate separat protokollieren. Ohne realen Host und
Serverzugang liegen weiterhin **keine entfernten HTTPS-/DNS-Nachweise** vor.

### Datenbanksicherung und kontrollierte Rücknahme

Es wurden keine produktiven Daten und kein Backup dieses Servers gelesen oder
gesichert. Für einen späteren Betreiberlauf muss der Sicherungspfad in einem
geschützten Verzeichnis **außerhalb von Git** liegen; ein genehmigter
Aufbewahrungszeitraum und -umfang ist vor Aktivierung noch durch den Betreiber
und Datenschutzverantwortliche festzulegen. Diese Runbook-Anleitung erfindet
keine Retention-Policy.

Der folgende Bash-Ablauf verlangt `age` und einen freigegebenen öffentlichen
age-Empfänger. Er verschlüsselt den `pg_dump`-Stream direkt, setzt enge
Dateirechte und erzeugt das endgültige Backup erst nach erfolgreichem Dump und
Verschlüsselung. Zugangsdaten oder private Schlüssel dürfen nicht als Argument
oder Log ausgegeben werden:

```bash
set -o pipefail
umask 077
: "${BACKUP_FILE:?Set a new .age path in a protected directory outside Git}"
: "${BACKUP_RECIPIENT:?Set the approved age public recipient}"
command -v age >/dev/null
test ! -e "$BACKUP_FILE"
temporary=$(mktemp "${BACKUP_FILE}.tmp.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
docker compose -f backend/compose.production.yaml exec -T postgres \
  pg_dump -U backend_migrator -d niknolig_health --format=custom \
  | age --encrypt --recipient "$BACKUP_RECIPIENT" > "$temporary"
chmod 600 "$temporary"
ln "$temporary" "$BACKUP_FILE"
rm -f -- "$temporary"
trap - EXIT
```

Bei Fehlern ist die temporäre Datei keine Sicherung und wird entfernt. Nie
überschreiben oder unverschlüsselte Zwischenstände hinterlassen. Protokolliere
nur Backup-ID, Zeitpunkt, Hash der Ciphertext-Datei, PostgreSQL-Version und
verwendete Image-Digests. Rollen-/Berechtigungsdefinitionen sind separat zu
sichern; Passwort-Hashes und Secret-Dateien gehören nicht in dieses Backup, Git
oder Logs. Keine laufenden PostgreSQL-Datendateien ungeprüft kopieren; ein
Volume-Snapshot benötigt ein eigenes konsistentes Verfahren.

Ein Restore-Test ist ausschließlich in einer neuen, isolierten, wegwerfbaren
Testinstanz und mit dem genehmigten age-Identitätsschlüssel zulässig. Erst
Authentizität und Lesbarkeit des Archivs prüfen:

```bash
age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_FILE" \
  | pg_restore --list > /dev/null
```

Danach darf in diesem Runbook nur eine lokale, isolierte Testdatenbank mit dem
Suffix `_restore_test` als Ziel verwendet werden. `RESTORE_DATABASE_URL` enthält
keine Passwörter; Zugangsdaten kommen ausschließlich aus einem geschützten
`PGPASSFILE`. Prüfe das Ziel unabhängig, bevor du den Restore startest:

```bash
: "${RESTORE_DATABASE_URL:?Set a non-secret local test-database URI}"
: "${PGPASSFILE:?Set a protected PostgreSQL passfile}"
test -f "$PGPASSFILE"
[[ "$RESTORE_DATABASE_URL" =~ ^postgres(ql)?://([^:/@]+@)?(127\.0\.0\.1|localhost)(:[0-9]+)?/[^/?#]+_restore_test$ ]]
age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_FILE" \
  | pg_restore --exit-on-error --no-owner --no-privileges \
      --dbname="$RESTORE_DATABASE_URL"
```

Es wird bewusst kein `--clean` verwendet. Der Betreiber muss vorab bestätigen,
dass die Testdatenbank neu und leer sowie von Produktion isoliert ist; niemals
Produktionsdaten überschreiben oder löschen. Prüfe danach Tabellen,
Migration-Prüfsummen, Readiness sowie Anwendungsinvarianten und dokumentiere
Ergebnis, Image-/PostgreSQL-Version, Zeitpunkt und redigierte Fehler. Keine
produktive Wiederherstellung wurde hier ausgeführt; ohne freigegebene
Testinstanz liegt kein Restore-Testnachweis vor.

Rollback zuerst durch einen autorisierten Betreiber und nach freigegebenem
Incident-Ablauf über Sperren des öffentlichen Zugangs und Stoppen von
`proxy`/`api` einleiten. Bei unverändert kompatiblem Schema das zuvor verifizierte,
immutable API-Image verwenden und Readiness/HTTPS erneut prüfen. Der
Migrationsrunner führt bewusst **keine Down-Migration** aus. Bei Datenbank- oder
Schema-Rücknahme ausschließlich den getesteten Restore-Ablauf gegen eine neue
isolierte Datenbank verwenden; Migration-Prüfsummen müssen zum zugehörigen
freigegebenen Image passen. Das ursprüngliche Volume bis zur bestätigten
Wiederherstellung erhalten; niemals `docker compose down --volumes` als
Rollback verwenden. `001_initial_contract.sql` bleibt ohne separate Freigabe
gesperrt. Wiederanlauf, Datenverlustfenster und Freigabe liegen beim Betreiber.

### Monitoring- und Incident-Verfahren (nicht aktiv überwacht)

Compose prüft PostgreSQL und der API-Container fragt `/health/ready` ab; die
API protokolliert Readiness-Fehler als JSON-Ereignis ohne Fehlerdetails,
Credentials, Requestdaten oder interne Adressen. `/health/live` prüft nur den
Prozess. Diese lokalen Healthchecks sind keine externe Überwachung: Es sind
keine Alarmierung, Bereitschaft, Incident-Kontakt oder automatische
Wiederherstellung nachgewiesen.

Bei einer Störung soll ein autorisierter Betreiber:

1. Zeitpunkt, betroffene Komponente und beobachteten Health-Status festhalten;
   `live=200` bei `ready=503` weist auf fehlende Datenbank-/Migrationsbereitschaft
   hin, nicht auf eine erfolgreiche Wiederherstellung.
2. Containerzustand, PostgreSQL-Health, Konfigurationsversion und redigierte
   Containerlogs prüfen. Keine Secret-Dateien, vollständigen Umgebungsvariablen,
   Tokens oder ungeprüften Rohlogs weitergeben.
3. Auswirkungen und Datenintegrität bewerten, den zuständigen Betriebs- und
   Security-Kontakt informieren und Änderungen/Deployment stoppen, bis die
   Ursache geklärt ist.
4. Nur nach Incident-Freigabe den kontrollierten Wiederanlauf ausführen:
   Datenbankverfügbarkeit und Migrationen verifizieren, API-Readiness prüfen,
   anschließend den öffentlichen HTTPS-Endpunkt ohne Redirects und ohne
   Zertifikatsprüfung zu umgehen testen. Keine produktive Datenbank per Restore
   überschreiben.
5. Ereignis, Maßnahmen, Ergebnis und offene Folgearbeiten datensparsam
   dokumentieren. Keine Verfügbarkeits- oder Alarmierungszusage aus einem
   erfolgreichen CI-Test ableiten.

Das Verfahren ist dokumentiert, aber mangels benanntem Betreiber,
Incident-Kontakt und Testumgebung nicht praktisch geübt. Externe
Alarmierung/Monitoring, RTO/RPO, Datenverlustfenster und Aufbewahrungsdauer
bleiben unbestätigt.

### Verifizierungsnachweise (21.10.2026)

- Lokal nach Installation der bereits festgeschriebenen `backend/requirements.txt`:
  `python3 -m unittest discover -s backend/tests` — **111 Tests bestanden,
  15 übersprungen**. Die übersprungenen PostgreSQL-Integrationstests verlangen
  eine ausdrücklich wegwerfbare `BACKEND_TEST_DATABASE_URL`; sie liefen lokal
  nicht.
- `python3 -m unittest discover -s tools/tests` — **49 Tests bestanden**.
- `docker compose -f backend/compose.production.yaml config --quiet` —
  **erfolgreich** mit ausschließlich synthetischen `api.invalid`- und
  `/tmp`-Werten zur Syntaxprüfung; kein DNS-, TLS-, Server- oder Deploymenttest.
- PR #121 wurde am 21.10.2026 gemergt
  ([PR #121](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/121)).
  Die PR-Backend- und Android-Checks waren erfolgreich
  ([Backend](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39607714188),
  [Android](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39607714178));
  die Post-Merge-Läufe auf `main` waren ebenfalls erfolgreich
  ([Backend](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39608447871),
  [Android](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39608447921)).
- Die CI-Läufe für die zusätzlichen Folgeänderungen auf
  `copilot/boss-auftrag-pr-121` stehen auf `action_required` und enthalten keine
  Jobs; sie haben diese Folgeänderungen nicht ausgeführt
  ([Backend](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39609360164),
  [Android](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/39609360102)).
  Lokale Tests ersetzen diesen noch ausstehenden CI-Lauf nicht.

Die Testresultate belegen weder eine öffentliche HTTPS-Adresse noch einen
Serverbetrieb, SecurityChain-P0-Freigabe, produktive Backup-Ausführung oder
Restore-/Incident-Übung.
