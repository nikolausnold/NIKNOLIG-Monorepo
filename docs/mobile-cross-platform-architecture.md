# Android-/iOS-Architektur und Integrationsplan

**Status:** Architektur- und Vertragsplanung. Keine iOS-App, kein neuer
API-Endpunkt, kein produktiver Backend-Dienst und keine Änderung an den
separaten Android-Quell-Repositories. SecurityChain P0 bleibt ein verbindliches
Stop-Gate.

## 1. Bestand: wiederverwenden statt duplizieren

Die Android-Apps sind die bestehenden Gradle-Module `:niknolig` und
`:niknolig-defense` unter `apps/`. Sie haben getrennte Application IDs und
bleiben in ihrer Zuständigkeit unverändert. Dieses Dokument autorisiert keine
Änderung in den Android-Quell-Repositories.

`backend/` ist bereits die gemeinsame, plattformneutrale Vertragsquelle:

| Bestehende Quelle | Tatsächlicher Umfang | Grenze |
| --- | --- | --- |
| `backend/openapi.yaml` | OpenAPI 3.1 mit nicht-sensitiven Health-Routen und einem stabilen Fehlercode-Katalog | Keine App-, Geräte-, Profil-, Authentifizierungs- oder Synchronisations-API ist implementiert oder freigegeben. |
| `backend/contracts/device-consent-v1.schema.json` | Geräte- und zweckgebundener Zustimmungsentwurf | Ein gültiges JSON-Objekt beweist weder Identität noch Berechtigung. |
| `backend/contracts/consent-audit-event-v1.schema.json` | Minimierte Metadaten für Consent-Ereignisse | Keine Nachrichten-, Sensor- oder sonstigen Nutzdaten. |
| `backend/contracts/sensor-capability-v1.schema.json` und `sensor-summary-v1.schema.json` | Laufzeitfähigkeit und abgeleitete Sensordaten | Deklarative Verträge, keine Sensor-Runtime und keine Übertragungsfreigabe. |
| `backend/migrations/001_initial_contract.sql` | Vorschlag für App-Bereiche, Installationen und Geräte-Link-Lifecycle | Nicht angewendet; ein Link verleiht keine appübergreifende Aktionserlaubnis. |
| `backend/tests/test_contracts.py` | Statische Invarianten und optionale JSON-Schema-2020-12-Validierung | Kein Authentifizierungs-, Server-, Plattform- oder Geräteintegrationstest. |

Die Fehlercodes in OpenAPI und ihre HTTP-Zuordnung sind in
[`backend/README.md`](../backend/README.md) dokumentiert. Das Elektro-Engel-
Architektur- und Migrationsziel steht in
[`electro-engel-architecture-and-migration.md`](electro-engel-architecture-and-migration.md);
die geräte- und sensorbezogenen Grenzen einschließlich Android-Planung in
[`electro-engel-multidevice-sensors.md`](electro-engel-multidevice-sensors.md).

**Vertragslücke, nicht Anlass für doppelte Entwürfe:** Die vorhandenen Dateien
bilden noch keine vollständigen NIKNOLIG-, Defense- oder Elektro-Engel-Produkt-
APIs. Es fehlen insbesondere freigegebene Geschäftsressourcen, Operationen,
Identitäts-/Login-Fluss und Synchronisationsregeln. Diese dürfen erst nach
fachlicher und Security-Freigabe als neue versionierte Verträge ergänzt werden.
Elektro-Engel ist aktuell eine NIKNOLIG-Systemfunktion, kein dritter App-Bereich
und keine eigene Sicherheitsdomäne.

## 2. Gemeinsame Vertrags- und Backend-Architektur

### Quelle, Versionen und Produktbereiche

- `backend/openapi.yaml` ist die vorgesehene Quelle für HTTP-Operationen,
  gemeinsame Antwortformen und Fehlercodes. `backend/contracts/` enthält die
  vorhandenen, eigenständig versionierten JSON-Schemas. Mobile Apps sollen
  diese Quellen konsumieren oder dagegen geprüft werden; keine App pflegt
  abweichende Kopien als eigene Wahrheit.
- Das vorhandene `app_area`-Modell kennt `niknolig` und `niknolig-defense`.
  Elektro-Engel-Funktionalität wird nur über eine ausdrücklich freigegebene
  NIKNOLIG-Operation und Berechtigung abgebildet, nicht über einen erfundenen
  dritten Bereich. Eine spätere Produktentscheidung für eine andere Grenze
  verlangt eine neue Sicherheits- und Vertragsprüfung.
- Beibehaltene, kompatible Felder und optionale Erweiterungen dürfen bestehende
  Verbraucher nicht brechen. Inkompatible Änderung bedeutet neue
  Vertragsversion bzw. neue versionierte Route; alte Verbraucher und Verträge
  bleiben während einer festgelegten Übergangsfrist bedienbar. Keine Version
  darf stillschweigend umgedeutet werden.
- Vertragstests verwenden dieselben JSON-Beispiele für Android, iOS und
  Backend. Zusätzliche/manipulierte Pflichtfelder, unbekannte kritische Werte,
  falsche App-Bereiche und ungültige Zustände müssen entsprechend dem Vertrag
  abgelehnt werden. Zeitwerte verwenden UTC nach RFC 3339; Feldtypen, UUID-
  Format, Null-/Auslassungssemantik, Grenzen und Enum-Verhalten müssen
  ausdrücklich festgelegt sein. Ein generierter Client ist kein Ersatz für
  Schema- und Verhaltenstests.

### Authentifizierung und Autorisierung

Der bestehende Bearer-Scheme-Eintrag ist nur eine Reservierung; es gibt keinen
Token-Aussteller, Login, Auth-Middleware oder produktiven API-Server. Für eine
spätere Freigabe gelten mindestens diese Entwurfsanforderungen:

1. Zugriffsnachweise sind kurzlebig, widerrufbar und an Aussteller,
   Zielgruppe, App-Bereich, Installation und minimale Aktion gebunden. Token-
   Format, Aussteller, Anmeldung und Erneuerung bleiben bis zur Freigabe offen.
2. Jede Serveroperation autorisiert die konkrete Kombination aus Akteur,
   App-Bereich, Ressource, Aktion, Zielinstallation, Zweck und aktivem Consent.
   Besitz eines gültigen Tokens, eines Geräteschlüssels oder eines Links allein
   erteilt keine Berechtigung. NIKNOLIG- und Defense-Credentials bleiben
   getrennt.
3. Installation-/Peer-Identität wird unabhängig vom Gerätenamen und von einer
   übermittelten Installations-ID geprüft. Schlüssel verlassen das Gerät nicht;
   Android Keystore und Apple Keychain/Secure Enclave sind getrennte
   Plattformimplementierungen, keine gemeinsam nutzbare Identität.
4. Bei Authentifizierungs-, Bereichs-, Consent-, Integritäts- oder
   Widerrufsfehlern gilt fail closed. Keine sensiblen Aktionen werden offline
   gepuffert oder automatisch erneut ausgeführt.

### Datenmodell und API-Fehler

Das einzige vorhandene relationale Modell ist der nicht angewendete Vorschlag
in `backend/migrations/001_initial_contract.sql`: `device_installations`
bindet eine Installation an `app_area`, einen undurchsichtigen Principal-
Verweis und einen öffentlichen Schlüsselfingerabdruck samt Identitätsstatus.
`device_links` hält zwei Installationen und ihren Status/Ablaufzeitpunkt fest.
Es enthält keine privaten Schlüssel, Nutzdaten oder automatische
Aktionsfreigabe. Es gibt noch kein persistentes Produktprofil-, Nachrichten-
oder Sync-Modell.

Gemeinsame API-Fehler verwenden die vorhandenen maschinenlesbaren Codes:

| Status | Bestehende Fehlercodes |
| --- | --- |
| 400 | `VALIDATION_FAILED` |
| 401 | `AUTHENTICATION_REQUIRED`, `AUTHENTICATION_INVALID` |
| 403 | `AUTHORIZATION_DENIED`, `APP_AREA_MISMATCH`, `DEVICE_IDENTITY_UNVERIFIED`, `PAIRING_REQUIRED`, `PAIRING_EXPIRED`, `REPLAY_DETECTED` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 429 | `RATE_LIMITED` |
| 500 | `INTERNAL_ERROR` |
| 503 | `SERVICE_UNAVAILABLE` |

Clients behandeln den Code als stabil und menschenlesbare Meldungen als nicht
stabil/lokalisiert. Antworten enthalten keine Stacktraces, internen Hosts,
Tokens, Schlüssel oder Payload-Kopien. `requestId` dient der Korrelation und
ist kein Berechtigungs- oder Wiederholungsnachweis. Sicherheits- und
Integritätsfehler beenden die betroffene Sitzung.

### Synchronisation

Der aktuelle Stand hat weder Sync-Endpunkte noch ein Sync-Protokoll. Daher
werden jetzt keine Konfliktauflösung, Offline-Warteschlange, automatische
Wiederholung oder Hintergrund-Synchronisation implementiert oder versprochen.
Vor einer Freigabe müssen Datenumfang, Quelle der Wahrheit, Löschung,
Konfliktregeln, Cursor-/Versionsmodell, Idempotenz, Reihenfolge,
Widerrufsverhalten und Wiederanlauf vertraglich definiert werden.
Sicherheitsrelevante Aktionen bleiben online autorisierungspflichtig und werden
nicht aus einer Offline-Queue nachgeholt. Lokale Speicherung und ihre
Aufbewahrung benötigen eine gesonderte Datenschutz- und Security-Freigabe.

## 3. Plattformneutrale Schnittstellen

Dies ist ein logischer Schnittstellenkatalog, keine Implementierungsvorgabe
für ein gemeinsames mobiles SDK. Die fachlichen Ein-/Ausgaben beziehen sich
auf versionierte Backend-Verträge; Android und iOS implementieren sie jeweils
in ihrer App und Sandbox.

| Schnittstelle | Gemeinsame Verantwortung | Plattformadapter / Grenze |
| --- | --- | --- |
| `ContractCodec` | Versionierte JSON-Verträge laden, validieren und serialisieren | Gleiche Feld-/Null-/Zeit-/Enum-Semantik in Kotlin und Swift; unbekannte oder ungültige sicherheitskritische Zustände ablehnen. |
| `CredentialProvider` | Einen bereits freigegebenen, app-scoped Nachweis für einen API-Aufruf bereitstellen und Erneuerungs-/Widerrufsfehler melden | Kein Token im Core, Log, Testfixture oder in der anderen App teilen; sichere Ablage im jeweiligen OS. |
| `BackendClient` | Freigegebene API-Operation aufrufen, Fehlercode und Request-ID typisiert zurückgeben | TLS, Timeouts, Antwortgrößenlimits und sichere Fehlerbehandlung je Plattform; keine Endpunkte aus dem lokalen Compose-Setup übernehmen. |
| `AuthorizationContext` | App-Bereich, Installation, Zweck, Ressource, konkrete Aktion und Consent für eine Entscheidung binden | Server bleibt Autorisierungsinstanz; UI oder lokaler Core darf eine Serverentscheidung nicht ersetzen. |
| `ConsentGateway` | Einen konkreten Zweck und eine konkrete Datenkategorie anzeigen, Grant/Deny/Revoke abbilden und Ablauf beachten | Plattformgerechte, aktive Nutzeraktion; Zustimmung niemals aus OS-Permission ableiten. |
| `CapabilityProvider` | Verfügbare Fähigkeit, Provider, Berechtigungszustand und Zeitpunkt melden | Nur lokal gebündelte, vertrauenswürdige Adapter; Hardware/API und Permission zur Laufzeit prüfen. |
| `DeviceLinkTransport` | Eine versionierte, authentisierte, begrenzte Nachricht transportieren, falls P0 und Protokoll freigegeben sind | Transport- und Pairing-Implementierung ist plattformspezifisch; Discovery ist keine Identität, TLS/OS-Pairing allein keine Autorisierung. |
| `Clock` / `IdGenerator` | UTC-Zeit und eindeutige Korrelations-/Idempotenzwerte für deterministische Regeln liefern | Testbar injizieren; keine Gerätezeit als einzige Autorisierungsquelle für Consent-/Tokenablauf verwenden. |

Die Zustandslogik und Verträge dürfen keine Android-/Apple-Frameworktypen,
Activities, ViewController, OS-Permission-Dialoge, UI-Texte, Credentials oder
app-spezifischen Daten importieren. Es wird aktuell kein Cross-Platform-
Framework und keine gemeinsame mobile Bibliothek festgelegt.

## 4. Android-/iOS-spezifische Umsetzung und Berechtigungen

Berechtigungen werden minimal, zweckbezogen und erst bei Nutzeraktion
angefordert. Ein Server-Consent ersetzt keine OS-Berechtigung; eine OS-
Berechtigung ersetzt weder Nutzerzustimmung noch Serverautorisierung. Keine
der folgenden Berechtigungen wird durch diesen Plan neu hinzugefügt.

| Fähigkeit | Android-Anforderung | iOS-Anforderung | Gemeinsame Einschränkung |
| --- | --- | --- | --- |
| Kamera / Tiefe | Manifestdeklaration und Laufzeitfreigabe, z. B. `CAMERA`; Camera2-/Gerätefähigkeit zur Laufzeit prüfen | `NSCameraUsageDescription` und AVFoundation-Freigabe; Depth-/ARKit-Fähigkeit auf unterstütztem Gerät feststellen | Keine Aufnahme ohne konkrete Nutzeraktion und gültigen Zweck; keine Rohdatenübertragung. |
| Mikrofon | Manifest und Laufzeitfreigabe `RECORD_AUDIO` | `NSMicrophoneUsageDescription` und Mikrofonfreigabe/AVAudioSession | Im aktuellen App-Stand nicht angefragt; neue Aufnahme ist gesondert freizugeben. |
| Standort | Je Zweck coarse/fine und Android-Version passende Laufzeitfreigabe; Hintergrundzugriff separat | `NSLocationWhenInUseUsageDescription` bzw. nur nach Freigabe passende Always-/Genauigkeitsoption | Keine Hintergrundortung; Nutzer kann Genauigkeit einschränken oder Zugriff widerrufen. |
| BLE / Geräte | Android-Version-abhängige `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` bzw. ältere Berechtigungsregeln; tatsächliche GATT-/Geräteunterstützung prüfen | CoreBluetooth-Zugriffsdeklaration passend zum Deployment-Target; State/Permission zur Laufzeit prüfen | Discovery, OS-Pairing und Berechtigung liefern keine App-Peer-Identität oder Consent. |
| Lokales Netzwerk | Netzwerk-/Discovery-APIs und Android-Version/Berechtigungen prüfen; `INTERNET` nur für tatsächlich freigegebene API-Verbindung | `NSLocalNetworkUsageDescription` und nötige Bonjour-Dienstdeklarationen für lokale Discovery | Kein lokaler oder externer Transport ist gewählt; keine unbestätigten Hintergrundgarantien. |
| LiDAR / Tiefenfähigkeit | Keine universelle LiDAR-Garantie; OEM-/Hardware-Nachweis und Camera2-Depth getrennt prüfen | ARKit-/Gerätemodell-Fähigkeiten zur Laufzeit prüfen; LiDAR ist nicht auf allen Geräten verfügbar | Capability darf nur bei belegter Hardware/API gemeldet werden; keine Gleichsetzung von „Depth“ und „LiDAR“. |

Alle konkreten Usage-Description-Texte, Berechtigungen, Entitlements,
Hintergrundmodi, Mindestversionen und Hardwarematrizen werden erst pro App und
nach Produkt-/Security-Freigabe entschieden. Auf beiden Plattformen führt
Berechtigungsverweigerung oder -widerruf zum sofortigen Stop der betroffenen
Erfassung. Signale wie iOS App Attest/DeviceCheck oder Android Attestation
werden nicht als bereits ausgewählt oder ausreichender Ersatz für
Peer-Authentifizierung vorausgesetzt.

## 5. Gemeinsame Vertragstests und Kompatibilität

Die vorhandenen Tests bleiben die Basis. Vor einem iOS-Client werden sie zu
plattformübergreifenden Konformitätstests erweitert, statt Produktlogik in
zwei Implementierungen unabhängig neu zu definieren:

1. Vertragsschema und Versionsmetadaten in CI prüfen; pro Version gemeinsame,
   nicht-sensitive gültige und ungültige JSON-Fixtures bereitstellen.
2. Dieselben Fixtures gegen Python/Backend, Kotlin/Android und Swift/iOS
   validieren. Tests prüfen Pflicht-/Zusatzfelder, UUID, UTC-Zeit, Enum- und
   Nullverhalten, Größen-/Grenzwerte sowie App-Bereich und Consent-Bezug.
3. Sicherheitsnegative Fälle abdecken: abgelaufener/widerrufener Consent,
   falsches Ziel oder App-Bereich, fehlender/ungültiger Nachweis, unbekannte
   Vertragsversion, Replay/Duplikat, verweigerte OS-Berechtigung und
   ungültige Sensorfähigkeit. Erwartung: keine Aktion, keine stille Queue und
   keine sensitiven Logs.
4. API-Fehler-Mapping, Timeout-/Abbruchverhalten und Request-Korrelation auf
   beiden Plattformen mit denselben erwarteten Code-/Status-Fixtures testen.
   Retries sind nur für ausdrücklich idempotente, freigegebene Leseoperationen
   zulässig; sensible Schreib-/Geräteaktionen werden nicht automatisch
   wiederholt.
5. Pro Vertragsänderung Kompatibilität gegen alle unterstützten Verbraucher
   nachweisen. Breaking Änderungen erhalten eine neue Version und parallele
   Consumer-Tests; Plattformtests dürfen nicht aus unterschiedlichen,
   manuell kopierten Beispielen bestehen.
6. Sensoren, Berechtigungsdialoge, Hintergrundverhalten und Geräteverbindungen
   auf unterstützten physischen Geräten separat abnehmen. Simulatoren und
   Vertragstests beweisen keine Hardwarefähigkeit oder P0-Konformität.

Die Tests verwenden synthetische Daten und keine produktiven Zugangsdaten,
Nutzerdaten, kostenpflichtigen Dienste oder Deployments.

## 6. Migrations- und Integrationsplan

Kein neues Repository wird im Rahmen dieser Vorbereitung erstellt.

1. **Vertragsinventar stabilisieren:** Bestehende Backend-OpenAPI-, JSON-
   Schema-, SQL- und Testquellen als einzige Vertragsbasis beibehalten. Fehlende
   Geschäfts- und Sync-APIs ausdrücklich als offen führen; keine bereits
   dokumentierten Consent-/Sensorverträge duplizieren.
2. **Freigaben vor Produktverträgen:** SecurityChain-P0-Muss-/Abbruchkriterien,
   Rollen, Datenfluss, App-Bereiche, Identität, Tokenlebenszyklus, Consent,
   Widerruf, Aufbewahrung und API-Betrieb schriftlich beschließen und
   unabhängig prüfen. Bis dahin keine operative API, Sync-Implementierung,
   Berechtigungsänderung, Pairing oder Sensoraktivierung.
3. **Versionierte API-Oberfläche entwerfen:** Nur genehmigte Operationen und
   Datenmodelle in `backend/openapi.yaml`/`backend/contracts/` ergänzen,
   kompatible Fehlersemantik definieren und gemeinsame positive/negative
   Test-Fixtures mit automatischer Vertragsprüfung bereitstellen.
4. **Android unabhängig integrieren:** Bestehende Android-Repositories und
   Monorepo-Module behalten Ownership und App-Identität. Eine spätere Anbindung
   wird von den zuständigen Teams separat geplant, reviewed und freigegeben;
   dieses Dokument ändert sie nicht.
5. **iOS-Repository NIKNOLIG-iOS:** Erst nach Freigabe separat erstellen. Es
   enthält NIKNOLIG-Oberfläche, eigenes Bundle-/Signing-/Release-Setup,
   App-scoped Authentifizierung und iOS-Adapter. Es konsumiert ausschließlich
   die genehmigten gemeinsamen Verträge; kein Defense-Schlüssel, keine
   Android-Runtime und kein impliziter Elektro-Engel-Berechtigungsbereich.
6. **iOS-Repository NIKNOLIG-Defense-iOS:** Ebenfalls separat und mit eigenem
   Bundle, Signing, Release, Identität, Authentifizierung und Test-/Consent-
   Fluss. Keine gemeinsame App-Sandbox, Credentials oder implizite Rechte mit
   NIKNOLIG-iOS oder den Android-Apps.
7. **Parität und Übergang:** Für jeden iOS-Verbraucher Schema-/Fehler-Fixtures,
   App-Bereich, Widerruf, Permission-Nein/Widerruf und Release-Artefakte
   verifizieren. Verträge werden nur nach einer dokumentierten Consumer-
   Migration und Kompatibilitätsprüfung ausgebaut oder abgekündigt.

Technisch sinnvoll werden getrennte iOS-Repositories, wenn Verantwortliche,
Bundle-IDs, Signierung, Releasezyklen und unabhängige Wartung feststehen und
die gemeinsamen Verträge versioniert, automatisiert geprüft und von Android
und Backend konsumiert werden. Davor vermeidet ein Vertragsinventar im
Monorepo unnötige Duplikation. Produktive Umsetzung bleibt unabhängig davon
SecurityChain-P0-blockiert.

## 7. Offene Entscheidungen und Stop-Gate

Offen sind die normative SecurityChain-P0-Fassung, Produkt- und Rollenmodell,
Auth-Anbieter/-Fluss, Installations-/Peer-Identität, Schlüssel- und
Recovery-Policy, konkrete Produkt- und Sync-Ressourcen, Konflikt-/Löschregeln,
Backend-Betrieb, Plattform-Mindestversionen, Apple-/Android-Berechtigungs-
details, Sensor-Gerätematrix und Retention. Keine dieser Entscheidungen wird
durch Architekturtext oder ein valides Schema genehmigt. Bei nicht erfüllter
oder nicht belegbarer Freigabe gilt fail closed.

## 8. Automatische iOS-Vertragsaktualisierung ohne App-Builds

Das Monorepo bleibt die gemeinsame Vertragsquelle für **beide** getrennten
iOS-Apps, NIKNOLIG und NIKNOLIG Defense. Ihre Swift-/Xcode-Projekte, Bundle-IDs,
Signierung, Tests, Builds und Veröffentlichungen gehören ausschließlich in
die jeweils separaten App-Repositories. Hier werden weder iOS-Apps gebaut
noch neue App-Repositories angelegt. Bestehende Android-Workflows bleiben
unverändert; der iOS-Vertragsworkflow selbst führt keinen App-Build aus.

### Automatischer Ablauf im Monorepo

Der Workflow
[`iOS contract update`](../.github/workflows/ios-contract-update.yml)
startet bei jedem Push, bei Pull-Request-Ereignissen (standardmäßig Öffnen,
neue Commits und Wiederöffnen) und per `workflow_dispatch`. „Nach jeder Aktion“
bedeutet hier eine Aktualisierung nach einer Repository-Änderung, nicht nach
einer Nutzeraktion in der App und nicht nach jedem einzelnen Workflow-Schritt.
Ein erneuter Lauf erzeugt ebenfalls einen neuen Snapshot für denselben Commit.
Es gibt bewusst keine `workflow_run`-Kette oder Selbst-Commit-Schleife.

1. Die bestehenden Backend-Vertragstests müssen erfolgreich sein. Ihre
   optionalen JSON-Schema-Prüfungen laufen nur bei installiertem `jsonschema`;
   der Workflow installiert keine Zusatzpakete. Ein grüner Lauf ist keine
   vollständige Schema-/OpenAPI-Validierung oder Produktfreigabe.
2. Ein gemeinsamer Snapshot enthält `backend/openapi.yaml`, die vorhandenen
   `backend/contracts/*.schema.json` und dieses Architektur-/Integrationsdokument.
   Kein Android-Code, keine Datenbankkonfiguration und keine Credentials
   werden aufgenommen.
3. `SOURCE.txt` nennt den tatsächlich ausgecheckten Commit, die getrennten
   Verbraucherbereiche `niknolig` und `niknolig-defense` sowie
   `production_approved=false`. `SHA256SUMS` enthält SHA-256-Prüfsummen für
   sämtliche Snapshot-Quelldateien einschließlich `SOURCE.txt`.
4. Erst nach erfolgreichen Prüfungen wird das Artefakt
   `ios-contracts-<Commit-SHA>` für sieben Tage hochgeladen. Bei einem
   fehlgeschlagenen Lauf entsteht kein neuer verwendbarer Snapshot.

Die Läufe und Artefakte sind unter
[iOS contract update in GitHub Actions](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/workflows/ios-contract-update.yml)
erreichbar. Bei Pull Requests bezeichnet die SHA normalerweise den getesteten
Merge-Commit, nicht den Head-Commit des Quellbranches. Solche Artefakte sind
reine Vorschauen und keine freigegebene Verbrauchergrundlage.

### Übernahme in den separaten iOS-Repositories

Die automatische **Bereitstellung hier** ist eingerichtet; automatisches
**Übernehmen dort** benötigt einen separat freigegebenen Workflow pro
iOS-Repository und ist durch diese Änderung nicht aktiviert:

- Beide Verbraucher verwenden denselben ausdrücklich ausgewählten, erfolgreichen
  Lauf eines vertrauenswürdigen Push-Commits auf dem geschützten Standardbranch.
  Sie prüfen Repository, Ereignis, Branch, Commit und Ergebnis des Laufs;
  niemals blind das neueste Artefakt oder ein PR-Artefakt übernehmen.
- Der Consumer bindet die Übernahme an die vollständige Commit-SHA, gleicht
  `SOURCE.txt` damit ab und prüft nach dem Download `sha256sum --check SHA256SUMS`.
  Die Prüfsummen erkennen Beschädigungen, ersetzen aber keine vertrauenswürdige
  Herkunft oder Freigabe. Für langfristige Reproduzierbarkeit bleibt der
  ausgewählte Git-Commit die Quelle; Artefakte sind nur kurzlebige Transportkopien.
- Eine spätere Automatisierung prüft auf neue erfolgreiche Snapshots und öffnet
  je App einen unabhängigen Update-PR mit alter/neuer Quell-SHA und
  Kompatibilitätsnachweisen. Unveränderte SHAs erzeugen keine doppelten PRs;
  fehlerhafte oder inkompatible Updates lassen den bisher gebundenen Stand
  unverändert. Keine automatische Zusammenführung oder Veröffentlichung.
- NIKNOLIG übernimmt nur seinen App-Bereich, Defense nur `niknolig-defense`;
  derselbe Vertragssnapshot teilt weder Zugangsdaten noch Laufzeitrechte.
  Vertragsänderungen bleiben den Versions-/Migrationsregeln aus Abschnitt 2
  und den gemeinsamen Konformitätstests aus Abschnitt 5 unterworfen.

Das Monorepo benötigt dafür nur `contents: read` und keine Apple-Zugangsdaten,
externen Repository-Tokens oder Schreibrechte. Es sendet keine
repositoryübergreifenden Dispatches und verändert keine fremden Repositories.
App-/TestFlight-/App-Store-Updates und iOS-Systemupdates werden nicht ausgelöst.
SecurityChain-P0 und die fehlenden Produkt-/Sync-APIs bleiben unverändert
blockierend; ein neuer Snapshot hebt kein Stop-Gate auf.
