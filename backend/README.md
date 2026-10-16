# Gemeinsame Backend-Grundlage

**Status: Health-only-Laufzeit und Verträge, lokal isoliert, nicht produktionsfreigegeben.**

Dieses Verzeichnis definiert gemeinsame, versionierte Verträge für die getrennten
Apps `com.niknolig.app` und `com.niknolig.defense`. `app.py` stellt ausschließlich
nicht-sensitive Health-Routen bereit; Produkt-, Authentifizierungs-, Geräte- und
Pairing-APIs, App-Clients, produktive Endpunkte und eine Cloudflare-/Deployment-
Konfiguration existieren nicht. NIKNOLIG und NIKNOLIG Defense bleiben getrennte
Sicherheits- und Release-Domänen; gemeinsame Verträge verleihen keine Rechte.
Elektro-Engel ist eine NIKNOLIG-Systemfunktion, keine dritte App.

## Artefakte

- [`openapi.yaml`](openapi.yaml): OpenAPI 3.1-Vertrag für nicht-sensitive
  Liveness-/Readiness-Prüfungen und einheitliche Fehlerantworten. Es sind bewusst
  noch keine operativen Geräte-, Profil- oder Pairing-Endpunkte freigegeben.
- [`app.py`](app.py): lokale Health-only-HTTP-Laufzeit ohne externe
  Python-Abhängigkeiten. Sie ist kein produktionsgeeigneter API-Server.
- [`migrations/001_initial_contract.sql`](migrations/001_initial_contract.sql):
  vorgeschlagenes relationales Modell für App-Bereiche, Installationen,
  Geräteidentitätsstatus und spätere Zwei-App-Link-Beziehungen. Das Anwenden der
  Migration ist bis zur Architektur-/Security-Freigabe gesperrt.
- [`compose.yaml`](compose.yaml): ausschließlich lokale PostgreSQL-Entwicklung,
  an Loopback gebunden und ohne API-Service oder öffentlich erreichbaren Port.
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
6. **Healthchecks:** `/health/live` meldet nur Prozessverfügbarkeit (200).
   `/health/ready` liefert bis zur Implementierung freigegebener Betriebsprüfungen
   immer 503 mit `SERVICE_UNAVAILABLE` im `ApiError`-Format (fail closed).
   Weder Datenbankverbindung, Migrationsstand noch Produktabhängigkeiten werden
   geprüft; ein laufender Health-Prozess ist kein Betriebsbereitschaftsnachweis.
   Antworten legen
   keine Umgebungsvariablen, internen Hosts, Stacktraces oder Datenbankdetails
   offen.

## Lokale Datenbankumgebung

Docker Compose veröffentlicht PostgreSQL ausschließlich auf
`127.0.0.1:54329` (konfigurierbar), nutzt ein erforderliches lokales Passwort,
ein isoliertes internes Compose-Netzwerk und ein lokales benanntes Volume. Es
gibt keinen API-Container, keine Internetfreigabe und keine produktive
Konfiguration. `.env` wird lokal aus `.env.example` erstellt und nicht
eingecheckt. Das Compose-Setup ist nicht für Deployment oder sensible Daten
bestimmt.

`app.py` verwendet keine PostgreSQL-Variablen und öffnet keine
Datenbankverbindung. Der Compose-Healthcheck `pg_isready` prüft nur die
Verbindungsannahme von PostgreSQL, nicht das Anwendungsschema, API-Rechte oder
P0-Konformität. Compose bindet keine Migration ein und führt sie nicht automatisch
aus. Ein gesunder PostgreSQL-Container ändert die API-Readiness daher nicht.

## Lokaler Health-Server

Mit Python 3 starten:

```sh
python3 backend/app.py
```

Die Standardbindung ist `127.0.0.1:8000`. `BACKEND_HOST` und `BACKEND_PORT`
können als Umgebungsvariablen gesetzt werden. Die Anwendung lädt `.env` nicht
automatisch. `/health/live` liefert 200 mit `{"status":"live"}`;
`/health/ready` liefert immer 503 mit einem generischen Fehlercode,
einer nicht-sensitiven Nachricht und einer neuen Korrelations-ID.
Andere GET-Pfade geben eine generische 404-Antwort zurück.
Es gibt keine Anmeldung, Datenbankverbindung, Gerätefunktion oder Produkt-API.
Die Standardbibliotheks-HTTP-Laufzeit ist nur für lokale Entwicklung und
Vertragstests gedacht: nicht öffentlich exponieren oder als produktiven
Internetserver verwenden. Serverplattform, TLS, Authentifizierung, Betrieb und
Deployment bleiben separat zu konfigurieren und freizugeben.

## SecurityChain-P0 und Freigabe

Der folgende SecurityChain-P0-Entwurf enthält prüfbare Muss-/Abbruchkriterien,
ist aber nicht als normative Fassung freigegeben. Keine P0-Konformität wird behauptet.
**Produktive Geräteintegration und die operative API bleiben BLOCKED**, bis
mindestens die verbindlichen P0-Kriterien, Bedrohungsmodell, Daten-/Aktionsumfang,
Rollen, Identitäts-/Authentifizierungsverfahren, Transport, Widerruf,
Aufbewahrung und Abnahmekriterien schriftlich von den Verantwortlichen
freigegeben und überprüfbar getestet sind. Die SQL-Modelle und zukünftigen
Routen in dieser Grundlage sind Vorschläge, keine Freigabe dieser offenen
Entscheidungen. Bei fehlender Prüfung gilt fail closed.

### Verbleibende Abschlussblocker

- **P0:** Der folgende Kriterien-/Bedrohungsmodellentwurf benötigt schriftliche
  Produkt-/Security-Freigaben und die noch fehlenden Abnahmenachweise.
- **Authentifizierung:** Identitätsanbieter, Login, Tokenprüfung/-widerruf,
  Schlüsselrotation und app-bereichsgetrennte Autorisierung sind nicht implementiert.
- **Deployment/Betrieb:** Produktionsgeeignete Laufzeit, Hosting, TLS,
  Secret-Verwaltung, Monitoring, Rollback und geprüfte Backup-/Restoreverfahren
  sind nicht eingerichtet. Es gibt keine Datenbankanbindung oder freigegebene
  Migrationsausführung; echte Readiness-Prüfungen bleiben offen.
- **Datenschutz:** Freigegebene Zwecke und Rechtsgrundlagen, Datenumfang,
  Aufbewahrungs-/Löschregeln sowie Zustimmungs- und Widerrufsdurchsetzung fehlen.

Diese Grundlage stellt nur Health-Signale und Anforderungsentwürfe bereit.
Sie aktiviert keine Produkt-API, Datenbankintegration oder Migration und
ersetzt keine Sicherheits-, Datenschutz- oder Betriebsfreigabe.

### SecurityChain-P0-Spezifikation – Entwurf SC-P0 v0.1

**Stand: 2026-10-16; Basis: `b7f0260`; Status: DRAFT / NICHT FREIGEGEBEN.**
Die folgenden „MUSS“-Regeln sind vorgeschlagene Abnahmebedingungen für zukünftige
Implementierung, keine Aussage über vorhandene Durchsetzung. Änderungen an diesem
Entwurf benötigen versionierten Review. Konflikte oder fehlende Entscheidungen
führen zum Stopp, nicht zur Abschwächung bestehender Regeln.

#### Bedrohungsmodell und Vertrauensgrenzen

Schutzgüter: Identitäten, app-spezifische Rollen, Geräte-/öffentliche
Schlüsselbindungen, Tokens/Sitzungen, Zustimmungen, private Nutzdaten und
Integrität der Auditnachweise. Private Schlüssel gehören nicht ins Backend.
Angreifer können Requests, Ressourcen-IDs, Header und App-Angaben frei wählen,
Tokens entwenden, alte Nachrichten wiederholen oder ein Gerät kompromittieren.
Auch legitim angemeldete Nutzer, Administratoren und Betreiber gelten nicht
automatisch als berechtigt, fremde Inhalte oder den anderen App-Bereich zu lesen.

Vertrauensgrenzen sind Gerät → TLS/API, API → Identitäts-/Widerrufsdienst,
API → Datenhaltung sowie Betrieb → Schlüssel-/Auditverwaltung. Geteiltes Hosting,
ein gemeinsamer Anbieter, gleicher Kontoinhaber oder ein Geräte-Link überwinden
keine dieser Grenzen. Eine kompromittierte Gerätesandbox kann lokale Inhalte
offenlegen; sichere lokale Speicherung, Verlustmeldung und Widerruf begrenzen
dieses Restrisiko, garantieren aber keinen Schutz eines vollständig kontrollierten
Endgeräts. Physische Gerätetests und das
[Geräte-Link-Sicherheitsdesign](../docs/device-link-security-design.md) bleiben nötig.

| Bedrohung | Erforderliche Gegenmaßnahme / P0-Kriterium |
| --- | --- |
| Gefälschte Identität, manipulierter/entwendeter Token | Vertrauenswürdige Tokenprüfung, kurze Laufzeit, Widerruf, Gerätebesitznachweis (P0-02/03/05) |
| NIKNOLIG-Token gegen Defense, gefälschter App-/Rollenheader | Serverseitige Bereichs-/Ressourcenprüfung; keinerlei Headervertrauen (P0-01/04) |
| Zugriff auf fremde IDs, Listen oder Adminfunktionen | Default deny, Eigentümer-/Aktionsprüfung auch bei Listen und Stapeloperationen (P0-04) |
| Replay, gestohlenes Gerät, unbestätigter Schlüsselwechsel | Einmalige Challenges, Frische, Bindung, Widerruf und erneute Zustimmung (P0-03/05) |
| MITM, manipulierte Schlüsselquelle oder Recovery | TLS-Prüfung, fest konfigurierte Vertrauensanker, abgesicherte Rotation/Recovery (P0-02/06/07) |
| Datenabfluss durch Logs, Betreiber oder Backups | Datenminimierung, getrennte Zugriffe, Löschung und überprüfter Restore (P0-08) |
| Überlastung oder Ausfall von Auth-/Policy-Diensten | Begrenzte Größen/Zeiten/Raten, keine Fail-open-Caches, ehrliche Readiness (P0-03/07) |

#### Muss- und prüfbare Abnahmekriterien

Für jede Zeile sind positive Kontrollfälle **und** die genannten Negativfälle
gegen die spätere echte Implementierung nachzuweisen. Derzeit sind diese
Produkt-/Auth-Abnahmen **OFFEN**, nicht durch Health-Tests bestanden.

| ID | MUSS-Anforderung | Abnahmekriterium / erwartete Ablehnung |
| --- | --- | --- |
| P0-01 | Tokenkontext und jede Ressource besitzen genau einen geprüften `app_area`; pro Bereich getrennte Client-/Audience-Konfiguration und Rollenzuweisungen. | In beiden Richtungen Token-/Bereichstausch, gleiche Benutzer-ID, Rollenheader und vorhandener Link gewähren keine Rechte; bei gültiger Identität Bereichsabweichung → 403 `APP_AREA_MISMATCH`, keine Daten/Seiteneffekte. |
| P0-02 | Fehlende oder ungültige Zugangsnachweise dürfen nie geschützte Operationen erreichen. Tokenherkunft, Aktivstatus, Subjekt, Aussteller, exakte Zielgruppe, Ablauf, Gültigkeitsbeginn und App-Bereich werden serverseitig geprüft. | Fehlend → 401 `AUTHENTICATION_REQUIRED`; leer, fehlerhaft, abgelaufen, zukünftige Gültigkeit, falscher Aussteller/Audience → 401 `AUTHENTICATION_INVALID`. Kein Zugriff und keine interne Fehleroffenlegung; Bearer-Challenge bei 401. |
| P0-03 | Token-, Sitzungs-, Rollen- und Gerätewiderruf gelten spätestens vor der nächsten geschützten Operation nach bestätigtem Widerruf. Unprüfbarer Status erlaubt keinen Zugriff. | Widerrufenes Token → 401; entzogene Aktion/Rolle → 403; Statusdienst ausgefallen/Timeout → 503 `SERVICE_UNAVAILABLE`, keine Aktion. Kein veralteter positiver Cache darf Widerruf umgehen. |
| P0-04 | Jede Aktion prüft Akteur, Bereich, Ressource/Eigentümer, konkrete serverseitige Allowlist und erforderliche Zustimmung. Unbekannte Rollen/Aktionen sind verboten. | Fremde Ressourcen-ID, Listen-/Stapelzugriff, Support-Schreibzugriff und Selbsteskalation → 403 `AUTHORIZATION_DENIED` ohne Daten/Mutation. Fehlende Objekte und verbotene Zugriffe dürfen keine fremden Inhalte offenlegen. |
| P0-05 | Geräteoperationen benötigen registrierte installationsgebundene öffentliche Schlüssel und frische Challenge-Besitzprüfung mit einem etablierten Protokoll. | Gerätename/Installations-ID allein, fremder Schlüssel → 403 `DEVICE_IDENTITY_UNVERIFIED`; verbrauchte Challenge → 403 `REPLAY_DETECTED`; abgelaufenes Pairing → 403 `PAIRING_EXPIRED`. Keine Aktion, Sitzung/Vertrauen im betroffenen Kontext beenden. |
| P0-06 | Rotation und Recovery benötigen nachvollziehbare Autorisierung, atomaren Vertrauenswechsel und Entzug kompromittierter Schlüssel. Keine Eigenbau-Kryptografie. | Reguläre Rotation akzeptiert nur freigegebene Schlüssel im definierten Überlappungsfenster; danach alter Schlüssel abgelehnt. Bei Kompromittierung sofortiger Entzug auch abhängiger Sitzungen; Recovery ohne unabhängige Bestätigung scheitert. |
| P0-07 | TLS-Verifikation, sichere Betriebsplattform, begrenzte Requestgrößen/Timeouts/Raten und geprüfte Abhängigkeiten sind vor Exposition verpflichtend. | Falsches/abgelaufenes Zertifikat wird vom Client abgelehnt; Größenüberschreitung → 413, Ratenlimit → 429, keine Mutation; Abhängigkeitsausfall macht Readiness 503. Gegenwärtig bleibt Readiness immer 503. |
| P0-08 | Nur freigegebene Zwecke/Daten; keine Tokens, privaten Schlüssel, Auth-Header oder Nutzpayloads im Audit. Lösch-/Aufbewahrungsregeln gelten auch für Backups. | Testdatenprüfung von Logs/Artefakten zeigt keine verbotenen Inhalte; nach freigegebener Frist ist Löschung nachweisbar. Restore darf widerrufene Rechte nicht reaktivieren. |
| P0-09 | Rollenvergabe, Recovery, Schlüssel-/Policyänderungen brauchen frische starke Authentifizierung, dokumentierte unabhängige Zweitfreigabe und minimiertes Audit. | Founder-Selbstzuweisung, fehlende MFA/Zweitfreigabe oder Replay einer Freigabe → keine Änderung; erfolgreicher Kontrollfall und Entzug sind nachvollziehbar. |

#### Authentifizierung und Tokenlebenszyklus – nur Anforderungen

- **Verfahren:** Für mobile Anmeldung ist ein etablierter Standardfluss mit
  externem Systembrowser und PKCE als zu prüfender Vorschlag vorgesehen, keine
  selbst gebaute Passwort-/Tokenplattform und kein eingebettetes Client-Secret.
  Anbieter, Fluss und MFA-/Recovery-Verfahren benötigen Entscheidung F-02.
- **Tokenprüfung:** Das bestehende `bearerFormat: opaque` ist ein reservierter
  Vertrag, keine Formatentscheidung. Opaque Tokens benötigen authentifizierte
  Introspektion bei einer fest konfigurierten Quelle. Falls signierte Tokens
  genehmigt werden, sind Signatur, feste Algorithmus-Allowlist und vertrauenswürdig
  konfigurierte Schlüsselquelle zusätzlich zu P0-02 zu prüfen; niemals `none`,
  aus Tokenfeldern frei gewählte URLs oder ID-Tokens als API-Zugang akzeptieren.
  Unbekannte Schlüssel/Claims oder mehrdeutige Auth-Header werden abgelehnt.
- **Laufzeiten:** Konkrete Maximalwerte für Access-/Refresh-Tokens, Clock-Skew,
  Challenge-Frische und Netztimeouts sind vor Implementierung unter F-02/F-04
  einzutragen und an ihren Grenzen zu testen. Fehlende Werte blockieren die
  Freigabe; sie sind keine unbeschränkte Gültigkeit.
- **Widerruf:** Logout, Geräteverlust, Kontosperre und Rollenentzug invalidieren
  die zugehörigen app-spezifischen Sitzungen und Refresh-Tokenfamilien.
  Refresh-Tokens werden bei Nutzung rotiert; Wiederverwendung sperrt die Familie.
  Offlinevalidierung allein erfüllt P0-03 nicht. Bei konkurrierender Aktion und
  Widerruf muss vor der Mutation nochmals atomar autorisiert werden.
- **Gerätebindung:** Sensible Geräteaktionen binden den geprüften Tokenkontext
  mittels standardisiertem Besitznachweis an Installation, Sitzung, App-Bereich
  und konkrete Aktion. Gestohlener Bearer-Token allein reicht nicht. Private
  Geräteschlüssel bleiben im Plattform-Keystore; Neuinstallation/Restore gilt
  nicht als automatische Wiederherstellung von Vertrauen.
- **Schlüsselrotation:** Ausstellerschlüssel und Geräteschlüssel haben getrennte
  Verantwortliche/Lebenszyklen. Neue Schlüssel nur aus genehmigtem Trust Store
  beziehungsweise nach autorisierter Geräte-Neuregistrierung; Zeitfenster,
  Schlüssel-IDs, Notfallentzug und Recovery werden nach F-04 getestet.

#### Rollen und Ressourcenberechtigungen

Die [Gründerrollenkonzeption](../docs/founder-roles-and-account-requirements.md)
bleibt maßgeblich; folgende Matrix ist ein Vorschlag zur Konkretisierung.
Jede Zuweisung gilt nur für **einen** App-Bereich und freigegebene Ressourcen.

| Rolle / Kontext | Maximal vorzusehende Aktionen | Immer ausgeschlossen ohne gesonderte Freigabe |
| --- | --- | --- |
| Nutzer / eigene Installation | Eigene freigegebene Ressourcen lesen, eigene Zustimmung erteilen/widerrufen und eigene Sitzung beenden | Fremde Ressourcen, Rollenvergabe, Zugriff auf anderen App-Bereich |
| Founder Owner | Produktfreigaben und einzeln geprüfte app-spezifische Rollenvergabe mit Zweitfreigabe | Globaler Superuser, private Nutzinhalte, Umgehen von Zustimmung |
| App Administrator | Freigegebene Konfiguration/Mitgliedschaften innerhalb der eigenen delegierten Rechte | Selbsteskalation, globale Identitäten, fremde App-Rollen |
| Security Operator | Minimierte Sicherheitsmetadaten und autorisierter Sitzungs-/Gerätewiderruf | Nutzinhalte oder Sensorzugriff |
| Support / Auditor | Zeitlich begrenzte redigierte Diagnosemetadaten lesen | Schreiben, Benutzerverwaltung, appübergreifende Suche |
| Elektro-Engel / Geräte-Link | Keine impliziten Rechte; nur explizit genehmigte Aktion mit gültiger Nutzerzustimmung | Rollen-/App-Bereichsüberbrückung, autonome Ausweitung von Rechten |

#### Verantwortlichkeiten und ausdrückliche Gründerentscheidungen

Alle Zuordnungen sind organisatorische Anforderungen, **keine Ernennung**.
Der Gründer muss Verantwortliche benennen; ohne Besetzung bleibt das Gate zu.

| Entscheidung | Vom Gründer ausdrücklich schriftlich freizugeben | Benötigte fachliche Prüfung / Nachweis |
| --- | --- | --- |
| F-01 | P0-Version, Produktumfang, Daten-/Aktionskatalog und Personen für beide getrennten App-Verantwortungen | Security-Verantwortlicher pflegt Bedrohungsmodell; unabhängiger Reviewer bestätigt Kriterienabdeckung |
| F-02 | Identitätsanbieter, Login-/Tokenformat, getrennte Clients/Audiences, MFA, Laufzeiten, Timeouts und Widerrufsarchitektur | Auth-Verantwortlicher liefert P0-01/02/03-Nachweise; keine Bindung an Anbieter vor Freigabe |
| F-03 | Konkrete Rollen-/Ressourcenmatrix, unabhängiger Zweitfreigeber, Einladungs-/Recovery- und Notfallverfahren | Je App eigener Produktverantwortlicher und Security-Review; kein Founder-Bypass |
| F-04 | Gerätebesitzprotokoll, Attestierungs-/Hardware-Anforderungen, Challengewerte, Rotation/Überlappung und Verlustverfahren | Geräte-/Auth-Verantwortliche liefern Replay-, Rotations- und physische Gerätenachweise |
| F-05 | Zwecke/Rechtsgrundlagen, Datensparsamkeit, Audit-Zugriffe, konkrete Aufbewahrungs-/Löschfristen | Datenschutzverantwortlicher prüft Texte, Datenflüsse und Löschung einschließlich Backups |
| F-06 | Hosting-/TLS-/Schlüsselbetrieb, Raten-/Größenlimits, Incident-, Backup-/Restore- und Rollbackverfahren | Betriebsverantwortlicher liefert Staging-, Ausfall-, Restore- und Betriebsnachweise |
| F-07 | Freigabe einer konkret benannten Implementierung für einen ausdrücklich benannten Einsatzbereich | Alle P0-Nachweise, unabhängiges Review, Datenschutz-/Betriebsabnahme und schriftliche Gründerentscheidung |

#### Abbruchregeln und Nachweispaket

Ein fehlendes F-01–F-07, ein fehlgeschlagenes P0-Kriterium, eine unbesetzte
Verantwortlichkeit, nicht prüfbare Identität/Policy/Widerruf oder ungeklärte
Daten-/Schlüsselherkunft blockiert die entsprechende Implementierungs- oder
Betriebsfreigabe. Während einer späteren Sitzung stoppen Integritäts-, Replay-
und Autorisierungsfehler den betroffenen Vorgang ohne Fortsetzung/Retry; ein
Ausfall darf nie auf anonymen Zugriff zurückfallen. Verdacht auf Schlüsselverlust
erfordert den freigegebenen Incident-/Widerrufsprozess. Keine automatische
Herabstufung von MFA, TLS, App-Trennung oder Zustimmung.

Das Abnahmepaket MUSS Spezifikationsversion, geprüften Commit, Umgebung,
benannte Prüfer/Freigeber, jeden Testfall mit erwarteten/tatsächlichen Ergebnissen,
redigierte Nachweise und alle offenen Befunde enthalten. Offene Pflichtfälle
bleiben BLOCKED. Gründerfreigabe ersetzt weder unabhängige Sicherheitsprüfung
noch technische Nachweise; dieser Entwurf erteilt keine davon.

**Aktuell lokal testbar:** Nicht implementierte Produktrouten bleiben bei
fehlendem, leerem, ungültigem oder behauptetem app-spezifischem Auth-Kontext 404;
gefälschte Rollen-/App-Header ändern das nicht. Öffentliche Health-Routen bleiben
ohne Authentifizierung erreichbar, Readiness immer 503. Das prüft nur die
bestehende Routen-/Nichtaktivierungsgrenze, **keine Tokenvalidierung oder
Autorisierung**. Die obigen zukünftigen 401-/403-, Widerrufs-, Ressourcen-,
Rotation- und Geräteprüfungen bleiben mangels Implementierung offen.

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

## Verifikation und nächste Schritte

`python3 -m unittest discover -s backend/tests` prüft Vertragsinvarianten und
die Health-only-Laufzeit. Sofern Docker Compose installiert ist, kann die lokale
Compose-Konfiguration mit diesem lokalen Platzhalter syntaktisch geprüft werden:

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
