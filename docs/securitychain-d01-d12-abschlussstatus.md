# SecurityChain-P0 D-01 bis D-12: Gesamtstatus und Freigaberegister

**Stand: 21.10.2026. Reviewentwurf, nicht genehmigt.** Dieses Dokument bündelt
die Bestandsprüfung zu D-01 bis D-12. Es ändert keine Entscheidung, erteilt
keine Freigabe und erfindet keine Prüfnachweise. Maßgeblich bleibt die
Entscheidungsmatrix in [Abschnitt 10 der Spezifikation](securitychain-p0-specification.md).
Abschnitt 10 wird nicht neu geöffnet; D-01 wurde nicht erneut bearbeitet
(vorhandene Nachweise: D-01-Prüfprotokoll, PR #111).

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

## Testergebnisse

Ausgeführt am 21.10.2026 im Verzeichnis `backend`:
`python -m unittest discover -s tests` → **73 Tests, OK** (inkl. Matrix-
Vollständigkeit, Statuszuordnung, fehlende BLE-Berechtigungen/iOS-Projekte,
Modulisolation). Diese Tests belegen Repository-Invarianten, **nicht**
Authentifizierung, Autorisierung, BLE-Sicherheit, P0-Konformität oder
menschliche Freigabe. Android-Builds wurden nicht neu ausgeführt, da keine
Android-Quellen geändert wurden.
