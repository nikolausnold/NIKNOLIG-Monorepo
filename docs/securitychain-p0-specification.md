# SecurityChain-P0 – verbindlicher Sicherheitsstandard (Reviewentwurf)

**Status:** Reviewentwurf, Version 0.2; noch nicht genehmigt oder produktiv
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
NIKNOLIG-Systemfunktion, keine dritte App oder Berechtigungsdomäne. Gemeinsame
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

| ID | Offene Entscheidung / erforderlicher Nachweis | Erforderliche Entscheidungsfunktion (Person noch zu benennen) |
| --- | --- | --- |
| D-01 | Verbindlicher Produktzweck, Akteure, Datenklassen, erlaubte Aktionen und Datenrichtungen je App. | Produktverantwortliche von NIKNOLIG und NIKNOLIG Defense, jeweils nur für ihren Scope |
| D-02 | Login-/Identitätsanbieter, Identitätsprüfung, Nutzer-/Adminrollen, MFA-Verfahren und Recovery. | Produkt- und Security-Verantwortliche; Identitäts-/Backend-Verantwortliche für die technische Ausgestaltung |
| D-03 | Registrierung/Verifikation von App-Installationen, Peer-Vertrauen und Zuordnung zu Nutzerkonto/App-Scope. | Security- sowie jeweilige Android-/iOS-/Backend-Verantwortliche |
| D-04 | Geprüftes Authentifizierungs-/Sitzungsprotokoll, Algorithmen/Parameter, Versionierung und Kryptografie-Review. | Unabhängige Security-Prüfung und technische Verantwortliche der betroffenen Plattformen/des Backends |
| D-05 | Hardware-Backing/Attestierung, Schlüsselrotation, Ablauf, Recovery, Neuinstallation und Verlust-/Kompromissverfahren. | Security- und jeweilige Plattform-/Identitätsverantwortliche |
| D-06 | Token-/Sitzungslaufzeiten, Reauthentifizierungsereignisse und messbarer Widerrufs-SLA. | Security-, Identitäts- und Backend-Betriebsverantwortliche |
| D-07 | Erlaubte Transportoptionen und Plattform-/Gerätematrix. BLE nur mit eigener dokumentierter Freigabe gemäß Abschnitt 6. | Produkt- und Security-Verantwortliche sowie betroffene Plattformverantwortliche; BLE benötigt separate Freigabe |
| D-08 | OS-Mindestversionen, Berechtigungen, Hintergrundverhalten und je App benötigte Hardwarefähigkeiten. | Jeweilige Android-/iOS- und Produktverantwortliche |
| D-09 | Consent-Texte, Dauer, Erneuerung, Widerruf und Löschverhalten je Zweck/Datenklasse. | Produkt- und Datenschutzverantwortliche sowie betroffene technische Verantwortliche |
| D-10 | Rechtsgrundlage/Datenschutzverantwortung, Datenregion, Aufbewahrungs- und Löschfristen sowie Audit-Zugriffsrollen. | Datenschutz-/Rechtsverantwortliche und Backend-Betriebsverantwortliche |
| D-11 | Backend-Betrieb, API-Basis/Trust, Monitoring, Incident-Kontakt, Backup/Restore und Rollback. | Backend-Betriebs-/Security-Verantwortliche und Produktverantwortliche |
| D-12 | Unabhängige Prüfer, technische Abnahmeverantwortliche und Release-/Produktverantwortliche je App. | Unabhängige Prüfer sowie jeweilige Produkt-, Plattform- und Release-Verantwortliche |

Vor einer späteren Verbindlichkeit sind mindestens zu dokumentieren: Freigabe
des NIKNOLIG-Produktverantwortlichen, des NIKNOLIG-Defense-Verantwortlichen für
ihren Scope, eines unabhängigen Security-Reviewers, der Datenschutz-/Rechts-
verantwortlichen, der Android-/iOS-/Backend-Verantwortlichen für ihre Bereiche
und einer Release-verantwortlichen Person. Namen, Rollenbesetzung,
Unabhängigkeit und Freigabeprozess sind **OFFEN**. Freigabe einer App erteilt
keine Freigabe der anderen App.

## 11. Versionierung und Änderungssteuerung

| Version | Status | Änderung |
| --- | --- | --- |
| 0.1 | Reviewentwurf, nicht genehmigt | Initialer SecurityChain-P0-Entwurf |
| 0.2 | Reviewentwurf, nicht genehmigt | Consent-Audit-Pflichtmetadaten und unbesetzte Entscheidungsfunktionen präzisiert; keine Freigabe oder Änderung der Implementierungsgrenzen |

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
