# Businessplan – NIKNOLIG, NIKNOLIG Defense und Elektro-Engel

**Status:** Arbeitsentwurf; keine Umsatz-, Kosten-, Markt- oder Funktionsprognose.  
**Stand:** 2026-10-14

Dieser Plan trennt belegte Repository-Fakten von Vorgaben und noch zu prüfenden
Ideen. Er beschreibt weder ein fertiges Produkt noch eine Investitions- oder
Erfolgsgarantie. Produktive Funktionen, Marktvalidierung und ein freigegebener
Release sind im Monorepo nicht belegt.

## 1. Geschäftsidee und Zusammenspiel

**Vorgegebene Positionierung:** NIKNOLIG ist die Hauptplattform. NIKNOLIG
Defense soll als getrenntes Sicherheitssystem beziehungsweise getrennte
Sicherheitsdomäne geführt werden. Elektro-Engel ist als Assistenz-/Lernkonzept
innerhalb von NIKNOLIG beschrieben, nicht als nachgewiesene eigenständige
Plattform oder Runtime.

**Belegter Entwicklungsstand:** Das Monorepo enthält zwei getrennte
Android-Module und App-IDs (`com.niknolig.app` und `com.niknolig.defense`).
Beide Module enthalten derzeit denselben Vorschau-Funktionsstand. Es gibt keine
Modulabhängigkeit, gemeinsame Laufzeitbibliothek oder App-zu-App-Schnittstelle.
Die Vorschau belegt keine produktive Geräte-, Sicherheits- oder
Cloud-Integration. Elektro-Engel hat eine begrenzte lokale Lernprofil-Vorschau;
automatisches Modelltraining oder produktiver KI-Betrieb sind nicht belegt.

**Geplantes Zusammenspiel:** NIKNOLIG soll Hauptzugang und Plattform sein;
Defense soll getrennt bleiben. Ein Datenaustausch oder gemeinsame Funktion ist
erst nach fachlicher und sicherheitlicher Freigabe konkreter Datenflüsse,
Berechtigungen und Verantwortlichkeiten vorgesehen. Ob und wie Elektro-Engel
später über die Vorschau hinaus angeboten wird, ist offen.

## 2. Geschäftsmodell und Preisstrategie

| Angebot | Vorgabe / belegter Stand | Offene Umsetzung |
| --- | --- | --- |
| NIKNOLIG | Verbindliche Produktregel: dauerhaft kostenlos. Das Monorepo enthält eine Android-Vorschau, keinen bestätigten Store-Release. | Store-Verfügbarkeit, Finanzierung, Betrieb und Bedingungen sind nicht festgelegt. Die kostenlose Bereitstellung ist in den jeweiligen Stores umzusetzen. |
| NIKNOLIG Defense | Verbindliche Produktregel: regulärer Preis einmalig **0,75 €**. Personen, die nachweislich nicht in der Lage sind, sich aus einer Notsituation zu befreien, sollen genau **48 Stunden** kostenlos nutzen können. Der Zeitraum beginnt mit der Aktivierung des Härtefallzugangs und endet exakt 48 Stunden danach; daraus folgt keine unbegrenzte Freischaltung. | Store- und Länderpreise, Steuern, Store-Gebühren, Auszahlung, Rückerstattungen, Lizenzumfang und konkrete Defense-Leistung sind zu klären. Nachweismethode, Missbrauchsbegrenzung, datenschutzrechtliche Umsetzung und technische Erfassung von Start und Ablauf sind noch festzulegen. Notwendige Notfallfunktionen dürfen nicht von einem vorherigen Nachweis abhängen. Kein Kaufangebot oder bestätigter Verkauf ist im Monorepo belegt. |
| Elektro-Engel | Als Assistenz-/Lernkonzept und begrenzte lokale Vorschau dokumentiert; kein eigener Preis belegt. | Eigenständigkeit, späterer Leistungsumfang, Preis und etwaige regulierte oder fachliche Einsatzbereiche sind offen. Nicht als separates kostenpflichtiges Produkt unterstellen. |

**Vorgeschlagene Erlösansätze, nicht beschlossen:** Die Preisvorgabe für
Defense ist die einzige benannte Preisidee. Weitere mögliche Einnahmequellen
wie freiwillige Unterstützung, Fördermittel oder klar abgegrenzte optionale
Zusatzleistungen wären zunächst zu prüfen und ausdrücklich zu entscheiden.
Sie sind weder vorhanden noch zugesagt; insbesondere werden keine
Werbe-, Abo-, Datenverkaufs- oder Partnerschaftserlöse behauptet.

## 3. Zielgruppen

Die folgenden Gruppen sind **Hypothesen für die spätere Validierung**, keine
nachgewiesenen Kunden- oder Nutzergruppen:

- Menschen, die verständliche und bewusst steuerbare digitale Technik suchen
  (NIKNOLIG);
- Nutzerinnen und Nutzer, für die ein separat abgegrenztes Sicherheitsangebot
  einen konkreten, nachweisbaren Nutzen hätte (NIKNOLIG Defense);
- Menschen, die eine nachvollziehbare technische Assistenz benötigen könnten
  (Elektro-Engel).

Bedarf, Zahlungsbereitschaft, Erreichbarkeit, Barrierefreiheit und
Marktgröße sind nicht untersucht. Es liegen hier keine Nutzerzahlen,
Kundeninterviews oder Marktdaten vor.

## 4. Entwicklung und Vermarktung

### Belegt / bereits vorhanden

- Zwei unabhängig installierbare Android-Vorschau-Module mit unterschiedlichen
  App-IDs.
- Ein Android-Build-Workflow für Debug-APKs; daraus folgt keine
  Release-, Store- oder Sicherheitsfreigabe.
- Websites und deren GitHub-Pages-Workflows verbleiben laut
  [Master-Integrationsplan](MASTER-INTEGRATION-PLAN.md) in den jeweiligen
  Quell-Repositories. Eine Cloudflare-Verbindung oder ein produktiver
  Cloudflare-Deploy ist nicht bestätigt.
- Eine Support-E-Mail wird in den App-Ressourcen als
  `n_nold@hotmail.com` angezeigt. Das bestätigt weder Anbieteridentität noch
  organisatorische Supportkapazität.

### Geplant / erst nach Prüfung und Freigabe

1. Bestehende Quellstände, Produktgrenzen und Anforderungen weiter inventarisieren.
2. Nutzungsbedarf und Preisannahmen mit geeigneten Zielgruppen validieren.
3. Nur konkret freigegebene Funktionen entwickeln; NIKNOLIG und Defense als
   getrennte Sicherheitsdomänen behandeln.
4. Vor einer Veröffentlichung Datenschutz-, Sicherheits-, Store-,
   Barrierefreiheits- und Rechtsanforderungen sowie Supportprozesse prüfen.
5. Vermarktung zunächst transparent über Produktstatus, belegte Funktionen und
   tatsächlich verfügbare Supportwege informieren. Konkrete Kanäle, Budgets,
   Kampagnen und Termine sind noch nicht beschlossen.

Es gibt in diesem Plan keine bestätigten Entwicklungsfristen,
Marketingausgaben, Partnerschaften, Reichweiten- oder Absatzprognosen.

## 5. Laufende Kosten und Wirtschaftlichkeit

Es liegen keine belastbaren Kostenbeträge, Angebote oder Finanzdaten vor.
Folgende mögliche Kostenblöcke sind zu ermitteln, nicht als bereits anfallende
Ausgaben zu verstehen:

- Entwicklung, Qualitätssicherung, Geräte und gegebenenfalls externe
  Fachprüfungen;
- Store-Konten, Zahlungsabwicklung und plattformabhängige Gebühren;
- Hosting, Domains, Support und gegebenenfalls Cloud-/Backendbetrieb;
- Buchhaltung, Steuern, Rechtsberatung, Datenschutz und Versicherung;
- Marketing, barrierefreie Inhalte und laufende Produktpflege.

Kostenfreiheit von Diensten, Höhe von Store-Abzügen, Steuern, Gebühren und
Deckungsbeiträge sind nicht geprüft. Vor einer Preisfreigabe sind die
Nettoerlöse je Store und Land sowie Rückerstattungen und laufende
Betriebskosten zu kalkulieren. Es werden keine Umsätze oder Gewinne
prognostiziert.

## 6. Statusübersicht und nächste Entscheidungen

| Einordnung | Aussage |
| --- | --- |
| **Bereits vorhanden** | Zwei getrennte Android-Vorschau-Apps; aktueller gemeinsamer Vorschau-Funktionsstand; begrenztes lokales Lernprofil; Debug-Build-Prüfung. |
| **Vorgegeben / geplant** | NIKNOLIG dauerhaft kostenlos; NIKNOLIG Defense regulär einmalig 0,75 €, mit genau 48 Stunden kostenloser Härtefallnutzung; NIKNOLIG als Hauptplattform; Defense als getrennte Sicherheitsdomäne; Elektro-Engel als Assistenzkonzept. |
| **Noch ungeprüft / offen** | Markt und Zahlungsbereitschaft; konkrete Produkt- und Defense-Leistungen; Nachweisverfahren und Missbrauchsbegrenzung für Härtefälle; datenschutzrechtliche Umsetzung; technische Erfassung von Aktivierung und Ablauf nach genau 48 Stunden; Verhalten nach Ablauf und Store-/Zahlungsablauf; eigenständige oder produktive Elektro-Engel-Leistung; Anbieter- und Rechtsform; Kosten und Erlöse; Backend/Cloudflare; Datenflüsse; Release- und Vermarktungsplan. |

Vor einem Geschäfts- oder Release-Beschluss sind mindestens Angebot und
Leistungsumfang je Produkt, Zielgruppe, Kostenmodell, Preisdefinition
(insbesondere „pro Store“), Verantwortlichkeiten und rechtliche
Voraussetzungen zu bestätigen. Bis dahin sind alle Planungen als vorläufig zu
behandeln.
