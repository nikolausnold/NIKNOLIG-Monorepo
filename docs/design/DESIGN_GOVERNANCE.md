# NIKNOLIG Design Governance

**Version:** 1.0  
**Stand:** 2026-10-24  
**Geltungsbereich:** NIKNOLIG und NIKNOLIG Defense auf Website, Android und iOS  
**Status:** Verbindlicher Soll- und Änderungsrahmen. Abweichungen im Bestand sind
Inventarbefunde, keine stillschweigende Änderung oder Freigabe des Bestands.

## 1. Zweck und Vorrang

Diese Datei ist die zentrale, versionierte Quelle für Designregeln beider Marken.
Sie konkretisiert einen Design Freeze und erlaubt kein Redesign. Bei Widerspruch
zu älteren Designbeschreibungen gilt diese Governance für den Sollzustand; ältere
Dateien dürfen nur den jeweils ausdrücklich gekennzeichneten Implementierungs-
oder Auditstand beschreiben.

Der Auftrag legt die nachstehenden Markenfarben verbindlich fest. Er bestätigt
nicht, dass sämtliche bestehenden Apps und Websites diese Farben bereits
verwenden oder dass eine Umstellung ihrer Oberflächen freigegeben ist. Die
Abweichungen unter [Bestandsprüfung](#10-bestandsprüfung-und-validierung) bleiben
offen und werden nicht im Rahmen dieses Dokumentationsauftrags visuell korrigiert.

## 2. Unveränderliche Markenidentitäten

| Marke | Botschaft | Hintergrund | Primärakzent | Sekundärakzent | Text | Charakter |
| --- | --- | --- | --- | --- | --- | --- |
| NIKNOLIG | DER STROM, DER SPRICHT | `#08090D` | Gold `#F4C95D` | Neongrün `#39F58A` | `#F2F2F5` | Premium, Zukunft, Energie, Eleganz, Innovation |
| NIKNOLIG Defense | SCHUTZ. SICHERHEIT. HANDELN. | `#101820` | Stahlblau `#8DA8C4` | Signalrot `#E5484D` | `#E8EDF2` | Sicherheit, Vertrauen, Klarheit, Schutz, Soforthilfe |

Diese Werte sind markeneigene, unveränderliche Design-Tokens. Gold und Neongrün
gehören nicht zur Defense-Palette; Stahlblau und Signalrot gehören nicht zur
NIKNOLIG-Palette. Ein Produkt darf Farben der anderen Marke nicht als
Markenakzent, Oberfläche, Logo-/Iconfarbe oder Identifikationsmerkmal verwenden.
Ein gemeinsamer semantischer Farbname oder globales Theme darf die Tokens nicht
zwischen den Produkten austauschen oder vererben.

Weitere Farben sind nur für notwendige Plattformkonventionen, Barrierefreiheit
oder semantische Zustände zulässig. Jede solche Farbe muss im jeweiligen
produktlokalen Tokenbereich mit Zweck, Zustand, Kontrastpaar und betroffenen
Plattformen dokumentiert werden. Sie darf die Markenpalette nicht erweitern oder
ersetzen.

## 3. Gestaltungsvorgaben

### Typografie

Es ist keine freigegebene Marken-Schriftfamilie oder plattformübergreifende
Typografieskala festgelegt. Bis zu einer ausdrücklichen Freigabe bleiben die
bestehenden Systemschriften, Plattform-Typografiestile und dynamischen
Schriftgrößen erhalten. Keine App oder Website darf eigenmächtig eine Schrift,
eine gemeinsame Markentypografie oder eine neue Hierarchie einführen.

### Logos, Icons und Markenassets

Logos, Produktzeichen, App-Icons und Illustrationen bleiben marken- und
produktlokal. Gemeinsame technische Asset-Pipelines sind zulässig, gemeinsame
Markenassets oder ungeprüfte Asset-Verweise zwischen NIKNOLIG und Defense nicht.
Bestehende Assets werden weder ersetzt noch umgefärbt. Ein Asset gilt erst dann
als kanonisch freigegeben, wenn seine Quelle und Zuordnung zur Marke dokumentiert
sind. Für externe Websites, deren Quellcode hier nicht vorliegt, wird keine
Asset-Prüfung behauptet.

### Buttons, Karten, Navigation und Formulare

Neue oder geänderte Oberflächen verwenden ausschließlich die Tokens und
produktlokalen Komponenten der jeweiligen Marke. Interaktionszustände müssen
sichtbar und verständlich sein; Farbe allein darf Fokus, Auswahl, Fehler,
Deaktivierung oder Erfolg nicht vermitteln. Formulare behalten verständliche
Labels, hilfreiche Hinweise und zugehörige Fehlermeldungen. Navigation, Inhalt
und bestehende Funktionen dürfen nicht allein wegen des Design Freeze entfallen
oder geändert werden.

Die Regeln legen keine neue Komponentenbibliothek und keine neuen visuellen
Geometrien fest. Bis eine ausdrücklich genehmigte Spezifikation vorliegt, bleiben
vorhandene Radien, Abstände, Schatten, Buttonformen und Layouts unverändert.
Markenbezogene Komponenten und Themes müssen getrennt bleiben; gemeinsame
Komponenten sind nur für markenneutrale Technik zulässig und müssen ihre
Markenvarianten explizit erhalten.

### Zustände, Bewegung und Fehlermeldungen

Lade-, Leer-, Erfolgs-, Warn-, Offline-, Fehler- und deaktivierte Zustände müssen
zur Marke passen, den tatsächlichen Systemzustand wahrheitsgemäß wiedergeben und
eine verständliche nächste Handlung oder Wiederherstellungsmöglichkeit nennen,
sofern vorhanden. Warnungen und Fehler dürfen nicht allein durch Rot oder Grün
gekennzeichnet werden. Animationen dürfen keine neue Markenidentität erzeugen,
keine Funktion vortäuschen und müssen reduzierte Bewegung respektieren. Es wird
keine neue Animation oder Laufzeitfunktion durch diese Governance eingeführt.

## 4. Barrierefreiheit

- Textkontrast erfüllt mindestens WCAG 2.2 AA: 4,5:1 für normalen Text und 3:1
  für großen Text; relevante Bedienelemente und Zustandsindikatoren benötigen
  ebenfalls ausreichenden Kontrast.
- Kontrast ist für jedes tatsächliche Vorder-/Hintergrundpaar und jeden Zustand
  zu prüfen. Ein Markenfarbwert allein garantiert keine barrierefreie Verwendung.
- Informationen und Zustände werden zusätzlich zu Farbe durch Text, Form,
  Symbol oder programmatisch zugängliche Beschriftung vermittelt.
- Fokus ist sichtbar, Inhalte bleiben bei vergrößerter Schrift nutzbar und
  Bedienelemente haben zugängliche Namen und ausreichende Bedienflächen.
- Android bleibt mit mindestens 48 dp Bedienfläche plattformgerecht; iOS
  berücksichtigt die Apple Human Interface Guidelines und ausreichend große
  interaktive Ziele (in der Regel mindestens 44 pt).
- Websites bleiben tastaturbedienbar, semantisch strukturiert und bei Zoom und
  schmalen Viewports verwendbar. Plattformbedingte Farb- und Fokusdarstellungen
  sind erlaubt, wenn sie dokumentiert und barrierefrei sind.

## 5. Plattform- und Produktgrenzen

| Oberfläche | Verbindliche Umsetzung |
| --- | --- |
| NIKNOLIG Website | NIKNOLIG-Tokens und NIKNOLIG-Markenassets; responsives Weblayout und Web-Barrierefreiheit. |
| NIKNOLIG Android | NIKNOLIG-Tokens und -Assets in nativer, Android-gerechter Bedienung; keine Website als App-Layout kopieren. |
| NIKNOLIG iOS | NIKNOLIG-Tokens und -Assets in nativer iOS-Bedienung; Apple Human Interface Guidelines und systemeigene Barrierefreiheitsfunktionen berücksichtigen. |
| NIKNOLIG Defense Website | Ausschließlich Defense-Tokens und -Assets; eigenständiges responsives Weblayout. |
| NIKNOLIG Defense Android | Ausschließlich Defense-Tokens und -Assets in nativer, Android-gerechter Bedienung. |
| NIKNOLIG Defense iOS | Ausschließlich Defense-Tokens und -Assets in nativer iOS-Bedienung; Apple Human Interface Guidelines berücksichtigen. |

Geschäftslogik darf geteilt werden. Gemeinsame technische Komponenten sind
zulässig, wenn sie keine Markenidentität vermischen und Markenparameter
produktlokal und ausdrücklich übergeben werden. Globale gemeinsame Farbpaletten,
geteilte Markenassets und implizite Theme-Vererbung sind unzulässig. Android und
iOS bleiben native Plattformen; die Websites behalten ihre jeweiligen
Weblayouts.

## 6. Design Freeze und Freigaben

1. Die Tokens aus Abschnitt 2 und freigegebene Markenassets dürfen nicht
   eigenmächtig geändert, ergänzt, entfernt oder zwischen Marken übertragen
   werden.
2. Neue Screens und neue Zustände folgen den Regeln der betroffenen Marke.
3. Änderungen an Markenfarben, Typografie, Logos, Icons, Navigation oder
   grundlegenden Layouts benötigen vor der Umsetzung die ausdrückliche Freigabe
   der Projektverantwortlichen.
4. Technische Fehlerbehebungen sind ohne Redesign möglich, sofern die
   freigegebene visuelle Identität erhalten bleibt.
5. Technisch notwendige Plattformabweichungen sind zulässig; Grund, Umfang und
   betroffene Plattform sind in dieser Dokumentation oder einer verlinkten
   Produktdokumentation festzuhalten.
6. Kein Copilot-Auftrag und keine technische Umsetzung darf ohne ausdrückliche
   Freigabe ein vollständiges Redesign auslösen.
7. Keine Marke übernimmt Layouts, Assets oder den visuellen Charakter der
   anderen Marke.
8. Eine Änderung dieses Dokuments erhält eine Versionsänderung und dokumentiert
   Anlass, betroffene Marke/Plattform und Freigabestatus. Sie ersetzt keine
   erforderliche Projektfreigabe.

## 7. Gemeinsame technische Komponenten

Gemeinsam genutzte Geschäftslogik, Accessibility-Helfer und plattformneutrale
Layoutmechanik dürfen keinen Markenstil festlegen. Designkomponenten erhalten
Tokens und Assets aus einem expliziten, markenlokalen Kontext; ein fehlender
Kontext darf nicht stillschweigend auf die jeweils andere Marke zurückfallen.
Tests sollen beide Markenvarianten getrennt prüfen. Technische Wiederverwendung
ist kein Grund, App-Identitäten, Releases oder visuelle Grenzen zusammenzuführen.

## 8. Versionierung und Änderungshistorie

Diese Datei ist der zentrale Governance-Eintrag. Die Versionsnummer wird bei
inhaltlichen Regeländerungen fortgeschrieben; der Git-Verlauf hält die konkrete
Änderung fest. Version 1.0 dokumentiert die in diesem Auftrag benannten
Markenwerte und Regeln. Sie behauptet keine nachträgliche Freigabe oder
Bestandsmigration.

## 9. Validierungsstandard

Vor einer freigegebenen Designänderung und bei relevanten Änderungen sind
mindestens folgende Prüfungen vorzusehen:

- vorgeschriebene Marken-Tokens sind vorhanden und stimmen exakt mit Abschnitt 2
  überein;
- markenfremde Token- und Asset-Verwendung, fehlende Produkttrennung und
  widersprüchliche Designdefinitionen werden erkannt;
- tatsächliche Farbpaare, Kontrastzustände, zugängliche Fokus-/Fehlerzustände und
  Plattformkonventionen werden geprüft;
- Dokumentationslinks und die Zuordnung von Marke, Plattform und Asset sind
  konsistent;
- vorhandene Tests und CI laufen ohne zusätzliche kostenpflichtige Dienste.

Eine statische Tokenprüfung kann keine vollständige visuelle, manuelle,
Assistive-Technology- oder Plattformabnahme ersetzen. Neue Prüfschritte dürfen
die Bestandsimplementierung nicht stillschweigend als konform ausgeben. Für
externe Websites ohne im Monorepo vorhandenen Quellcode sind nur Dokumentations-
und Zuordnungsprüfungen möglich.

## 10. Bestandsprüfung und Validierung

Die Repository-Prüfung am 2026-10-24 hat Folgendes ergeben:

- Vorhanden ist ein App-Web-Abgleich mit Android-Farbwerten und
  Geometrieangaben. Er beschreibt den aktuellen Implementierungsstand, nicht die
  in Abschnitt 2 verbindlich festgelegten Werte.
- Die Android-Ressourcen und `tools/tests/test_app_design.py` verwenden noch
  ältere Paletten. NIKNOLIG enthält `#101A14` und `#C8F169`; Defense enthält
  `#10151D` und `#72C7F5`. Das bestehende Design-Testmodul prüft diese Werte und
  bestehende Kontraste, aber nicht die Tokens aus Abschnitt 2.
- Die beiden iOS-Ziele enthalten derzeit denselben expliziten grünen Tint, keine
  hier nachgewiesenen getrennten Token-Dateien.
- `docs/download/index.html` enthält eine ältere dunkle NIKNOLIG-Palette. Sie ist
  eine lokal vorhandene Website-ähnliche Downloadseite, kein vollständiger
  Quellcode-Nachweis für die offizielle NIKNOLIG-Website.
- Der Quellcode der Defense-Website und damit deren Farben, Assets und
  Designprüfungen sind in diesem Monorepo nicht vorhanden.
- Es gibt vorhandene Android-, iOS- und Python-Tests in CI. Die im Bestand
  erkannten Abweichungen belegen, dass die neue Token-Governance derzeit nicht
  technisch für alle sechs Oberflächen erzwungen wird.

Diese Abweichungen werden hier dokumentiert, nicht im Code oder in der visuellen
Oberfläche umgestellt. Ein Folgeauftrag muss die ausdrücklich freigegebene
Bestandsmigration, getrennte Tokens/Assets und geeignete CI-Prüfungen behandeln.
