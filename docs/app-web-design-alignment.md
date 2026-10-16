# App-Web-Designabgleich

## Gemeinsame visuelle Basis

Die Websites von NIKNOLIG und NIKNOLIG Defense verwenden denselben dunklen
Grün-/Limetten-Stil. Die Android-Farbressourcen beider Apps wurden an diese
gemeinsame Palette angepasst:

| Verwendung | Wert |
| --- | --- |
| Hintergrund | `#0C1110` |
| Flächen | `#131A17` |
| Primärtext | `#F3F4EF` |
| Sekundärtext | `#A0AAA2` |
| Markenakzent | `#C8F169` |
| Abgestufter Statusgrün-Ton | `#A6CF4D` |

Die Tokens liegen getrennt in
`apps/niknolig/src/main/res/values/colors.xml` und
`apps/niknolig-defense/src/main/res/values/colors.xml`; Android-Themes und
Akzenttexte verwenden den Limettenton. Der bestehende Resource-Name `gold`
bleibt vorerst als Alias auf `brand_accent`, damit die Layouts unverändert
bleiben und keine alte Referenz wieder Gold darstellt.

## Bewusst erhaltene Unterschiede

- Websites behalten ihre jeweilige Positionierung und Texte: NIKNOLIG
  kommuniziert die Plattform und Assistenz, NIKNOLIG Defense Sicherheit und
  Support.
- Android-Layouts bleiben für mobile Nutzung und App-spezifische Abläufe
  optimiert; sie werden nicht als Desktop-Webseiten nachgebaut.
- Die bestehende lokale Assistenzseite bleibt NIKNOLIG-spezifisch; die
  bisherigen Lernprofile bleiben unverändert. Die neue Defense-
  Designvorschau ist **keine operative Assistenzintegration**.
- Die neuen Engel sind verwandt, aber getrennt gestaltet: NIKNOLIG mit
  runden Flügeln, weicher Karte und Assistenztext; Defense mit kantigem
  Engel, Schild, kantiger Karte und eigener Produktkennzeichnung.
- Es werden weder Funktionen noch Identitäten, Daten oder Rechte zwischen
  den Apps vereinheitlicht.

## Lokale adaptive Designvorschauen

In NIKNOLIG öffnet „Elektro-Engel: Designvorschau“ auf der Assistenzseite
die Vorschau; in Defense liegt dieser Einstieg auf der Startseite. Jedes
Modul besitzt eine eigene, nicht exportierte `AppearancePreviewActivity`,
eigene Ressourcen und keine neue Modulabhängigkeit.

Die Auswahl dient ausschließlich dem lokalen Designvergleich:

| Auswahl | Darstellung |
| --- | --- |
| Ruhe / Hilfe / Verarbeitung / Warnung / Fehler | Aufrechter bzw. unterschiedlich geneigter Engel, eindeutiges Symbol, Zustandsname und erklärender Beispieltext; Warnung/Fehler zusätzlich mit stärkerem Rahmen |
| Telefon / Tablet | Zielbreite maximal 320 / 600 dp, auf die tatsächlich verfügbare Breite begrenzt; angepasste Engel- und Überschriftgröße |
| App / Website-inspiriert | Kompakte App-Orientierung oder einleitender Web-Mustertext mit größerer Überschrift und mehr Innenabstand, jeweils mit eigener Produktkennzeichnung; kein Browser, keine echte Webseite |

Ein sichtbarer Hinweis kennzeichnet alle Zustände als Beispiele und jeden
Zielwechsel als **Simulation ohne Übertragung**. Auch „Verarbeitung“ startet
keinen Auftrag und zeigt keinen Fortschritt. Die Darstellung ist immer
statisch (auch bei aktivierter Bewegungsreduktion): kein Blinken, keine
Animationen oder Timer. Text und Symbole vermitteln den Zustand ohne
Farbabhängigkeit; die dekorative Silhouette wird nicht doppelt vorgelesen.

Die Oberflächen verwenden native Android-Views, vertikales Scrollen,
mehrzeilige Auswahltexte und inhaltsabhängige Höhen statt Overlays oder
festen Bildschirmhöhen. Beschriftungen sind den Auswahlfeldern zugeordnet;
deutsche und englische Texte liegen je Modul separat vor. Die drei Auswahlen
werden über `Bundle` bei Rotation und systembedingter Neuerstellung erhalten.
Es gibt keine neue Berechtigung, Sensorabfrage, Geräteerkennung, Verbindung,
Authentifizierung, Backend-Anbindung oder Übertragungsfunktion.

Die strukturellen Regressionstests unter
`backend/tests/test_appearance_previews.py` prüfen unter anderem
App-Grenzen, nicht exportierte Activities, fehlende Berechtigungen,
lokalisierte Zustände und beschriftete Auswahlfelder. Sie ersetzen keine
visuelle Geräteabnahme. Noch manuell zu prüfen: beide Produkte × fünf
Situationen × beide Zielgrößen × beide Oberflächen, kleine/große tatsächliche
Viewports, Querformat, große Schrift, TalkBack, RTL und Wiederherstellung
nach Prozessende. Eine visuelle Geräte-/Browserabnahme wird nicht behauptet.

## Änderungsgrenze und nächste Integration

Die Website-Quellen liegen in den separaten Repositories
`nikolausnold/NIKNOLIG` und `nikolausnold/NIKNOLIG-Defense`; sie wurden für
diesen Abgleich nur gelesen und nicht verändert. Die gemeinsamen visuellen
Tokens sollten dort bei späteren Designänderungen mit den Werten oben
abgeglichen werden. Die Android-Anpassungen bleiben auf die getrennten Module
`apps/niknolig` und `apps/niknolig-defense` beschränkt.

Für die Build-Prüfung dieses Abgleichs:

```sh
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug \
  :niknolig:lintDebug :niknolig-defense:lintDebug --no-daemon
```
