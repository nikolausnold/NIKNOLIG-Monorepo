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
   müssen als freigegebener Nachweis vorliegen. In den derzeit geprüften
   Repository-Dateien ist keine konkrete SecurityChain-P0-Spezifikation
   dokumentiert. Bei fehlender oder nicht erfüllter Vorgabe gilt **fail closed**.
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
