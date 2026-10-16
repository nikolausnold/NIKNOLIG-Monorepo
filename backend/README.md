# Gemeinsame Backend-Grundlage

**Status: contract-first, lokal isoliert, nicht produktionsfreigegeben.**

Dieses Verzeichnis definiert gemeinsame, versionierte Verträge für die getrennten
Apps `com.niknolig.app` und `com.niknolig.defense`. Es gibt derzeit keinen
Backend-Server im Repository, keine App-API-Clients, keinen produktiven Endpunkt und keine
Cloudflare-/Deployment-Konfiguration. NIKNOLIG und NIKNOLIG Defense bleiben
getrennte Sicherheits- und Release-Domänen; gemeinsame Verträge verleihen keine
Rechte. Elektro-Engel ist eine NIKNOLIG-Systemfunktion, keine dritte App.

## Artefakte

- [`openapi.yaml`](openapi.yaml): OpenAPI 3.1-Vertrag für nicht-sensitive
  Liveness-/Readiness-Prüfungen und einheitliche Fehlerantworten. Es sind bewusst
  noch keine operativen Geräte-, Profil- oder Pairing-Endpunkte freigegeben.
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
6. **Healthchecks:** `/health/live` meldet nur Prozessverfügbarkeit;
   `/health/ready` darf bei einer späteren Serverimplementierung zusätzlich
   notwendige Abhängigkeiten prüfen. Antworten dürfen keine Umgebungsvariablen,
   interne Hosts, Stacktraces oder Datenbankdetails offenlegen. Aktuell existiert
   kein Server, der diese Routen bedient.

## Lokale Datenbankumgebung

Docker Compose veröffentlicht PostgreSQL ausschließlich auf
`127.0.0.1:54329` (konfigurierbar), nutzt ein erforderliches lokales Passwort,
ein isoliertes internes Compose-Netzwerk und ein lokales benanntes Volume. Es
gibt keinen API-Container, keine Internetfreigabe und keine produktive
Konfiguration. `.env` wird lokal aus `.env.example` erstellt und nicht
eingecheckt. Das Compose-Setup ist nicht für Deployment oder sensible Daten
bestimmt.

## SecurityChain-P0 und Freigabe

Im geprüften Repository liegt keine normative SecurityChain-P0-Fassung mit
prüfbaren Muss-/Abbruchkriterien. Daher wird keine P0-Konformität behauptet.
**Produktive Geräteintegration und die operative API bleiben BLOCKED**, bis
mindestens die verbindlichen P0-Kriterien, Bedrohungsmodell, Daten-/Aktionsumfang,
Rollen, Identitäts-/Authentifizierungsverfahren, Transport, Widerruf,
Aufbewahrung und Abnahmekriterien schriftlich von den Verantwortlichen
freigegeben und überprüfbar getestet sind. Die SQL-Modelle und zukünftigen
Routen in dieser Grundlage sind Vorschläge, keine Freigabe dieser offenen
Entscheidungen. Bei fehlender Prüfung gilt fail closed.

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

`python3 -m unittest discover -s backend/tests` prüft die oben genannten
statischen Invarianten. Sofern Docker Compose installiert ist, kann die lokale
Compose-Konfiguration mit diesem lokalen Platzhalter syntaktisch geprüft werden:

```sh
POSTGRES_PASSWORD=local-only-check docker compose \
  --env-file backend/.env.example -f backend/compose.yaml config --quiet
```

Der Start verlangt bewusst ein gesetztes lokales Passwort und ist nicht Teil der
automatischen Tests. Keine der Prüfungen belegt eine laufende API, sichere Authentifizierung,
P0-Freigabe oder Verbindung zwischen zwei physischen Geräten.

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

## Hetzner-Integrationsprüfung – 16.10.2026

### Prüfgrundlage und belastbare Grenzen

Geprüfter gemergter Stand:
[`e91be056f0ffb8f178aa208bc64ddc11316acc2c`](https://github.com/nikolausnold/NIKNOLIG-Monorepo/commit/e91be056f0ffb8f178aa208bc64ddc11316acc2c)
(Merge PR #20; davor PR #19). Der lokale Ausgangscommit stimmt mit dem zum
Prüfzeitpunkt über GitHub abgefragten neuesten Commit des Default-Branches
überein. PR-Titel sind kein Funktionsnachweis; maßgeblich sind die Dateien.

Bekannter Serverbestand **laut Auftrag, nicht live verifiziert**:
Hetzner Ubuntu, `/opt/nold/backend`, FastAPI „0.1.0“, Docker Compose und
PostgreSQL. Es gab keinen Serverzugriff, keinen Containerstart, keine
Migration und kein Deployment. Die Aussage „kein Backend-Server“ oben bezieht
sich ausschließlich auf dieses Repository, nicht auf den gemeldeten Server.
„0.1.0“ ist hier die OpenAPI-Produktversion, kein Nachweis einer installierten
FastAPI-Paketversion oder identischen Serverimplementierung.

### Vollständiger Backend-Bestand und Gap-Analyse

Repository-Wurzel der Prüfung:
`/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo`.

| Bereich | Im gemergten Repository tatsächlich vorhanden | Serverabgleich / erforderliche Änderung |
| --- | --- | --- |
| HTTP-API | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/openapi.yaml`: ausschließlich `GET /health/live` (200), `GET /health/ready` (200/503), Fehlercodes und reserviertes Bearer-Schema; Host `https://backend.invalid` ist Platzhalter | FastAPI nur gemeldet; Routen, Abhängigkeiten und Quellstand unbekannt. Kein deploybares API-Artefakt vorhanden. Serververtrag vor einem Update abgleichen. |
| Laufzeit / Module | Kein Python-API-Modul, Router, ORM, Dependency-Lockfile, Dockerfile, API-Service oder Migrationsrunner im Repository | Bestehenden Server nicht durch diese Vertragsgrundlage ersetzen. Implementierung, Herkunft, reproduzierbares Build und genehmigtes Image fehlen. |
| SQL-Modell | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/migrations/001_initial_contract.sql`: drei Enums, `device_installations`, `device_links`, Constraints/Indizes, Transaktion; ausdrücklich gesperrter Vorschlag | Server-Schema, Historie und PostgreSQL-Version unbekannt. Kein freigegebener Upgrade-/Downgradepfad; nicht automatisch einspielen. Kein Profil-, Nachrichten-, Consent-, Grant- oder Sync-Persistenzmodell. |
| Consent / Audit | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/contracts/device-consent-v1.schema.json` und `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/contracts/consent-audit-event-v1.schema.json`: geschlossene, zweck-/gerätegebundene Entwürfe | Keine Speicherung, Identitätsprüfung, zeitliche Prüfung, Widerrufsdurchsetzung oder beweiskräftige Audit-Pipeline implementiert. |
| Sensoren | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/contracts/sensor-capability-v1.schema.json` und `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/contracts/sensor-summary-v1.schema.json`: deklarative Fähigkeiten und abgeleitete Zusammenfassungen | Keine Sensor-Runtime, Freigabeprüfung oder Übertragung implementiert. Schemavalidität ist keine Autorisierung. |
| Docker / DB | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/compose.yaml`: nur PostgreSQL `17.6-alpine`, Loopback-Port 54329, internes Netzwerk, benanntes Volume, `pg_isready` | Compose/PostgreSQL serverseitig nur gemeldet. Projektname, Service-/Volumenname, Major-Version, Rechte und Sicherungen fehlen als Nachweis. Lokales Compose niemals auf den Serverbestand anwenden oder dessen Volume übernehmen. |
| Secrets | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/.env.example`: leeres Passwort; lokale `.env` ignoriert; Compose verweigert leeres Passwort | Produktionsablage, Zugriffsschutz, Rotation und Log-Redaktion unbekannt. Beispielwerte sind keine Produktionskonfiguration. |
| Tests | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/backend/tests/test_contracts.py`: statische Invarianten, optionale JSON-Schema-Validierung und App-Isolation | Kein FastAPI-, HTTP-, Auth-, DB-, Migrations-, Last-, Restore- oder Serverintegrationstest. Grüne Vertragstests sind keine Produktionsabnahme. |

### Sicherheitsbewertung und Stop-Gates

Es wurde kein ausnutzbarer Backend-Endpunkt im Repository nachgewiesen; es
existiert keine API-Laufzeit. Daraus folgt **keine** Aussage zur Sicherheit des
laufenden Hetzner-Backends. Offene sicherheitskritische Lücken sind:

1. **P0 / BLOCKER:** Normative SecurityChain-P0-Kriterien, Bedrohungsmodell,
   Verantwortliche und prüfbare Freigaben fehlen. Kein Ersatz durch neue
   Annahmen oder Abschwächung bestehender Prüfungen.
2. **Identität / BLOCKER:** Kein Login, Token-Aussteller, Validierungs- und
   Widerrufsmechanismus, Schlüsselrotation oder Gerätebesitznachweis.
   Fehlende/falsche/abgelaufene/widerrufene Tokens müssen später fail closed
   getestet werden; Health darf keine Produktoperation freischalten.
3. **Autorisierung / BLOCKER:** Kein Laufzeitnachweis für Trennung von
   NIKNOLIG und Defense, Ressourcenbesitz, minimale Aktionen, aktiven Consent,
   dessen Ablauf/Widerruf und Replay-Abwehr. SQL-Fremdschlüssel und
   Linkstatus ersetzen diese Prüfungen nicht. Kein Founder-Bypass.
4. **Datenbank / BLOCKER:** Keine freigegebene Kompatibilitätsmatrix,
   Migrationshistorie, Rollen-/Grant-Strategie oder Restore-Probe.
   Der lokale `POSTGRES_USER` wird durch das offizielle Image als
   Bootstrap-Superuser angelegt und darf nicht als API-Laufzeitrolle dienen.
   Produktion benötigt getrennte minimale Laufzeit-, Migrations- und
   Backup-Rechte, parametrisierte Zugriffe und begrenzte Verbindungen/Timeouts;
   keine App erhält DB-Credentials. PostgreSQL-Major-Version nicht beiläufig
   ändern und nie ein bestehendes Volume mit einem anderen Major starten.
5. **Betrieb / BLOCKER:** TLS-/Proxy-Vertrauensgrenzen, erlaubte Hosts/Origins,
   Debug-/API-Dokumentationszugriff, Rate-/Payloadlimits, Containerbenutzer,
   Dateisystemrechte, Ressourcenlimits, Patchstand/Image-Digests,
   Secret-Ablage und datensparsame Überwachung sind serverseitig unbekannt.
   Kein öffentliches DB-/API-Portmapping ergänzen. Vorhandene
   Loopback-Bindung und internes Entwicklungsnetz bleiben unverändert.
6. **Health / BLOCKER:** Health-Routen sind nur Verträge.
   `pg_isready` meldet Annahmebereitschaft, nicht erfolgreiche Anmeldung,
   richtige Schema-Version oder minimale Rechte. Readiness muss später
   notwendige Abhängigkeiten mit der tatsächlichen Laufzeitrolle und
   Zeitgrenzen prüfen; Liveness bleibt unabhängig von DB-Ausfällen.
   Keine Secrets, Hosts, SQL-Fehler oder Stacktraces in Antworten.
7. **Validierung / BLOCKER für Freigabe:** Formatprüfungen waren im
   optionalen JSON-Schema-Test nicht aktiviert. Die begrenzte Korrektur
   aktiviert den vorhandenen FormatChecker und testet ungültige UUIDs.
   Fehlende optionale RFC-3339-Unterstützung wird nun ausdrücklich als
   übersprungener Test angezeigt. Auch mit Formatprüfung bleiben
   zeitliche Reihenfolge, Consent-Gültigkeit und referenzierte Identitäten
   Laufzeitaufgaben. Für eine Freigabe darf keine erforderliche Prüfung
   übersprungen werden; nötige Validator-Abhängigkeiten sind zuvor
   gesondert zu prüfen und reproduzierbar festzulegen.

### Verifikation dieses Arbeitsstands

- Bestehender [Main-CI-Lauf 38873661692](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38873661692)
  zum Ausgangscommit: erfolgreich, einschließlich Vertragsprüfungen und beider
  Android-Debug-Builds. Jobs und Logs über GitHub geprüft; keine redundanten
  Android-Builds gestartet. Kein Beleg für Hetzner oder Produktionssicherheit.
- Lokale Baseline: 10 Backend-Tests erfolgreich. Nach Testkorrektur:
  12 Tests, 11 erfolgreich, 1 ausdrücklich übersprungen
  (RFC-3339-Formatchecker fehlt). Python 3.12.3, vorhandenes jsonschema 4.10.3.
  Keine neuen Abhängigkeiten installiert.
- Statisch: bestehende Compose-Konfiguration mit dem oben dokumentierten
  nicht-sensitiven Syntaxprüfwert und `config --quiet` erfolgreich geprüft
  (Compose 2.38.2); keine aufgelösten Credentials ausgegeben.
  Vorhandener YAML-Parser bestätigt exakt zwei GET-Health-Routen,
  leere Health-Security und den Platzhalterhost. `git diff --check` erfolgreich.
- SQL nur gelesen; keine Ausführung wegen fehlender Modellfreigabe.
  Kein API-Build möglich: Laufzeit und Dockerfile fehlen.
  Kein behaupteter HTTP-/DB-/P0-/Restore-Erfolg.

### Kontrollierter Deployment-Plan – aktuell NICHT ausführungsfreigegeben

Dieser Ablauf ist eine Vorbereitung für einen später separat genehmigten
Betriebseingriff, keine Aufforderung, jetzt auf Produktion zu arbeiten.
**Mit diesem Repository-Stand endet der Ablauf vor dem Update.**
Unbekannte Service-/Dateinamen oder Ports werden nicht geraten; ohne ausgefülltes
Releaseprotokoll ist ein reproduzierbares Deployment weiterhin BLOCKED.
Es werden weder neue Server noch neue öffentliche Ports oder kostenpflichtige
Dienste benötigt.

1. **Bestand aufnehmen, nur nach ausdrücklicher Serverzugriffsfreigabe:**
   Für `/opt/nold/backend` tatsächlichen Quellcommit bzw. Artefaktherkunft,
   Ubuntu-/Docker-/Compose-/PostgreSQL-Versionen und wirkliche FastAPI-
   Paketversion erfassen. Bestehende Compose-Dateien einschließlich Overrides,
   Projekt-/API-/DB-/Worker-Service-Namen, Image-IDs/Digests, Volumen-/Mount-
   Zuordnung, DB-Name/-Rollen, Schemahistorie, Bind-Adressen, Proxy/TLS und
   bereits genehmigten Health-Zugang feststellen. Nur freigegebene Metadaten
   teilen; kein vollständiges Container-Inspect, Environment, Compose-Rendering,
   Request-Payloads oder Dumps in Logs/Issues übernehmen.
2. **Releaseprotokoll vervollständigen und freigeben:**
   Alte/neue unveränderliche Image-Digests, Quellcommit, exakte Compose-
   Dateireihenfolge und Projektkennung, betroffene Services, Konfigurations-
   Referenzen ohne Secret-Werte, Schema-Vor-/Nachversion, Migrationen mit
   Prüfsummen, Health-Zugang und erwartete Antworten festhalten. P0-, Produkt-,
   Datenschutz- und Security-Freigaben, Verantwortliche, Wartungsfenster,
   RPO/RTO, Health-Zeitlimit und Rollback-Auslöser dokumentieren.
   Ohne API-Artefakt und aufgelöste Gates abbrechen.
3. **Vorabprüfung ohne Produktionsänderung:**
   Freigegebenes Artefakt aus exakt dem Zielcommit bauen/prüfen, Abhängigkeiten
   und Images auf Schwachstellen/Secrets prüfen, Tests mit allen erforderlichen
   Formatcheckern ausführen. Auth-/Bereichs-/Consent-/Replay-Negativtests,
   DB-Rechte, SQL-Upgrades und Rückwärtskompatibilität isoliert testen.
   Falls nötig auf demselben bestehenden Host ausschließlich in genehmigter,
   netzwerkisolierter Testumgebung ohne produktive Volumes/Ports und ohne
   echte Nutzdaten; keine zusätzlichen Server. Kapazität vorher prüfen.
4. **Backup vor jedem Update, separat autorisiert:**
   Alle schreibenden Dienste, Jobs und externen Schreiber im genehmigten
   Wartungsfenster kontrolliert pausieren. Konsistenten PostgreSQL-Dump im
   Custom-Format mit zur Serverversion passenden Werkzeugen und erforderlichen
   Rollen-/Rechte-Metadaten sichern; zugehörige Dateien/Object-Daten
   transaktionskonsistent berücksichtigen. Compose-/Proxy-Konfiguration,
   Schemahistorie, alte Images/Digests und Secret-Referenzen sichern.
   Secret-Material nur falls erforderlich in der genehmigten verschlüsselten
   Backup-Ablage mit restriktiven Rechten, nie im Repository oder in Logs.
   Backup-ID, UTC-Zeit, Prüfsumme, Verschlüsselung, Aufbewahrung und Zugriff
   erfassen. Ein Kopieren eines laufenden PostgreSQL-Volumes genügt nicht.
5. **Restore als zwingendes Gate:**
   Backup auf Integrität prüfen und isoliert in eine separate Testdatenbank
   ohne Kontakt zu Produktionsdiensten wiederherstellen. Bei echten Daten
   sind explizite Datenschutzfreigabe und gleiche Zugriffsschutzmaßnahmen
   erforderlich; andernfalls bleibt diese Probe BLOCKED. Schema, Rollen,
   Constraints und konsistente Datensätze prüfen sowie Wiederherstellungszeit
   gegen RTO messen. Ungeprüftes/unvollständiges Backup bedeutet Abbruch.
6. **Kontrolliertes Update erst nach allen Freigaben:**
   Alten laufenden Stand mit dem Releaseprotokoll erneut vergleichen; bei Drift
   stoppen. Nur genehmigte, vorab rückwärtskompatibel getestete Migrationen
   mit dedizierter Rolle und Versionssperre ausführen. Den derzeitigen
   SQL-Vorschlag nicht als fertige Migration behandeln.
   Nur betroffene API-/Worker-Services mit den protokollierten Compose-Dateien,
   unveränderlichen Ziel-Digests und unveränderten Produktionsvolumes ersetzen.
   Keine pauschale Compose-Neuanlage, kein DB-Major-Upgrade, kein Löschen von
   Volumes oder produktiven Daten; bestehende Netz-/Proxygrenzen erhalten.
7. **Abnahme vor Freigabe von Schreibverkehr:**
   Innerhalb des festgelegten Zeitlimits über den bereits genehmigten lokalen
   bzw. internen Zugang Liveness 200 mit `status=live`, Readiness 200 mit
   `status=ready`, korrekte Schema-Version und DB-Zugriff mit minimaler
   Laufzeitrolle prüfen. Auth-Negativfälle erwarten 401, Bereichs-/
   Berechtigungsverletzungen 403 ohne Zustandsänderung. DB-Ausfall muss in der
   isolierten Vorabprüfung Readiness 503 ergeben, nicht sensible Fehlerdetails.
   TLS, keine zusätzlichen Listener und bereinigte Logs bestätigen.
   Produktive Testschreibvorgänge nur mit gesondert freigegebenen Testkonten
   und Daten. Erst dann Schreiber kontrolliert fortsetzen und beobachten.
8. **Rollback bei Fehlern, kein Datenverlust als Automatismus:**
   Bei Health-Timeout, unerwarteten Schema-/Auth-/TLS-/Portabweichungen oder
   Sicherheitsfehlern Update abbrechen und Schreiber weiter pausieren.
   Bei nachgewiesener Schema-Kompatibilität ausschließlich betroffene Services
   mit alten Digests und alter Konfiguration zurücksetzen; DB/Volumes behalten.
   Kein blindes SQL-Downgrade. Bei inkompatibler Datenänderung oder notwendigen
   Datenverlusten: **BLOCKER**, Betriebs-/Datenverantwortliche hinzuziehen;
   keine Produktionsdaten löschen oder automatisch überschreiben.
   Backup zunächst separat wiederherstellen, Integrität prüfen und einen
   gegebenenfalls nötigen Datenbankwechsel gesondert freigeben lassen.
   Danach dieselben Health-/Auth-/Integritätsprüfungen wie nach dem Update
   durchführen; ohne Erfolg keinen Schreibverkehr freigeben.

**Nächster Schritt:** Zuerst den [geprüften Quellstand](https://github.com/nikolausnold/NIKNOLIG-Monorepo/tree/e91be056f0ffb8f178aa208bc64ddc11316acc2c/backend)
und die [offenen Security-Gates](https://github.com/nikolausnold/NIKNOLIG-Monorepo/blob/e91be056f0ffb8f178aa208bc64ddc11316acc2c/docs/device-link-security-design.md)
mit den Verantwortlichen abgleichen und eine bereinigte Serverinventur
freigeben. Weder Gleichstand mit `/opt/nold/backend` noch Deployment-Bereitschaft
oder ein erfolgtes Deployment werden behauptet.
