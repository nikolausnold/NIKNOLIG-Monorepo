# App-Web-Designabgleich

## Getrennte Android-Produktidentitäten

NIKNOLIG und NIKNOLIG Defense bleiben getrennte Apps mit eigenen Installationen,
Kennungen und Ressourcen. Die Android-Apps unterscheiden sich nicht nur durch
Farbe, sondern auch durch Formen, Produktzeichen und Einstieg:

| Merkmal | NIKNOLIG | NIKNOLIG Defense |
| --- | --- | --- |
| Charakter | Persönliche Assistenz | Strukturierte Übersicht und Support |
| Hintergrund | Dunkelgrün `#101A14` | Graphit `#10151D` |
| Flächen | `#1B2A20` | `#192330` |
| Akzent | Limette `#C8F169` | Eisblau `#72C7F5` |
| Formen | Weiche Karten mit 20-dp-Rundungen | Konturierte Panels mit 4-dp-Rundungen |
| Produktzeichen | Orbitales N | Geometrische Schild-/N-Kontur |
| Einstieg | Elektro-Engel und persönliche Hilfe | Defense-Produktname und Support-Zentrale |

Die Tokens liegen getrennt in
`apps/niknolig/src/main/res/values/colors.xml` und
`apps/niknolig-defense/src/main/res/values/colors.xml`. Der bestehende
Resource-Name `gold` bleibt ein Alias auf den jeweiligen `brand_accent`.
Karten, Schaltflächen und Support-Symbole verwenden produktlokale Drawables.
Die Support-Symbole kennzeichnen lediglich die Oberfläche: Sie sind kein
Nachweis einer aktiven KI oder einer Geräteverbindung.

## KI-zuerst-Support und bewusste Eskalation

Beide Startseiten führen zuerst in eine interne, nicht exportierte
`SupportActivity`, nicht direkt in die E-Mail-App. Auch die lokale
Elektro-Engel-Ansicht in NIKNOLIG bietet diesen Einstieg.

1. Die Oberfläche erklärt das Ziel: zuerst KI-Unterstützung.
2. „KI-Verfügbarkeit prüfen“ zeigt den tatsächlichen lokalen
   Konfigurationsstand: **kein KI-Dienst angeschlossen**. Es erfolgt kein
   Netzwerkaufruf, keine Problemerfassung und keine simulierte KI-Antwort.
3. Nur danach erscheint die E-Mail-Eskalation für fehlende KI-Hilfe.
4. Ein Bestätigungsdialog nennt den vorhandenen Support-Empfänger und erklärt
   den Datenumfang. Erst die Bestätigung öffnet einen E-Mail-Entwurf.
5. Der Entwurf enthält nur festen Betreff und Hinweistext, keine Anfrage,
   Gesprächsdaten, Lernprofile, Anhänge oder Gerätekennungen. Der Nutzer ergänzt,
   prüft und versendet selbst. Ohne E-Mail-App wird der Empfänger angezeigt.

Die Empfängeradresse kommt weiterhin aus der bestehenden app-lokalen
`support_email`-Ressource. Es gibt keinen automatischen Mailversand und keine
Weiterleitung an einen fremden KI-Dienst. Zahlungsfragen bleiben außerhalb des
technischen Supports. Deutsche und englische Texte sind vorhanden.

**Noch offen:** Ein echter KI-Support samt Entscheidung „nicht lösbar“ benötigt
einen freigegebenen serverseitigen Anbieter/Endpunkt, Datenschutz- und
Datenminimierungsregeln, Fehler-/Unsicherheitsbehandlung und explizite
Eskalationskriterien. Es wurde kein Modell angebunden und kein Schlüssel im
Android-Client hinterlegt. Der Health-only-Backend-Status und SecurityChain-P0
werden durch diese Oberfläche nicht aufgehoben.

## Funktions- und Plattformgrenzen

- Die lokale Elektro-Engel-Assistenzvorschau bleibt NIKNOLIG-spezifisch;
  Defense erhält keinen kopierten Geräte- oder Assistenzruntime.
- Defense meldet unbekannten Gerätestatus und keinen aktiven Schutzdienst,
  statt eine Überwachung oder Einsatzbereitschaft vorzutäuschen.
- Apps verwenden mobile Bedienflächen, flexible Texthöhen und scrollbare
  Inhalte; sie werden nicht als Desktop-Webseiten nachgebaut.
- Animationen und ein tatsächlicher Gerätewechsel des Elektro-Engels sind
  nicht implementiert. Die produktlokalen Support-Symbole sind statisch.

Die Website-Quellen liegen in den separaten Repositories
`nikolausnold/NIKNOLIG` und `nikolausnold/NIKNOLIG-Defense`; sie wurden nicht
verändert. Dort ist die jeweilige Produktidentität später separat zu übernehmen,
mit größeren Einstiegsflächen und responsiven Inhaltsrastern statt kopierter
App-Layouts. Diese Änderung bleibt im Monorepo.

## Prüfung und verbleibende Abnahme

```sh
./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug :niknolig:lintDebug :niknolig-defense:lintDebug
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/tests
```

Die Python-Prüfungen sind statische Ressourcen-/Quellcode-Regressionen, keine
Android-Interaktionstests. Vor einer Gerätefreigabe sind insbesondere kleine
Displays, große Systemschrift, TalkBack-Reihenfolge, Farbkontraste und mindestens
48-dp-Bedienflächen zu prüfen. Beide Produkte müssen auch ohne Farbwahrnehmung
unterscheidbar bleiben. E-Mail-Abbruch, fehlender Mail-Client sowie die
Nichtverfügbarkeitsanzeige müssen auf einem Gerät durchgespielt werden.
