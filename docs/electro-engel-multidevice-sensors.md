# Elektro-Engel: Gerätewechsel und Sensorverträge

**Status: Entwurf und versionierte Verträge; keine Laufzeitintegration. P0: BLOCKED.**

Die Apps `:niknolig` und `:niknolig-defense` bleiben getrennte Installationen,
Application IDs, Sicherheitsdomänen und Releases. Dieses Dokument und
`backend/contracts/` definieren keine geteilte Android-Runtime und verleihen
Defense keine impliziten Elektro-Engel-Rechte. Es wurden keine Sensoren
abgefragt, Geräte gekoppelt oder Nutzerdaten erfasst.

## Vorhandener Stand und Verträge

Die aktuellen Android-Manifeste enthalten keine Kamera-, Mikrofon-, Standort-,
Bluetooth- oder Netzwerkberechtigungen. NIKNOLIG zeigt den Assistenten lokal;
die Anfrage wird lokal dargestellt und nicht übertragen. In den geprüften
Quellen gibt es weder Gerätewechsel noch Sensorerkennung/-zugriff, Pairing,
Authentifizierung, Fernsteuerung oder eine Netzwerkverbindung.

Die versionierten JSON-Schemas sind deklarative Vorschläge:

- `backend/contracts/device-consent-v1.schema.json`: ausdrückliche,
  installations- und zweckgebundene Freigabe, enger Datentyp, Textversion und
  Ablaufzeit. Der Grant ist keine Berechtigungsentscheidung und enthält keine
  Freigabe für beliebige Nachrichten, Profile, Rohdaten oder Fernsteuerbefehle.
- `backend/contracts/consent-audit-event-v1.schema.json`: grant/deny/revoke/expire
  Ereignisse mit Geräte-, Zweck-, Zeit- und Korrelationsmetadaten; keine freien
  Notizen oder Nutzdaten.
- `backend/contracts/sensor-capability-v1.schema.json`: Plugin-Identität,
  Sensorart, tatsächlicher Laufzeitstatus, Berechtigungsstatus und bestätigte
  Fähigkeiten. `other` verlangt eine benannte Erweiterungs-ID. „available“ ist
  nicht gleich Zustimmung.
- `backend/contracts/sensor-summary-v1.schema.json`: ausschließlich lokale
  Vorverarbeitung und abgeleitete Zusammenfassungen. Unbekannte Retention-IDs,
  Rohaufnahmen und Remote-Übertragung ohne Consent-Prüfung müssen abgelehnt
  werden. Kein Schema ist bereits mit einer JSON-Schema-Laufzeit oder API
  verdrahtet.

Versionierung: `contractVersion: "1.0"` sowie unveränderliche Schema-Dateien.
Unbekannte Versionen, Sensorarten, Zwecke, Datenklassen oder Fähigkeiten sind
fail closed abzulehnen. Eine inkompatible Änderung benötigt eine neue
Schema-/Contract-Version und kompatible Verbraucherprüfungen.

## Gerätewechsel, Zustimmung und Sicherheitsgrenzen

Vorgesehener Ablauf nach Freigabe:

1. Quell- und Zielinstallation werden jeweils innerhalb ihrer App-Domäne sicher
   authentifiziert; Geräteanzeigenamen oder UUIDs allein sind keine Identität.
2. Die aktive Quelle zeigt Zielgerät, Zweck, Datenkategorien, Laufzeit und
   Folgen gut verständlich an. Freigabe erfordert aktive Bestätigung am
   betroffenen Gerät und ist an genau dieses Ziel und diesen Zweck gebunden.
3. Die Zielinstallation muss die Aufnahme ebenfalls aktiv bestätigen. Erst
   danach darf eine eng begrenzte, autorisierte Sitzung fortgesetzt werden.
   Dieser Vertragsentwurf gibt keine Übertragung von Chatverlauf, Profil,
   Zugangsdaten oder privaten Inhalten frei.
4. Jede Fortsetzung und jede Geräteaktion wird gegen Installation, App-Bereich,
   konkrete Aktion, Consent, Ablauf und Widerrufsstatus geprüft. Ein Link oder
   eine vorherige Zustimmung erteilt keine allgemeine Fernsteuerberechtigung.
5. Widerruf am Quell- oder Zielgerät beendet die Sitzung, sperrt Folgeaktionen
   und erzeugt ein minimiertes Audit-Ereignis. Verbindungsabbruch,
   App-Neustart, Gerätewechsel und Ablauf führen nicht zur automatischen
   Wiederaufnahme. Wiederverbindung benötigt frische Peer-Authentifizierung
   und erneute Autorisierungsprüfung; bei Unklarheit wird beendet.

Threat Model: fremde oder kompromittierte Geräte, manipulierte/gespoofte
Discovery, Replay und Duplikate, gestohlene Installation, veraltete/widerrufene
Einwilligung, App-/App-Bereich-Verwechslung, Netzwerk-/Prozessabbruch und
unbefugte Sensorfreigabe. Vertrauensgrenzen liegen zwischen jeder App-Sandbox,
OS-/Sensor-API, Transport/Backend und Audit-Speicher. Schutzmaßnahmen müssen
mindestens frische Challenge/Nonce und Sitzungsbindung, authentisierte
Peer-Identität, Integritätsschutz, Aktions-Allowlist, Zeitlimits,
Wiederholungsschutz, Widerruf und minimale Audit-Metadaten umfassen. Verschlüsselter
Transport, Android-Pairing oder gemeinsame Verträge allein belegen weder
gegenseitige App-Authentifizierung noch Autorisierung.

Schlüsselhaltung: private Installationsschlüssel verlassen ihr Gerät nicht.
Kein Schlüssel-Backup/Export in Cloud-Speicher, Logs oder den jeweils anderen
App-Bereich. Hardware-Backing/Attestierung, Schlüsselalgorithmus,
Rotation/Löschung, Neuinstallation, Geräteverlust und Recovery sind offene
verbindliche Entscheidungen. Keine Kryptografie-Eigenentwicklung. Ein
Sicherheits-/Integritätsfehler stoppt die Sitzung; kein stiller Fallback auf
schwächere Identität oder Transport.

Audit enthält nur Ereignistyp, pseudonyme Consent-/Installationsreferenzen,
Zweck, Zeit und Korrelations-ID; keine Rohdaten, Inhalte, Schlüssel oder Tokens.
Zugriff, Aufbewahrung, Löschung und rechtliche Verantwortlichkeit müssen vor
Implementierung festgelegt werden. Derzeit ist keine Speicherdauer freigegeben;
keine konkrete Retention oder Nutzdatenübertragung ist dadurch erlaubt.

## Sensor-Plugin-Modell und Android-Anforderungen

Jede App integriert künftig ihren eigenen, lokal gebündelten Adapter hinter
derselben versionierten Capability-Schnittstelle. Ein Adapter meldet erst nach
Laufzeitprüfung `available`, welche konkreten Outputs/APIs und OS-Berechtigungen
tatsächlich vorhanden sind. Remote geladene Plugins, implizite Berechtigungen,
Annahme aus Modell-/Gerätenamen und ein Sensor-Fallback ohne erneute
Capability- und Consent-Prüfung sind ausgeschlossen.

| Sensor / Funktion | Laufzeitnachweis und mögliche Android-Anforderung | Grenze |
| --- | --- | --- |
| LiDAR | Android hat keine universelle LiDAR-Gerätegarantie/API im bestehenden Vertrag. OEM-/Geräte-API und konkrete Hardware müssen separat entdeckt und verifiziert werden. | Camera2-Depth-Unterstützung ist kein Beweis für LiDAR. Nur als `lidar` deklarieren, wenn Hardware/OEM-API diese Eigenschaft tatsächlich belegt; sonst unavailable/unknown. |
| Tiefe / Tiefenkamera | Camera2 ab API 21; `REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT` und DEPTH16-Tauglichkeit ab API 23. Laufzeitabfrage der Kameracharakteristiken und Outputformate erforderlich. | Die Apps setzen aktuell `minSdk 26`; trotzdem muss jedes Gerät die konkrete Fähigkeit zur Laufzeit bestätigen. Keine angenommene Verfügbarkeit oder Genauigkeit. |
| Kamera | `android.permission.CAMERA`, Manifestdeklaration plus Laufzeitfreigabe; nur während klarer Nutzeraktion/Sitzung. | Preview-/Bildsensorzugriff ist nicht implementiert. Keine Aufnahme im Hintergrund; keine Übertragung von Frames. |
| Mikrofon | `android.permission.RECORD_AUDIO`, Manifestdeklaration plus Laufzeitfreigabe. | Nicht vorhanden oder angefragt. Sprachaufnahme/-übertragung ist ausdrücklich nicht Teil des jetzigen Vertrags. |
| Standort | Nur bei freigegebenem Zweck coarse/fine Laufzeitberechtigung; tatsächliche Anbieter-/Provider-Verfügbarkeit zur Laufzeit. | Keine Hintergrundortung; Standort ist bisher keine freigegebene Datenkategorie. |
| BLE für späteres Pairing | Ab Android 12 je nach Operation `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`; ältere Zielsysteme/Berechtigungsmodelle und Scan-Standortfolgen separat prüfen. | Transportwahl offen. BLE-Freigabe ist nicht Peer-Identität oder Zustimmung zur Datenfreigabe. |
| Andere Sensoren | Plugin-ID und Capability nur für dokumentierte Android-/OEM-API und wirklich verfügbare Geräte melden. | Unbekannter Plugin-Code, API oder Output ist `unknown`/nicht unterstützt und wird nicht aktiviert. |

Die genannten API-/Berechtigungsangaben sind Planungsanforderungen, keine
verifizierte Gerätekompatibilitätsmatrix. Vor jeder Implementierung sind
Android-Versionen, OEM-APIs, API-Level und Laufzeitdialoge gegen offizielle
Android-Dokumentation sowie unterstützte physische Geräte zu prüfen. Bei
verweigertem oder später widerrufenem OS-Recht ist Capture sofort zu stoppen;
ein allgemeines Session-Consent ersetzt nie Android-Runtime-Permission.

Datengrenze: Sensor-Rohdaten lokal und flüchtig verarbeiten, wo technisch möglich;
nur abgeleitete, minimierte Ergebnisse weiterverarbeiten. Keine Rohbilder,
Audioaufnahmen, Punktwolken oder präzisen Standortdaten an Backend/Zielgerät
übertragen. Welche abgeleiteten Daten übertragen werden dürfen, welcher Zweck
gilt und welche Aufbewahrungszeit angemessen ist, sind offene Freigaben; bis
dahin nur lokale Verarbeitung, standardmäßig ohne Persistenz und ohne
Netzübertragung. Ein unterstützter alternativer Tiefensensor ist nur nach
separater Laufzeitfeststellung und zweckbezogener Zustimmung zulässig.

## Tests und reale Geräteabnahme

`backend/tests/test_contracts.py` prüft Schema-Versionen, Pflichtfelder und
verbotene implizite Zustände mit Python-Standardbibliothek. Das ersetzt keine
JSON-Schema-Validator-Ausführung, Transport-/Auth-Tests oder physische
Geräteabnahme.

Vor Freigabe sind mindestens automatisiert negativ zu prüfen: fehlende Quelle,
Ziel, Zweck, Textversion oder Ablaufzeit; falsche App-Domäne; veralteter oder
widerrufener Consent; Zielgerätwechsel; ungültige/abgelaufene Nonce, Replay und
Duplikat; unbekannte Contract-/Plugin-Version; `available` bei verweigerter
Berechtigung; `other` ohne Extension-ID; Sensorübertragung ohne passende
Zustimmung; Rohdaten/unbekannte Eigenschaften; OS-Berechtigungswiderruf während
der Sitzung; Wiederverbindung ohne erneute Authentifizierung. Erwartetes
Ergebnis: ablehnen, Sitzung beenden, keine Warteschlange/Retry und kein
sensitiver Payload im Audit.

Physischer Testplan (noch nicht durchgeführt): je mindestens zwei tatsächlich
unterstützte Android-Geräte je freizugebender Kombination; Modell, Build,
Android-/API-Level und App-Signatur erfassen. Separate Fälle für bestätigtes und
abgelehntes Pairing, falsches Ziel, Timeout/Offline/WLAN-Wechsel, App-Neustart,
Widerruf/Verlust, OS-Rechte ablehnen/widerrufen, LiDAR wirklich vorhanden und
nicht vorhanden, Camera2 Depth Output vorhanden und nicht vorhanden sowie
kompatible und inkompatible OEM-APIs. Sensor-Tests erst nach expliziter
Testperson-Zustimmung und ohne produktive Nutzdaten. Keine Geräte- oder
Sensorunterstützung wird bis zu solchen Belegen behauptet.

## Integrationsschritte je App nach P0-Freigabe

Keine Änderung an den separaten Quell-Repositories wurde vorgenommen. Ihre
aktuellen App-/Gradle-/Manifestpfade sind `app/build.gradle.kts`,
`app/src/main/AndroidManifest.xml`, `app/src/main/java/`, `app/src/main/res/`,
`app/src/test/` und `app/src/androidTest/`.

- **NIKNOLIG:** eigener Adapter/Consent-UI unter
  `app/src/main/java/com/niknolig/app/`, UI-Texte in
  `app/src/main/res/values/strings.xml`, nur einzeln freigegebene
  Sensor-/Netzwerkrechte in Manifest und abhängige Runtime in
  `app/build.gradle.kts`. Assistenten-Daten bleiben ohne zweckgebundenen Grant
  lokal.
- **NIKNOLIG Defense:** getrennte Implementierung/Consent-UI unter
  `app/src/main/java/com/niknolig/defense/`, eigene UI-Texte, Manifestrechte,
  Adapter, Tests, Identität und Credentials. Kein Austausch privater App-Daten
  oder NIKNOLIG-Credentials.
- **Beide Autobuild-Aufträge:** Unit-/Vertrag-/Negativtests und Manifestprüfung
  in `app/src/test/`/`app/src/androidTest/` integrieren; keine Secrets oder
  Produktionstargets für Tests. Hardwaretests als getrennt dokumentiertes
  manuelles Gate. Keine App bekommt eine gemeinsame Laufzeitabhängigkeit, bevor
  deren separat geprüfte Freigabe vorliegt.

## Offene Freigaben / Stop-Gate

SecurityChain-P0-Norm und Kriterien, Identitätsanbieter/Peer-Authentifizierung,
Transport, Schlüsselhardware/Attestierung und Recovery, Daten-/Aktionsumfang,
Zustimmungstexte und -dauer, Sensoranbieter/-genauigkeit, Retention/Löschung,
Audit-Zugriff sowie unterstützte Gerätematrix sind nicht im Repository
entschieden. Bis schriftliche Freigabe und unabhängige Prüfung vorliegen:
keine Produktiv-API, kein Pairing, keine Sensorberechtigung/-aktivierung, keine
App-Runtimeänderung und kein produktiver Gerätewechsel. Ungeklärte Punkte werden
nicht durch diese Vorbereitungsdokumente genehmigt.
