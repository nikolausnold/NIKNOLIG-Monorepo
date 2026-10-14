# NIKNOLIG Master-Integration – Inventur und Vorschlag

**Status:** Entwurf zur Prüfung, keine Implementierungsfreigabe

**Inventurstand:** 2026-10-14

**Geprüfter Arbeitsbranch:** `copilot/maintain-existing-work`

**Geprüfter Commit:** `48476be8fbbad2ddff7e9792d68c1ea80c6a8df2`

Dieser Entwurf trennt Repository-Fakten von Angaben und Zielvorstellungen. Nicht
lesbare Quellen oder nicht zugängliche Cloudflare-Einstellungen werden nicht
als bestätigt behandelt. Er genehmigt weder Änderungen noch Veröffentlichung,
Produktivzugriff oder Deployment.

## 1. Bestandsinventur

### Im Monorepo nachgewiesen

Zum Inventurzeitpunkt enthält der ausgecheckte Arbeitsbranch diese getrackten
Projektdateien:

| Datei | Nachgewiesener Inhalt |
| --- | --- |
| `README.md` | Dokumentiert den begrenzten Repository-Stand und die fehlenden Anwendungskomponenten. |
| `.github/workflows/audit-workers.yml` | Manueller Read-only-Überblick über dieses Repository; keine Projekt-Workflows oder Skripte werden ausgeführt. |
| `docs/MASTER-INTEGRATION-PLAN.md` | Dieser Inventur- und Vorschlagsentwurf. |

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

Die GitHub-Inhaltsabfragen sind jetzt erfolgreich. Die folgenden Revisionsstände
und begrenzten Inhalte wurden read-only über die GitHub-API geprüft; es wurde
nichts geklont:

| Quelle | `main`-Revision | Geprüfte Struktur und Inhalte | Status / Grenzen |
| --- | --- | --- | --- |
| [nikolausnold/NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG) | `3c4d6618a61604f6433639151e741371491a5f0d` | README; Android-Gerüst mit Gradle-Wrapper, `app/`, `app/src/main/AndroidManifest.xml`; statische Website mit `index.html` und `styles.css`; Android-Build- und GitHub-Pages-Workflows. | README beschreibt eine frühe Vorschau. BLE, Gerätevertrauen, Sicherheitsfreigaben und produktive Funktionen seien noch nicht implementiert. |
| [nikolausnold/NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense) | `5f0f385089bc27347eacd282c13a546eb4511da2` | README; Android-Gerüst mit Gradle-Wrapper, `app/`, `app/src/main/AndroidManifest.xml`; eigene statische Website mit `index.html` und `styles.css`; Android-Build- und GitHub-Pages-Workflows. | README/Website beschreiben die App und Defense als in Entwicklung; sie belegen keine produktive Sicherheitsintegration. |

Beide geprüften App-Gradle-Konfigurationen verwenden `com.niknolig.app` als
Namespace und `applicationId`. Die READMEs nennen JDK 17, Gradle Wrapper 8.13,
Android Gradle Plugin 8.11.1 und compile SDK 35. Das ist ein konkreter
Identitätskonflikt, falls beide APKs gleichzeitig als getrennte Apps installiert
werden sollen. Eine beabsichtigte gemeinsame oder getrennte Veröffentlichung
ist nicht belegt.

Beide Repositories listen `android-build.yml` und `deploy-website.yml` in
`.github/workflows`. Die Website-Workflows bauen ein GitHub-Pages-Artefakt und
deployen mit `actions/deploy-pages`; dies ist kein Cloudflare-Deployment.
GitHub Actions meldet für NIKNOLIG einen erfolgreichen Android-Build auf der
aktuellen `main`-Revision und für Defense ebenfalls einen erfolgreichen
Android-Build auf der aktuellen `main`-Revision. Die jüngste erfolgreiche
NIKNOLIG-GitHub-Pages-Ausführung lief auf `81e30ffbc279b370974bccf995105b68b040a59c`,
nicht auf dem aktuell ausgewiesenen `main`-Stand. Die jüngste erfolgreiche
Defense-GitHub-Pages-Ausführung lief auf ihrer aktuellen `main`-Revision.

Für NIKNOLIG ist ein als Pre-release markiertes GitHub-Release
`13.10.2026` vorhanden; für Defense wurde in der Releases-Abfrage kein Release
zurückgegeben. Das bestätigt keinen Cloudflare- oder Android-Produktiv-Release.
API-Tests erscheinen in der Actions-Workflowliste, aber die Datei
`.github/workflows/api-tests.yml` war über den Dateiabruf nicht verfügbar, die
Workflow-Verzeichnisse listeten sie nicht und die abgefragten Runs lieferten
keine Ergebnisse. Das bleibt eine nicht aufgelöste Inkonsistenz.

Elektro-Engel erscheint in der NIKNOLIG-README als Assistenz-/Lernkonzept und
in der Website als Entwicklungsziel. Die geprüften Hinweise belegen keine
eigenständige API oder getrennte Runtime. Ebenso verlinkt die NIKNOLIG-Website
ein Defense-Ziel mit dem Repository-Pfad `nikolausnold/-NIKNOLIG-Defense`
(führender Bindestrich); das tatsächlich geprüfte Repository heißt
`nikolausnold/NIKNOLIG-Defense` ohne diesen Bindestrich. Der Link muss vor
öffentlicher Nutzung geprüft und gegebenenfalls separat korrigiert werden.

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
| `nikolausnold/NIKNOLIG` | Hauptsystem und behauptete bestehende Cloudflare-Quelle | `main` ist lesbar; Android-Gerüst und GitHub-Pages-Website nachgewiesen. Cloudflare-Verbindung nicht bestätigt. |
| `nikolausnold/NIKNOLIG-Defense` | Getrenntes Sicherheitssystem und behauptete bestehende Cloudflare-Quelle | `main` ist lesbar; Android-Gerüst und GitHub-Pages-Website nachgewiesen. Cloudflare-Verbindung nicht bestätigt. |
| `nikolausnold/NIKNOLIG-Monorepo` | Integrations-, Dokumentations- und Prüfungsbasis; laut Auftrag keine Cloudflare-Worker-Quelle | Im geprüften Branch README, Audit-Workflow und dieser Plan; keine Anwendungsintegration. |
| Elektro-Engel | Assistenz-/Lernfunktion innerhalb NIKNOLIG laut Quellen-README/Website | Als Entwicklungsziel beschrieben; keine eigene Runtime/API in den geprüften Dateien nachgewiesen. |

## 4. Cloudflare-Zuordnung

### Bereits vorhandene, konkrete Nachweise

Die Quell-Repositories sind über die vorhandene GitHub-Verbindung lesbar; ihre
`main`-Revisionen sind oben festgehalten. Die nachfolgenden Actions-Nachweise
betreffen **GitHub Actions/GitHub Pages**, nicht Cloudflare:

| Quelle | Nachweis | Was er belegt |
| --- | --- | --- |
| NIKNOLIG | [Erfolgreicher Android-Build](https://github.com/nikolausnold/NIKNOLIG/actions/runs/38383624857) auf `main` bei `3c4d6618a61604f6433639151e741371491a5f0d` | Android-Build-Workflow auf dieser Revision. Kein Store- oder Cloudflare-Release. |
| NIKNOLIG | [Deploy website #4](https://github.com/nikolausnold/NIKNOLIG/actions/runs/38316422738), erfolgreich auf Commit `81e30ffbc279b370974bccf995105b68b040a59c` | GitHub-Pages-Deployment der Website auf einem älteren Commit als das aktuelle `main`. |
| NIKNOLIG | [GitHub Pre-release `13.10.2026`](https://github.com/nikolausnold/NIKNOLIG/releases) | Ein als Pre-release markiertes GitHub-Release existiert; kein Cloudflare- oder Android-Produktionsnachweis. |
| NIKNOLIG Defense | [Erfolgreicher Android-Build](https://github.com/nikolausnold/NIKNOLIG-Defense/actions/runs/38328310272) auf `main` bei `5f0f385089bc27347eacd282c13a546eb4511da2` | Android-Build-Workflow auf dieser Revision. Kein Store- oder Cloudflare-Release. |
| NIKNOLIG Defense | [Deploy website #3](https://github.com/nikolausnold/NIKNOLIG-Defense/actions/runs/38328310314), erfolgreich auf `main` bei `5f0f385089bc27347eacd282c13a546eb4511da2` | GitHub-Pages-Deployment der Website auf dieser Revision. |
| Monorepo | [Read-only Audit #10](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38524704790), erfolgreich auf `main` bei `2caa4098abf8a6464c21720383b7f47289b5be98` | Nur den manuellen Monorepo-Inventurworkflow; keine Anwendung, Cloudflare-Verbindung oder Deployment. |

Der Auftraggeber teilte mit, die GitHub-App „Cloudflare Workers und Seiten“ sei
für alle Repositorys mit Lese-/Schreibzugriff installiert. Das ist eine
Nutzerangabe, kein aus den vorliegenden GitHub-Workflows ablesbarer Nachweis
einer Cloudflare-Konto-Verbindung. Eine GitHub-App-Installation oder
GitHub-Pages-Deployment belegt für sich weder ein Cloudflare-Projekt noch
dessen Git-Verknüpfung.

Im Monorepo sind nur `README.md`, dieser Plan und
`.github/workflows/audit-workers.yml` vorhanden; insbesondere fehlen
Wrangler-/Cloudflare-Konfiguration, Anwendungscode und ein Cloudflare-
Deploymentworkflow. Die Quell-Root- und Workflow-Inventare belegen die
GitHub-Pages-Workflows; die hier vorliegenden Nachweise belegen keine
Cloudflare-Worker-/Pages-Verbindung.

| System | GitHub-Nachweis | Cloudflare-Nachweis |
| --- | --- | --- |
| NIKNOLIG | `main` lesbar; Workflow `deploy-website.yml` veröffentlicht das Website-Artefakt mit GitHub Pages. | Keine Verbindung, Produktionsbranch, Build-Befehl oder Deploy-Status bei Cloudflare verifiziert. Erfolgreicher Pages-Lauf #4 liegt auf einem älteren Commit als aktuelles `main`. |
| NIKNOLIG Defense | `main` lesbar; Workflow `deploy-website.yml` veröffentlicht das Website-Artefakt mit GitHub Pages. | Keine Verbindung, Produktionsbranch, Build-Befehl oder Deploy-Status bei Cloudflare verifiziert. Erfolgreicher Pages-Lauf #3 liegt auf aktuellem `main`. |
| Monorepo | Vom Auftrag als nicht freigegebene Worker-Quelle ausgeschlossen; vorhanden ist ein manueller Read-only-Repository-Audit. | Keine Wrangler-Konfiguration oder Cloudflare-Verbindung in den geprüften Repository-Dateien. |

### Konkrete Cloudflare-Nachweislücken

Für **jede** behauptete Cloudflare-Anwendung fehlt ein lesbarer, aktueller
Cloudflare-Projektnachweis, der diese Punkte ausweist:

1. Cloudflare-Produktart und Projekt-/Worker-Name.
2. Tatsächlich verbundenes GitHub-Repository und Produktionsbranch.
3. Build-Befehl, Deploy-Befehl und eingestelltes Root-Verzeichnis.
4. Ergebnis, Zeitpunkt und Quell-Commit des letzten Cloudflare-Deployments.

In dieser Umgebung steht keine Cloudflare-Dashboard-/API-Ansicht oder
Cloudflare-spezifische Verbindung zur Verfügung; auch ein
Cloudflare-Deploymentprotokoll liegt nicht vor. Aus den GitHub-Pages-Läufen
können diese Felder nicht abgeleitet werden. Es werden dafür keine Tokens,
Secrets, IDs oder Domains benötigt; ein redigierter read-only
Einstellungsnachweis und der Deploymentstatus genügen.

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

- Die dokumentierte Inventur prüfte begrenzte Dateien und Konfigurationen der
  Quell-Repositories, aber keine vollständige Sicherheitsprüfung ihres Codes,
  ihrer Abhängigkeiten, Laufzeit oder Deployments. Diese Angriffsflächen,
  Datenarten und Kontrollen sind daher nicht abschließend verifiziert.
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

1. **Provenienz klären.** Die bestätigten Quellrevisionen festhalten und
   Cloudflare-Konfigurationsnachweise read-only prüfen.
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

## 8. Offene Fragen und Blocker

Der Lesezugriff auf beide GitHub-Quell-Repositories funktioniert für `main`;
fehlender GitHub-Contents-Zugriff ist nach den oben dokumentierten
Inhaltsabfragen und Actions-Nachweisen nicht der Blocker. Die berichtete
GitHub-App-Installation ist nicht gleichbedeutend mit verifiziertem
Cloudflare-Kontozugriff.

1. Für NIKNOLIG und Defense jeweils fehlen die vier oben aufgeführten
   Cloudflare-Projektdaten (Produktart/Name, Repository/Produktionsbranch,
   Build-/Deploy-Befehl/Root sowie letzter Deploy-Status mit Quell-Commit).
2. Welche Repository-/App-Identität ist beabsichtigt? Beide Android-App-
   Konfigurationen verwenden `com.niknolig.app`; eine getrennte Installation
   der zwei APKs wäre damit nicht belegt.
3. Wo liegt die tatsächliche API-Testworkflow-Datei? Die Actions-Liste nennt
   einen API-Testworkflow, aber der aktuelle Workflow-Verzeichnisabruf und der
   direkte Dateiabruf bestätigten keine Datei; es wurden keine zugehörigen Runs
   zurückgegeben.
4. Ist der Defense-Link in der NIKNOLIG-Website mit dem führenden Bindestrich
   (`nikolausnold/-NIKNOLIG-Defense`) beabsichtigt? Er stimmt nicht mit dem
   tatsächlich geprüften Repository-Namen `nikolausnold/NIKNOLIG-Defense`
   überein.
5. Welche Austauschdaten und Aktionen dürfen zwischen NIKNOLIG und Defense
   fließen, in welche Richtung und mit welcher Genehmigung?
6. Welche Daten müssen offline verfügbar sein; welche Datenschutz-,
   Aufbewahrungs-, Kosten- und Wiederherstellungsanforderungen gelten?
7. Welche konkreten Release-Anforderungen, Review-Gates und Rollback-
   Verfahren gelten über die vorhandenen Debug-Builds und GitHub-Pages-
   Deployments hinaus?

**Nächster sicherer Schritt:** Für beide bereits bestehenden Cloudflare-
Projekte einen redigierten read-only Einstellungsnachweis mit genau den vier
aufgeführten Feldern und den letzten Deploy-Status/Commit bereitstellen. Die
GitHub-Quellen und GitHub-Pages-/Android-Workflow-Nachweise sind vorhanden;
die Cloudflare-Zuordnung bleibt ungeklärt. App-ID-Absicht und Defense-Link-Ziel
bleiben zusätzliche, nicht in diesem Monorepo lösbare Release-Fragen.
