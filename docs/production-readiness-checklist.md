# NIKNOLIG / NIKNOLIG Defense – Infrastruktur- und Produktionsfreigabe

**Status: NICHT FREIGEGEBEN.** Diese Liste trennt lokale Nachweise,
GitHub-CI-Baselines und externe Betreiber-/Menschengates. Ein vorhandener
Compose-Stack oder erfolgreicher Build ist keine Produktionsabnahme. Die zuletzt
erfolgreichen GitHub-Läufe vor diesem Änderungssatz verwendeten SHA
`51f85deee2f5bb8b1c04728c94ae9884f5bca14a`; sie belegen nicht die nachfolgenden
Änderungen.

## Gate-Matrix

| Gate | Status | Nachweis / Blocker |
| --- | --- | --- |
| App- und Mandantentrennung | **PASS (Repository)** | `:niknolig` und `:niknolig-defense` bleiben getrennte Application-IDs und App-Module. Gemeinsame Bibliotheken gewähren keine Rechte; `backend/tests/test_contracts.py` verbietet direkte App-zu-App-Abhängigkeiten. Produktive Cross-App-Datenflüsse sind nicht implementiert. |
| Backend-/PostgreSQL-Testlauf | **PASS (lokal)** | Auf dem lokalen Änderungssatz: `python3 -m unittest discover -s backend/tests` → **251 bestanden, 1 übersprungen**, mit CI-gepinntem PostgreSQL-17.9-Digest. Der einzelne Skip ist der optionale JSON-Schema-Validator, weil `jsonschema` nicht Teil der Backend-Laufzeitabhängigkeiten ist. |
| Tooling-Tests | **PASS (lokal)** | `python3 -m unittest discover -s tools/tests`: **74 bestanden**. |
| Android-Validierung | **PASS (vorheriger CI-SHA)** | [Android workflow, Lauf 41382290982](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41382290982), Versuch 2, SHA `51f85de`: beide APKs, App-Tests/Lint-/Identitätsprüfungen erfolgreich. Der Lauf enthält nicht die hier dokumentierten Änderungen und ist keine Geräte-/Produktabnahme. |
| Backend-/Contract-CI | **PASS (vorheriger CI-SHA)** | [Backend workflow, Lauf 41382290646](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41382290646), Versuch 2, SHA `51f85de`: PostgreSQL-Backend- und Tooling-Jobs erfolgreich. Keine Aussage über den neuen Commit. |
| CI auf diesem Änderungssatz | **PENDING / Gate nicht bestanden** | Erforderliche Backend- und Android-Checks müssen nach Push auf dem resultierenden PR-Head erfolgreich laufen. Ergebnisse auf `51f85de` ersetzen sie nicht. |
| Swift-Core-Tests | **PASS (vorherige CI-Baseline)** | Lauf `41382290982` enthielt den erfolgreichen portablen `electro-engel-ios-core`-Job; lokal waren zuvor 15 Support- und 8 Elektro-Engel-Core-Tests bestanden. Keine App-Simulator-Builds. |
| iOS-App-/Simulator-Builds | **FAIL / nicht nachgewiesen** | `xcodebuild` ist lokal nicht verfügbar. Der iOS-App-Workflow reagiert nur auf iOS-Pfade; dieser Änderungssatz enthält keine iOS-Quellen und löste keinen nativen Simulator-Build aus. |
| CodeQL / geänderte Dateien | **PENDING für diesen Änderungssatz** | Unabhängiger Security-Review fand keine Befunde. CodeQL wird nach dem Commit auf diesem Änderungssatz ausgeführt. GitHub-Code-Scanning-Alerts konnten wegen HTTP 403 nicht vollständig über die API geprüft werden. |
| Externe Security-/Datenschutzfreigabe | **FAIL** | SecurityChain-P0 bleibt ein nicht genehmigter Reviewentwurf; unabhängige, commitgebundene Security-/Datenschutzsignoffs fehlen. Technische Tests ersetzen sie nicht. |
| Identität und Sitzung | **FAIL** | Kein bestätigter Identitätsanbieter, Issuer/Audience-/App-Scope-Vertrag, produktiver Tokenvalidator, Login, Widerruf, Recovery oder getrennte synthetische Staging-Identitäten. `RejectAllAuthenticator` bleibt Standard. |
| Staging-Host, DNS und TLS | **FAIL / extern offen** | `backend/compose.staging.yaml` ist eine isolierte Health-only-Vorlage mit Pflichtvariablen und getrennten Secrets/Volumes. Es wurden weder Staging-Hostname noch DNS, Zertifikat, Firewall, Hetzner-Zugang oder Deployment bestätigt. Die Vorlage wurde nicht gestartet. |
| Staging-Compose-Modell | **PASS (Konfigurationsprüfung)** | `docker compose ... config` mit zwei unterschiedlichen Projektwerten erzeugte zwei unterschiedliche, projektgebundene Backend-Image-Tags; HTTPS bindet an `127.0.0.1`. Pflichtwerte bleiben fail-closed. Es wurden kurzlebige Platzhalter und `/dev/null`-Dateipfade verwendet; keine Staging-Container gestartet. |
| PostgreSQL-Produktdaten | **FAIL** | Der vorhandene Stack und die Migrationen belegen Health-Readiness, nicht ein freigegebenes Produktdaten-/Memory-Schema. Eine produktive Memory-Migration, Verschlüsselung, KMS/HSM und Datenbankrollen für Produktdaten fehlen. |
| Backups und Storage Box | **PARTIAL / Gate nicht bestanden** | Das Backend-Runbook dokumentiert `pg_dump` direkt in `age`-Verschlüsselung, isolierte Restore-Prüfung und Rücknahme unter `backend/README.md` („Datenbanksicherung und kontrollierte Rücknahme“). Es gab keinen echten Backup-/Restore-Lauf oder Storage-Box-Transfer. SSH-Zugang, eingeschränkter Schlüssel, Retention, Verschlüsselungsschlüsselverwaltung und Restore-Nachweis sind offen. Nur verschlüsselte Backup-Dateien dürfen übertragen werden; die Storage Box ist kein Live-PostgreSQL-Datenträger. |
| Zugriffsschutz / Netzwerk | **PARTIAL / Gate nicht bestanden** | Compose bindet PostgreSQL an ein internes Netzwerk. Staging veröffentlicht HTTPS nur auf `127.0.0.1`; externer Zugriff benötigt einen separat geprüften und freigegebenen Ingress sowie Betreiberprüfung von Host-Firewall, DNS/TLS und Zugangsschutz. Keine Remote-Konfiguration ist verifiziert. |
| Logging / Audit | **PARTIAL / Gate nicht bestanden** | Health-Fehlerantworten und Logs sind generisch und inhaltsfrei; produktiver genehmigter Audit-Sink, Zugriffskontrolle, Aufbewahrung, Alarmierung und Incident-Prozess fehlen. |
| Elektro-Engel / KI | **FAIL** | Kein Android-/iOS-Gateway-Client oder produktiver KI-Aufruf. Provider-, Datenfluss-, Region-, Kosten- und Secret-Freigabe fehlen; Runtime und Authentifizierung bleiben fail-closed. |
| Memory Engine | **FAIL für Produktion; sicher deaktiviert** | Regressionen prüfen aktuelle Autorisierung/Einwilligung nach Persistenz und Rollback partieller Updatefehler. Trotzdem nicht in HTTP verdrahtet, `enabled=False`, In-Memory-Store, kein produktiver Consent-Verifier, keine persistente Verschlüsselung oder verteilte/garantierte Löschung. |
| Rollback / Wiederherstellung | **PARTIAL / Gate nicht bestanden** | Image-/Datenbank-Rücknahme und isolierte Restore-Schritte sind im Backend-Runbook dokumentiert. Kein tatsächlicher Staging-Restore, Recovery-Time-Nachweis oder Rollback-Drill auf Hetzner. |
| PR-Schutz / Merge | **FAIL / blockiert** | PR #189 ist offen und GitHub meldet `mergeable_state=blocked`. Auto-Merge wurde nicht geändert. Die verfügbare PR-Abfrage liefert keinen Auto-Merge-Wert; ob er aktiv ist, bleibt damit nicht verifiziert. |
| Live-Betrieb | **FAIL / nicht geprüft** | Kein Remote-Zugriff, DNS-/TLS-/Health-Nachweis oder Deployment auf dem Hetzner-Server. Es wurde keine produktive Änderung vorgenommen. |

## Staging-Konfiguration

`backend/compose.staging.yaml` ist bewusst nicht mit Produktionswerten befüllt.
Vor einem Start müssen Betreiber und Verantwortliche außerhalb von Git:

1. einen echten, bestätigten Staging-Hostname samt DNS und passendem Zertifikat
   bereitstellen; Zertifikat-SAN und Hostname müssen exakt übereinstimmen;
2. einen eindeutigen `STAGING_COMPOSE_PROJECT`-Namen, einen freien und
   freigegebenen `STAGING_HTTPS_PORT` sowie eine isolierte Staging-VM oder
   gleichwertige Netzwerkgrenze festlegen. Der Compose-Port bindet ausschließlich
   an `127.0.0.1`; externer Zugriff erfordert einen separat geprüften, freigegebenen
   Ingress. Keine direkte Veröffentlichung auf allen Host-Interfaces aktivieren;
3. ein Staging-PostgreSQL-DB-Kennzeichen und vier separate, geschützte Dateien
   konfigurieren: `STAGING_POSTGRES_PASSWORD_SECRET_FILE`,
   `STAGING_HEALTH_PASSWORD_SECRET_FILE`,
   `STAGING_TLS_CERTIFICATE_FILE` und
   `STAGING_TLS_PRIVATE_KEY_FILE`;
4. ausschließlich synthetische Daten und eigens dafür ausgestellte Testidentitäten
   verwenden. Keine Produktionsdaten, Produktionsschlüssel oder Produktions-
   Secrets in Staging kopieren.

Pflichtvariablen sind `STAGING_COMPOSE_PROJECT`,
`STAGING_BACKEND_HOSTNAME`, `STAGING_BACKEND_HOSTNAME_CONFIRMED`,
`STAGING_POSTGRES_DB`, `STAGING_HTTPS_PORT` und die vier genannten Secret-
Dateipfade. Es gibt keine geratenen Default-Hosts, Domains oder Credentials.
Die Vorlage stellt nur den bestehenden Health-/gesperrten Supportdienst bereit;
sie aktiviert weder Login, Memory noch KI. Vor erstem Start sind
`docker compose -f backend/compose.staging.yaml config --quiet`, Preflight,
Firewall-/TLS-Prüfung und ein schriftlich genehmigter Testplan auszuführen.

## Backup, Restore und Betrieb

- Vor Backup-Aktivierung müssen Datenschutz/Betreiber Umfang und Retention
  genehmigen sowie Schlüsselverantwortung, Rotation und Notfallzugriff festlegen.
- `age` verschlüsselt den `pg_dump`-Stream vor Speicherung. Erst die `.age`-
  Ciphertext-Datei wird über einen auf das Backup-Verzeichnis eingeschränkten
  Storage-Box-Zugang übertragen. Den privaten Entschlüsselungsschlüssel getrennt,
  offline oder in einem genehmigten Secret-Manager aufbewahren.
- Rollen-/Berechtigungsdefinitionen separat sichern; keine Secret-Dateien,
  Passwort-Hashes, privaten Schlüssel oder unverschlüsselten Datenbanksicherungen
  auf der Storage Box speichern. Nur nicht-sensitive Backup-ID, Zeit,
  Ciphertext-Hash, PostgreSQL-Version und Image-Digests protokollieren.
- Vor Freigabe müssen Integrität und Entschlüsselbarkeit regelmäßig geprüft sowie
  vollständige Restores in einer neuen, isolierten Testdatenbank erprobt werden.
  Keine Wiederherstellung über produktive Daten hinweg ohne freigegebenen
  Rollback-Plan und verifizierte Sicherung.
- Maßgebliche detaillierte Befehle und Abbruchbedingungen stehen in
  [`backend/README.md`](../backend/README.md) im Abschnitt
  „Datenbanksicherung und kontrollierte Rücknahme“; sie wurden hier nicht gegen
  eine echte Hetzner- oder Storage-Box-Instanz ausgeführt.

## Produktionsfreigabe – zwingende Reihenfolge

1. **PASS erforderlich:** benannte Betreiber, bestätigte Domain/Staging-DNS,
   getrennte Staging-Secrets, Host-Firewall und TLS-Nachweis.
2. **PASS erforderlich:** SecurityChain-P0-D-Entscheidungen, Auth-/Session- und
   App-Scope-Vertrag, Einwilligung/Rechtsgrundlage, Datenklassen, Retention und
   unabhängige Datenschutz-/Security-Abnahme.
3. **PASS erforderlich:** freigegebene PostgreSQL-Produktmigrationen, Least-
   Privilege-/Mandantentests, Verschlüsselung/KMS, Audit-/Quota-/Monitoring- und
   Löschkonzept.
4. **PASS erforderlich:** verschlüsselter Storage-Box-Backuptransfer, erfolgreicher
   isolierter Restore, Backup-Retention sowie getesteter Rollback/Recovery.
5. **PASS erforderlich:** getrennte synthetische Identitäten und Ende-zu-Ende-
   Positiv-/Negativtests für beide Apps einschließlich abgelaufener und widerrufener
   Sitzungen/Einwilligungen. Kein appübergreifender Zugriff.
6. **PASS erforderlich:** Provider-, Datenfluss-, Region-, Kosten- und
   serverseitige Secret-Freigabe; erfolgreiche echte KI-Prüfung in freigegebener
   Staging-Umgebung, ohne Tests oder Mocks als Live-Erfolg auszugeben.
7. **PASS erforderlich:** aktuelle Backend-, Android- und iOS-App-CI auf dem
   Freigabe-SHA, alle erforderlichen Branch-Protection- und Security-Gates grün,
   keine offenen kritischen/hohen Findings sowie dokumentierte manuelle Signoffs.
8. **PASS erforderlich:** Betreiber bestätigt Staging-Abnahme, Monitoring/Alarm-
   und Incident-Übung sowie Rollback. Erst danach separate Produktionsfreigabe
   und kontrollierter Deploy-Plan.

Solange mindestens ein Gate **FAIL**, **PARTIAL** oder ungeprüft ist, lautet die
Entscheidung **NICHT FREIGEGEBEN**. Der Status dieser Liste ist kein Auto-Merge-
oder Deployment-Befehl.
