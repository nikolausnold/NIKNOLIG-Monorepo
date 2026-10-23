# Zwei-Geräte-Verbindung – Sicherheitsdesign und Umsetzungsgates

**Status:** Entwurf; keine Implementierung oder Transportwahl freigegeben
**Freigabe:** P0-blockiert bis SecurityChain-P0-Kriterien und offene
Produkt-/Sicherheitsentscheidungen schriftlich bestätigt sind

## 1. Ziel und Grenzen

Eine explizit freigegebene, authentifizierte Verbindung zwischen einer
NIKNOLIG-Installation und einer NIKNOLIG-Defense-Installation auf zwei
Android-Geräten. Die Apps, `applicationId`s, Installationen, Releases und
Sicherheitsdomänen bleiben getrennt. Es gibt keinen Zugriff auf die Sandbox der
anderen App und keine implizite Berechtigung durch gemeinsam genutzten Code.

Dieses Dokument ist eine Planungsgrundlage, keine Behauptung, dass Verbindung,
Verschlüsselung oder Pairing bereits vorhanden seien. Der Audit weist in den
Apps keine Transport-, Pairing-, Authentifizierungs-, Verschlüsselungs- oder
Wiederverbindungsimplementierung nach.

## 2. Vor Implementierungsbeginn erforderliche Freigaben

1. Die verbindliche SecurityChain-P0-Version und ihre Muss-/Abbruchkriterien
   müssen als freigegebener Nachweis vorliegen. Der neue
   [SecurityChain-P0-Reviewentwurf](securitychain-p0-specification.md) ist noch
   nicht genehmigt und kein Freigabenachweis. Bei fehlender oder nicht erfüllter
   Vorgabe gilt **fail closed**.
2. Fachverantwortliche müssen Zweck, zulässige Daten, erlaubte Aktionen,
   Rollen beider Geräte, Nutzerzustimmung, Widerruf, Offlineverhalten und
   Aufbewahrung freigeben. Defense erhält keine Rechte über einen pauschalen
   Vertrauens- oder Pairingstatus hinaus.
3. Bedrohungsmodell und Transportwahl müssen einschließlich unterstützter
   Android-Versionen, Berechtigungen, externer Dienste, Bibliotheken und
   kryptografischer Vertrauensgrenzen geprüft werden. Keine Eigenentwicklung
   von Kryptografie; eine verschlüsselte Transportverbindung allein ist kein
   Nachweis gegenseitiger Geräteauthentifizierung.
4. Protokollbesitzer, Nachrichtenmodell, Versionierung, Datenminimierung,
   Fehlerverhalten, Zeitlimits, Wiederholungsschutz und
   Schlüssel-/Identitätslebenszyklus müssen genehmigt werden.
5. Gemeinsame Laufzeitkomponenten, neue Abhängigkeiten, Berechtigungen und
   Veränderungen an Build-/Releasepipelines benötigen gesonderte
   Architektur-/Security-Freigabe. Keine Änderungen an separaten
   App-Repositories oder Cloud-/Backend-Systemen im Rahmen dieses Plans.

### Transportoptionen – keine Auswahl getroffen

Die Optionen sind Kandidaten für eine spätere Prüfung, keine
SecurityChain-P0-Freigabe:

| Option | Eignung und offene Sicherheitsfragen |
| --- | --- |
| Nearby Connections | Bietet Peer-to-Peer-Discovery und -Datenaustausch über Google Play Services. Googles API-Dokumentation beschreibt eine Authentifizierungsphase mit Bestätigung auf beiden Geräten und verschlüsselte Verbindungen. Zu prüfen bleiben unter anderem Play-Services-Verfügbarkeit, genaue Berechtigungen je Android-Version, Identitätsbindung über Wiederverbindungen, Widerruf und ob der dokumentierte Authentifizierungstoken die freigegebenen SecurityChain-P0-Anforderungen erfüllt. [Übersicht](https://developers.google.com/nearby/connections/overview), [Verbindungen verwalten](https://developers.google.com/nearby/connections/android/manage-connections), [Berechtigungen](https://developers.google.com/nearby/connections/permissions) |
| Bluetooth LE/GATT | Verwendet Androids Bluetooth- und GATT-APIs. GATT kann verschlüsselte Zugriffe mit MITM-Schutz verlangen; das allein belegt weder stabile App-Geräteidentität noch Aktionen-Autorisierung, Sitzungsfrische oder Widerrufsverhalten. Zu prüfen sind Pairing-Verfahren, unterstützte Geräte und Laufzeitberechtigungen. [BluetoothGattCharacteristic API](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic), [Android Bluetooth Security](https://source.android.com/docs/core/connect/bluetooth/secure) |
| Lokales WLAN mit NSD und TLS | NSD dient der Dienstsuche, nicht der Peer-Authentifizierung oder Verschlüsselung. Nach der Discovery wären ein separat spezifizierter TLS-Kanal und eine sichere Zertifikats-/Schlüssel-Vertrauensverteilung nötig. Gemeinsames WLAN, mDNS-Verhalten, Netzwerkwechsel und lokale Netzwerkberechtigungen sind zu prüfen. [Android NSD](https://developer.android.com/develop/connectivity/wifi/use-nsd), [Android TLS](https://developer.android.com/privacy-and-security/security-ssl) |

Für keine Option ist hiermit festgestellt, dass sie die verbindlichen
SecurityChain-P0-Anforderungen erfüllt. Eine verschlüsselte Verbindung,
OS-Pairing oder Nutzerbestätigung darf nicht allein als ausreichende
gegenseitige App-Geräteauthentifizierung gewertet werden. Auswahl, Bedrohungs-
und Kompatibilitätsprüfung sowie Abnahmekriterien sind offene Freigabepunkte.

## 3. Vorgesehene Architektur nach Freigabe

- Die App-Module `:niknolig` und `:niknolig-defense` bleiben getrennt. Die
  jeweilige App stellt eigene UI, Berechtigungsabfragen und
  App-Lebenszyklusintegration bereit.
- Ein optionales gemeinsames Gradle-Modul `:device-link-core` ist nur nach
  ausdrücklicher Freigabe vorgesehen. Es darf ausschließlich versionierte
  Nachrichtenmodelle, Validierung und eine deterministische Zustandsmaschine
  enthalten. Keine gemeinsamen UI-/Android-Berechtigungen, Identitäten,
  Secrets, privaten Schlüssel oder appübergreifende Autorisierungsdefaults.
- Ein Transportadapter wird pro App an den freigegebenen Transport angebunden.
  Auswahl und Abhängigkeiten bleiben bis zur Sicherheitsprüfung offen. Es
  werden keine direkten Modul-/Sandbox-Zugriffe, unbestätigten Worker oder
  ungeprüften externen Dienste vorausgesetzt.
- Pairing erfordert aktive Zustimmung auf beiden Geräten sowie einen
  freizugebenden, sicheren Identitätsnachweis außerhalb des bloßen
  Gerätenamens. Geräteschlüssel müssen gerätegebunden verwaltet werden;
  Sitzungsschlüssel und gegenseitige Authentifizierung müssen durch ein
  etabliertes, überprüftes Protokoll gewährleistet werden.
- Jede Nachricht ist an Protokollversion, Sitzung und erlaubte Aktion gebunden.
  Unbekannte Versionen, nicht erlaubte Aktionen, ungültige oder veraltete
  Nachrichten werden abgelehnt. Kein automatisches Wiederholen sensibler
  Aktionen und keine nicht freigegebene Offline-Warteschlange.
- Die Verbindung hat explizite Zustände: `idle`, `discovering`, `pairing`,
  `connected`, `reconnecting`, `revoked` und `failed`. Authentifizierungs-,
  Autorisierungs-, Integritäts- oder Sicherheitsfehler beenden die Sitzung;
  Wiederverbindung authentifiziert den Peer erneut. Widerruf löscht die
  Vertrauensbeziehung und erfordert ein neues beidseitig bestätigtes Pairing.

## 4. Erwartete Änderungsorte

Änderungen erfolgen erst nach den Freigaben in Abschnitt 2.

| Bereich | Vorgesehene Dateien / Orte |
| --- | --- |
| Modulregistrierung | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/settings.gradle.kts` – nur für ein genehmigtes optionales Core-Modul |
| App-Konfiguration | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/build.gradle.kts` und `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/build.gradle.kts` – nur freigegebene, geprüfte Abhängigkeiten |
| App-Berechtigungen | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig/src/main/AndroidManifest.xml` und `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/apps/niknolig-defense/src/main/AndroidManifest.xml` – ausschließlich minimal benötigte freigegebene Rechte |
| App-Integration | Bestehende `MainActivity.kt`, neue app-spezifische Verbindungs-/Pairing-UI und Transportadapter unter den jeweiligen `apps/*/src/main/java/`-Paketen |
| UI-Texte | Je App erforderliche Ressourcen unter `apps/*/src/main/res/layout/` und `apps/*/src/main/res/values*/strings.xml` |
| Gemeinsamer Kern | Optional `modules/device-link-core/` (oder freigegebener äquivalenter Pfad) für Protokollmodell, Validator und Zustandsmaschine |
| Tests | `src/test/` für Protokoll, Zustandsmaschine und Autorisierung; `src/androidTest/` für Manifest-/Berechtigungs-/UI- und Transportverhalten je App |
| CI | `/home/runner/work/NIKNOLIG-Monorepo/NIKNOLIG-Monorepo/.github/workflows/android-build.yml` für freigegebene Unit- und Instrumentierungstesttasks; keine Veröffentlichung oder Secrets für Tests |
| Dokumentation | Dieses Design ergänzen; freigegebenen Nachrichtenvertrag, Datenfluss, Bedrohungsmodell und Geräteabnahme nachvollziehbar versionieren |

Der Audit dokumentiert derzeit keine Android-Testquellen. Der aktuelle Workflow
baut beide APKs und prüft Paket-IDs/Signaturen, führt jedoch keine App-Tests aus.

## 5. Test- und Abnahmekriterien

### Automatisierte Unit-/Vertragstests

- Zustandsübergänge: gültiges Pairing, Abbruch in jedem Pairing-Schritt,
  Timeout, Prozessneustart, Peerwechsel und Widerruf.
- Gegenseitige Authentifizierung: unbekannter Peer, falscher/veränderter
  Identitätsnachweis, Schlüsselwechsel ohne Zustimmung und Replay eines alten
  Handshakes müssen abgelehnt werden.
- Autorisierung: nicht genehmigte Aktion, falsche Rolle, widerrufener Peer,
  nicht erlaubte Richtung, veraltete Sitzung und ungültige Protokollversion
  müssen abgelehnt werden.
- Nachrichtenvalidierung: fehlende/zusätzliche Pflichtfelder, ungültige
  Kodierung, Grenzwerte, übergroße Payloads, Duplikate und manipulierte
  Integritätsdaten.
- Sitzungsschutz: Integritätsfehler, Authentifizierungsfehler und
  Berechtigungsfehler schließen die Sitzung; sensible Aktionen werden nicht
  stillschweigend gepuffert oder erneut ausgeführt.
- Fehler/Verfügbarkeit: Transportabbruch, Offlinebetrieb, Netzwerkwechsel,
  Berechtigungsverweigerung/-widerruf und erfolglose Wiederverbindung.

### Physische Zwei-Geräte-Abnahme

Auf zwei benannten, unterstützten Android-Geräten mit dokumentierten
Android-Versionen und freigegebenen App-Builds sind mindestens zu protokollieren:

- beidseitige Zustimmung und erfolgreiche Peer-Verifikation;
- Ablehnung eines fremden/unerwarteten Geräts und eines veränderten
  Identitätsnachweises;
- nur freigegebener Nachrichtenaustausch und Ablehnung nicht autorisierter
  Aktionen;
- Berechtigungsverweigerung und nachträglicher Widerruf;
- Abbruch während Pairing und aktiver Sitzung, Offlinebetrieb,
  Wiederverbindung nach erneuter Authentifizierung sowie expliziter Widerruf;
- Ergebnis mit Zeit, Build-/Versions- und Gerätezuordnung sowie redigiertem
  Nachweis. Schlüssel, Tokens und unnötige personenbezogene Nutzdaten dürfen
  nicht in Logs oder Testberichten stehen.

Automatisierte Tests oder Emulatoren ersetzen nicht die Abnahme auf beiden
physischen Geräten. Ein erfolgreicher APK-Build hebt den P0-Blocker nicht auf.

### BLE-Anforderungs- und Testmatrix (Planung; nicht freigegeben)

Die Matrix beschreibt spätere Nachweise, keine gegenwärtige Funktion oder
Freigabe. Bis alle zugeordneten Entscheidungen schriftlich genehmigt sind,
bleiben BLE-Berechtigungen, Discovery, Pairing und Verbindungen deaktiviert.
Vorher zulässig sind nur Tests bestehender, deaktivierter Grenzen. Sobald eine
Architektur freigegeben ist, dürfen automatisierte Vorabtests ausschließlich
deterministische Mock-Transporte und synthetische Identitäten/Daten verwenden.
Ein Mock kann weder BLE-Verhalten noch Kryptografie, Geräteidentität oder
physische Interoperabilität nachweisen.

| Anforderung | Erlaubter Mock-Test nach Freigabe | Negativ-/Fehlerfälle, die abgelehnt werden müssen | Erforderliche Entscheidung / Abnahme |
| --- | --- | --- | --- |
| Explizite Nutzerfreigabe und App-Scope | Simulierte Zustimmung beider Nutzer für den konkret freigegebenen Zweck, die Daten, Aktion und Zielinstallation; getrennte NIKNOLIG-/Defense-Identitäten | Fehlende, abgelaufene oder widerrufene Zustimmung; einseitige Zustimmung; falscher Zweck, Scope, Empfänger oder Ziel; Gerätename oder Pairingstatus als alleiniger Zustimmungs-/Identitätsnachweis | D-01, D-02, D-03, D-09: Produkt-Allowlist je App, Identitätsbindung und Consent-Text/-Lebenszyklus; Datenschutz-/Security-Freigabe |
| Authentifiziertes Pairing und Vertrauensprüfung | Synthetischer, vorab festgelegter Peer-Nachweis besteht nur bei passender App-Identität und beidseitiger Bestätigung | Unbekannter/falscher Peer, geänderte Identität oder Schlüssel, unvollständiger Besitznachweis, App-Scope-Wechsel oder fehlende Bestätigung; niemals Vertrauen allein aus BLE-Adresse, Werbung oder OS-Pairing ableiten | D-02 bis D-05: Auth-/Vertrauensmodell, Protokoll und Schlüssel-Lebenszyklus; unabhängiger Security-Review |
| Verbindung, Sitzungszustand und Abbruch | Mock-Transport prüft ausschließlich freigegebene Zustandsübergänge, den genehmigten Zeitlimitvertrag sowie Beendigung bei Abbruch | Timeout, Teilantwort, unerwarteter Zustand, Prozessneustart, Peerwechsel, Integritätsfehler oder nicht prüfbare Berechtigung; Sitzung schließen, kein schwächerer Transport, keine automatische sensible Wiederholung/Queue | D-04, D-06, D-07: Protokoll, Zeitlimits, Offline-/Wiederverbindungsverhalten und Transport; physische Abnahme erst nach Freigabe |
| Android-Berechtigungen und Widerruf | Synthetische Rückgaben für Berechtigung erteilt und später widerrufen; keine Android-Bluetooth-API im Mock-Test aufrufen | Verweigerung, Widerruf, fehlende/unerwartete Capability oder nicht unterstützte OS-Version: Discovery/Verbindung bleibt aus bzw. endet | D-07, D-08 und D-06: minimale Rechte je unterstützter OS-/Gerätematrix sowie Widerrufsverhalten; separate schriftliche BLE-Freigabe |
| Nicht autorisierte Geräte, Aktionen und Replay | Synthetische Allowlist-Fälle akzeptieren nur genehmigte Rolle, Richtung, Aktion, Sitzung und Zielinstallation | Fremdes Gerät, nicht erlaubte Aktion/Richtung, falsche Rolle, Duplikat oder Replay einer alten Challenge/Nachricht, veraltete Sitzung, Downgrade oder unbekannte Version: ablehnen und betroffene Sitzung schließen | D-01 bis D-06 und D-09: Aktions-/Daten-Allowlist, etablierter geprüfter Schutz gegen Replay/Downgrade, Consent und Autorisierung; unabhängiger Review |
| Fehlerantworten und datensparsames Logging | Mock-Fehler werden in stabile, allgemeine Fehlercodes umgewandelt; synthetische Audit-Ereignisse enthalten nur freigegebene Metadaten | Keine Stacktrace-, Payload-, Gerätenamen/-adresse-, Token-, Schlüssel-, Nonce-/Challenge- oder Sensorrohwert-Ausgabe; Audit-Ausfall darf keine geschützte Aktion freigeben | D-06, D-10: Fehler-/Audit-Verhalten, Rechtsgrundlage, Zugriff und Retention; datenschutzrechtliche und Security-Abnahme |
| App-Isolation und Testbelege | Mock-Fälle laufen getrennt je App mit synthetischen App- und Installationsreferenzen | Kein Credential-, Schlüssel-, Berechtigungs- oder Sitzungsübertritt zwischen Apps; kein Cross-App-Zugriff ohne ausdrücklich genehmigten, getesteten Datenfluss | D-01, D-05, D-08, D-12: getrennte App-Freigaben, Plattformtests und unabhängige, commit-/artefaktgebundene Review-Nachweise |

**Wiederverwendbare Bestandsnachweise:** `BackendContractTests.test_current_android_ble_and_ios_targets_are_explicit`
prüft, dass beide Manifeste derzeit nur `INTERNET` deklarieren und keine
Bluetooth-Berechtigung enthalten. Die getrennten
`BackendHealthClientTest`-Klassen nutzen injizierte Fake-HTTPS-Verbindungen für
synthetische HTTP-Erfolgs- und Fehlerantworten; sie testen ausschließlich den
Health-Endpunkt und sind kein BLE-Transport, Pairing- oder
Kryptografietest. Es gibt aktuell keine BLE-Schnittstelle, BLE-Runtime,
Pairing-Zustandsmaschine oder BLE-Testgeräte-/Mock-Abstraktion, die
wiederverwendet werden könnte. Die vorhandenen Tests belegen daher nur den
deaktivierten Ist-Zustand, keine BLE-Sicherheit.

Für die spätere Umsetzung müssen die genehmigten Negativfälle als Unit-/
Vertragstests mit synthetischen Daten umgesetzt werden. Physische Gerätetests
dürfen erst nach Freigabe der Architektur und auf den ausdrücklich unterstützten
Geräten stattfinden; Mock-Tests ersetzen sie nicht. Bis dahin wird weder eine
Verbindung simuliert noch ein Gerät als gepaart oder sicher markiert.

## 6. Risiken und verbleibende Unbekannte

- Ohne verbindliche SecurityChain-P0-Kriterien lässt sich keine
  Konformitätsaussage treffen; die Implementierung darf dieses Gate nicht
  umgehen.
- Eine unpassende Transportwahl kann Geräte ausschließen oder unzureichende
  Discovery-, Authentifizierungs- oder Hintergrundgarantien liefern.
- Neuinstallation, Gerätewechsel, Backup/Restore oder Schlüsselverlust können
  Identitäten ungültig machen; Rotation, Löschung und erneute Zustimmung sind
  vorab festzulegen.
- Wiederverbindung und Offlineverhalten bergen Risiken durch Replay,
  Doppelaktionen und fortbestehende Berechtigungen. Standard ist kein
  automatisches Fortsetzen sensibler Aktionen.
- Die konkreten Daten, Aktionen, Rollen, externe Dienste, Transportbibliothek,
  Berechtigungen, Mindestversionen und Aufbewahrungsregeln sind offen.
- Keine Secrets, Schlüssel, Kontoeinstellungen oder fremden Repositories
  werden benötigt, erstellt oder geprüft, um diesen Entwurf vorzubereiten.

## 7. Freigabe-Gate

Die Planung ist abgeschlossen; die Implementierung bleibt **BLOCKED**, bis
SecurityChain-P0-Nachweis, Bedrohungsmodell, fachlicher Daten-/Aktionsumfang,
Transportwahl und Protokollvertrag freigegeben sind. Danach sind die
Dateiänderungen schrittweise umzusetzen und die Tests in Abschnitt 5 als
verbindliche Gates in CI und Geräteabnahme zu verankern. Keine bestehende
Sicherheitsregel oder App-/Repository-Grenze darf dafür abgeschwächt werden.
