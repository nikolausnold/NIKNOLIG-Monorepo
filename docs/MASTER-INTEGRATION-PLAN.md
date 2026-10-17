# NIKNOLIG Master-Integration – Inventur und Vorschlag

**Status:** Android-Module im Monorepo umgesetzt. Elektro-Engel ist eine
Systemfunktion des NIKNOLIG-Systems. Die NIKNOLIG-App bietet eine lokale
Assistenzoberfläche ohne KI-/Backend- oder Geräteintegration. Eine produktive
Integration, Cloudflare-Verbindung und Deployment sind nicht nachgewiesen oder
freigegeben.

**Inventurstand:** 2026-10-17

**Historischer Inventurbranch:** `copilot/maintain-existing-work`

**Historischer Inventurcommit:** `48476be8fbbad2ddff7e9792d68c1ea80c6a8df2`

Dieser Plan trennt Repository-Fakten von Angaben und Zielvorstellungen. Nicht
lesbare Quellen oder nicht zugängliche Cloudflare-Einstellungen werden nicht
als bestätigt behandelt. Die folgende Monorepo-Integration ändert weder die
Quell-Repositories noch Websites oder Deployments und genehmigt keinen
Produktivzugriff.

## Aktueller Monorepo-Integrationsstand

Die Android-Projekte sind als unabhängige Gradle-Module `:niknolig` und
`:niknolig-defense` unter `apps/` eingebunden. Ihre `applicationId`s sind
`com.niknolig.app` und `com.niknolig.defense`; die Defense-App hat zusätzlich
einen eigenen Namespace und ein eigenes Kotlin-Paket. Es gibt keine
Modulabhängigkeit, gemeinsame Laufzeitbibliothek, App-zu-App-Schnittstelle oder
neue Android-Berechtigung. Die vorhandenen Launcher-/internen Activity-Grenzen
und deaktivierten Backups bleiben bestehen.

Die `app/`-Git-Trees der geprüften Quell-Commits
`nikolausnold/NIKNOLIG@3c4d6618a61604f6433639151e741371491a5f0d` und
`nikolausnold/NIKNOLIG-Defense@5f0f385089bc27347eacd282c13a546eb4511da2`
haben denselben Tree-Hash (`72ba65da7e3603fabf0938e6a6a254aa09dadb52`).
Damit ist nur dieselbe Android-Vorschau in zwei getrennten App-Sandboxes
nachgewiesen, keine Defense-spezifische Runtime oder Sicherheitsfunktion. Die
Monorepo-Konfiguration trennt App-IDs und Quellpakete; sie erfindet keine
Defense-Funktionen.

Websites und GitHub-Pages-Workflows verbleiben in den Quell-Repositories. Im
Monorepo gibt es keinen App-zu-App-Datenaustausch und keine bestätigte
Cloudflare-Verbindung. Der Android-Build-Workflow prüft beide Debug-Apps und
deren unterschiedliche Paket-IDs; Testquellen waren im geprüften Stand nicht
vorhanden.

## 1. Bestandsinventur

### Historischer Inventurstand vor der Android-Integration

Zum Inventurzeitpunkt enthält der ausgecheckte Arbeitsbranch diese getrackten
Projektdateien:

| Datei | Nachgewiesener Inhalt |
| --- | --- |
| `README.md` | Dokumentiert den begrenzten Repository-Stand und die fehlenden Anwendungskomponenten. |
| `.github/workflows/audit-workers.yml` | Manueller Read-only-Überblick über dieses Repository; keine Projekt-Workflows oder Skripte werden ausgeführt. |
| `docs/MASTER-INTEGRATION-PLAN.md` | Dieser Inventur- und Vorschlagsentwurf. |

Zu diesem historischen Stand wurden keine Anwendungsquellen,
API-Definitionen, Build-/Paketmanifestdateien, Tests, Wrangler-Konfigurationen
oder Deployment-Skripte gefunden. Im damaligen lokalen Arbeitsbaum waren keine
uncommitteten Änderungen vorhanden. GitHub zeigte
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

Die Inventur der sichtbaren Repositories des Accounts `nikolausnold` ergab sieben
Einträge einschließlich dieses Monorepos. Die folgenden externen Quellstände und
begrenzten Inhalte wurden read-only über die GitHub-API geprüft; es wurde nichts
geklont oder in externen Repositories geändert:

| Quelle | `main`-Revision | Geprüfte Struktur und Inhalte | Status / Grenzen |
| --- | --- | --- | --- |
| [nikolausnold/NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG) | `3c4d6618a61604f6433639151e741371491a5f0d` | README; Android-Gerüst mit Gradle-Wrapper, `app/`, `app/src/main/AndroidManifest.xml`; statische Website mit `index.html` und `styles.css`; Android-Build- und GitHub-Pages-Workflows. | README beschreibt eine frühe Vorschau. BLE, Gerätevertrauen, Sicherheitsfreigaben und produktive Funktionen seien noch nicht implementiert. |
| [nikolausnold/NIKNOLIG-Defense](https://github.com/nikolausnold/NIKNOLIG-Defense) | `5f0f385089bc27347eacd282c13a546eb4511da2` | README; Android-Gerüst mit Gradle-Wrapper, `app/`, `app/src/main/AndroidManifest.xml`; eigene statische Website mit `index.html` und `styles.css`; Android-Build- und GitHub-Pages-Workflows. | README/Website beschreiben die App und Defense als in Entwicklung; sie belegen keine produktive Sicherheitsintegration. |
| [nikolausnold/NIKNOLIG-iOS-](https://github.com/nikolausnold/NIKNOLIG-iOS-) | `ff77f13d01df26a2e4749d061a9ec6e9b05528d8` | README; eigenständiger Android-Gradle-Root mit `:app`, Website-Dateien und zusätzlichen Assets/Docs. | Trotz Repository-Namens kein nativer iOS-App-Root; README verweist auf das iOS-Monorepo. |
| [nikolausnold/NIKNOLIG-Defense-iOS-](https://github.com/nikolausnold/NIKNOLIG-Defense-iOS-) | `1100ed6e1f636c296747d4c2bc628a78c99975d2` | README; eigenständiger Android-Gradle-Root mit `:app`, Website-Dateien und zusätzlichen Assets/Docs. | Trotz Repository-Namens kein nativer iOS-App-Root; README beschreibt ein Android-Gerüst. |
| [nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo](https://github.com/nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo) | `afe4f5a3f0b84500437484a3bf0b3976d7b99e58` | Swift-Package für Health-Vertragsmodelle/Keychain-Adapter und Tests; getrennte NIKNOLIG- und Defense-iOS-App-Projekte/Schemes laut README. | Native iOS-Quelle mit SecurityChain-P0 als Release-Blocker; Simulator-Builds benötigen macOS/Xcode. Keine Produktionsfreigabe abgeleitet. |
| [nikolausnold/nold-edge-v0.1](https://github.com/nikolausnold/nold-edge-v0.1) | `3556a8d8d2d7d14fa685f37f2454fb0bbe38dfc4` | Android-Gradle-App `com.nold.edge`, Gradle Wrapper, BLE-Scaffold, Debug-APK-Workflow und Starter-ZIP. | README/STATUS nennen den Stand ungetestet und ohne BLE-Runtime. README behauptet widersprüchlich, `app/` und Wrapper fehlten; im aktuellen `main` sind beide vorhanden. Root-Level-Kotlin/Manifest parallel zu App-Quellen und ZIP weisen auf aufzuräumende doppelte Starterstände hin. Keine System-/Produktfreigabe. |

Das Register `config/system-repositories.json` erfasst nun alle sechs externen
Quellen mit den jeweils beobachteten `main`-Revisionen. Die beiden Repositories
mit „iOS“ im Namen werden nicht als native iOS-Apps fehlklassifiziert; das
separate iOS-Monorepo wird als eigentliche native iOS-Quelle beobachtet. Diese
Inventur bestätigt weder vollständige Kompatibilität noch Builds oder Releases.

Für NOLD Edge wurde lediglich der verfügbare Repository-Inhalt über die GitHub-API
eingesehen. Es wurde nicht in dieses Monorepo importiert, lokal gebaut oder
installiert. Die vorhandene Edge-Architekturbestandsaufnahme bestätigt, dass BLE-
Scaffold-Zustände keine NOLD-Sicherheitszustände sind und keine NOLD Core-,
SecurityChain-P0- oder Electro-Angel-Integration existiert. Das Register beobachtet
nur den Upstream-Commit; es erteilt keine Freigabe und startet keinen Build.

Beide geprüften Upstream-App-Gradle-Konfigurationen verwenden weiterhin
`com.niknolig.app` als Namespace und `applicationId`. Das wäre für parallele
Installationen der unveränderten Upstream-APK-Varianten ein Identitätskonflikt;
im Monorepo hat Defense deshalb Namespace und `applicationId`
`com.niknolig.defense`. Die READMEs nennen JDK 17, Gradle Wrapper 8.13,
Android Gradle Plugin 8.11.1 und compile SDK 35. Der Auftrag bestätigt getrennte
Apps, nicht einen produktiven Store-Release.

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

Elektro-Engel ist eine Systemfunktion des NIKNOLIG-Systems und kein eigenes
Projekt, Repository oder eine separate App. Die NIKNOLIG-App hat eine lokale
Anfrageoberfläche und ein Lernprofil; Anfrageverarbeitung durch KI/Backend,
Geräteerkennung und Steuerung sind nicht implementiert. Es gibt keine
gemeinsame Runtime oder einen systemübergreifenden Datenaustausch mit Defense.
Ebenso verlinkt die NIKNOLIG-Website
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
- Elektro-Engel ist eine Systemfunktion des NIKNOLIG-Systems, keine separate
  App, Plattform oder Repository. Die vorhandenen lokalen Lernprofil-Vorschauen
  belegen keine gemeinsame Laufzeit oder produktive Integration mit Defense.
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
| Elektro-Engel | Systemfunktion des NIKNOLIG-Systems; keine eigene App oder Repository | Lokale Assistenzoberfläche und Lernprofil in NIKNOLIG; keine KI-/Backend-, Geräte- oder Defense-Integration nachgewiesen. |

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

### GitHub-Pages- und Navigationsprüfung (2026-10-15)

Die Quell-Workflows `deploy-website.yml` beider separater Repositories deployen
nur bei `main` nach GitHub Pages. Die erfolgreichen Deployment-Logs nennen die
tatsächlichen URLs:

| Website | Pages-URL und letzter erfolgreicher Deploy | Abgleich mit Quellstand |
| --- | --- | --- |
| NIKNOLIG | [`https://nikolausnold.github.io/NIKNOLIG/`](https://nikolausnold.github.io/NIKNOLIG/); [Deploy #4](https://github.com/nikolausnold/NIKNOLIG/actions/runs/38316422738), `81e30ffbc279b370974bccf995105b68b040a59c` | `main` steht inzwischen auf `3c4d6618a61604f6433639151e741371491a5f0d`; die Website ist nicht auf dem aktuellen `main`-Stand deployed. |
| NIKNOLIG Defense | [`https://nikolausnold.github.io/NIKNOLIG-Defense/`](https://nikolausnold.github.io/NIKNOLIG-Defense/); [Deploy #3](https://github.com/nikolausnold/NIKNOLIG-Defense/actions/runs/38328310314), `5f0f385089bc27347eacd282c13a546eb4511da2` | Der erfolgreiche Deploy-Commit entspricht dem abgefragten aktuellen `main`-Commit. |

Der NIKNOLIG-Quellstand bei `main` enthält in `index.html` den Link
`https://github.com/nikolausnold/-NIKNOLIG-Defense/tree/main`. Dieser Link führt
wegen des zusätzlichen Bindestrichs auf ein nicht existentes Repository und
antwortete bei der Prüfung mit HTTP 404. Die korrekte Repository-URL
`https://github.com/nikolausnold/NIKNOLIG-Defense/tree/main` antwortete mit HTTP
200. Der fehlerhafte Link zeigt außerdem auf GitHub-Quellcode statt auf die
Defense-Website. Auf der Defense-Website wurde kein Rücklink zur NIKNOLIG-Website
gefunden; ein geforderter wechselseitiger Website-Link ist nicht dokumentiert.

Die HTTP-Aufrufe beider `github.io`-URLs konnten aus dieser Laufzeit nicht
abgeschlossen werden: Die DNS-Auflösung scheiterte mit `No address associated
with hostname`. Deshalb sind Live-HTTP-Status, Erreichbarkeit und Redirects
unbestätigt; erfolgreiche Actions-Deployments sind kein Live-Aufrufnachweis. Die
internen Navigationsanker beider geprüfter HTML-Dateien verweisen auf vorhandene
Section-IDs. Ein App-Installations- oder App-Startlink wurde nicht gefunden.
Die Website-Quellen liegen in den jeweiligen Quell-Repositories und wurden von
diesem Monorepo-Audit aus nicht verändert.

Der Auftraggeber teilte mit, die GitHub-App „Cloudflare Workers und Seiten“ sei
für alle Repositorys mit Lese-/Schreibzugriff installiert. Das ist eine
Nutzerangabe, kein aus den vorliegenden GitHub-Workflows ablesbarer Nachweis
einer Cloudflare-Konto-Verbindung. Eine GitHub-App-Installation oder
GitHub-Pages-Deployment belegt für sich weder ein Cloudflare-Projekt noch
dessen Git-Verknüpfung.

Im Monorepo sind Android-Quellen und ein Android-Build-Workflow vorhanden.
Wrangler-/Cloudflare-Konfiguration und ein Cloudflare-Deploymentworkflow fehlen
weiterhin. Die Quell-Root- und Workflow-Inventare belegen die
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
Einstellungsnachweis und der Deploymentstatus genügen. Beim aktuellen Versuch
scheiterte bereits die Namensauflösung von `dash.cloudflare.com` (`No address
associated with hostname`); ein angemeldeter Dashboard-Zugriff war daher nicht
möglich. Die Suche in beiden GitHub-Quell-Repositories ergab keine
Cloudflare-/Wrangler-Konfiguration. Dies bestätigt keine Cloudflare-Verbindung
und schließt eine außerhalb der Repositorys konfigurierte Verbindung nicht aus.

## 5. Abhängigkeiten und API-Verträge

Die Android-Module verwenden die in den Quell-Repositories vorhandenen
Gradle-/Android-Plugins; laufende APIs oder App-zu-App-Verträge sind im
Monorepo nicht nachgewiesen. Der Audit nutzt `actions/checkout@v4` mit
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
3. **Zielgrenzen und Datenflüsse freigeben.** Elektro-Engel als
   Systemfunktion, Defense-Trennung und etwaige benötigte Austauschfälle mit
   Verantwortlichen festlegen.
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
2. Wo liegt die tatsächliche API-Testworkflow-Datei? Die Actions-Liste nennt
   einen API-Testworkflow, aber der aktuelle Workflow-Verzeichnisabruf und der
   direkte Dateiabruf bestätigten keine Datei; es wurden keine zugehörigen Runs
   zurückgegeben.
3. Der falsche NIKNOLIG-Website-Link
   `https://github.com/nikolausnold/-NIKNOLIG-Defense/tree/main` ist bestätigt
   (HTTP 404). Er muss in `nikolausnold/NIKNOLIG` auf die verifizierte
   Defense-Pages-URL korrigiert und nach einem Deploy live geprüft werden; diese
   Korrektur liegt außerhalb des Monorepos.
4. Welche Austauschdaten und Aktionen dürfen zwischen NIKNOLIG und Defense
   fließen, in welche Richtung und mit welcher Genehmigung?
5. Welche Daten müssen offline verfügbar sein; welche Datenschutz-,
   Aufbewahrungs-, Kosten- und Wiederherstellungsanforderungen gelten?
6. Welche konkreten Release-Anforderungen, Review-Gates und Rollback-
   Verfahren gelten über die vorhandenen Debug-Builds und GitHub-Pages-
   Deployments hinaus?
7. Die aktuelle Android-Releasepipeline baut signierte APKs und vergleicht den
   APK-Fingerabdruck mit dem Fingerabdruck des im selben Lauf verwendeten
   Keystores. Eine unabhängig freigegebene Zertifikat-Fingerprint-Referenz wird
   im Workflow nicht geprüft. Ein erfolgreicher Lauf belegt daher die interne
   Übereinstimmung, aber nicht die unabhängige Freigabe oder Kontinuität der
   Signieridentität. Der erfolgreiche Release-Lauf [#13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201)
   verwendete `main` bei Commit `c8d152f4dff28f452e768b2379ebedf6ae4688e4`.
   Er lud die Artefakte [NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201/artifacts/11974091975)
   und [NIKNOLIG Defense](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201/artifacts/11974306823)
   hoch; beide laufen am 16.10.2026 um 12:43 UTC ab. Der erfolgreiche
   [Debug-Autobuild #73](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38737020384)
   verwendete denselben Commit. Diese Läufe belegen weder unabhängige
   Signierfreigabe noch ein Store-Release. Die Pipeline lädt APK-Artefakte hoch,
   sie veröffentlicht nicht in einem App-Store.
8. Beide Apps bleiben separate Vorschau-Apps. Für NIKNOLIG Defense ist keine
   unabhängige, Defense-spezifische Sicherheitsfunktion implementiert oder
   verifiziert; die statische Geräte-Statusanzeige ist keine Geräteerkennung.
   Produktumfang und zutreffende Store-/Marketingaussagen sind vor einem
   produktiven Defense-Release zu entscheiden und zu belegen.

**Nächster sicherer Schritt:** Den bestätigten fehlerhaften Defense-Link im
NIKNOLIG-Quellrepository auf die verifizierte
`https://nikolausnold.github.io/NIKNOLIG-Defense/`-URL korrigieren und nach
erfolgreichem Pages-Deploy live testen. Danach die NIKNOLIG-Website auf ihren
aktuellen `main`-Stand deployen und beide Live-URLs von einer Umgebung mit
funktionierender DNS-Auflösung auf Status, Redirects und Navigation prüfen. Die
Korrektur und Deployments wurden in diesem Audit nicht vorgenommen. Für
Cloudflare bleibt ein redigierter read-only Einstellungsnachweis beider Projekte
erforderlich. Ein produktiver Android-Release bleibt außerdem von den oben
genannten Scope-, Rechts- und unabhängig verifizierten Signierfreigaben abhängig.
