# Getrennte Gründerrollen und Kontoanforderungen

**Status: Soll-Konzept, keine Konten oder Rollen angelegt. Produktivvergabe: BLOCKED bis SecurityChain-P0-Freigabe.**

NIKNOLIG und NIKNOLIG Defense bleiben getrennte Apps und Sicherheitsbereiche.
Ein Gründerkonto ist jeweils an genau einen App-Bereich gebunden. Ein Mensch
kann nach expliziter, separat geprüfter Vergabe in beiden Bereichen eine Rolle
haben; daraus entstehen zwei getrennte Berechtigungszuweisungen, keine
gemeinsame App-Identität. Geteilte Gründerkonten, Passwörter, Sitzungen,
Tokens oder privaten Schlüssel sind nicht zulässig.

Dieses Konzept behauptet weder ein vorhandenes Backend noch echte Benutzerkonten,
eine Identitätsprüfung oder eine SecurityChain-P0-Freigabe. Es definiert keine
Rechtsform, Eigentumsanteile oder tatsächliche Gründeridentität.

## Rollen je App

| Rolle | NIKNOLIG-Bereich | NIKNOLIG-Defense-Bereich |
| --- | --- | --- |
| **Founder Owner** | Verantwortet Produktumfang, benannte App-Administratoren und Freigaben ausschließlich für NIKNOLIG. Hat standardmäßig keinen Zugriff auf sensible Nutzinhalte. | Verantwortet Produktumfang, benannte App-Administratoren und Freigaben ausschließlich für Defense. Hat standardmäßig keinen Zugriff auf sensible Nutzinhalte und keine NIKNOLIG-Rechte. |
| **App Administrator** | Verwaltet nur freigegebene Konfiguration, App-Mitgliedschaften und App-spezifische Zugriffe für NIKNOLIG. Kann keine globale Identität oder Defense-Rechte vergeben. | Verwaltet nur freigegebene Konfiguration, Mitgliedschaften und Zugriffe für Defense. Kann keine NIKNOLIG-Rechte vergeben. |
| **Security Operator** | Prüft sicherheitsrelevante Ereignismetadaten, Widerruf und Vorfälle innerhalb des NIKNOLIG-Bereichs. Kein standardmäßiger Inhaltszugriff. | Prüft ausschließlich Defense-Ereignismetadaten, Widerruf und Vorfälle. Kein Zugriff auf NIKNOLIG-Logs oder Inhalte. |
| **Support / Auditor (read-only)** | Zeitlich begrenzter, genehmigter Zugriff auf erforderliche, redigierte Diagnosemetadaten. Keine Benutzerverwaltung, Sensorrohwerte oder Sitzungsinhalte. | Gleiche Begrenzung ausschließlich im Defense-Bereich; keine appübergreifende Suche. |

Der Founder Owner ist kein technischer „Superuser“ mit appübergreifendem
Zugriff. Rollenzuweisungen und hochriskante Änderungen sollten nach Freigabe
mindestens einen zweiten, unabhängigen approvierenden Verantwortlichen
erfordern. Bis ein berechtigter zweiter Verantwortlicher und ein sicherer
Freigabefluss festgelegt sind, werden solche Änderungen nicht produktiv
ermöglicht. Rollenrechte werden als App-spezifische Allowlist konkreter Aktionen
implementiert; der Rollenname allein autorisiert keine Geräteaktion,
Sensorfreigabe oder Übertragung privater Daten.

## Mindestanforderungen an jedes Gründerkonto

1. **Eindeutige Person und App-Scope:** Konto erhält eine stabile interne
   Kennung, eine verifizierte Identität und genau einen App-Scope pro
   Berechtigungszuweisung (`niknolig` oder `niknolig-defense`). Keine
   Benutzerkonten, E-Mail-Adressen oder Anzeigenamen als alleinige
   Autorisierungsnachweise.
2. **Individuelle Anmeldung:** Pro Person individuelle Zugangsdaten, kein
   gemeinsames Gründer-Login. Primäre Authentifizierung, passwortlose Verfahren
   oder Passwortanforderungen sind mit dem später ausgewählten
   Identitätsanbieter festzulegen. Keine Anmeldedaten im Quellcode, in mobilen
   Apps oder in gemeinsamen CI-Secrets.
3. **Starke Mehr-Faktor-Authentifizierung:** Vor Produktivzugriff MFA
   verpflichtend. Phishing-resistente Passkeys/Sicherheitsschlüssel sind das
   bevorzugte Ziel; zulässige Alternativen, Gerätewechsel und Fallback müssen
   im Threat Model festgelegt sein. SMS allein ist kein ausreichender
   Admin-Schutz.
4. **Einladung statt Selbstzuweisung:** Kontoanlage und App-Rollenzuweisung nur
   über eine einzeln adressierte Einladung mit kurzer Gültigkeit, einmaliger
   Verwendung und Bestätigung durch einen berechtigten zweiten Verantwortlichen.
   Keine öffentliche Registrierung als Founder Owner. Einladungen enthalten
   keine Berechtigung für den jeweils anderen App-Bereich.
5. **Minimale Sitzung und erneute Prüfung:** Kurze, widerrufbare Sitzungen;
   erneute Authentifizierung für Rollenvergabe, Recovery, Schlüssel-/Policy-
   Änderungen und andere freizugebende sensible Aktionen. Jede API-Operation
   prüft Identität, App-Scope, Rolle, konkrete Aktion, Zweck und aktuellen
   Widerrufsstatus serverseitig.
6. **Sicherer Recovery-Prozess:** Recovery darf MFA oder App-Scope nicht
   herabstufen. Identitätsprüfung, unabhängige Freigabe, Benachrichtigung,
   Entzug alter Sitzungen/Authenticatoren und Audit sind vorab zu spezifizieren.
   Ist eine sichere Recovery nicht möglich, bleibt das Konto gesperrt und wird
   kontrolliert neu eingerichtet.
7. **Audit und Datenschutz:** Protokolliert werden nur Akteur-Referenz,
   App-Scope, Rollen-/Aktionstyp, Ergebnis, Zeit, Korrelations-ID und
   Freigabe-Referenzen. Keine Passwörter, MFA-Codes, Tokens, privaten Schlüssel,
   Sensorrohwerte oder unnötigen Nutzinhalte. Aufbewahrung und Zugriff auf das
   Audit sind freizugeben.
8. **Widerruf und Offboarding:** Sofortige Sperrung einer App-spezifischen
   Rolle, Beendigung zugehöriger Sitzungen/Tokens und Widerruf betroffener
   Gerätebeziehungen. Entzug in einer App darf die andere App nicht automatisch
   ändern; eine dortige Rolle wird separat überprüft. Verlorene
   Authenticatoren/Geräte werden nach bestätigtem Vorfall gesperrt.

## App-spezifische Berechtigungsgrenzen

- **NIKNOLIG Founder Owner:** NIKNOLIG-Produkt- und Mitgliedschaftsverwaltung
  erst nach Freigabe. Elektro-Engel erhält keine implizite Berechtigung, auf
  Defense-Daten oder Geräte zuzugreifen.
- **NIKNOLIG Defense Founder Owner:** Defense-Verantwortung beschränkt sich auf
  die gesondert freigegebenen Defense-Funktionen. Sie erteilt keine
  NIKNOLIG- oder Elektro-Engel-Rechte.
- **Gleiche Person in beiden Bereichen:** Zwei getrennte App-Scope-Zuweisungen,
  getrennte Sitzungs-/Tokenkontexte und getrennte Audit-Abfragen. Keine
  Cross-App-Rolle und kein „linked account“-Shortcut für Autorisierung.
- **Sensor- und Gerätezugriff:** Gründerstatus gewährt weder Fernsteuerung noch
  Kamera-, Mikrofon-, Standort- oder Tiefensensorzugriff. Diese Zwecke brauchen
  gesonderte Nutzerzustimmung auf betroffenem Gerät, passende Android-
  Laufzeitberechtigung und eine separat freigegebene konkrete Aktion. Nutzer
  können nicht durch eine Gründerrolle überstimmt werden.

## Offene Entscheidungen und Freigabegate

Vor einer echten Kontoanlage müssen Verantwortliche schriftlich festlegen:

- Identitätsanbieter und tatsächlich geprüfte Identitätsmerkmale;
- verifizierte Eigentümer/Gründer pro App und unabhängige zweite approvierende
  Personen (hier nicht vorgegeben oder angenommen);
- verbindliche SecurityChain-P0-Kriterien, Threat Model und Security-Review;
- MFA-/Passkey-Unterstützung, Authenticator-Recovery und Geräteverlustverfahren;
- konkrete Aktionen je Rolle, Datenzugriff, Einladungs-/Genehmigungsprozess und
  Break-glass-Verfahren;
- Audit-Eigentümer, Zugriffsgruppen, Aufbewahrung und Löschfristen;
- Regeln zu Datenschutz, Verantwortlichkeit und erforderlichen
  Einwilligungstexten.

Im aktuellen Monorepo sind kein Login-/Benutzerverwaltungsserver, kein
Identitätsanbieter und keine produktiven Endpunkte vorhanden. Das Backend ist
vertraglicher Entwurf. Daher werden hier keine Konten erstellt, E-Mail-Adressen
oder Namen eingetragen, Rollen provisioniert oder Zugangsdaten angefordert.
Bis alle erforderlichen Freigaben und Tests belegt sind, bleibt die
Produktivvergabe **gesperrt (fail closed)**.

## Integrationsorte nach Freigabe

Konten und Rollen werden nicht in den Android-Manifesten oder lokal in der App
als vertrauenswürdige Admin-Entscheidung hinterlegt. Nach freigegebener
Backendimplementierung:

- Backend: versionierter Auth-/Admin-Vertrag, serverseitige Policy-Prüfung,
  app-scoped Mitgliedschafts-/Rollenpersistenz, Einladung, Widerruf und
  minimiertes Audit; getrennte App-Scope-Negativtests.
- [NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG): eigener Login- und
  Rollenstatus-Client unter `app/src/main/java/com/niknolig/app/`, UI in
  `app/src/main/res/`, Tests in `app/src/test/` und
  `app/src/androidTest/`; keine Defense-Berechtigungsdaten.
- [NIKNOLIG Defense](https://github.com/nikolausnold/NIKNOLIG-Defense): eigener
  Login- und Rollenstatus-Client unter `app/src/main/java/com/niknolig/defense/`,
  UI in `app/src/main/res/`, Tests in `app/src/test/` und
  `app/src/androidTest/`; keine NIKNOLIG-Berechtigungsdaten.

Die separaten App-Repositories werden durch dieses Dokument nicht geändert.
Keine Authentifizierungsbibliothek, Berechtigung oder Produktionskonfiguration
wird vor gesonderter Review und SecurityChain-P0-Freigabe ausgewählt.
