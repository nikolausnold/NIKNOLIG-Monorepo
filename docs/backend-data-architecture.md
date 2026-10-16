# Verbindliche Backend- und Datenarchitektur

**Geltung:** verbindliche Zielgrenzen für die Integrationsplanung dieses
Monorepos. **Keine produktive Implementierung oder Freigabe:** Die API,
Authentifizierung, Supabase-Anbindung und RLS sind nicht nachgewiesen; bis zur
schriftlichen SecurityChain-P0- und Produktfreigabe bleibt jede operative
Integration gesperrt. Diese Dokumentation ändert keine Produkt-Repositories,
Supabase-Projekte oder produktiven Daten.

## 1. Verifizierter Ist-Stand und Status der Projektzuordnung

Die IDs in der folgenden Tabelle stammen aus dem Auftrag. Sie sind im
Repository nicht konfiguriert oder unabhängig gegen Supabase verifiziert. Es
wurde kein Supabase-Dashboard und keine Projekt-Datenbank abgefragt. Die
Projekt-IDs sind keine Zugangsdaten.

| Supabase-Projekt | Projekt-ID (Auftragsangabe) | Verbindliche Zielverwendung | Ist-Stand / Schema | Daten- und Betriebsverantwortung |
| --- | --- | --- | --- | --- |
| NIKNOLIG | `mxmwztqzpyxfilfbovvx` | Ausschließlich NIKNOLIG-Produktdaten und -Identitäten; keine Defense-Datensätze. | Schema, RLS, Auth-Konfiguration, Projektstatus und vorhandene Daten **nicht verifiziert / OFFEN**. Im Monorepo keine Supabase-Anbindung. | Fachlicher Data Owner, Projekt-Admin, Security-/Incident-Verantwortliche und Betrieb: **OFFEN**. |
| NIKNOLIG Defense | `keaskglhmnouywvwtmue` | Ausschließlich Defense-Produktdaten und -Identitäten; keine NIKNOLIG-Datensätze. | Schema, RLS, Auth-Konfiguration, Projektstatus und vorhandene Daten **nicht verifiziert / OFFEN**. Im Monorepo keine Supabase-Anbindung. | Fachlicher Data Owner, Projekt-Admin, Security-/Incident-Verantwortliche und Betrieb: **OFFEN**. |
| NIKNOLIG Monorepo | `kkxrnebrampevumolrfq` | Standardmäßig keine Nutzer-, Profil-, Geräte-, Consent- oder Sensordaten. Allenfalls ausdrücklich genehmigte, nicht personenbezogene Backend-/Vertragsmetadaten; bleibt ungenutzt, wenn dafür kein konkreter Bedarf freigegeben ist. Kein gemeinsamer Produktdaten- oder Auth-Tenant. | Schema, RLS, Auth-Konfiguration, Projektstatus und vorhandene Daten **nicht verifiziert / OFFEN**. Keine Verbindung aus Backend oder Workflow nachgewiesen. | Fachlicher Data Owner, Projekt-Admin, Security-/Incident-Verantwortliche und Betrieb: **OFFEN**. |

`backend/migrations/001_initial_contract.sql` ist ein nicht angewendeter
Vorschlag für Installationen und Gerätebeziehungen. Er enthält keine RLS-Policies
und belegt weder Supabase-Schemas noch eine Migration in einem der drei
Projekte. `backend/compose.yaml` beschreibt ausschließlich lokales,
loopback-gebundenes PostgreSQL ohne API-Service; es ist kein Supabase- oder
Produktionssystem. Die OpenAPI-Definition und der lokale HTTP-Server enthalten
nur Health-Routen. Produkt-API, Authentifizierung, Autorisierung und
Projektzugriffe sind nicht implementiert.

Consent-, Audit- und Sensor-Schemas unter `backend/contracts/` sind
**ENTWÜRFE**. Ein valides Schema ist keine erteilte Zustimmung und erzwingt
weder RLS noch Identität, Autorisierung, Sensorzugriff oder Datenminimierung zur
Laufzeit.

## 2. Zielarchitektur und Verantwortungsgrenzen

```text
Android / iOS / Web (je Produkt getrennte Clients)
                 │ HTTPS, produktspezifischer Nutzer-Nachweis
                 ▼
       NOLD-Backend (einzige Produkt-API)
        │                         │
        │ nur Projekt NIKNOLIG    │ nur Projekt Defense
        ▼                         ▼
  NIKNOLIG Supabase          Defense Supabase
  Auth + PostgreSQL          Auth + PostgreSQL

Monorepo Supabase: kein Frontend-Zugriff und keine Produktdaten;
höchstens separat genehmigte, nicht personenbezogene Backend-Metadaten.

Lokales Compose PostgreSQL: isolierte Entwicklung/Tests, keine
Produktionsverbindung und kein stillschweigender Ersatz für Supabase.
```

- **Frontends:** zeigen Daten an und senden Nutzeraktionen an die versionierte
  NOLD-Backend-API. Kein Frontend verbindet sich direkt mit PostgreSQL,
  PostgREST, Supabase Storage oder einem anderen Supabase-Datenendpunkt. Keine
  Service-Rolle, Datenbank-Credentials oder privilegierten Schlüssel in Apps,
  Websites, Artefakten oder Logs.
- **NOLD-Backend:** einzige vertrauenswürdige Produkt-API und
  Autorisierungsgrenze. Es validiert den Nutzer-Nachweis und dessen Aussteller,
  Zielgruppe, Ablauf, Widerruf, Produktbereich und erlaubte Aktion. Es wählt
  das Supabase-Projekt ausschließlich aus vertrauenswürdiger serverseitiger
  Konfiguration und geprüften Claims, niemals aus einer ungeprüften
  Request-`project_id`, `tenant_id` oder Client-URL.
- **Supabase/PostgreSQL:** jedes Produktprojekt ist eine eigene Daten- und
  Identitätsgrenze mit eigenem Schema-/Migrations- und RLS-Prüfbedarf. Der
  Backend-Zugriff ist an den jeweiligen Nutzer-Nachweis gebunden und muss
  RLS durchlaufen. Ein privilegierter Bypass ist für normale Nutzeranfragen
  verboten. Nicht notwendige Tabellen und APIs werden nicht angelegt.
- **Monorepo-Supabase:** wird nicht als gemeinsames Benutzerverzeichnis, als
  Sammeldatenbank oder als Hintertür zwischen den Produktprojekten verwendet.
  Ein späterer konkreter Zweck braucht eigene Datenklassifizierung,
  Verantwortliche, minimales Schema, RLS und Freigabe. Ohne diese Freigabe
  bleibt das Projekt ungenutzt.
- **PostgreSQL lokal:** bestehende lokale Compose-Daten sind nicht automatisch
  mit Supabase synchronisiert. Keine produktiven Daten kopieren oder
  Testzugriffe auf Produktionsprojekte konfigurieren.

Der Identitätsanbieter und Login-/Tokenfluss sind im Ist-Stand **OFFEN**. Vor
Implementierung muss festgelegt werden, wie ein kurzlebiger, widerrufbarer
Nachweis je Produkt ausgestellt und vom Backend geprüft wird. Falls Supabase
Auth gewählt wird, bleiben Benutzer, Issuer/Audience-Prüfung und Sessions
zwischen NIKNOLIG und Defense projekt- und produktgebunden; ein gemeinsamer
Account oder übertragener Token erteilt keine Rechte im anderen Projekt.

## 3. Verbindliche Datenfluss- und Sicherheitsregeln

Der folgende Fluss ist die **vorgesehene, noch nicht freigegebene**
Implementierung. Derzeit ist kein operativer Datenfluss freigegeben oder
implementiert:

1. Der Nutzer authentifiziert sich in der eigenen Produktdomäne. Der Client
   sendet den kurzlebigen Nachweis über HTTPS an eine versionierte
   Backend-Operation; Zugangsdaten und vollständige Tokens werden nie geloggt.
2. Das Backend prüft Signatur/Issuer, Audience, Ablauf und Widerruf. Es bindet
   den Akteur an genau ein Produkt (`niknolig` oder `niknolig-defense`) und
   bestimmt Ressource, Aktion und Zweck. Vom Client gelieferte Tenant-,
   Projekt- oder Rollenwerte sind keine Autorisierungsnachweise.
3. Das Backend prüft zusätzlich die konkrete Ressourcenzugehörigkeit und
   gegebenenfalls den gültigen Zweck/Consent. Standard ist Verweigerung.
   Es routet ausschließlich zum diesem Produkt zugeordneten Supabase-Projekt
   und führt Abfragen mit Nutzerkontext aus, sodass dessen RLS greift.
4. Die Datenbank erzwingt Zeilenbesitz und Produktbereich unabhängig von
   UI- und Backend-Checks. Keine implizite Berechtigung entsteht durch eine
   Geräteverknüpfung, geteilte Komponente, gültigen Token eines anderen
   Produkts oder Kenntnis einer UUID.
5. Antworten enthalten nur erlaubte, minimierte Felder. Rohbilder, Audio,
   Punktwolken, Tokens, Schlüssel und vollständige Request-Payloads gehören
   nicht in Audit- oder Anwendungslogs. Nur erforderliche Sicherheitsmetadaten
   und eine zufällige Korrelations-ID dürfen protokolliert werden; Aufbewahrung
   und Zugriff sind **OFFEN** bis zur Freigabe.

| Bedingung | Zielreaktion |
| --- | --- |
| Fehlender, ungültiger, abgelaufener oder widerrufener Nachweis | `401` mit `AUTHENTICATION_REQUIRED` bzw. `AUTHENTICATION_INVALID`; keine Datenbankabfrage. |
| Gültiger Nachweis, aber falscher Produktbereich, Projekt oder nicht erlaubte Aktion | `403` mit `APP_AREA_MISMATCH` bzw. `AUTHORIZATION_DENIED`; keine projektübergreifende Abfrage. |
| Ressource im eigenen Bereich nicht vorhanden oder für den Nutzer nicht sichtbar | Nicht-sensitive `404 NOT_FOUND`; keine Existenzdetails aus einem fremden Bereich offenlegen. |
| Schema-/Eingabefehler | `400 VALIDATION_FAILED`; keine partielle Änderung. |
| Abhängigkeit nicht verfügbar | Generische `503 SERVICE_UNAVAILABLE`; keine Host-, SQL-, Projekt- oder Credential-Details. |

Fehlerantworten verwenden die vorhandenen stabilen OpenAPI-Codes. Die genaue
Tokenprüfung, Widerrufsquelle, Fehlerübersetzung und Datenaufbewahrung benötigen
vor Implementierung eine dokumentierte Entscheidung. Bei Unsicherheit oder
Prüffehler gilt fail closed.

## 4. Mandantentrennung und gemeinsame Zugriffe

- Die Vertrauensdomänen sind `niknolig` und `niknolig-defense`; jedes Produkt
  hat eigene Nutzer-/Installationsidentität, Credentials, Supabase-Projekt,
  Rollen und Daten. Authentifizierung in einer Domäne impliziert niemals
  Zugriff in der anderen.
- Das Backend leitet `app_area` ausschließlich aus verifiziertem Kontext ab.
  Ein frei gesetzter Mandanten-Header oder Body-Wert wird ignoriert oder
  abgelehnt. Bei Konflikt zwischen Token, Route, Ressource und Datenbank wird
  vor dem Zugriff verweigert.
- RLS-Policies müssen bei jeder betroffenen Tabelle aktiviert und erzwungen
  werden, einschließlich Prüfung von SELECT/INSERT/UPDATE/DELETE und
  Beziehungen. Policies prüfen verifizierte Nutzer-/Ressourcenbindung statt
  allein clientseitiger `tenant_id`. Views, RPCs, Storage-Policies und
  Sicherheitsfunktionen dürfen RLS nicht umgehen. Rollen mit
  `BYPASSRLS`/Owner-Rechten dürfen nicht im Nutzerpfad verwendet werden.
- Es gibt **keinen** pauschalen gemeinsamen Zugriff. Ein späterer
  NIKNOLIG↔Defense-Datenfluss benötigt einen konkreten Zweck, minimale
  Datenfelder/Aktionen, explizite Freigabe beider verantwortlicher Stellen,
  getrennten versionierten Vertrag, frische Authentifizierung und
  widerrufbare ressourcen- und zweckgebundene Autorisierung. Eine
  Cross-App-Operation muss explizit modelliert und auditiert werden; ein
  Link-/Pairing-Eintrag oder gemeinsames Monorepo-Projekt reicht nicht.
- Der aktuelle SQL-Link-Entwurf verbietet gleiche App-Bereiche, ist nicht
  angewendet und erklärt ausdrücklich, dass eine Verbindung keine Aktion
  freigibt. Er ersetzt weder das spätere Cross-App-Autorisierungsmodell noch
  RLS.

## 5. Plattform- und Repository-Kompatibilität

Die Architektur ist mit getrennten Android-, iOS- und Web-Repositories
vereinbar: Sie teilen nur freigegebene, versionierte HTTP-/JSON-Verträge und
Fehlersemantik, nicht Laufzeit, Secrets, Datenbankzugriff oder
Produktidentitäten. Android- und iOS-Clients verwenden je Produkt eigene
Adapter und sichere Betriebssystem-Speicher; Web-Clients verwenden nur den
Backend-Endpunkt und eine nach Freigabe eng begrenzte Origin-/CORS-Regel.
Kein Client enthält Datenbank-Credentials. Gemeinsame Fixtures prüfen dieselbe
Vertragsversion über Backend und alle genehmigten Clients.

Im Monorepo existieren zwei getrennte Android-Module. Eine iOS-App und
produktive Web-Clients sind hier nicht vorhanden; die Websites verbleiben in
ihren jeweiligen Quell-Repositories. Daher ist die Kompatibilität eine
Vertragsvorgabe, kein Nachweis einer bereits erfolgten Integration. Änderungen
in Produkt-Repositories bleiben separat zu planen, zu reviewen und freizugeben.

## 6. Implementierungs- und Testplan (noch nicht ausgeführt)

Keine produktive Umsetzung beginnt vor benannten Verantwortlichen,
SecurityChain-P0-Nachweis, Datenklassifizierung, Identitäts-/Widerrufsentscheidung
und schriftlicher Freigabe. Anschließend in isolierter, synthetischer
Testumgebung:

1. **Projektinventar und Ownership:** Projekt-IDs read-only bestätigen;
   Projekt-Admins, Data Owner, Incident-Verantwortung, bestehende Schemas,
   Auth-Einstellungen, Daten und Policies je Projekt dokumentieren. Unbekannte
   Einträge bleiben **OFFEN**. Keine Datenmigration oder Änderung bei dieser
   Bestandsaufnahme.
2. **Verträge und Schema:** freigegebene APIs, Ressourcen und app-scoped
   Claims versionieren. Drei unabhängig adressierte Schema-/Migrationssätze
   und minimale Tabellen festlegen. Für neue und vorhandene Tabellen
   Daten-Owner, Retention, Löschung und RLS-Pflicht dokumentieren. Keine
   Migration in Produktion ausführen, bevor Review, Backup-/Rollback-Plan und
   explizite Freigabe vorliegen.
3. **API-Autorisierung:** Middleware für Tokenprüfung und serverseitiges
   Produkt-Routing implementieren; pro Operation Akteur, Ressource, Aktion,
   Consent und Produktbereich autorisieren. Zulässige Nutzerdatenbankzugriffe
   ausschließlich mit RLS-wirksamem Nutzerkontext ausführen. Secrets nur in
   genehmigter Laufzeitkonfiguration, nie in Git/Clients/Build-Artefakten.
4. **RLS und DB-Rollen:** RLS/`FORCE ROW LEVEL SECURITY` pro geschützter
   Tabelle, engste SQL-/API-Rechte und getrennte Projektkonfiguration
   einführen. Policies und Views/RPCs gegen Owner-, `service_role`- und
   `BYPASSRLS`-Umgehung prüfen. Service-Role-Zugriff ist kein Ersatz für
   Endnutzer-Autorisierung und im normalen Request-Pfad untersagt.
5. **Negativ- und Isolationstests:** Nur synthetische Nutzer und Datensätze in
   disposable lokalen/isolierten Projekten verwenden. API- und direkte
   RLS-Prüfungen für jede Operation ausführen; Datenbankzustand vor/nach
   fehlgeschlagenen Schreibversuchen vergleichen. Keine produktiven Projekte
   als Testziele.
6. **Plattformkonformität und Betrieb:** Dieselben erlaubten/abgelehnten
   Fixtures gegen Backend sowie separat freigegebene Android-, iOS- und
   Web-Consumer prüfen. Widerruf, Fehlerbehandlung, Logging, Rate Limits,
   Löschung, Backup/Restore, Alarmierung und Verantwortungsübergabe reviewen.
   Deployment und Veröffentlichungen bleiben ein gesondertes Freigabetor.

### Gezielte Negativtests (Abnahmekriterien, keine vorhandenen Laufzeittests)

| Testfall | Manipulation | Erwartung |
| --- | --- | --- |
| Fehlende Authentifizierung | Geschützte API ohne `Authorization` | `401 AUTHENTICATION_REQUIRED`; kein DB-Aufruf und keine Zustandsänderung. |
| Ungültiger/abgelaufener Nachweis | Falsche Signatur, Audience, Issuer, Ablauf oder widerrufener Test-Token | `401 AUTHENTICATION_INVALID`; kein DB-Aufruf. |
| Unberechtigter Nutzer | Nutzer desselben Produkts liest/ändert/löscht fremde Ressource | API gibt generisches `404` oder `403` gemäß freigegebenem Vertrag; RLS gibt keine fremde Zeile frei; Schreibversuch verändert keine Daten. |
| Falsche Mandanten-ID | NIKNOLIG-Token fordert `app_area=niknolig-defense` oder setzt fremde `tenant_id` | `403 APP_AREA_MISMATCH`; Backend verwendet keine fremde Projektverbindung; RLS gibt keine Zeile frei. |
| Unzulässiger Projektzugriff | NIKNOLIG-Token/Route versucht Defense- oder Monorepo-Projekt | `403 AUTHORIZATION_DENIED`/`APP_AREA_MISMATCH`; kein Fallback-Projekt, keine Abfrage oder Änderung dort. Gleiches symmetrisch für Defense. |
| Nicht erlaubter Monorepo-Zugriff | Produktclient fordert Daten des Monorepo-Supabase-Projekts | Abgewiesen; das Projekt bietet keine Produktdaten/API für Clients. |
| Querzugriff ohne ausdrückliche Freigabe | Verknüpfte Geräte oder gleicher Nutzer versuchen Cross-App-Aktion | `403`; kein impliziter Grant und keine Nebenwirkung. |
| RLS-Bypass | API-/Anwendungskonto mit Owner-/`BYPASSRLS`-Rechten wird im normalen Nutzerpfad verwendet | Deployment-/Konfigurationstest schlägt fehl; keine produktive Anfrage wird mit dieser Rolle ausgeführt. |
| Vertrauliche Nutzdaten/Consent | Ungültiger Consent, widerrufener Zweck oder rohe Sensorpayload | Validierung/Autorisierung verweigert; kein Upload, keine Speicherung, keine Payload im Log. |

**Aktueller Teststatus:** Diese Fälle sind Abnahmespezifikation, keine
nachgewiesene Durchsetzung. Bestehende Backendtests prüfen statische
Vertragsinvarianten, Health-Routen und dass nicht vorhandene Routen `404`
liefern; sie belegen keine Authentifizierung, API-Berechtigung, RLS oder
Mandantentrennung. Insbesondere beweist ein `404` für eine nicht implementierte
Route nicht, dass ein geschützter Endpunkt einen unberechtigten Nutzer sicher
ablehnt.

## 7. Offene Freigaben und Sicherheitslücken

- **OFFEN:** Projektzuordnung/Existenz und Ist-Schema aller drei IDs,
  tatsächliche Daten, RLS-Status und Auth-Konfiguration.
- **OFFEN:** Fachliche Data Owner, Projekt-Admins, Security-/Incident-
  Verantwortliche, Betrieb und Zuständigkeit für Migrationsfreigaben.
- **OFFEN:** Normative SecurityChain-P0-Kriterien, Login-/Tokenissuer,
  Rollen/Rechte, Widerruf, Aufbewahrung/Löschung, zulässige Ressourcen und
  mögliche Cross-App-Anwendungsfälle.
- **Nicht implementiert:** Produkt-API, Auth-Middleware, Backend-
  Projektverbindungen, Supabase-RLS, produktive Datenmodelle und ausführbare
  API-/RLS-Negativtests.
- **Sicherheitsstatus:** Es kann keine RLS- oder Mandantensicherheit für die
  drei Supabase-Projekte bestätigt werden. Daher keine produktiven oder
  sensiblen Daten über eine angenommene Schutzwirkung übertragen.

Nächster Schritt ist die read-only Bestätigung der drei Projekte und die
Benennung der Verantwortlichen. Erst nach den oben genannten Freigaben darf
eine isolierte Implementierung mit synthetischen Daten beginnen.
