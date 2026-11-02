# SecurityChain-P0 D-01 bis D-12: Gesamtstatus und Freigaberegister

**Stand: 21.10.2026. Reviewentwurf, nicht genehmigt.** Dieses Dokument bündelt
die Bestandsprüfung zu D-01 bis D-12. Es ändert keine Entscheidung, erteilt
keine Freigabe und erfindet keine Prüfnachweise. Maßgeblich bleibt die
Entscheidungsmatrix in [Abschnitt 10 der Spezifikation](securitychain-p0-specification.md).
Abschnitt 10 wird nicht neu geöffnet; D-01 wurde nicht erneut bearbeitet
(vorhandene Nachweise: D-01-Prüfprotokoll, PR #111).

**Nachtrag 22.10.2026:** Zwei native iOS-Vorschauziele wurden unter `apps/ios/`
ergänzt. Sie implementieren keine Authentifizierung, Geräteverbindung,
Notfallauslösung oder Sensorzugriffe. Dieser Nachtrag ändert keine D-01–D-12-
Freigabe; die iOS-Ziele wurden mangels Xcode nicht nativ gebaut oder abgenommen.

## Ergebnis der Prüfung

Alle in der Matrix genannten Punkte D-02 bis D-12 hängen von Entscheidungen
(Anbieter, Vertrauensmodell, Protokoll, Fristen, Plattformmatrix, Rechtsgrundlagen,
Betriebsmodell, Rollenbesetzung) oder von Betriebs-/Abnahmenachweisen ab, die
im Repository nicht vorhanden sind. Eine Implementierung ohne diese Vorgaben
würde die Freigabegrenzen aus den Abschnitten 8 und 9 verletzen (Eigenentwicklung
von Kryptografie, Scheinauthentifizierung, produktive Dienste). Deshalb wurden
**kein App-/Backend-Code, keine Berechtigungen und keine Workflows geändert.**
Es wurden keine neuen Repositories, Tokens oder kostenpflichtigen Dienste angelegt.

## Status je Punkt

| Punkt | Thema | Status (unverändert) | Technischer Ist-Nachweis | Fehlende menschliche Freigabe / fehlender Nachweis |
| --- | --- | --- | --- | --- |
| D-01 | App-Grenzen | Bereits bearbeitet; Detailfreigaben offen | Getrennte Module/IDs, Test auf Modulisolation | Allowlist je App, Security-/Datenschutzbestätigung |
| D-02 | Authentifizierung | Entscheidung erforderlich | Standard `RejectAllAuthenticator` (fail closed) | Anbieter, Rollen, MFA, Recovery, Tokenvertrag |
| D-03 | Gerätevertrauen | Blockiert / Nachweis fehlt | Keine Registrierungs-Runtime; SQL nur Entwurf | Vertrauensmodell und Lebenszyklus |
| D-04 | Protokoll/Schlüssel | Entscheidung erforderlich | Kein Protokoll implementiert | Versionierter Vorschlag, unabhängiger Kryptografie-Review |
| D-05 | Geräteidentität | Entscheidung erforderlich | Apps verwalten keine Identitätsschlüssel | Keystore-/Keychain-Policy, Rotation, Recovery |
| D-06 | Sitzungen/Widerruf | Entscheidung erforderlich | Keine produktiven Sitzungen | TTL, Widerrufs-SLA, Offlineverhalten |
| D-07 | Transport | Technisch nachgewiesen (nur Ist-Zustand) | Keine BLE-/Netzwerkrechte in beiden Manifesten, Regressionstest | Transportwahl; BLE nur mit separater schriftlicher Freigabe |
| D-08 | Plattformmatrix | Entscheidung erforderlich | `minSdk = 26`, kein iOS-Projekt | OS-/Gerätematrix je App und Plattform |
| D-09 | Einwilligung | Entscheidung erforderlich | Nur deklarative Schemas | Texte, Zweck, Laufzeit, Löschfolgen |
| D-10 | Audit | Entscheidung erforderlich | `UnavailableAuditSink` als Standard | Rechtsgrundlage, Region, Retention, Zugriff |
| D-11 | Betrieb | Blockiert / Nachweis fehlt | Nur lokale Health-Laufzeit, loopback-Compose | Betreiber, TLS/Trust, Monitoring, Backup, Incident |
| D-12 | Unabhängige Prüfung | Entscheidung erforderlich | Nur CI-Ergebnisse | Namentliche Reviewer, Prüfplan, commitgebundene Signoffs |

## Entscheidungsvorlagen D-02 bis D-12

Die Vorlagen sind **Empfehlungen zur gezielten menschlichen Entscheidung**, keine
Freigaben und keine Statusänderung der Matrix in Abschnitt 10. Der belegte
Ist-Zustand beschreibt nur den geprüften Repository-Stand. Eine Freigabe muss
die konkrete Spezifikationsversion, den Daten-/Aktionsumfang und die zuständigen
Rollen benennen. D-01, Abschnitt 10 und der Technical Closeout werden hier nicht
erneut bearbeitet. Für D-02 bis D-12 liegt keine konkrete genehmigte
Implementierungsentscheidung vor; daher werden keine App-/Backend-Code,
Berechtigungen oder Workflows geändert.

### D-02 – Authentifizierung

- **Ist-Zustand:** `RejectAllAuthenticator` lehnt standardmäßig jede Anfrage ab
  ([`backend/ai_support.py`](../backend/ai_support.py#L32-L40)); der Bearer-Eintrag
  ist laut OpenAPI nur reserviert, ohne Aussteller oder Validator
  ([`backend/openapi.yaml`](../backend/openapi.yaml#L57-L66)). Produktive
  Login-/Auth-Routen fehlen ([`backend/README.md`](../backend/README.md#L3-L10)).
- **Fehlende Entscheidung:** Identitätsanbieter und Anmelde-/Recovery-Fluss;
  getrennte App-Rollen und MFA-Regeln; Tokenformat, Aussteller, Zielgruppe,
  App-Scope, Aktionen, Laufzeit, Erneuerung und Widerruf; Datenregion und
  verantwortliche Betreiber.
- **Empfehlung:** Bis zur Auswahl und Prüfung eines Anbieters geschlossen bleiben.
  Einen etablierten Kandidaten anhand der genehmigten Anforderungen vergleichen,
  ohne Anbieter oder Tokenformat vorwegzunehmen. NIKNOLIG und Defense benötigen
  getrennte Credentials; Hochrisiko-Rollen benötigen die in der Spezifikation
  vorgesehene starke MFA.
- **Auswirkungen:** Android benötigt je App einen eigenen freigegebenen
  Anmeldeclient und geschützte Credential-Ablage; Backend muss Identität,
  App-Bereich und konkrete Aktion serverseitig validieren; für iOS gibt es noch
  keine App und später wären eigener Client und eigene Credentials erforderlich.
- **Sicherheit/Datenschutz:** Ungeprüfte Tokens oder gemeinsame App-Sitzungen
  ermöglichen Identitäts-/Bereichsverwechslung. Anbieter, Claims, Region,
  Kontowiederherstellung und MFA-Metadaten erfordern eine Minimierungs- und
  Datenschutzprüfung.
- **Nachweis/Abnahme:** Schriftlich freigegebener Auth-Vertrag samt Anbieter-,
  Rollen-, MFA-, Recovery-, Scope- und Betriebsentscheidung; Security- und
  Datenschutzprüfung; Tests, die fehlende, ungültige, abgelaufene, widerrufene,
  falsch ausgestellte und falsch gescopte Nachweise ablehnen. Erfolgsfälle nur
  mit eigens genehmigten synthetischen Testidentitäten.

### D-03 – Gerätevertrauen

- **Ist-Zustand:** Es gibt keine Registrierungs-API oder Runtime. Die SQL-Datei
  kennzeichnet sich ausdrücklich als nicht anzuwendenden Entwurf
  ([`001_initial_contract.sql`](../backend/migrations/001_initial_contract.sql#L1-L3));
  Apps haben keine Pairing-Runtime
  ([`device-link-security-design.md`](device-link-security-design.md#L15-L18)).
- **Fehlende Entscheidung:** Wie Nutzer, App-Bereich, Installation und
  öffentlicher Schlüssel gebunden werden; Besitznachweis/Challenge,
  Registrierungsberechtigung, Attestierungsbedarf, Neuinstallation,
  Schlüsselwechsel, Verlust und Recovery.
- **Empfehlung:** Je App-Installation eine eigenständige Identität mit frischem
  kryptografischem Besitznachweis vorsehen; IDs, Gerätenamen oder Linkstatus
  allein nicht als Vertrauen werten. Attestierung nicht voraussetzen und den
  SQL-Entwurf bis zu seiner separaten Freigabe unverändert lassen.
- **Auswirkungen:** Android braucht zwei getrennte Registrierungs- und
  Lebenszykluspfade; Backend müsste Challenge und Bindung prüfen und
  Installationsstatus widerrufen können; iOS fehlt und benötigt später eine
  gesondert geprüfte Implementierung.
- **Sicherheit/Datenschutz:** Ohne Besitznachweis drohen Geräte-Spoofing,
  Replay und App-Scope-Übertritt. Installationskennungen und Fingerprints können
  Gerätebeziehungen offenbaren und müssen zweckgebunden sowie minimiert bleiben.
- **Nachweis/Abnahme:** Freigegebenes Vertrauens- und Recovery-Modell von
  Produkt, Security und betroffenen Plattformverantwortlichen; Tests gegen
  gefälschte ID, ungültige/abgelaufene Challenge, Replay, Scope-Wechsel,
  unbestätigten Schlüsselwechsel und widerrufene Installation; physische
  Abnahme auf jeder freigegebenen Plattformkombination.

### D-04 – Protokoll und kryptografische Schlüssel

- **Ist-Zustand:** Es ist kein produktives Geräte-/Sitzungsprotokoll
  implementiert; das Sicherheitsdesign ist ausdrücklich ein Entwurf ohne
  Transportwahl ([`device-link-security-design.md`](device-link-security-design.md#L1-L5)).
  Die Muss-Anforderungen in Abschnitt 3 verbieten Eigenentwicklung von
  Kryptografie und lassen Profil und Parameter offen
  ([Spezifikation](securitychain-p0-specification.md#L147-L154)).
- **Fehlende Entscheidung:** Versionierter Nachrichten-/Sitzungsvertrag,
  etabliertes Protokoll und geprüfte Bibliothek, unterstützte Profile/Parameter,
  Versions- und Downgrade-Verhalten sowie unabhängige Kryptografieprüfung.
- **Empfehlung:** Erst nach Threat-Model- und Anforderungsfreigabe etablierte,
  gepflegte Verfahren vergleichen; kein eigenes kryptografisches Protokoll und
  keine Abhängigkeit vor Security-Prüfung auswählen.
- **Auswirkungen:** Android und künftiges iOS benötigen interoperable,
  getrennte Plattformadapter; Backend muss seine Rolle im Protokoll und die
  versionierten API-Grenzen explizit erfüllen. Keine Plattform kann aus einer
  bloßen Schema- oder Transportverschlüsselung Identität ableiten.
- **Sicherheit/Datenschutz:** Fehler bei Sitzung, Version, Identität,
  Integrität oder Schlüsselbindung gefährden Vertraulichkeit und Aktionen.
  Protokollmetadaten sind auf notwendige Diagnosewerte zu beschränken.
- **Nachweis/Abnahme:** Versionierter Vorschlag mit Threat Model,
  Interoperabilitätsvektoren und begründeten Profilen; unabhängiger
  Kryptografie-Review vor Umsetzung; anschließend Negativtests für falsche
  Identität, Manipulation, Replay, Downgrade und unbekannte Version sowie
  Abnahme auf den genehmigten Plattformen.

### D-05 – Geräteidentitätsschlüssel

- **Ist-Zustand:** Die Apps verwalten keine Identitätsschlüssel; der
  SQL-Entwurf enthält nur einen öffentlichen Fingerprint und untersagt private
  Schlüssel im Backend ([`001_initial_contract.sql`](../backend/migrations/001_initial_contract.sql#L9-L16);
  [`backend/README.md`](../backend/README.md#L60-L66)).
- **Fehlende Entscheidung:** Anforderungen an nicht exportierbare Schlüssel,
  Hardware-Backing und seine Fallbacks, Erzeugung/Registrierung, Rotation,
  Ablauf, Backup/Restore, Neuinstallation, Kompromittierung und Recovery je OS.
- **Empfehlung:** Schlüssel je App-Installation auf dem Gerät erzeugen und in
  den freigegebenen Android-/Apple-Speichern schützen; weder Schlüssel teilen
  noch exportieren. Verlorene oder nicht verifizierbare Identität erst nach
  freigegebener erneuter Prüfung wiederherstellen; Attestierung nicht als
  vorhandene Fähigkeit annehmen.
- **Auswirkungen:** Android braucht getrennte Keystore-Policies und Tests;
  Backend soll nur erforderliche öffentliche Nachweise und Status behandeln;
  eine künftige iOS-App muss Keychain/Secure-Enclave-Fähigkeit separat belegen.
- **Sicherheit/Datenschutz:** Export, Backup oder Cross-App-Wiederverwendung
  kann dauerhaften Zugriff oder Domänenwechsel ermöglichen. Öffentliche
  Fingerprints sind trotz fehlenden privaten Materials potenziell
  verknüpfbare Kennungen.
- **Nachweis/Abnahme:** Freigegebene Plattform-/Schlüsselmatrix inklusive
  Fallbacks, Rotation und Recovery; physische Tests für Erzeugung,
  Nicht-Exportierbarkeit, Neuinstallation, Backup/Restore, Widerruf und
  Schlüsselwechsel; Nachweis, dass keine privaten Schlüssel in Backend,
  Logs oder Testartefakten landen.

### D-06 – Sitzungen und Widerruf

- **Ist-Zustand:** Es gibt keine produktiven Sitzungen oder serverseitige
  Widerrufsprüfung. Ablaufprüfung an einer injizierten `Principal` ist ein
  lokaler Testpfad, kein Sitzungssystem
  ([`backend/ai_support.py`](../backend/ai_support.py#L23-L40);
  [`backend/ai_support.py`](../backend/ai_support.py#L232-L252)).
- **Fehlende Entscheidung:** Token-/Sitzungs-TTL, erneute Authentifizierung,
  Widerrufs-SLA und Durchsetzungsintervall, Zuständigkeit, Offline-Verhalten
  sowie Nutzerablauf bei Ablauf oder Ausfall.
- **Empfehlung:** Vor jeder sensiblen Aktion aktuelle Autorisierung verlangen;
  bei nicht prüfbarem Widerruf oder Backend-Ausfall fail closed. Keine
  automatische Offline-Queue oder Wiederholung sensibler Aktionen. Konkrete
  Fristen und Verfügbarkeit erst nach Produkt-/Betriebsabwägung beschließen.
- **Auswirkungen:** Android muss Ablauf und Widerruf pro App-Sitzung behandeln;
  Backend benötigt eine durchsetzbare Status-/Widerrufsquelle; iOS muss später
  dieselben Vertrags- und Negativfälle abdecken.
- **Sicherheit/Datenschutz:** Unzureichender Widerruf verlängert kompromittierte
  Zugriffe; zu lange Sitzungen erhöhen Folgen eines Geräteverlusts. Sitzungs-
  und Ereignisprotokolle dürfen keine Tokens oder unnötigen Identitätsdaten
  enthalten.
- **Nachweis/Abnahme:** Schriftliche, messbare TTL-/SLA-/Offline-Entscheidung
  mit verantwortlicher Betriebsrolle; Tests für Ablauf, Widerruf, Ausfall,
  Wiederverbindung und Sitzungsende; Nachweis, dass nach Widerruf keine
  sensible Aktion fortgesetzt oder nachträglich abgespielt wird.

### D-07 – Transport

- **Ist-Zustand:** Beide Android-Manifeste haben keine Berechtigungen; es gibt
  keine BLE-Runtime und kein iOS-Projekt. Der Nachweis bezieht sich nur auf
  diesen deaktivierten Ist-Zustand. Die Spezifikation verlangt eine separate
  schriftliche BLE-Freigabe
  ([`Android-Manifeste`](../apps/niknolig/src/main/AndroidManifest.xml#L1-L27);
  [`Android-Defense-Manifest`](../apps/niknolig-defense/src/main/AndroidManifest.xml#L1-L24);
  [`SecurityChain-P0, Abschnitt 6`](securitychain-p0-specification.md#L289-L313)).
- **Fehlende Entscheidung:** Ob und über welchen Transport ein bestimmter,
  genehmigter Daten-/Aktionsfluss überhaupt erfolgen soll; für BLE zusätzlich
  die separate schriftliche Produkt-/Security-Freigabe.
- **Empfehlung:** Den aktuellen Zustand beibehalten: keine Discovery,
  Berechtigung, Pairing-, Netzwerk- oder Fallback-Aktivierung, bis Transport,
  Protokoll und Zweck freigegeben und geprüft sind. Keine Kandidatenwahl wird
  hiermit vorweggenommen.
- **Auswirkungen:** Android bleibt ohne Transport-Runtime; Backend erhält keine
  neue Geräte-/Transport-API; mangels iOS-App gibt es auch dort keine
  Transportfreigabe.
- **Sicherheit/Datenschutz:** Aktivierung ohne Freigabe könnte Geräte,
  Standort-/Discovery-Metadaten oder Nutzdaten offenlegen und würde die
  bestehende Sicherheitsgrenze umgehen.
- **Nachweis/Abnahme:** Der bestehende Regressionstest muss weiterhin fehlende
  BLE-Berechtigungen und iOS-Implementierung bestätigen. Eine spätere
  Transportfreigabe benötigt versionierten Datenfluss, Plattformmatrix,
  Bedrohungs-/Protokollreview und physische Negativtests einschließlich
  MITM/Replay/Wiederverbindung. **Status bleibt technisch nachgewiesen nur für
  den deaktivierten Ist-Zustand.**

### D-08 – Plattformmatrix

- **Ist-Zustand:** Beide Android-Module setzen `minSdk = 26`; iOS-Quellen und
  Deployment-Matrix fehlen
  ([`NIKNOLIG build.gradle.kts`](../apps/niknolig/build.gradle.kts#L44-L50);
  [`Defense build.gradle.kts`](../apps/niknolig-defense/build.gradle.kts#L44-L50);
  [`mobile-cross-platform-architecture.md`](mobile-cross-platform-architecture.md#L3-L5)).
- **Fehlende Entscheidung:** Unterstützte OS-/Geräteversionen pro App,
  Hardwarefähigkeiten, Berechtigungen, Hintergrundverhalten,
  Mindestversionen und jeweilige Ausschluss-/Fehlerzustände.
- **Empfehlung:** Nur Plattformkombinationen zusagen, die für die jeweilige App
  explizit freigegeben und physisch abgenommen sind. Keine Android- oder
  iOS-Fähigkeit aus einer anderen App oder einem Schema ableiten.
- **Auswirkungen:** Android benötigt getrennte Matrizen für beide Apps;
  Backend-Verträge müssen mit deren kleinsten unterstützten Clientversionen
  kompatibel bleiben; iOS bleibt bis zu einer eigenen App- und
  Freigabeentscheidung nicht unterstützt.
- **Sicherheit/Datenschutz:** Zu breite Mindestunterstützung kann
  Sicherheitsupdates oder Permission-Semantik umgehen. Neue OS-Rechte können
  zusätzliche personenbezogene Daten zugänglich machen und bedürfen einer
  Zweckprüfung.
- **Nachweis/Abnahme:** Von Produkt-, Plattform- und Security-Verantwortlichen
  genehmigte App-/OS-/Geräte-/Capability-Matrix; getestete Permission-
  Verweigerung/-Widerruf, unbekannte Fähigkeit und Abbruch auf jeder
  unterstützten physischen Kombination; kein Supportversprechen außerhalb der
  Matrix.

### D-09 – Einwilligung

- **Ist-Zustand:** Die Consent-Schemas sind ausdrücklich deklarativ und nicht an
  eine Runtime gebunden
  ([`device-consent-v1.schema.json`](../backend/contracts/device-consent-v1.schema.json#L1-L20);
  [`electro-engel-multidevice-sensors.md`](electro-engel-multidevice-sensors.md#L30-L47)).
  Es gibt keine Consent-Oberfläche oder Geräteaktion.
- **Fehlende Entscheidung:** Genehmigte Zwecke, Datenkategorien, Quell-/Ziel-
  installation, verständliche Textversionen, Laufzeit, Erneuerung, Widerruf,
  Folgen für laufende Sitzungen und Löschung sowie die rechtliche Grundlage.
- **Empfehlung:** Vor jeder später genehmigten Verarbeitung eine aktive,
  informierte, zweck-/daten-/zielgebundene und befristete Zustimmung verlangen;
  Zweck- oder Zielwechsel erfordern neue Zustimmung. Ein gültiges Schema oder
  OS-Recht ersetzt sie nicht.
- **Auswirkungen:** Android benötigt getrennte, verständliche App-Flows und
  muss Widerruf umsetzen; Backend darf Verarbeitung nur nach Prüfung des
  gültigen, passenden Grants erlauben; eine künftige iOS-App benötigt eigene
  gleichwertige Texte und Flows.
- **Sicherheit/Datenschutz:** Ein Schema-validierter Grant allein beweist weder
  Identität noch wirksame Zustimmung. Zweckfremde oder nach Widerruf fortgesetzte
  Verarbeitung verletzt die festgelegten Daten-/Aktionsgrenzen.
- **Nachweis/Abnahme:** Produkt-/Datenschutz-/Rechtsfreigabe von Zweck,
  Dateninventar, Text, Gültigkeit und Löschfolgen; Tests für grant, deny,
  Ablauf, Widerruf, Ziel-/Zweckwechsel und Widerruf während einer Sitzung;
  nachvollziehbarer Nachweis, dass keine Aktion ohne gültigen Grant erfolgt.

### D-10 – Audit

- **Ist-Zustand:** Das Audit-Schema erlaubt festgelegte Metadaten, keine freien
  Nutzdaten; `UnavailableAuditSink` ist der Standard und es gibt keinen
  genehmigten produktiven Speicher
  ([`consent-audit-event-v1.schema.json`](../backend/contracts/consent-audit-event-v1.schema.json#L1-L20);
  [`backend/ai_support.py`](../backend/ai_support.py#L82-L88)).
- **Fehlende Entscheidung:** Zweck/Rechtsgrundlage, Speicherregion,
  Verantwortliche, zulässige Zugriffsrollen, Manipulationsschutz,
  Aufbewahrung/Löschung sowie Verhalten bei Audit-Ausfall.
- **Empfehlung:** Bis zur Freigabe keinen Audit-Speicher aktivieren. Danach nur
  erforderliche Vertragsmetadaten erfassen; kein Token, Schlüssel,
  Nutzdateninhalt, Sensorrohwert oder Freitext. Pflichtfelder und
  Identifizierbarkeit ausdrücklich gegen Datenschutz und Beweiszweck abwägen.
- **Auswirkungen:** Android und künftiges iOS sollen keine eigenen
  Schatten-Auditlogs oder sensitiven Telemetriedaten erzeugen; Backend bleibt
  ohne genehmigten Sink geschlossen und braucht eine serverseitige, kontrollierte
  Auditgrenze.
- **Sicherheit/Datenschutz:** Auditdaten können trotz Pseudonymisierung
  personenbezogen oder verknüpfbar sein. Zu wenig Schutz gefährdet
  Vorfallnachweise; zu breite Erfassung/Zugriffe gefährden Privatsphäre.
- **Nachweis/Abnahme:** Freigegebenes Dateninventar mit Region, Rechtsgrundlage,
  Zugriff und Retention; Zugriff-/Lösch-/Manipulationsschutz-Nachweise;
  Negativtests auf Geheimnisse und Nutzdaten sowie ein dokumentierter
  Fail-closed-Test bei fehlendem oder ausgefallenem Sink.

### D-11 – Backend-Betrieb

- **Ist-Zustand:** `app.py` ist lokale Vorbereitung; `asgi.py` und eine
  getrennte Health-only-Produktions-Compose-Konfiguration existieren, jedoch ist
  kein Serverdeployment nachgewiesen. `/health/ready` prüft PostgreSQL und
  Migrationen; `/health/live` prüft nur den Prozess
  ([`backend/README.md`](../backend/README.md#L413-L430);
  [`backend/asgi.py`](../backend/asgi.py#L43-L55);
  [`compose.production.yaml`](../backend/compose.production.yaml#L1-L115)).
  Die lokale Datenbankdatei bleibt loopbackgebunden
  ([`compose.yaml`](../backend/compose.yaml#L1-L26)).
- **Fehlende Entscheidung:** Betreiber und Verantwortlichkeiten, Datenregion,
  Verfügbarkeit, TLS-/Trust-Regeln, Secret-Verwaltung, Monitoring,
  Backup/Restore, Incident-/Kontaktweg, Rollback, Kosten und Umgang mit
  Widerruf bei Ausfall.
- **Empfehlung:** Keine Produktivumgebung oder externe Erreichbarkeit aktivieren.
  Betriebsoptionen erst anhand genehmigter Sicherheits-, Datenschutz- und
  Verfügbarkeitsanforderungen vergleichen; keinen Anbieter oder Trust-Modus
  festlegen.
- **Auswirkungen:** Android erhält keine Produktions-URL oder API-Funktion;
  Backend bleibt lokal und ohne Produktabhängigkeiten; iOS besitzt keine
  Laufzeit. Ein späterer Betrieb erfordert serverseitige Autorisierung und
  app-spezifische Grenzen.
- **Sicherheit/Datenschutz:** Ein unfreigegebener Dienst könnte Datenregion,
  Zugriffsschutz, Schlüsselverwaltung und Widerruf unbekannt lassen. Der
  vorhandene Readiness-Status ist kein Produktionsbereitschaftsnachweis.
- **Nachweis/Abnahme:** Benannter Betreiber und freigegebene Architektur,
  Region und Kosten; nach Implementierung verifizierte TLS-/Trust- und
  Zugriffskontrollen, Monitoring/Alarmierung, Backup-Restore, Incident- und
  Rollback-Übung; readiness nur gegen tatsächlich erforderliche freigegebene
  Abhängigkeiten prüfen.

### D-12 – Unabhängige Prüfung und Release-Abnahme

- **Ist-Zustand:** PR #112 dokumentiert 73 erfolgreiche Repository-Tests, weist
  aber ausdrücklich darauf hin, dass sie keine Authentifizierung,
  Geräte-/BLE-Sicherheit, P0-Konformität oder menschliche Freigabe belegen
  (siehe [Testergebnisse](#testergebnisse)). Unabhängige Reviewer,
  iOS-Abnahme und physische Zwei-Geräte-Nachweise sind im Statusregister offen.
- **Fehlende Entscheidung:** Benennung unabhängiger Security-, Plattform-,
  Produkt-, Datenschutz-, Betriebs- und Release-Verantwortlicher; Prüfplan,
  Abweichungsbehandlung und verbindliche Signoffs je App, Version, Commit und
  Artefakt.
- **Empfehlung:** CI-Ergebnisse nicht als Freigabe behandeln. Reviewer müssen
  vom Implementierungsergebnis unabhängig sein; Signoffs an unveränderliche
  Spezifikationsversion, Commit und konkretes Release-Artefakt binden und
  NIKNOLIG/Defense getrennt freigeben.
- **Auswirkungen:** Android benötigt je App reproduzierbare Build-, Negativ-
  und physische Gerätebelege; Backend-Nachweise müssen exakt denselben Commit,
  Vertrag und Betriebsstand betreffen; iOS benötigt vor jeder Freigabe eine
  eigene Plattformabnahme.
- **Sicherheit/Datenschutz:** Ein grüner CI-Lauf kann fehlende menschliche,
  physische oder datenschutzrechtliche Prüfung nicht ersetzen. Testberichte
  müssen redigiert sein und dürfen keine Geheimnisse oder unnötigen Nutzdaten
  enthalten.
- **Nachweis/Abnahme:** Genehmigter, risikobasierter Prüfplan; namentliche
  unabhängige Reviewer und dokumentierte Findings/Dispositionen; commit- und
  artefaktgebundene Testergebnisse, erforderliche physische Geräte- und
  Datenschutz-/Betriebsnachweise sowie getrennte schriftliche Release-
  Freigaben. Keine Gesamtfreigabe, solange ein Pflichtnachweis fehlt.

## Register offener menschlicher Freigaben

Keine der folgenden Freigaben liegt vor; Namen und Daten sind **OFFEN**.

| Rolle | Freigabe für | Punkte |
| --- | --- | --- |
| Produktverantwortliche NIKNOLIG / Defense (je App) | Scope, Nutzerabläufe, Verfügbarkeit | D-01, D-02, D-03, D-06, D-08, D-09 |
| Unabhängige Security-Prüfung | Authentifizierung, Protokoll, Identität, Sitzungen, Transport | D-02 bis D-07, D-12 |
| Datenschutz / Recht | Rechtsgrundlagen, Texte, Audit, Region | D-01, D-09, D-10, D-11 |
| Android-/iOS-/Backend-Verantwortliche | Plattformmatrix, Schlüsselspeicher, Backend | D-03, D-05, D-08 |
| Betreiber / Backend-Betrieb | Betriebsmodell, Monitoring, Backup, Incident, Kosten | D-10, D-11, D-12 |
| Release-Verantwortliche | Abnahme je App an Version/Commit/Artefakt gebunden | D-12 |

## Vorlage für einen späteren Freigabenachweis

Die folgende leere Vorlage strukturiert die bereits in Abschnitt 10 und D-12
geforderten Nachweise. Sie ist weder eine Freigabe noch ein neu beschlossener
Freigabeprozess. Je betroffener App ist ein eigener Nachweis erforderlich; eine
Freigabe für NIKNOLIG gilt nicht für NIKNOLIG Defense und umgekehrt.

| Feld | Eintrag |
| --- | --- |
| Entscheidungspunkt(e) | `[D-01 … D-12]` |
| App-/System-Scope und ausdrücklich ausgeschlossene Scopes | `[NIKNOLIG / NIKNOLIG Defense / Backend / Plattform; konkretisieren]` |
| SecurityChain-P0-Version | `[Version/Stand]` |
| Spezifikations- und Implementierungs-Commit | `[Commit-SHA(s)]` |
| Betroffenes Release-Artefakt, falls vorhanden | `[Identität und Hash oder nicht anwendbar mit Begründung]` |
| Zuständige Entscheidungsfunktion und Name | `[Rolle und verantwortliche Person]` |
| Unabhängigkeit, falls für diese Prüfung erforderlich | `[Bestätigung und Bezug zur Implementierung]` |
| Entscheidung, genauer Umfang und etwaige Vorbehalte | `[Eintragen; offene Punkte nicht als genehmigt behandeln]` |
| Review-, Test-, Datenschutz-, Betriebs- und Abnahmenachweise | `[Referenzen und Findings-Disposition, soweit für den Scope erforderlich]` |
| Datum und Referenz des schriftlichen Nachweises | `[Eintragen]` |

Die zuständigen Personen, Rollenbesetzung, Unabhängigkeit, Signatur-/Dokumentations-
und Aufbewahrungsform sowie der Freigabeprozess bleiben **OFFEN**. Diese Vorlage
legt dafür keine Werte oder Mechanismen fest. Ein nicht ausgefülltes Feld,
fehlender Pflichtnachweis oder eine nicht dokumentierte Entscheidung schließt
keinen Blocker und erteilt keine Implementierungs- oder Produktivfreigabe.

## Testergebnisse

Ausgeführt am 21.10.2026 im Verzeichnis `backend`:
`python -m unittest discover -s tests` → **73 Tests, OK** (inkl. Matrix-
Vollständigkeit, Statuszuordnung, fehlende BLE-Berechtigungen/iOS-Projekte,
Modulisolation). Diese Tests belegen Repository-Invarianten, **nicht**
Authentifizierung, Autorisierung, BLE-Sicherheit, P0-Konformität oder
menschliche Freigabe. Android-Builds wurden nicht neu ausgeführt, da keine
Android-Quellen geändert wurden. Der dokumentierte Testlauf stammt aus PR #112;
für diese reine Dokumenterweiterung wurde er nicht wiederholt.
