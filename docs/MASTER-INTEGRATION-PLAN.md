# NIKNOLIG Master-Integration – Inventur und Vorschlag

**Status:** Android-Module im Monorepo umgesetzt. Elektro-Engel ist eine
Systemfunktion des NIKNOLIG-Systems. Die NIKNOLIG-App bietet eine lokale
Assistenzoberfläche ohne KI-/Backend- oder Geräteintegration. Eine produktive
Integration, Cloudflare-Verbindung und Deployment sind nicht nachgewiesen oder
freigegeben.

**Inventurstand:** 2026-10-14

**Historischer Inventurbranch:** `copilot/maintain-existing-work`

**Historischer Inventurcommit:** `48476be8fbbad2ddff7e9792d68c1ea80c6a8df2`

Dieser Plan trennt Repository-Fakten von Angaben und Zielvorstellungen. Nicht
lesbare Quellen oder nicht zugängliche Cloudflare-Einstellungen werden nicht
als bestätigt behandelt. Die folgende Monorepo-Integration ändert weder die
Quell-Repositories noch Websites oder Deployments und genehmigt keinen
Produktivzugriff.

**Produktabgrenzung ergänzt am 21.10.2026:** NIKNOLIG: allgemeine
Systemfunktionen. Defense: zusätzliche Sicherheits- und Notfallfunktionen,
einschließlich Elektro-Engels Infrastruktur-Erkennung und Reparaturhinweisen
ausschließlich in Defense. Keine Infrastruktur-Erkennung in der normalen
NIKNOLIG-App. Das präzisiert den Zielumfang, nicht die historische Inventur
oder den implementierten Bestand. Das
[D-01-Prüfprotokoll](securitychain-p0-specification.md#d-01-prüfprotokoll-bestätigte-produktgrenzen-und-offene-detailfreigaben)
führt Datenzugriffe, Berechtigungen, automatische Aktionen und Datenschutz
ausdrücklich als offen; D-01 bleibt ohne vollständige Bestätigungen offen.
D-02 bis D-12 und sämtliche technischen Stop-Gates bleiben unverändert.

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

Die GitHub-Inhaltsabfragen sind jetzt erfolgreich. Die folgenden Revisionsstände
und begrenzten Inhalte wurden read-only über die GitHub-API geprüft; es wurde
nichts geklont:

| Quelle | `main`-Revision | Geprüfte Struktur und Inhalte | Status / Grenzen |
| --- | --- | --- | --- |
| [nikolausnold/NIKNOLIG](https://github.com/nikolausnold/NIKNOLIG) | `2531bdfa9a4c7e949c2778fbf515c132fed9d4d3` | `app/` Android-Quelle; statische Website (`index.html`, `styles.css`, Assets) und `.github/workflows/deploy-website.yml`; außerdem ein `ios/`-Projektverzeichnis. | Aktueller `main`-Stand zum 23.10.2026. |
| [nikolausnold/-NIKNOLIG-Defense-Website](https://github.com/nikolausnold/-NIKNOLIG-Defense-Website) | `26922857d919be4a5ae01a8cad016e69c174fba1` | `app/` Android-Quelle; statische Website (`index.html`, `styles.css`, Assets) und `.github/workflows/deploy-website.yml`. | Aktueller `main`-Stand zum 23.10.2026; der Repositoryname enthält einen führenden Bindestrich. |
| [nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo](https://github.com/nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo) | `afe4f5a3f0b84500437484a3bf0b3976d7b99e58` | Getrennte Xcode-Projekte unter `apps/niknolig-ios/` und `apps/niknolig-defense-ios/`. | `main` enthält die beiden gelisteten iOS-Projekte; eine verbindliche Vorrang-/Mirror-Beziehung zu den lokalen Monorepo-Zielen oder `NIKNOLIG/ios` ist nicht belegt. |

**Aktualisierung der Defense-Website-Zuordnung:** Die vorstehende Defense-Zeile
ist ein historischer Repository-Snapshot. Laut aktueller Produktvorgabe ist
`nikolausnold/-NIKNOLIG-Defense-Website` archiviert und nicht mehr die aktuelle
Website-Quelle. Die Pflege erfolgt im aktiven App-Repository
[`nikolausnold/-niknolig-defense`](https://github.com/nikolausnold/-niknolig-defense).
Die GitHub-API lieferte für dieses Repository während des Audits HTTP 404; sein
Inhalt, Status und eine aktuelle Revision konnten daher nicht unabhängig
verifiziert werden.

Die externen Android-Projektpfade sind `NIKNOLIG/app` und
`-NIKNOLIG-Defense-Website/app`; im Monorepo entsprechen sie getrennten Modulen
`apps/niknolig` und `apps/niknolig-defense` mit unterschiedlichen
`applicationId`s. Die iOS-Ziele des Monorepos liegen gemeinsam im
`apps/ios/NIKNOLIG.xcodeproj`; der externe iOS-Workspace führt beide Projekte
getrennt in den oben genannten Pfaden. Das ist kein Nachweis, welches externe
iOS-Projektverzeichnis jeweils die alleinige Veröffentlichungsquelle ist.

Beide Android-/Website-Quell-Repositories listen `android-build.yml` und
`deploy-website.yml` in `.github/workflows`. Die Website-Workflows bauen ein
GitHub-Pages-Artefakt und deployen mit `actions/deploy-pages`; dies ist kein
Cloudflare-Deployment. Die aktuellen erfolgreichen Website-Läufe und ihre
Revisionsstände sind im Audit-Nachtrag vom 23.10.2026 dokumentiert.

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
| `nikolausnold/NIKNOLIG` | NIKNOLIG Android (`app/`), Website (Repository-Root) und ein iOS-Verzeichnis | `main` ist lesbar; GitHub-Pages-Website und die Android-Quelle sind nachgewiesen. Cloudflare-Verbindung nicht bestätigt. |
| `nikolausnold/-NIKNOLIG-Defense-Website` | NIKNOLIG Defense Android (`app/`) und Website (Repository-Root) | Aktueller `main`-Stand sowie erfolgreicher Pages-Deploy sind nachgewiesen. Keine Aussage über Archivierung oder Löschung anderer Repositorynamen. |
| `nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo` | Getrennte NIKNOLIG- und Defense-iOS-Projekte | Beide Projektverzeichnisse sind auf `main` vorhanden; Vorrang oder Mirror-Beziehung zu anderen iOS-Ablagen nicht belegt. |
| `nikolausnold/NIKNOLIG-Monorepo` | Lokale Android-Module, iOS-Vorschauziele, Integrationsdokumentation und Prüfungen | `apps/niknolig`, `apps/niknolig-defense` und zwei iOS-Targets in `apps/ios/`; kein Website- oder Cloudflare-Deployment nachgewiesen. |
| Elektro-Engel | Systemfunktion des NIKNOLIG-Systems; keine eigene App oder Repository | Lokale Assistenzoberfläche und Lernprofil in NIKNOLIG; keine KI-/Backend-, Geräte- oder Defense-Integration nachgewiesen. |

## 4. Cloudflare-Zuordnung

### GitHub-Actions-Nachweise (historische und aktuelle Deploymentstände)

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

### Aktueller Website- und App-Bindungsaudit (2026-10-23)

Dieser Nachtrag aktualisiert die Repo- und Deploymentstände aus der
15.-Oktober-Inventur. GitHub-Inhalte, Branches, Pull Requests und Actions wurden
read-only abgefragt; es wurden keine externen Repositories oder Websites geändert.

| Bereich | Tatsächlicher Repository-Pfad / Branch | Befund |
| --- | --- | --- |
| NIKNOLIG Android | Monorepo `apps/niknolig`; externe Quelle `nikolausnold/NIKNOLIG/app`, `main` @ `2531bdfa9a4c7e949c2778fbf515c132fed9d4d3` | Getrennte lokale Android-App `:niknolig`, `com.niknolig.app`. |
| NIKNOLIG Defense Android | Monorepo `apps/niknolig-defense`; laut aktueller Produktvorgabe externe Quelle `nikolausnold/-niknolig-defense` | Das frühere Repository `nikolausnold/-NIKNOLIG-Defense-Website` ist laut Produktvorgabe archiviert. Die GitHub-API lieferte für das owner-designierte aktive App-Repository HTTP 404; aktuelle Dateien und Revision konnten nicht verifiziert werden. |
| NIKNOLIG iOS | Monorepo `apps/ios/NIKNOLIG.xcodeproj` und `NIKNOLIGApp.swift`; separates iOS-Projekt `nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/apps/niknolig-ios`, `main` @ `afe4f5a3f0b84500437484a3bf0b3976d7b99e58` | Das NIKNOLIG-Repository enthält außerdem `ios/`. Welche externe Ablage für Releases maßgeblich ist, ist nicht belegt. |
| NIKNOLIG Defense iOS | Monorepo `apps/ios/NIKNOLIG.xcodeproj` und `NIKNOLIGDefenseApp.swift`; separates iOS-Projekt `nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo/apps/niknolig-defense-ios`, gleicher `main`-Stand | Getrenntes lokales Target; keine externe Veröffentlichungsquelle oder Store-Veröffentlichung nachgewiesen. |
| NIKNOLIG Website | `nikolausnold/NIKNOLIG`, Root-Dateien `index.html`, `styles.css`, `assets/niknolig-mark.svg`; `.github/workflows/deploy-website.yml`, `main` | [Pages-Lauf #36](https://github.com/nikolausnold/NIKNOLIG/actions/runs/39954787871) erfolgreich auf `6eec28fc830056b57127ddd06d934e62f2dba50d`; das Deploy-Log nennt `https://niknolig.com/`. PR [#41](https://github.com/nikolausnold/NIKNOLIG/pull/41) ist gemergt und ergänzt den SVG-Workflow-Trigger sowie Dokumentation. |
| NIKNOLIG Defense Website | Laut aktueller Produktvorgabe gepflegt im aktiven App-Repository [`nikolausnold/-niknolig-defense`](https://github.com/nikolausnold/-niknolig-defense) | Die GitHub-API lieferte bei diesem Audit HTTP 404; Inhalt und Deployment des aktiven Repositorys sind nicht unabhängig bestätigt. Das frühere Repository `nikolausnold/-NIKNOLIG-Defense-Website` ist archiviert; sein Pages-Lauf #35 und PR #4 sind historische Nachweise, keine aktuelle Eigentums- oder Deploymentbestätigung. |

Die verbindliche Website-Zuordnung für alle vier lokalen App-Targets ist
NIKNOLIG → `https://niknolig.com/` und NIKNOLIG Defense →
`https://defense.niknolig.com/`. Die Android-Supportseiten verwenden eine
produktspezifische URL-Ressource und `ACTION_VIEW`; die beiden nativen
iOS-Supportansichten verwenden jeweils einen externen `Link`. Es gibt keine
WebViews, Android-App-Link-Filter oder iOS-Associated-Domain-Einträge für diese
Websites.

Die früher dokumentierte GitHub-Pages-URL
`https://nikolausnold.github.io/NIKNOLIG-Defense/` ist keine offizielle
Defense-Domain und wird hier nur als historischer Website-Quellbefund geführt.
Die aktuellen offiziellen Domains wurden am 23.10.2026 mit `getent` und `curl`
geprüft; DNS-Auflösung scheiterte für beide (`curl`-Fehler 6, HTTP-Code 000).
Daher konnten weder HTTPS-Antwort noch TLS-Zertifikat oder Redirects geprüft
werden. Frühere GitHub-Pages-Läufe belegen keinen aktuellen Deploy und keine
öffentliche Erreichbarkeit. Eine Cloudflare-Verbindung ist weiterhin nicht
belegt.

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
| NIKNOLIG | `main` lesbar; aktueller dokumentierter Pages-Lauf [#36](https://github.com/nikolausnold/NIKNOLIG/actions/runs/39954787871) auf `6eec28f` erfolgreich. | Keine Cloudflare-Verbindung, Build- oder Deploy-Einstellungen verifiziert. |
| NIKNOLIG Defense | `nikolausnold/-NIKNOLIG-Defense-Website`, aktueller Pages-Lauf [#35](https://github.com/nikolausnold/-NIKNOLIG-Defense-Website/actions/runs/39912347042) auf `2692285` erfolgreich. | Keine Cloudflare-Verbindung, Build- oder Deploy-Einstellungen verifiziert. |
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
3. Ein früherer NIKNOLIG-Website-Snapshot enthielt den veralteten Link
   `https://nikolausnold.github.io/NIKNOLIG-Defense/`. Der aktuelle Zielinhalt
   wurde nicht erneut geprüft; der aktive Defense-Website-Quellstand ist laut
   Produktvorgabe im App-Repository `nikolausnold/-niknolig-defense`, dessen
   GitHub-API-Abruf im Audit HTTP 404 lieferte.
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

**Nächster sicherer Schritt:** Die Verfügbarkeit des owner-designierten
Defense-App-Repositorys und seiner aktuellen Website-Dateien klären; aus dem
Monorepo-Audit wurden keine externen Repositorys oder Websites geändert. Für
Cloudflare bleibt ein redigierter read-only Einstellungsnachweis beider Projekte
erforderlich. Ein produktiver Android-Release bleibt außerdem von den oben
genannten Scope-, Rechts- und unabhängig verifizierten Signierfreigaben abhängig.
