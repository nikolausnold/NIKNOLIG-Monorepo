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
- Die lokale Elektro-Engel-Vorschau bleibt NIKNOLIG-spezifisch. Es werden
  weder Funktionen noch Identitäten zwischen den Apps vereinheitlicht.
- Diese Änderung fasst nur die gemeinsame Farbpalette an. Typografie,
  Abstände, Komponentenstruktur und Responsive-Verhalten wurden nicht
  visuell auf Geräten oder Browsern abgenommen.

## Änderungsgrenze und nächste Integration

Die Website-Quellen liegen in den separaten Repositories
`nikolausnold/NIKNOLIG` und `nikolausnold/NIKNOLIG-Defense`; sie wurden für
diesen Abgleich nur gelesen und nicht verändert. Die gemeinsamen visuellen
Tokens sollten dort bei späteren Designänderungen mit den Werten oben
abgeglichen werden. Die Android-Anpassungen bleiben auf die getrennten Module
`apps/niknolig` und `apps/niknolig-defense` beschränkt.

Für die Build-Prüfung dieses Abgleichs:

```sh
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug
```
