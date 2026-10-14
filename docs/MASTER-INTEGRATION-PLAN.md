# NIKNOLIG Master-Integration – Inventur und Vorschlag

**Status:** Entwurf zur Prüfung, keine Implementierungsfreigabe  
**Inventurstand:** 2026-10-14  
**Geprüfter Arbeitsbranch:** `copilot/maintain-existing-work`  
**Geprüfter Commit:** `9f6c24ea15d944cf698b5906da20d8a135b60f27`

Dieser Entwurf trennt Repository-Fakten von Angaben und Zielvorstellungen. Nicht
lesbare Quellen oder nicht zugängliche Cloudflare-Einstellungen werden nicht
als bestätigt behandelt. Er genehmigt weder Änderungen noch Veröffentlichung,
Produktivzugriff oder Deployment.

## 1. Bestandsinventur

### Im Monorepo nachgewiesen

Zum Inventurzeitpunkt enthält der ausgecheckte Arbeitsbranch genau diese
getrackten Projektdateien:

| Datei | Nachgewiesener Inhalt |
| --- | --- |
| `README.md` | Dokumentiert den begrenzten Repository-Stand und die fehlenden Anwendungskomponenten. |
| `.github/workflows/audit-workers.yml` | Manueller Read-only-Überblick über dieses Repository; keine Projekt-Workflows oder Skripte werden ausgeführt. |

Es wurden keine Anwendungsquellen, API-Definitionen, Build-/Paketmanifestdateien,
Tests, Wrangler-Konfigurationen oder Deployment-Skripte gefunden. Im lokalen
Arbeitsbaum waren keine uncommitteten Änderungen vorhanden. GitHub zeigte
`main` auf `2caa4098abf8a6464c21720383b7f47289b5be98`; der geprüfte
Arbeitsbranch lag auf dem oben genannten späteren Dokumentationscommit.

Die GitHub-Actions-API listete den Audit sowie zwei dynamische Copilot-Workflows.
Im Checkout liegt nur die YAML-Datei des Audits; aus den dynamischen Einträgen
wird keine Projekt-CI oder Produktivpipeline abgeleitet. Für den Audit ist ein
erfolgreicher manueller Lauf auf `main` bei Commit
`2caa4098abf8a6464c21720383b7f47289b5be98` nachgewiesen:
[Workflow-Lauf](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38524704790).
Dies bestätigt ausschließlich den Audit-Lauf, nicht die Anwendung oder eine
Cloudflare-Verbindung.

### Quell-Repositories

Lesende GitHub-API-Inhaltsabfragen des Repository-Root mit angefragter Revision
`refs/heads/main` für beide angegebenen Quellen lieferten `404 Not Found`:

| Quelle | Prüfergebnis | Aussagegrenze |
| --- | --- | --- |
| [nikolausnold/NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG) | Inhalt nicht lesbar | `404` unterscheidet nicht zwischen fehlendem Repository und fehlender Sichtbarkeit/Berechtigung. |
| [nikolausnold/NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense) | Inhalt nicht lesbar | `404` unterscheidet nicht zwischen fehlendem Repository und fehlender Sichtbarkeit/Berechtigung. |

Damit sind Quellcode, Branch-Stand, README, APIs, Konfigurationen, Tests und
Buildsysteme beider Anwendungen **nicht verifiziert**. Es wurden keine Inhalte
geklont oder aus den 404-Antworten abgeleitet.

Elektro-Engel ist in der Aufgabenstellung als bestehendes Projekt/Modul benannt.
In den tatsächlich vorliegenden Dateien ist jedoch weder eine Implementierung
noch eine Schnittstelle oder ein eigener Repository-Nachweis vorhanden. Ein
separates Repository oder einen konkreten Einbaupunkt nimmt dieser Vorschlag
nicht an.

## 2. Zielarchitektur – Vorschlag unter Vorbehalt

Die tatsächlichen Technologien, Prozesse und Modulgrenzen sind erst nach
lesbarem Quellzugriff festzulegen. Bis dahin gelten folgende Prüfleitlinien,
keine implementierte Architektur:

- NIKNOLIG ist gemäß Projektvorgabe die Hauptplattform; zuerst müssen ihre
  vorhandene Struktur und produktiven Abläufe erfasst werden.
- NIKNOLIG Defense bleibt gemäß Projektvorgabe eine getrennte Sicherheitsdomäne.
  Austausch erfolgt nur über eine später ausdrücklich freigegebene, eng
  begrenzte Schnittstelle. Gemeinsame Modelle oder Bibliotheken verleihen keine
  Zugriffsrechte.
- Elektro-Engel wird erst nach Quellprüfung dem tatsächlich vorhandenen Modul
  zugeordnet. Eine eigenständige Plattform, ein Deployment oder eine
  Vertrauensdomäne wird nicht unterstellt.
- Gemeinsame APIs oder Datentypen werden erst spezifiziert, wenn konkrete
  Verbraucher, Datenflüsse, Verantwortliche und Berechtigungen belegt sind.
- Offlinebetrieb und geringe Betriebskosten sind Anforderungen zur Prüfung;
  sie sind keine nachgewiesenen Eigenschaften. Speicherung, Synchronisation,
  Konfliktbehandlung und Kostenfolgen benötigen eigene Entscheidungen.

## 3. Repository-Zuordnung

| Repository | Vorgesehene Rolle laut Auftrag | Verifizierter Inhalt / Status |
| --- | --- | --- |
| `nikolausnold/NIKNOLIG` | Hauptsystem und bestehende Cloudflare-Quelle | Nicht lesbar; Rolle und Cloudflare-Verbindung sind hier nicht technisch bestätigt. |
| `nikolausnold/NIKNOLIG-Defense` | Getrenntes Sicherheitssystem und bestehende Cloudflare-Quelle | Nicht lesbar; Rolle und Cloudflare-Verbindung sind hier nicht technisch bestätigt. |
| `nikolausnold/NIKNOLIG-Monorepo` | Integrations-, Dokumentations- und Prüfungsbasis; laut Auftrag keine Cloudflare-Worker-Quelle | Im geprüften Branch README und manueller Repository-Audit; keine Anwendungsintegration. |
| Elektro-Engel | Bestehendes Projekt/Modul laut Auftrag; Zuordnung offen | In den zugänglichen Dateien nicht implementiert oder anderweitig nachgewiesen; kein separates Repository wird angenommen. |

## 4. Cloudflare-Zuordnung

Es gab keinen lesenden Zugriff auf ein Cloudflare-Konto oder dessen Projekt-,
Build- und Deployment-Einstellungen. Daher ist keine Worker- oder Pages-
Verbindung unabhängig bestätigt.

| System | Vorgesehene Zuordnung laut Auftrag | Unabhängig bestätigter Quelllink, Branch, Build, Root oder Deployment |
| --- | --- | --- |
| NIKNOLIG | Bestehende Cloudflare-Quelle `nikolausnold/NIKNOLIG` | Nein; Repository-Inhalt und Cloudflare-Einstellungen ungeklärt. |
| NIKNOLIG Defense | Bestehende Cloudflare-Quelle `nikolausnold/NIKNOLIG-Defense` | Nein; Repository-Inhalt und Cloudflare-Einstellungen ungeklärt. |
| Monorepo | Nicht als Cloudflare-Worker-Quelle freigegeben | Keine Worker-Konfiguration oder Cloudflare-Verbindung in den geprüften Dateien. |

Für eine Verifikation werden ausschließlich lesbare Nachweise benötigt:
Cloudflare-Projektart (Workers oder Pages), tatsächlich verbundenes GitHub-
Repository und Produktionsbranch, Build-/Deploy-Kommandos und Root-Verzeichnis
sowie Ergebnis und Revision des letzten Deployments. IDs, Domains, Variablen
oder Secrets sind für diesen Entwurf nicht erhoben und werden nicht ergänzt.

## 5. Abhängigkeiten und API-Verträge

Aktuell sind keine Projekt-Abhängigkeiten oder laufenden APIs im Monorepo
nachgewiesen. Der Audit nutzt `actions/checkout@v4` mit
`persist-credentials: false` und Python-Standardbibliothek; dies ist eine
Audit-Abhängigkeit, keine Anwendungsintegration.

Vor Festlegung eines Vertrags müssen mindestens Schnittstellenbesitzer und
Verbraucher, Zweck, Datenklassifizierung, Identität, Authentifizierung,
Autorisierung je Aktion, Versionierung, Validierung, Fehlerverhalten,
Zeitlimits/Wiederholungen und Widerruf feststehen. Direkte Datenbank- oder
interne Modulzugriffe zwischen getrennten Systemen sind nicht als
Integrationsweg vorauszusetzen.

## 6. Sicherheit und Datenschutzrisiken

- Ohne Quellzugriff bleiben tatsächliche Angriffsflächen, Datenarten und
  Sicherheitskontrollen unbekannt.
- Geheimnisse gehören nicht in Quellcode, Commits, Beispielkonfigurationen,
  Logs oder diesen Plan. Falls später Zugangsdaten nötig werden, sind Ort,
  Eigentümer, Rotation und kleinstmögliche Berechtigungen getrennt freizugeben.
- NIKNOLIG Defense erhält keine impliziten Rechte aus gemeinsam genutzten
  Komponenten. Austausch muss authentifiziert, autorisiert, minimiert und
  nachvollziehbar sein.
- Logs sollen notwendige Sicherheitsereignisse ohne Tokens, Schlüssel oder
  unnötige personenbezogene Nutzdaten erfassen. Aufbewahrung und Zugriff sind
  vor Umsetzung festzulegen.
- Offline-Synchronisation darf keine Berechtigungen umgehen oder Vorgänge
  unkontrolliert wiederholen. Verschlüsselung, Konflikte, Löschung und
  Wiederholbarkeit sind offene Designfragen.
- Der Credential-Musterscan des vorhandenen Audits ist begrenzt und kein
  Nachweis, dass ein Repository frei von Geheimnissen ist.
- Keine kostenpflichtigen Dienste, erweiterten Berechtigungen oder
  Produktionsänderungen ohne gesonderte Freigabe.

## 7. Geordneter Umsetzungsplan mit Prüfkriterien

1. **Zugriff und Provenienz klären.** Lesenden Zugriff auf die beiden
   Quell-Repositories und Cloudflare-Konfigurationsnachweise herstellen.
   *Prüfkriterium:* Repository-Revisionen und tatsächliche Cloudflare-
   Verbindungen sind unabhängig belegbar; Geheimnisse werden nicht geteilt.
2. **Quelleninventur durchführen.** README, Struktur, Einstiegspunkte,
   Konfigurationen, Tests, Buildsysteme und relevante Sicherheitsabläufe nur
   lesend dokumentieren.
   *Prüfkriterium:* Jede Aussage verweist auf vorhandene Dateien/Revisionen;
   unbekannte Punkte bleiben ausdrücklich offen.
3. **Zielgrenzen und Datenflüsse freigeben.** Elektro-Engels Einordnung,
   Defense-Trennung und benötigte Austauschfälle mit Verantwortlichen
   festlegen.
   *Prüfkriterium:* Daten, Richtung, Nutzer/Akteur, Berechtigung und
   Fehlerverhalten sind fachlich und sicherheitlich freigegeben.
4. **Verträge und Kosten-/Offline-Entscheidungen spezifizieren.** Nur
   tatsächlich benötigte, versionierte APIs und Modelle planen.
   *Prüfkriterium:* Authentifizierung, Autorisierung, Datenschutz,
   Offlineverhalten und Betriebskosten sind geprüft; keine Annahme wird als
   Implementierung ausgegeben.
5. **CI und Tests vorbereiten.** Bestehende Quellprojektverfahren erhalten und
   geeignete isolierte Tests für Verträge, Berechtigungen und Fehlerfälle
   festlegen.
   *Prüfkriterium:* Tests laufen ohne Produktionszugriff, echte Secrets oder
   kostenpflichtige Dienste.
6. **Änderungsvorschlag separat vorlegen.** Erst nach Inventur und Freigabe
   Änderungen in einem reviewbaren Branch planen.
   *Prüfkriterium:* Diff ist auf die freigegebenen Dateien begrenzt; Reviews
   und notwendige Prüfungen sind erfolgreich; keine Änderung wird ungeprüft
   nach `main` übernommen.
7. **Deployment und Rollback gesondert freigeben.** Bestehende Cloudflare-
   Verbindungen verwenden, sofern verifiziert und autorisiert; kein neues
   Projekt oder Worker anlegen.
   *Prüfkriterium:* Ziel, Revision, Auswirkungen, Zuständigkeit und
   Rollback-Verfahren sind bestätigt. Ein Deployment erfolgt nur nach
   ausdrücklicher menschlicher Freigabe.

## 8. Offene Fragen und fehlende Zugriffsrechte

1. Kann der prüfende GitHub-Zugriff `Metadata: read` und `Contents: read`
   für [`NIKNOLIG`](https://github.com/nikolausnold/NIKNOLIG) und
   [`NIKNOLIG-Defense`](https://github.com/nikolausnold/NIKNOLIG-Defense)
   erhalten? Aktuelle API-Abfragen lieferten bei beiden `404`; das beweist
   weder Nichtexistenz noch eindeutig eine bestimmte Berechtigungslücke.
2. Kann die tatsächliche Cloudflare-Verbindung für jedes der beiden Systeme
   read-only belegt werden, einschließlich Produktart, Quellrepository,
   Produktionsbranch, Build-/Deploy-Einstellungen, Root und letztem
   Deployment-Ergebnis?
3. Welche nachweisbare Komponente in NIKNOLIG enthält Elektro-Engel, und welche
   Funktionen/Ein- und Ausgaben bestehen tatsächlich?
4. Welche Informationen dürfen zwischen NIKNOLIG und Defense in welcher
   Richtung ausgetauscht werden, und wer genehmigt die Freigabe?
5. Welche Daten müssen offline verfügbar sein; welche Datenschutz-,
   Aufbewahrungs-, Kosten- und Wiederherstellungsanforderungen gelten?
6. Welche Build-, Test-, Review-, Deployment- und Rollback-Verfahren sind für
   die bestehenden Quellen bereits verbindlich?

**Nächster sicherer Schritt:** Zunächst lesenden Zugang zu beiden Quell-
Repositories und geeignete read-only Cloudflare-Nachweise bereitstellen.
Danach die Inventur anhand konkreter Revisionen vervollständigen. Bis dahin
bleiben Architekturdetails, Integrationsstatus und Produktionsbereitschaft
ungeklärt.
