# SecurityChain-P0 – verbindlicher Sicherheitsstandard (Reviewentwurf)

**Status:** Reviewentwurf, Version 0.6; noch nicht genehmigt oder produktiv
verbindlich

**Geltung nach Freigabe:** Sicherheitsgate für NIKNOLIG, NIKNOLIG Defense,
künftige iOS-Clients, Backend und jede Geräte-/Datenverbindung

**Aktueller Effekt:** Keine Implementierungs-, Konto-, Transport-, Daten- oder
Produktivfreigabe. Bis zur schriftlichen Freigabe gelten alle bestehenden
Sicherheitsgrenzen und Stop-Gates unverändert.

Dieser Entwurf bündelt und präzisiert vorhandene Sicherheitsregeln. Er ersetzt
keine bestehende Regel stillschweigend. Bei Widerspruch, fehlendem Nachweis oder
ungeklärter sicherheitsrelevanter Entscheidung gilt bis zu einer ausdrücklich
reviewten Klärung die restriktivere Regel und **fail closed**. Eine Änderung der
geltenden Baseline erfordert eine versionierte, begründete und menschlich
freigegebene Änderung dieses Dokuments.

## 1. Zweck, Umfang und Bestandsgrenzen

SecurityChain-P0 definiert Mindestanforderungen für Identität, Authentifizierung,
Autorisierung, Schlüssel- und Sitzungslebenszyklus, Datenschutz, Fehlerverhalten,
Tests und Freigabe. Der Scope umfasst:

- Anmeldung und Zugriff auf künftig genehmigte Backend-Operationen;
- Identität einer App-Installation und eines Kommunikationspartners;
- Pairing, Gerätewechsel, Sitzungen und etwaige Sensor-/Datenfreigaben;
- Datenflüsse zwischen App, Backend und einem ausdrücklich freigegebenen
  Zielgerät;
- Audit-, Diagnose- und Betriebsdaten sowie Schlüssel, Tokens und Recovery;
- Build-, Test- und menschliche Release-Freigaben, soweit sie diese Funktionen
  ermöglichen.

NIKNOLIG und NIKNOLIG Defense sind getrennte Apps, Installationen,
Application-IDs, Identitäts- und Sicherheitsdomänen. Elektro-Engel ist eine
Systemfunktion des NIKNOLIG-Systems, keine dritte App oder Berechtigungsdomäne.
NIKNOLIG umfasst allgemeine Systemfunktionen; NIKNOLIG Defense zusätzliche
Sicherheits- und Notfallfunktionen. Elektro-Engels Infrastruktur-Erkennung und
Reparaturhinweise gehören ausschließlich zu Defense; die normale NIKNOLIG-App
erhält keine Infrastruktur-Erkennung. Diese bestätigte Produktgrenze ist keine
Implementierungs- oder Datenfreigabe (siehe D-01 in Abschnitt 10). Gemeinsame
Schemas oder Bibliotheken begründen keine gemeinsame Identität und gewähren
keine Rechte.

Der Repository-Bestand ist kein produktives Sicherheitssystem: Die Android-Apps
haben keine Geräteverbindung oder Pairing-Laufzeit; iOS-Apps sind nicht
vorhanden. Das Backend bietet lokal Health-Routen und den standardmäßig
gesperrten `POST /v1/ai/support`-Testendpunkt; lokale Tests prüfen Mock-Erfolg,
Zugriffskontrolle und standardmäßige Sperre. Produktive Login-, Geräte-,
Pairing- und Produkt-APIs existieren nicht. Eine vorhandene API-Fläche oder ein
lokaler Test belegt weder Betriebsfreigabe noch P0-Konformität oder eine
Sicherheitsfreigabe.

### Produktionsfunktionen – aktueller Bestand

Die folgenden Punkte sind Bestandsfeststellungen, keine Implementierungs- oder
Freigabeaussage:

- **Token-Ausstellung und produktive Authentifizierung:** Es gibt keinen
  Identitätsanbieter, Login-/Token-Aussteller oder produktiven Token-Validator.
  Der lokale Support-Testendpunkt verwendet standardmäßig einen Authenticator,
  der alle Anfragen ablehnt; injizierbare Testimplementierungen ersetzen keine
  produktive Authentifizierung.
- **Geräteidentität:** Es gibt keine Registrierungs-API, Challenge-Prüfung,
  Geräte-/Installationsschlüsselverwaltung oder Peer-Authentifizierung. Die
  SQL-Migration ist ein nicht angewendeter Entwurf.
- **Autorisierung:** Es gibt keine produktive, allgemeine serverseitige
  Policy-Durchsetzung für Produktoperationen. Lokale Support-Testlogik prüft
  injizierte Testprinzipale und App-/Feature-Bereiche, ist aber kein produktives
  Identitäts- oder Autorisierungssystem.
- **Backend-Infrastruktur:** Neben der lokalen Laufzeit existiert eine getrennte,
  health-only FastAPI-/Compose-Produktionskonfiguration mit PostgreSQL-Prüfung
  und statischer TLS-Proxy-Konfiguration. Sie ist nicht auf einem Server
  nachgewiesen oder freigegeben. Domain/DNS, Zertifikatserneuerung,
  Host-Firewall, Produktionsbetrieb, Secret-Rotation, Monitoring, Backup/Restore
  und Incident-Verfahren sind weiterhin nicht nachgewiesen oder eingerichtet.

Alle diese Funktionen bleiben blockiert, bis die einschlägigen Entscheidungen
dieses Dokuments freigegeben und Umsetzung sowie Abnahme nachgewiesen sind.
Weder die Vorschläge unten noch die vorhandenen Verträge erlauben einen
Produktivbetrieb.

## 2. Threat Model und Vertrauensgrenzen

### Zu schützende Werte und Ziele

- Nutzer-, App- und Installationsidentitäten sowie private Schlüssel und
  Zugangsnachweise;
- zweckgebundene Zustimmungen, Rollen, Aktionen und Daten, einschließlich
  Profil-, Sensor- und Geräteinformationen;
- Integrität, Vertraulichkeit und korrekte Zielzuordnung jeder Nachricht;
- Widerruf, Audit-Metadaten und Verfügbarkeit sicherheitskritischer Funktionen.

### Bedrohungen

Der Entwurf berücksichtigt mindestens:

- fremde, verlorene, gestohlene oder kompromittierte Geräte und Installationen;
- gefälschte Discovery, Peer-/App-Verwechslung, Cross-App-Verwechslung und
  unberechtigte Rollen- oder Aktionsausweitung;
- Netzwerkangreifer, manipulierte Nachrichten, Replay, Duplikate,
  Downgrade, falsche Versionen und übergroße Eingaben;
- gestohlene, abgelaufene oder widerrufene Zugangsnachweise, Schlüsselverlust
  sowie Wiederherstellung oder Neuinstallation ohne gültige Neuverifikation;
- abgelaufene, widerrufene oder zweckfremde Zustimmung sowie OS-Berechtigungs-
  verweigerung oder -widerruf;
- Prozess-, Transport-, Backend- oder Netzwerkabbrüche, veraltete Sitzungen,
  automatische Wiederholung und nicht autorisierte Offline-Ausführung;
- übermäßige Datenerfassung, unsichere Speicherung, übermäßig detaillierte
  Logs/Fehler und unberechtigten Audit-Zugriff;
- Fehlbedienung, fehlerhafte Konfiguration und kompromittierte Abhängigkeiten
  oder Betriebszugänge.

Vertrauensgrenzen bestehen zwischen jeder App-Sandbox, Betriebssystem und
Hardware-Sicherheitsfunktionen, Backend/API, Transport, Daten-/Audit-Speicher,
Build-/Releaseprozess und menschlichen Freigaben. Gerätename, Discovery,
Installations-ID, TLS/verschlüsselte Übertragung, OS-Pairing und eine
Schema-validierte Nachricht sind für sich allein kein Nachweis von App-Identität,
Autorisierung oder Zustimmung.

Angreifer mit Kontrolle über ein Gerät/OS oder einen freigegebenen
Backend-Betrieb können Schutzmaßnahmen dieser Komponente beeinträchtigen.
Umfang, Erkennungs- und Recovery-Anforderungen für solche Kompromittierungen
sind in der Risikoentscheidung ausdrücklich zu behandeln; sie gelten nicht als
automatisch ausgeschlossen oder durch Attestierung gelöst.

## 3. Normative Sprache, Muss- und Abbruchkriterien

In diesem Entwurf bezeichnet **MUSS** eine Voraussetzung für die spätere
Freigabe. **MUSS abgebrochen/abgelehnt werden** bezeichnet ein
Fail-closed-Ergebnis. Anforderungen werden erst nach den Freigaben in Abschnitt
10 verbindlich. Offene Werte sind als **OFFEN** markiert und dürfen nicht durch
Implementierungsdefaults, UI-Texte oder Transportverhalten entschieden werden.

### Verbindliche Muss-Anforderungen nach Freigabe

1. **MUSS** jede Identität, Berechtigung, Aktion, Datenklasse, Zielinstallation
   und jeder Zweck explizit begrenzt und serverseitig beziehungsweise am
   jeweiligen durchsetzenden Vertrauenspunkt geprüft werden.
2. **MUSS** jede App eigene Credentials, App-Scope-Zuweisungen, Installations-
   identitäten und Sitzungen verwenden. NIKNOLIG-Rechte dürfen nicht in Defense
   gelten und umgekehrt. Ein Link, eine Rolle oder ein Gerätebesitz erteilt
   keine zusätzliche Aktionserlaubnis.
3. **MUSS** jede sensible Freigabe konkret, informiert, aktiv, zweck- und
   zielgebunden, widerrufbar und zeitlich begrenzt sein. Nutzerzustimmung ersetzt
   keine OS-Berechtigung; eine OS-Berechtigung ersetzt weder Zustimmung noch
   Autorisierung.
4. **MUSS** Geräteidentität durch einen verifizierten kryptografischen
   Besitznachweis an eine registrierte App-Installation gebunden sein.
   Anzeigename, übermittelte ID, Discovery oder Transport-Pairing allein reichen
   nicht.
5. **MUSS** ein geprüftes, etabliertes Protokoll gegenseitige Authentifizierung,
   Vertraulichkeit, Integrität, Sitzungsfrische und Replay-Schutz gewährleisten.
   Es darf keine selbst entwickelte Kryptografie eingesetzt werden. Protokoll,
   Profile und Parameter bleiben bis zur Freigabe **OFFEN**.
6. **MUSS** jede Nachricht an Protokollversion, Sitzung, Absender, Ziel,
   erlaubte Aktion und aktuelle Autorisierung gebunden sein. Eingabegrößen,
   Zeitlimits und Aktions-Allowlist sind zu begrenzen.
7. **MUSS** bei unbekannter/inkompatibler Version, fehlender oder ungültiger
   Identität, Berechtigung, Zustimmung oder Integrität, Replay, Widerruf,
   Ablauf, Bereichsabweichung oder nicht eindeutigem Zustand abgelehnt und die
   betroffene Sitzung beendet werden.
8. **MUSS** eine Wiederverbindung Peer-Identität und Berechtigung erneut prüfen.
   App-Neustart, Gerätewechsel, Schlüsselwechsel, Ablauf und Widerruf dürfen
   nicht stillschweigend Vertrauen wiederherstellen.
9. **MUSS** ein Widerruf weitere Aktionen sperren, laufende Sitzungen beenden
   und betroffene Credentials/Vertrauensbeziehungen invalidieren. Das zulässige
   technische Durchsetzungsintervall und der Widerrufs-SLA sind **OFFEN** und
   vor Produktfreigabe messbar festzulegen.
10. **MUSS** ein Authentifizierungs-, Autorisierungs-, Integritäts- oder
    Sicherheitsfehler ohne schwächeren Fallback, Offline-Warteschlange oder
    automatische Wiederholung sensibler Aktionen behandelt werden.
11. **MUSS** Datenerhebung und Aufbewahrung auf ausdrücklich genehmigte Zwecke
    minimieren. Schlüssel, Tokens, Zugangscodes, Nutzdaten und unnötige
    personenbezogene Informationen dürfen nicht in Logs, Fehlerantworten,
    Telemetrie, Testberichten oder CI-Artefakten erscheinen.
12. **MUSS** alle sicherheitskritischen Entscheidungen durch automatisierte
    Negativtests und unabhängige menschliche Prüfung belegt werden. Ein
    erfolgreicher Build oder Vertragstest allein genügt nicht.

### Harte Abbruch-/Stop-Kriterien

Jeder folgende Fall blockiert die betroffene Operation und, wenn die
Vertrauensgrenze betroffen ist, die gesamte Sitzung:

- P0-Version, Threat Model, Daten-/Aktionsumfang oder erforderliche
  Freigabeentscheidung fehlt, ist widersprüchlich oder nicht überprüfbar;
- Identität, App-Bereich, Rolle, Ziel, Zweck, Einwilligung, Schlüsselstatus
  oder aktuelle Berechtigung lässt sich nicht eindeutig validieren;
- ungültiger, unbekannter, abgelaufener, widerrufener oder zurückgestufter
  Schlüssel, Token, Peer, Consent oder Protokollzustand;
- Replay, Duplikat sicherheitsrelevanter Nachricht, Integritätsfehler,
  unerwarteter Peer, Downgrade oder Protokollabweichung;
- OS-Recht wird verweigert/widerrufen, Capability ist unbekannt oder eine
  freigegebene Daten-/Aktionsgrenze wird überschritten;
- Schlüsselverlust, Geräteverlust, bestätigter Kompromiss oder nicht sicher
  abschließbare Recovery;
- Transport-/Backend-Ausfall, Timeout oder Teilantwort bei einer Aktion, deren
  Ergebnis nicht sicher bestimmbar ist;
- unerwartete Datenpersistenz, Nutzdaten in Logs oder fehlende Lösch-/Retention-
  Kontrolle;
- ein Pflicht-Test, Security-Review, Geräte-Abnahmekriterium oder unabhängiger
  Freigabeschritt schlägt fehl oder fehlt.

Ein Stop wird nicht durch erneuten Versuch, Wechsel auf BLE, TLS-only,
schwächere Authentifizierung, alternative App-Identität oder manuelle
Kontoeingabe umgangen. Fortsetzung erfordert Fehlerbehebung, erneute Prüfung und
gegebenenfalls frisches, beidseitig bestätigtes Pairing.

## 4. Authentifizierung, Autorisierung und Geräteidentität

### Authentifizierung

- Jede spätere API- und Geräteoperation MUSS einen authentisierten Akteur und
  einen app- und installationsgebundenen Kontext nachweisen. Kontoauthentisierung
  und Gerätebesitznachweis sind getrennte Prüfungen.
- Zugriffsnachweise MÜSSEN kurzlebig, widerrufbar und an Aussteller, Zielgruppe,
  App-Bereich, Installation und minimale erlaubte Aktionen gebunden sein.
  Format, Aussteller/IdP, Ablaufwerte, Erneuerung und Gerätebindung sind
  **OFFENE** Entscheidungen.
- Administrative Konten und hochriskante Rollen MÜSSEN individuell und mit
  verpflichtender starker Mehr-Faktor-Authentifizierung geschützt werden.
  Phishing-resistente Passkeys/Sicherheitsschlüssel sind das dokumentierte
  Ziel; zulässige Verfahren und Recovery sind freizugeben. Rollenvergabe und
  hochriskante Policy-Änderungen benötigen einen unabhängigen zweiten
  approvierenden Verantwortlichen.
- Ein gemeinsamer Login, ein gemeinsames App-Token oder eine appübergreifende
  Sitzung ist unzulässig. Nutzer-/Identitätsanbieter und Prüfmerkmale sind
  **OFFEN**.

### Autorisierung

Jede Operation MUSS die konkrete Kombination aus Akteur, App-Bereich,
Installation, Ressource, Aktion, Zielinstallation, Zweck, gültiger Zustimmung,
Ablauf und Widerrufsstatus prüfen. Backend-Entscheidungen müssen serverseitig
durchgesetzt werden; UI, lokale Zustände, Rollenname, gültiges Token,
Geräteschlüssel, Linkstatus oder valides Schema ersetzen diese Entscheidung
nicht.

Für jedes Produkt sind vor Freigabe eine explizite Allowlist von Aktionen und
Daten, Richtung, Rollen, Nutzerzustimmung, Berechtigungsumfang und
Fehlerverhalten zu beschließen. „Defense“, „Administrator“ oder
„Elektro-Engel“ sind für sich keine Berechtigung.

### Geräte- und Installationsidentität

Jede Installation MUSS eine eigene, nicht exportierbare private Identität
besitzen. Der Peer-Nachweis MUSS kryptografisch an diese Installation, den
App-Bereich und eine frische Sitzung gebunden sein. Schlüsselwechsel,
Neuinstallation, Backup/Restore und Gerätewechsel erfordern eine festgelegte
Neuprüfung und dürfen keine alte Vertrauensbeziehung übernehmen.

Challenge-/Nonce-Verfahren, Schlüsselalgorithmus, Geräteattestierung,
Hardware-Backing und Zuordnung einer Nutzeridentität zur Installation sind
**OFFEN**. Attestierung ist kein Ersatz für Authentifizierung oder
Autorisierung und darf nicht als vorhandene Fähigkeit vorausgesetzt werden.

## 5. Schlüsselverwaltung, Widerruf und erneute Authentifizierung

- Private Installationsschlüssel MÜSSEN auf dem jeweiligen Gerät erzeugt und
  dort durch Android Keystore beziehungsweise Apple Keychain/Secure Enclave
  geschützt werden, soweit die freigegebene Plattform dies unterstützt.
  Private Schlüssel dürfen das Gerät nicht verlassen, nicht in Logs oder
  Backups gelangen und nicht zwischen Apps geteilt werden.
- Algorithmen, Parameter, hardwaregestützte Schlüsselanforderungen,
  Attestierungsprofile, Speicherklassifizierung, Token-TTL und Rotationsfristen
  sind **OFFEN**; sie müssen durch Security Review festgelegt und von
  unterstützten Plattformen nachweisbar erfüllt werden.
- Rotation MUSS eine autorisierte, frische Besitzprüfung erfordern. Alte
  Schlüssel werden nach erfolgreicher Umstellung widerrufen; ein ungeklärter
  Schlüsselwechsel beendet die Vertrauensbeziehung.
- Bei Verlust, Diebstahl, Kontokompromiss, vermuteter Schlüsselkopie oder
  Recovery MUSS die Installation gesperrt, die betroffene Sitzung beendet und
  das zugehörige Credential/Peer-Pairing widerrufen werden. Recovery darf
  Identitätsprüfung, App-Scope, MFA oder Zustimmung nicht herabstufen.
- Vor der Ausführung jeder sensiblen Aktion MUSS eine erneute Authentifizierung
  erfolgen. Eine bestehende Sitzung oder ein vorheriger Consent darf diese
  Prüfung nicht überspringen.
- Erneute Authentifizierung und Autorisierungsprüfung sind zusätzlich nach
  Ablauf, Wiederverbindung, Prozess-/App-Neustart, Geräte-/Schlüsselwechsel,
  Scope-Wechsel, Widerruf und sicherheitsrelevantem Berechtigungswechsel
  erforderlich. Diese Lebenszyklusprüfungen ersetzen nicht die Prüfung vor
  einer sensiblen Aktion.
- Widerrufsverteilung, maximale Durchsetzungsverzögerung, Offline-Verhalten und
  Recovery-Freigabe sind **OFFEN**. Ohne erreichbare und gültige
  Widerrufsentscheidung dürfen keine neuen sensiblen Aktionen ausgeführt
  werden. Eine sichere Wiederherstellung verlangt erneute Identitätsprüfung
  und ausdrückliche Bestätigung der betroffenen Installationen.

## 6. Transport: BLE ausschließlich nach separater Freigabe

BLE/GATT ist **nicht freigegeben**, weder durch diesen Entwurf noch durch
vorhandene Berechtigungen, UI-Texte oder dokumentierte Transportkandidaten.
Vor Auswahl oder Implementierung sind eine eigene, schriftliche
Security-/Produktfreigabe und eine Ergänzung dieser Spezifikation erforderlich.
Bis dahin darf keine App BLE-Rechte, Discovery, Pairing oder Datentransfer dafür
aktivieren.

Eine etwaige spätere BLE-Freigabe MUSS mindestens dokumentieren:

- konkrete Datenflüsse, Rollen, unterstützte Geräte/OS-Versionen und
  BLE-/GATT-Berechtigungen je Plattform;
- Authentisierung und kryptografische Bindung des App-Peers unabhängig vom
  Gerätenamen, der BLE-Adresse, Discovery, GATT-Pairing oder Link-Layer;
- Protokoll-/Kryptografie-Review, Schutz gegen MITM, Replay, Downgrade,
  Verbindungsübernahme, Gerätewechsel und Wiederverbindung;
- Grenzen von Reichweite/Discovery, Hintergrundverhalten, Permission-Verweigerung
  und -Widerruf sowie beobachtbare Abbruchzustände;
- Tests gegen fremde Geräte, manipulierte Werbung, Verbindungsabbruch und
  Wiederverbindung auf jeder freigegebenen physischen Plattformkombination.

BLE-Verschlüsselung oder OS-Pairing allein erfüllt weder Geräteidentität,
Nutzerzustimmung, Aktionsautorisierung noch P0. Bei Nichterfüllung bleibt BLE
deaktiviert; es gibt keinen schwächeren Fallback.

## 7. Datenschutz, Logging und sichere Fehlerbehandlung

### Datenminimierung und Aufbewahrung

Vor einer Datenerhebung MUSS ein freigegebenes Inventar Datenklasse, Zweck,
Quelle, Empfänger, Sensitivität, Rechtsgrundlage/Einwilligung, lokale und
serverseitige Verarbeitung sowie Löschung abbilden. Keine nicht freigegebene
Profil-, Sensor-, Standort-, Audio-, Bild- oder Geräteinformation darf erfasst,
übertragen oder persistiert werden. Sensor-Rohdaten bleiben bis zu einer
separaten Entscheidung lokal und flüchtig; ein Schema allein genehmigt keine
Übertragung.

Aufbewahrungsfristen, Speicherorte/Regionen, Audit-Zugriffsrollen, Löschfristen
und rechtliche Verantwortlichkeiten sind **OFFEN** und vor dem jeweiligen
Datenfluss festzulegen. Bis dahin wird keine neue persistente Speicherung oder
Nutzdatenübertragung genehmigt. Widerruf muss auch festgelegte Folgelöschung
und deren Nachweis berücksichtigen; konkrete Fristen bleiben eine
Freigabeentscheidung.

### Protokollierung

Logs dürfen nur erforderliche, minimierte Sicherheitsmetadaten enthalten:
Ereignistyp, pseudonyme Akteur-/Installationsreferenz, App-Bereich, Ergebnis,
Zeit und zufällige Korrelations-ID. Keine Tokens, Passwörter, MFA-Codes,
privaten Schlüssel, Nonces/Challenge-Geheimnisse, vollständigen Nachrichten,
Sensorrohwerte oder unnötigen personenbezogenen Inhalte. Zugriff,
Manipulationsschutz, Aufbewahrung und Löschung der Audit-Daten sind vor
Inbetriebnahme zu genehmigen.

Für einen ausdrücklich freigegebenen Consent-Audit-Datensatz müssen zusätzlich
die Pflichtfelder des versionierten Audit-Vertrags erhalten bleiben,
insbesondere `contractVersion`, `eventId`, `eventType`, `consentId`,
Akteur-/Zielinstallationsreferenz und App-Bereich, `purposeCode`, `occurredAt`
und `correlationId` (derzeit
[`consent-audit-event-v1.schema.json`](../backend/contracts/consent-audit-event-v1.schema.json)).
Die Freigabe muss deren Identifizierbarkeit, Zugriff und Aufbewahrung bewerten.
Der Vertrag autorisiert selbst keine Protokollierung; sind Pflichtfelder nicht
vertretbar, muss der Audit-Vertrag versioniert angepasst werden, bevor er
verwendet wird. Weitere Nutzdaten oder Freitext bleiben ausgeschlossen.

### Fehler und Verfügbarkeit

Fehlerantworten MÜSSEN stabilen maschinenlesbaren Codes folgen und dürfen keine
Stacktraces, internen Hosts, Konfigurationen, Zugangsdaten, Schlüssel oder
Payload-Kopien offenlegen. Eine Korrelations-ID dient nur der Diagnose; sie ist
kein Authentifizierungs-, Autorisierungs- oder Wiederholungsnachweis.
Unbekannte, ungültige oder fehlende sicherheitskritische Werte werden
abgelehnt. Ein interner Fehler liefert eine allgemeine Antwort und beendet
betroffene Sitzungen, wenn Integrität oder Autorisierung nicht verlässlich
festgestellt werden kann. Es gibt kein automatisches Wiederholen sensibler
Schreib-, Geräte- oder Sensoraktionen.

## 8. Getrennte Anforderungen nach Plattform und Systembereich

| Bereich | Anforderungen |
| --- | --- |
| **Android – NIKNOLIG** | Eigene App-/Installationsidentität, OS-geschützte Schlüssel und eigene Credentials. Nur einzeln genehmigte Manifest-/Laufzeitrechte; Zustimmung und Permission bei Zweck-/Zielwechsel erneut prüfen. Defense-Daten und -Credentials bleiben unzugänglich. |
| **Android – NIKNOLIG Defense** | Vollständig eigener Authentifizierungs-, Schlüssel-, Consent-, Release- und Audit-Scope. Kein NIKNOLIG-Token, Schlüssel, Shared-Preferences, impliziter Link oder Elektro-Engel-Recht. Berechtigungen und Aktionen sind unabhängig zu genehmigen. |
| **iOS – NIKNOLIG und künftig Defense** | Keine bestehende iOS-Runtime voraussetzen. Jede künftige App erhält eigene Bundle-/App-Identität, Credentials, Keychain/Secure-Enclave-Integration, Berechtigungsdialoge, Consent, Release- und Testfreigabe. Getrennte Apps teilen weder Schlüssel noch Sitzungen. Plattformparität ist durch dieselben versionierten Verträge und Negativfälle zu belegen. |
| **Backend** | Lokal existieren Health-Routen und der standardmäßig gesperrte `POST /v1/ai/support`-Testendpunkt; Tests verwenden lokale Mocks. Das ist keine Betriebsfreigabe und kein Produktiv-API- oder Auth-System. Vor Betrieb: versionierte API, TLS-/Vertrauensregeln, serverseitige Autorisierung je Operation, token- und install-scope, Widerruf, Rate-/Payload-Limits, minimiertes Audit, sichere Fehler und Betriebs-/Incident-Verantwortung freigeben. Keine App erhält Datenbankzugriff. |
| **NIKNOLIG Defense (Produkt-/Sicherheitsdomäne)** | Keine impliziten Rechte aus NIKNOLIG, gemeinsamem Backend, Person, Gerät, Link oder Core. Jede bereichsübergreifende Daten- oder Aktionsbeziehung benötigt einen ausdrücklich genehmigten Zweck, beide betroffenen App-Scopes und unabhängige Tests; andernfalls ist sie ausgeschlossen. |

Für iOS gibt es derzeit weder App noch Implementierung. Für beide Android-Apps
fehlen Geräte-/Pairing-Laufzeit und App-Tests. Diese Spezifikation autorisiert
keine Implementierung, Berechtigungsänderung, Dependency, API, Konten,
Deployments oder Releases.

## 9. Test-, Abnahme- und Freigabekriterien

Alle Tests verwenden synthetische Daten und eigens freigegebene, nichtproduktive
Testidentitäten. Keine produktiven Schlüssel, Tokens, Nutzerdaten oder
kostenpflichtigen Dienste. Testnachweise werden Build/Commit, Vertragsversion,
Geräte-/OS-Version und Prüfer zugeordnet und redigiert aufbewahrt.

### Vorgelagerte Freigabe von Spezifikation und Testplan

Vor Implementierungsbeginn müssen die konkrete Spezifikationsversion und der
dazugehörige Testplan geprüft und schriftlich freigegeben sein. Dafür sind keine
bestandenen Implementierungs- oder Gerätetests vorausgesetzt. Das bestehende
P0-Stop-Gate bleibt bis zu dieser Freigabe und den weiteren offenen
Produkt-/Sicherheitsentscheidungen bestehen.

### Automatisierte Prüfungen – Nach Implementierung als Nachweis für P0-Konformität

1. **Verträge und Versionen:** Gemeinsame gültige/ungültige Fixtures gegen
   Backend, Android und iOS; unbekannte kritische Versionen/Felder,
   falsche App-Bereiche, Pflichtfeld-, Größen- und Null-/Enum-Grenzen ablehnen.
2. **AuthN/AuthZ:** Nicht authentisiert, falscher Aussteller/Zielbereich,
   falsche Rolle/Aktion/Richtung/Zielinstallation, fehlender/abgelaufener/
   widerrufener Consent und unzulässige Cross-App-Zugriffe ablehnen.
3. **Geräte-/Schlüsselidentität:** Fremder Peer, gefälschte ID, falscher oder
   rotierter Schlüssel ohne Zustimmung, abgelaufene Challenge, Replay,
   Duplikat, Downgrade und veraltete Sitzung ablehnen.
4. **Lebenszyklus:** Ablauf, Widerruf, Recovery, Geräteverlust, Neuinstallation,
   Schlüsselrotation und erneute Authentifizierung einschließlich Sitzung
   beenden, Berechtigung entziehen und keine automatische Wiederaufnahme.
5. **Datenschutz/Fehler:** Berechtigungsverweigerung/-widerruf, übergroße oder
   ungültige Payload, Timeout, Abbruch, Offlinezustand und Backendfehler;
   keine sensible Aktion, Queue, unzulässiger Retry oder sensible Log-/Fehler-
   ausgabe.
6. **Grenzen:** Je App isolierte Credentials/Sandboxes und gezielte
   Cross-App-Negativtests. Keine automatisierte Prüfung darf geheime oder
   produktive Credentials benötigen.

Diese Prüfungen und die nachfolgende Plattform-/Geräteabnahme sind Nachweise
für P0-Konformität und Voraussetzung für Produkt-/Releasefreigabe; sie sind
keine Voraussetzung für den vorgelagerten Implementierungsbeginn.

### Plattform- und physische Abnahme

- Jede freigegebene Android- und iOS-Kombination benötigt Tests auf unterstützten
  physischen Geräten mit dokumentiertem Modell, OS-Version, App-Build und
  Signaturidentität.
- Für Geräteverbindung: beidseitige Zustimmung, Peer-Verifikation, Ablehnung
  fremder Geräte/Aktionen, Permission-Nein/-Widerruf, Pairing-Abbruch, Timeout,
  Offline-/Netzwechsel, Prozessneustart, Wiederverbindung nach erneuter
  Authentifizierung und expliziter Widerruf.
- Für jede freigegebene Sensor-/Datenfähigkeit: tatsächliche Capability und
  Zweckbindung, minimale Erfassung, keine nicht freigegebene Übertragung sowie
  Abbruch bei Consent-/OS-Permission-Widerruf prüfen.
- Emulatoren, Schema-/Unit-Tests, CI, APK- oder App-Store-Builds ersetzen keine
  physische Abnahme. Ein Test mit nur einer App, nur einem Gerät oder nur
  erfolgreichem Ablauf reicht nicht.

### Annahmebedingungen

SecurityChain-P0 darf erst als erfüllt gekennzeichnet werden, wenn **alle**
folgenden Nachweise vorliegen:

- alle offenen Entscheidungen aus Abschnitt 10 sind entschieden, versioniert
  und mit Eigentümer/Begründung dokumentiert;
- unabhängiges Security Review bestätigt Threat Model, Protokoll, Umsetzung,
  Widerruf, Fehlerverhalten, Datenflüsse und Grenzen;
- automatisierte Vertrags-, Missbrauchs-, App-Isolations- und
  Lebenszyklustests sind erfolgreich und nachvollziehbar dem geprüften Stand
  zugeordnet;
- erforderliche physische Geräteprüfungen, Datenschutz-/Löschkontrollen,
  Betriebs-/Incident-Verfahren und unterstützte Plattformmatrix sind
  dokumentiert und bestanden;
- keine P0-Stop-Kriterien sind offen; Abweichungen besitzen keine ungeprüfte
  Ausnahme;
- die erforderlichen menschlichen Freigaben sind schriftlich für exakt dieselbe
  Spezifikationsversion und denselben Implementierungs-/Release-Stand erteilt.

## 10. Offene Entscheidungen und menschliche Freigaben

Jeder Punkt ist ein Blocker bis zur dokumentierten Entscheidung. Eine
ausbleibende Antwort ist keine Zustimmung. Die Tabelle nennt die erforderliche
Entscheidungsfunktion, nicht bereits benannte oder zustimmende Personen. Rollen
müssen für den jeweiligen Scope ausdrücklich besetzt und dokumentiert werden;
wo mehrere Funktionen betroffen sind, sind alle erforderlichen Freigaben nötig.

### Entscheidungsmatrix D-01 bis D-12

**Stand:** Technische Bestandsprüfung des Repository-Commits
`47dbab6f09a74dfa03a599eba50f6f82c51d735c` (20.10.2026).
Der Status bezeichnet den Stand des technischen Nachweises beziehungsweise der
Entscheidungsvorbereitung, nicht den Abschluss der Entscheidung. Ein technischer
Nachweis schließt keine menschliche Freigabe ab. Für alle zwölf Punkte fehlen
weiterhin vollständige Freigaben. Die ergänzend bestätigte Produktgrenze für
D-01 vom 21.10.2026 ist unten mit Quelle und verbleibenden Lücken dokumentiert;
weitergehende Zustimmung einer Rolle oder Person wird nicht angenommen.

| ID | Status | Technischer Ist-Zustand und Nachweis | Fehlender Nachweis | Risiko | Verantwortliche Rolle | Optionen, notwendige Tests und nächster Schritt |
| --- | --- | --- | --- | --- | --- | --- |
| D-01 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Getrennte Android-Module, Application-IDs und Backend-App-Bereiche ohne gegenseitige Modulabhängigkeit (`settings.gradle.kts`, beide `apps/*/build.gradle.kts`, `backend/ai_support.py`). Produktgrenzen am 21.10.2026 im Korrekturauftrag bestätigt: NIKNOLIG allgemein; Defense zusätzlich Sicherheit/Notfall; Infrastruktur-Erkennung und Reparaturhinweise durch Elektro-Engel ausschließlich in Defense. Detailnachweise siehe D-01-Prüfprotokoll unten. | Konkrete Akteure, Ressourcen, Datenzugriffe, Aktions-Allowlist und Richtungen je App sowie Security-/Datenschutzbestätigung bleiben offen. | Produktgrenze allein könnte fälschlich als Sensor-, Cross-App- oder Automationsfreigabe gelesen werden. | Produktverantwortliche je App; Security und Datenschutz für betroffene Datenklassen. | Bestätigte Produktgrenzen übernehmen, nicht neu entscheiden. Bis zur bestätigten Allowlist keine neuen Produktoperationen freigeben. Tests danach: erlaubte Aktionen positiv sowie falsche App, Aktion, Richtung, Ziel und Ressource negativ prüfen. Nächster Schritt: offene Punkte des D-01-Prüfprotokolls bestätigen lassen. |
| D-02 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Kein Login, Identitätsanbieter, produktiver Token-Aussteller oder produktiver Validator. `backend/ai_support.py` verwendet standardmäßig `RejectAllAuthenticator`; injizierte Principals und UUIDs sind lokale Test-Fixtures. | Anbieter, Identitätsprüfung, Rollen, MFA, Recovery und Tokenvertrag fehlen. | Ein selbst gewähltes oder nur syntaktisch geprüftes Token wäre keine Authentifizierung; schwache Recovery kann Konten übernehmen lassen. | Produkt- und Security-Verantwortliche; Identitäts-/Backend-Verantwortliche; Datenschutz/Betreiber für Anbieter und Region. | Optionen erst nach Scope- und Risikoentscheidung vergleichen (z. B. etablierter OIDC-kompatibler Anbieter versus kein Login bis zur Freigabe); keinen Anbieter vorwegnehmen. Tests: fehlend, ungültig, falscher Aussteller/Zielgruppe/Scope, abgelaufen und widerrufen ablehnen; erfolgreiche Prüfung nur mit kontrollierter Testidentität. Nächster Schritt: Anforderungen und Anbieterprüfung freigeben. |
| D-03 | BLOCKIERT / NACHWEIS FEHLT | Keine Installationsregistrierungs-API, Challenge-/Schlüsselprüfung oder Peer-Authentifizierung. SQL-Datei ist ein ausdrücklich nicht anzuwendender Entwurf; Apps besitzen keine entsprechende Runtime. | Bindung von Nutzer, Installation, App-Scope und Schlüssel sowie Registrierungs-/Recovery-Prozess fehlen. | Gefälschte IDs oder übernommene Schlüssel könnten fremde Geräte legitimieren. | Security-, Android-, iOS- und Backend-Verantwortliche; Produktverantwortliche für Registrierung/Recovery. | Optionen für Besitznachweis und ggf. Attestierung erst plattformübergreifend prüfen. Tests: gefälschte ID, falscher/abgelaufener Challenge, Replay, App-Scope-Wechsel und nicht genehmigter Schlüsselwechsel ablehnen. Nächster Schritt: Vertrauensmodell und Lebenszyklus entscheiden, dann separat implementieren und prüfen. |
| D-04 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Kein produktives Authentifizierungs- oder Sitzungsprotokoll ist implementiert oder freigegeben; es gibt keine Protokoll-/Kryptografie-Review-Nachweise. | Protokoll, Algorithmen, Parameter, Versionierung und unabhängiger Review fehlen. | Eigenentwickelte Kryptografie oder falsch konfigurierte Standardverfahren können Identität, Integrität und Vertraulichkeit gefährden. | Unabhängige Security-Prüfung und technische Verantwortliche für Backend und jede betroffene Plattform; Produktverantwortliche für Nutzerabläufe. | Etablierte, gewartete Verfahren vergleichen; keine Eigenentwicklung. Tests nach Auswahl: Protokollvektoren, falsche Identität, Integritätsfehler, Replay, Downgrade und Versionswechsel. Nächster Schritt: versionierten Protokollvorschlag unabhängig prüfen lassen. |
| D-05 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Die Apps erzeugen/verwalten keine Geräteidentitätsschlüssel; das vorgeschlagene SQL-Modell enthält nur öffentlichen Fingerabdruck und Identitätsstatus, keine privaten Schlüssel. | Hardware-Backing, Attestierung, Rotation, Ablauf, Recovery, Neuinstallation und Kompromissbehandlung sind nicht spezifiziert oder getestet. | Ein verlorener, kopierter oder nicht widerrufener Schlüssel könnte dauerhaften unberechtigten Zugriff ermöglichen. | Security-, Plattform- und Identitätsverantwortliche; Produktverantwortliche für Recovery und Nutzerfolgen. | Android Keystore und Apple Keychain/Secure Enclave getrennt bewerten; Attestierung nur als optionale, geprüfte Ergänzung. Tests je Plattform: nicht exportierbarer Schlüssel, Rotation/Widerruf, Verlust, Neuinstallation und Backup/Restore ohne Vertrauensübernahme. Nächster Schritt: Policy und unterstützte Plattformfähigkeit festlegen. |
| D-06 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Keine produktiven Sitzungen, Token-TTLs, Reauthentifizierung oder serverseitige Widerrufsprüfung existieren. Der lokale Support-Testpfad validiert nur eine injizierte Test-Principal-Ablaufzeit. | TTL, Reauth-Ereignisse, Widerrufs-SLA, Verteilung und Offlineverhalten sind offen. | Ohne frische Widerrufsentscheidung könnten entzogene Rechte fortbestehen; zu strenge Verfügbarkeit kann Funktionen blockieren. | Security-, Identitäts- und Backend-Betriebsverantwortliche; Produktverantwortliche für Verfügbarkeit/Nutzerfolgen. | Vorgeschlagene Fail-closed-Prüfung vor sensiblen Aktionen und keine Offline-Queue mit Betriebsfähigkeit abgleichen. Tests: Ablauf, Widerruf, Backend nicht erreichbar, Wiederverbindung und Sitzungsende. Nächster Schritt: messbare Fristen und Verantwortlichkeit beschließen. |
| D-07 | TECHNISCH NACHGEWIESEN | In beiden Android-Manifesten gibt es keine BLE-/Netzwerkberechtigungen; Quellstand enthält keine BLE-Runtime. Die Spezifikation erklärt BLE/GATT ausdrücklich für nicht freigegeben; es gibt kein iOS-Projekt. | Ein Transport und eine Geräte-/OS-Matrix sind nicht ausgewählt. | Die spätere Transportwahl ohne Prüfung könnte Geräte ausschließen oder unzureichende Schutzmaßnahmen aufweisen. | Produkt- und Security-Verantwortliche sowie betroffene Android-/iOS-Verantwortliche; für BLE separate schriftliche Freigabe. | BLE bleibt deaktiviert. Kein Implementierungspfad oder Fallback wird gewählt. Regressionstest: keine BLE-Permissions, keine unfreigegebene Transportaktivierung; nach einer späteren Freigabe zusätzlich MITM/Replay/Downgrade, Abbruch, Wiederverbindung und physische Geräte je Matrix testen. Nächster Schritt: Transportentscheidung und separate BLE-Freigabe dokumentieren. |
| D-08 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Android-Module setzen derzeit `minSdk = 26`, deklarieren aber keine BLE-/Sensorrechte; keine iOS-App oder iOS-Deployment-Matrix ist vorhanden. | Unterstützte OS-/Gerätematrix, Berechtigungen, Hintergrundverhalten und Hardwarefähigkeiten sind nicht entschieden. | Unklare oder zu breite Unterstützung kann Berechtigungen überfordern oder auf nicht getesteten Geräten scheitern. | Android-/iOS- und Produktverantwortliche je App; Security für Identitäts-/Berechtigungsannahmen. | Matrix pro Plattform/App festlegen; nur notwendige Berechtigungen anfordern. Tests: unterstützte/unsupported Version, Permission-Verweigerung und Widerruf, Capability unbekannt und Hintergrund-/Abbruchverhalten. Nächster Schritt: Produktmatrix mit Plattformverantwortlichen beschließen. |
| D-09 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Vorhandene Consent- und Audit-JSON-Schemas sind deklarativ; Consent ist nicht an eine Runtime gebunden. Keine App-Consent-Oberfläche oder Geräteaktion existiert. | Texte, Zweck-/Datenumfang, Gültigkeitsdauer, Erneuerung, Widerruf und Löschung fehlen. | Schema-Gültigkeit ohne wirksame Zustimmung könnte nicht genehmigte Datenverarbeitung oder Aktionen zulassen. | Produkt- und Datenschutzverantwortliche sowie technische Verantwortliche; Rechts-/Datenschutzprüfung der Texte und Zwecke. | Consent je Zweck/Ziel/Datensatz spezifizieren und keine Datenaktion ohne gültige Zustimmung. Tests: grant/deny/expire/revoke, Zweck-/Zielwechsel, fehlender Consent und Widerruf während Sitzung. Nächster Schritt: Texte, Laufzeit und Löschfolgen freigeben. |
| D-10 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Consent-Audit-Schema erlaubt nur festgelegte Metadaten; lokaler Supportpfad nutzt einen injizierten In-Memory-Auditsink, Standard ist `UnavailableAuditSink`. Kein produktiver Speicher oder Retention-Mechanismus ist eingerichtet. | Rechtsgrundlage, Region, Aufbewahrung/Löschung, Rollen/Zugriff und manipulationsgeschützte Speicherung fehlen. | Unkontrollierte Logs könnten sensible Inhalte offenlegen oder notwendige Vorfallnachweise verlieren. | Datenschutz-/Rechtsverantwortliche, Backend-Betrieb und jeweilige Produktverantwortliche. | Metadaten minimiert halten; Speicher-/Retention-Optionen erst nach Region/Zugriff/Cost-Freigabe vergleichen. Tests: keine Tokens, Schlüssel, Prompts oder Payloads in Logs; Zugriff, Retention, Löschung und Audit-Ausfall fail closed prüfen. Nächster Schritt: Dateninventar und Audit-Policy genehmigen. |
| D-11 | BLOCKIERT / NACHWEIS FEHLT | Health-only-ASGI- und separate Produktions-Compose-Konfiguration existieren; Serverdeployment, bestätigte API-URL und externe TLS-/DNS-Prüfung sind nicht belegt (`backend/asgi.py`, `backend/compose.production.yaml`). | Betriebsmodell, Datenregion, Verantwortliche, Verfügbarkeit, Secret-Rotation, Monitoring/Alarmierung, Incident-Kontakt, freigegebene Backup-Aufbewahrung, getesteter Restore und Rollback sind unbelegt. | Ein produktiver API-Betrieb ohne Betriebs-/Recovery-Nachweise gefährdet Verfügbarkeit, Widerruf und Vorfallreaktion. | Backend-Betrieb und Security; Produktverantwortliche für Verfügbarkeit; Datenschutz/Recht für Region/Aufbewahrung. | Keine Produktionsumgebung oder kostenpflichtige Dienste aktivieren. Host/DNS/TLS und Betriebs-/Datenschutzanforderungen freigeben lassen; anschließend TLS/Trust, Restore, Monitoring, Incident- und Rollback-Übung nachweisen. |
| D-12 | ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH | Workflowläufe belegen automatisierte Builds/Tests für einzelne Commits; sie benennen keine unabhängigen Security-Reviewer oder physischen Abnahmeverantwortlichen. Dieser Repository-Stand enthält keine iOS-App oder Zwei-Geräte-Abnahme. | Unabhängigkeit, namentliche Rollen, Prüfumfang und version-/commitgebundene menschliche Signoffs fehlen. | CI-Erfolg ohne unabhängige Prüfung und verantwortliche Freigabe könnte als unbelegter Produktionsnachweis missverstanden werden. | Betreiber und unabhängige Security-Prüfung; Produkt-, Plattform- und Release-Verantwortliche je App. | Signoffs an exakte Spezifikationsversion, Commit und Artefakt binden; getrennte Freigaben je App. Tests/Nachweise: Reviewprotokoll, reproduzierbare automatisierte Ergebnisse, physische Geräteabnahme und Release-Identität. Nächster Schritt: Rollen besetzen, Prüfplan genehmigen, Nachweise erfassen. |

**Klassifikation und Abschluss:** „TECHNISCH NACHGEWIESEN“ bestätigt ausschließlich
den jeweils genannten Ist-Zustand; es ist keine Zustimmung zur Transportauswahl.
„BLOCKIERT / NACHWEIS FEHLT“ markiert fehlende Implementierung oder
Betriebs-/Abnahmeevidenz. „ENTSCHEIDUNG DURCH MENSCHEN ERFORDERLICH“ markiert
Policy- und Freigabefragen, die nicht aus Quellcode abgeleitet werden können.
Keine D-01–D-12-Entscheidung ist durch diese Bestandsprüfung geschlossen.
NIKNOLIG und NIKNOLIG Defense bleiben getrennte Scopes. iOS bleibt eine offene
Integration; es wird weder eine iOS-Implementierung noch eine Validierung
behauptet.

**Technischer Abschluss von Abschnitt 10 (20.10.2026):** D-07 ist der einzige
Punkt mit einem abgeschlossenen technischen Nachweis; BLE bleibt deaktiviert.
Für D-03 und D-11 fehlen Vertrauens- beziehungsweise Betriebsentscheidungen und
Nachweise. Ihre Implementierung oder ein produktiver Betrieb würde die
Freigabegrenzen aus den Abschnitten 8 und 9 verletzen. Für D-01, D-02, D-04 bis
D-06 sowie D-08 bis D-10 und D-12 sind die in der Matrix benannten
Produkt-, Sicherheits-, Datenschutz-, Plattform- und Betriebsentscheidungen
weiterhin erforderlich. Damit ist die technische Bestandsprüfung dieses
Abschnitts vollständig, nicht aber SecurityChain-P0 freigegeben oder erfüllt.

Der Regressionstest
`BackendContractTests.test_security_decision_matrix_covers_all_decisions_without_closing_them`
prüft Vollständigkeit und Klassifikation der zwölf Matrixzeilen. Ein weiterer
Test prüft die Statuszuordnung und den technischen Abschluss; ein weiterer
prüft die derzeit fehlenden BLE-Berechtigungen und iOS-Projektdateien.
Diese Repository-Invarianten sind keine Tests der Authentifizierung,
Autorisierung, BLE-Sicherheit, P0-Konformität oder menschlichen Freigabe.

### Erforderliche Freigaben

Vor einer späteren Verbindlichkeit sind mindestens zu dokumentieren: Freigabe
des NIKNOLIG-Produktverantwortlichen, des NIKNOLIG-Defense-Verantwortlichen für
ihren Scope, eines unabhängigen Security-Reviewers, der Datenschutz-/Rechts-
verantwortlichen, der Android-/iOS-/Backend-Verantwortlichen für ihre Bereiche
und einer Release-verantwortlichen Person. Namen, Rollenbesetzung,
Unabhängigkeit und Freigabeprozess sind **OFFEN**. Freigabe einer App erteilt
keine Freigabe der anderen App.

### D-01-Prüfprotokoll: bestätigte Produktgrenzen und offene Detailfreigaben

**Stand: 21.10.2026. D-01 ist nicht abgeschlossen.** Die Produktabgrenzung ist
bestätigt und hier dokumentiert; die vollständige fachliche Aktions-/Daten-
Allowlist und die erforderlichen Security-/Datenschutzbestätigungen fehlen.
Diese Punkte werden nicht stillschweigend nach D-02 bis D-12 verschoben, um
D-01 zu schließen.

**Entscheidungsquelle:** Korrekturauftrag „D-01 VOLLSTÄNDIG ABSCHLIESSEN“ vom
21.10.2026 für dieses Monorepo, Abschnitt 2: „NIKNOLIG: allgemeine
Systemfunktionen“, „NIKNOLIG Defense: zusätzliche Sicherheits- und
Notfallfunktionen“, „Elektro Engel: Infrastruktur-Erkennung und Reparaturhinweise
ausschließlich in Defense“ und „Keine Infrastruktur-Erkennung in der normalen
NIKNOLIG-App“. Dies bestätigt die Produktzuordnung, nicht deren technische
Umsetzung, konkrete Eingriffsrechte oder eine unabhängige Sicherheitsabnahme.

#### Festgelegter Funktionsumfang je App

| App / Bereich | Bestätigter Produktumfang | Belegter Stand und Ausschlüsse |
| --- | --- | --- |
| NIKNOLIG (`niknolig`) | Allgemeine Systemfunktionen; die vorhandene lokale Assistenz-/Lernprofil-Vorschau und der Support bleiben davon getrennt beschriebener Bestand. | `MainActivity.kt`, `AssistantActivity.kt`, `LearningProfileActivity.kt` und `SupportActivity.kt` unter `apps/niknolig/src/main/java/com/niknolig/app/`: lokale Anfrageanzeige ohne KI-Antwort/Übertragung, app-lokales Profil mit Stil, optionalen Feedbackzählern und manuell gespeicherter Sitzungszusammenfassung; bestätigtes Zurücksetzen und nutzerbestätigter externer E-Mail-Entwurf. Keine Infrastruktur-Erkennung; aus der Elektro-Engel-Oberfläche folgt kein Recht auf Defense-Funktionen. |
| NIKNOLIG Defense (`niknolig-defense`) | Zusätzliche Sicherheits- und Notfallfunktionen. Elektro-Engels Infrastruktur-Erkennung und Reparaturhinweise ausschließlich hier. Reparaturhinweise sind keine Freigabe automatischer Reparaturen oder Steuerbefehle. | `MainActivity.kt`, `LearningProfileActivity.kt` und `SupportActivity.kt` unter `apps/niknolig-defense/src/main/java/com/niknolig/defense/` belegen lokale Profil-/Support-Vorschau, nicht Infrastruktur-Erkennung, Reparaturhinweise oder eine Notfall-Runtime. Einzelne Erkennungs-, Warn- und Eskalationsabläufe sind noch offen; keine Zuverlässigkeits-, Zustell- oder Sicherheitsgarantie. |

„Zusätzlich“ bezeichnet Defense-Funktionsklassen, keinen gemeinsamen Account,
keinen Zugriff auf die andere Sandbox und keine automatische Übernahme aller
NIKNOLIG-Funktionen. Elektro-Engel bleibt eine Systemfunktion, keine dritte App
und kein neues Repository. Die lokale Vorschau in NIKNOLIG ist keine
Infrastruktur-Erkennung und wird durch diese Dokumentation nicht verändert.

#### Vollständigkeitsprüfung der D-01-Entscheidungspunkte

| Prüfpunkt zu D-01 | Vorhandene Entscheidung / Nachweis | Ergebnis und noch erforderliche Bestätigung |
| --- | --- | --- |
| Produktzwecke und App-Zuordnung | Obiger Korrekturauftrag; getrennte Identitäten bereits in `settings.gradle.kts` und beiden App-Builddateien. | **BESTÄTIGT:** allgemeine Funktionen in NIKNOLIG; zusätzliche Sicherheit/Notfall und Infrastruktur-Erkennung/Reparaturhinweise in Defense; keine Infrastruktur-Erkennung in NIKNOLIG. |
| Akteure und Verantwortlichkeiten je App | `founder-roles-and-account-requirements.md` enthält app-gebundene Rollenvorschläge, keine vergebenen Rollen. | **OFFEN:** konkrete Nutzer-/Administrationsakteure, Rollenbesetzung und zulässige Aufgaben je Funktion bestätigen; Gründerstatus gewährt keinen Inhalts-/Sensorzugriff. Bezug D-02/D-12 ohne deren Abschluss. |
| Ressourcen, Datenklassen und Datenzugriffe je App | Lokale Profil-/Supportquellen belegen nur den Bestand. Consent-/Sensorschemas in `backend/contracts/` sind deklarative Entwürfe. | **OFFEN:** konkrete Infrastrukturarten, Eingaben/Ergebnisse, Ressourcen und zulässige Lese-/Schreibzugriffe je Akteur und Zweck. Keine neue Datenklasse durch die Produktzuordnung freigegeben. |
| Erlaubte Aktionen und Berechtigungen | Keine gegenseitige Modulabhängigkeit; beide Android-Manifeste deklarieren keine Berechtigungen. | **OFFEN:** fachliche Aktions-Allowlist je App, OS-/Sensor-/Netzwerkrechte und Autorisierung pro Ressource. Keine Sensoraktivierung, Überwachung oder Steuerung aus Namen, Profil oder Schema ableiten. Bezug D-03/D-08/D-09. |
| Richtungen, Ziele und App-übergreifende Beziehungen | `device-link-security-design.md` ist ein gesperrter Entwurf; kein implementierter App-Datenaustausch. | **OFFEN:** ob und welche Quelle, Zielinstallation, Empfänger und Richtung je Daten-/Aktionsfluss zulässig sind. Bis dahin keine neue Übertragung, kein Pairing und kein Cross-App-Zugriff. Bezug D-03/D-04/D-07/D-09. |
| Automatische Aktionen und Notfallabläufe | `BUSINESSPLAN.md` beschreibt mögliche Hilferuf-/Eskalationsanforderungen ausdrücklich ohne Produktionsfreigabe. | **OFFEN:** Auslöser, Nutzerbestätigung, Warnung/Eskalation, Abbruch, Fehlalarm, Offlineverhalten und Verantwortlichkeit je Defense-Aktion. Keine automatische Reparatur, Alarmierung, Wiederholung oder Datenweitergabe freigegeben. Bezug D-06/D-09. |
| Datenschutz und Datenlebenszyklus | Sensorplanung, `LEGAL-CHECKLIST.md` und `AGB-ENTWURF.md` verlangen Zweckbindung und Prüfung; sie sind keine Datenschutzfreigabe. | **OFFEN für beide Apps:** Rechtsgrundlagen, Einwilligungstexte/-dauer, Empfänger/Region, lokale/externe Verarbeitung, Speicherung, Aufbewahrung/Löschung, Widerruf und Audit-Zugriff. Bezug D-09/D-10/D-11. |
| Bestätigungen und Abnahmenachweise | Die Produktzuordnung ist durch den Korrekturauftrag bestätigt. Matrix und bisheriger technischer Abschluss in PR #109/#110 schließen keine menschlichen Freigaben. | **OFFEN:** vollständige Scope-Bestätigung je App durch Produktverantwortliche und für betroffene Daten/Aktionen durch Security und Datenschutz; Rolle, Datum, Dokumentversion und Freigabeumfang nachvollziehbar festhalten. Technische Tests ersetzen diese Bestätigungen nicht. Bezug D-12. |

**Übernommene Entscheidungen und Evidenz:** Die Matrix und ihr technischer
Abschluss aus [PR #109](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/109)
und [PR #110](https://github.com/nikolausnold/NIKNOLIG-Monorepo/pull/110) bleiben
Grundlage. Deren PR-Beschreibungen und die geprüften PR-Kommentare enthalten
keine weitergehende D-01-Freigabe. Getrennte Apps/Identitäten, keine impliziten
Rechte, deklarative Verträge und bestehende Stop-Gates werden übernommen,
nicht neu erfunden. Frühere allgemeine Zuordnungen zu „NIKNOLIG“ in der
Architekturplanung sind keine Freigabe der Infrastruktur-Erkennung in der
normalen App; hierfür gilt die oben bestätigte Defense-Grenze. Preisvorgaben
aus dem Businessplan werden nicht neu entschieden oder verändert.

**Abschlusskriterium:** D-01 darf erst auf abgeschlossen gesetzt werden, wenn
alle offenen Zeilen dieses Prüfprotokolls für beide Apps entweder konkret
entschieden oder ausdrücklich als nicht zum Scope gehörend bestätigt sind
und die zugehörigen Produkt-/Security-/Datenschutzbestätigungen vorliegen.
Noch nicht festgelegte Einzelheiten dürfen nicht als Allowlist gelten.
Nach späterer Implementierung bleiben die bereits vorgesehenen positiven und
negativen Autorisierungstests sowie unabhängigen Abnahmen eigene Gates.
D-02 bis D-12 bleiben mit unverändertem Status offen; D-07 ist weiterhin nur
technisch nachgewiesen, keine Transportfreigabe. An SecurityChain-P0-Technik,
App-Code, Berechtigungen und Laufzeitverhalten wird nichts geändert.

## 11. Versionierung und Änderungssteuerung

| Version | Status | Änderung |
| --- | --- | --- |
| 0.1 | Reviewentwurf, nicht genehmigt | Initialer SecurityChain-P0-Entwurf |
| 0.2 | Reviewentwurf, nicht genehmigt | Consent-Audit-Pflichtmetadaten und unbesetzte Entscheidungsfunktionen präzisiert; keine Freigabe oder Änderung der Implementierungsgrenzen |
| 0.3 | Reviewentwurf, nicht genehmigt | Nicht bindende Vorschläge, Begründungen, Risiken und Freigaben für D-01 bis D-12 ergänzt; fehlende Produktionsfunktionen ausdrücklich dokumentiert |
| 0.4 | Reviewentwurf, nicht genehmigt | D-01 bis D-12 mit technischen Bestandsnachweisen, offenen Nachweisen, Risiken, Rollen, Prüfoptionen und nächsten Schritten einzeln klassifiziert; Backend-Regressionstests prüfen Matrixvollständigkeit und BLE-/iOS-Iststand; keine menschliche Freigabe ergänzt |
| 0.5 | Reviewentwurf, nicht genehmigt | Technischen Abschluss von Abschnitt 10 und weiterhin offene Produkt-/Sicherheits-/Betriebsentscheidungen präzisiert; Regressionstest prüft Statuszuordnung; keine menschliche Freigabe ergänzt |
| 0.6 | Reviewentwurf, nicht genehmigt | Bestätigte D-01-Produktgrenzen vom 21.10.2026, Funktionsumfang je App, Einzelpunkt-/Nachweisprüfung und Abschlusskriterien dokumentiert; D-01 bleibt mangels Detailbestätigungen offen, D-02 bis D-12 unverändert; keine technische oder produktive Freigabe |

Diese Datei ist ein Reviewentwurf. Reviewkommentare und Entscheidungen müssen
als nachvollziehbare Änderung mit Versions-/Änderungshistorie, betroffenen
Anforderungen, Risikoauswirkung und erneutem menschlichem Signoff festgehalten
werden. Änderungen an einer genehmigten P0-Regel dürfen Anforderungen nicht
still abschwächen; bis erneute Prüfung/Freigabe gilt die zuletzt genehmigte
Regel, bei Unsicherheit fail closed.

Verwandte Bestandsdokumente:

- [Geräteverbindungs-Sicherheitsdesign](device-link-security-design.md)
- [Android-/iOS-Architektur und Integrationsplan](mobile-cross-platform-architecture.md)
- [Gerätewechsel- und Sensorverträge](electro-engel-multidevice-sensors.md)
- [Backend-Grundlage und bestehende Sicherheitsgrenzen](../backend/README.md)
- [Gesamtstatus und Freigaberegister D-01 bis D-12](securitychain-d01-d12-abschlussstatus.md)
- [Getrennte Gründerrollen und Kontoanforderungen](founder-roles-and-account-requirements.md)
- [Master-Integrationsplan: Sicherheit und Datenschutz](MASTER-INTEGRATION-PLAN.md#6-sicherheit-und-datenschutzrisiken)

### Rückverfolgbarkeit der Anforderungen

| Themen im Entwurf | Bestehende Grundlage |
| --- | --- |
| App-Grenzen, P0-Blockade, Transport-/Geräteabnahme | [Geräteverbindungs-Sicherheitsdesign](device-link-security-design.md) |
| Authentifizierung, Autorisierung, API-/Plattformgrenzen und Vertragsprüfungen | [Android-/iOS-Architektur](mobile-cross-platform-architecture.md) und [Backend-Grundlage](../backend/README.md) |
| Threat Model, Consent, Geräteidentität, Widerruf, Sensor-/Datengrenzen und physische Tests | [Gerätewechsel- und Sensorverträge](electro-engel-multidevice-sensors.md) |
| Getrennte Admin-Rollen, MFA-Ziel, Dual-Control, Recovery und Audit-Metadaten | [Gründerrollen und Kontoanforderungen](founder-roles-and-account-requirements.md) |
| Geheimnisse, minimale Logs, Datenschutzfreigabe und Produktionsänderungs-Gates | [Master-Integrationsplan](MASTER-INTEGRATION-PLAN.md#6-sicherheit-und-datenschutzrisiken) |

Die Tabellenzuordnung dokumentiert Herkunft und Abgleich, nicht die Übernahme
unbestätigter Entscheidungen als geltende Policy. Konkrete offene Werte bleiben
in Abschnitt 10 zu entscheiden.

Diese Spezifikation ist keine Rechtsberatung, Zertifizierung,
Penetrationstestbestätigung oder Freigabe für produktive Nutzung.
