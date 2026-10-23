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

## Gesperrter KI-Support und bewusste E-Mail-Eskalation

Beide Startseiten führen zuerst in eine interne, nicht exportierte
`SupportActivity`, nicht direkt in die E-Mail-App. Auch die lokale
Elektro-Engel-Ansicht in NIKNOLIG bietet diesen Einstieg.

1. Die Support-Ansicht zeigt unmittelbar, dass KI-Support nicht freigegeben und
   kein KI-Dienst angeschlossen ist. Es gibt keinen KI-Aufruf und keine simulierte
   Antwort.
2. Die optionale Backend-Prüfung ruft ausschließlich `GET /health/ready` auf;
   eine erfolgreiche Health-Antwort bestätigt keine KI-Verfügbarkeit.
3. Die E-Mail-Alternative ist unabhängig von dieser Prüfung stets verfügbar.
   Ein Bestätigungsdialog nennt den vorhandenen Support-Empfänger und erklärt
   den Datenumfang. Erst die Bestätigung öffnet einen E-Mail-Entwurf.
4. Der Entwurf enthält nur festen Betreff und Hinweistext, keine Anfrage,
   Gesprächsdaten, Lernprofile, Anhänge oder Gerätekennungen. Der Nutzer ergänzt,
   prüft und versendet selbst. Ohne E-Mail-App wird der Empfänger angezeigt.
5. Die nativen iOS-Supportansichten zeigen denselben KI-/Health-Grenzstatus und
   öffnen nach Bestätigung ebenfalls nur einen E-Mail-Entwurf.

Die Empfängeradresse kommt weiterhin aus der bestehenden app-lokalen
`support_email`-Ressource. Es gibt keinen automatischen Mailversand und keine
Weiterleitung an einen fremden KI-Dienst. Zahlungsfragen bleiben außerhalb des
technischen Supports. Die Android-Texte sind auf Deutsch und Englisch
vorhanden; die nativen iOS-Vorschauen sind derzeit deutschsprachig.

**Noch offen:** Ein echter KI-Support samt Entscheidung „nicht lösbar“ benötigt
einen freigegebenen serverseitigen Anbieter/Endpunkt, Datenschutz- und
Datenminimierungsregeln, einen genehmigten Authentifizierungs-/Autorisierungsweg,
Fehler-/Unsicherheitsbehandlung und explizite Eskalationskriterien. Es wurde kein
Modell angebunden und kein Schlüssel in einer App hinterlegt. Der Health-only-
Backend-Status und SecurityChain-P0 werden durch diese Oberfläche nicht
aufgehoben.

Die [Backend-Vorbereitung](../backend/README.md#ki-support-vorbereitete-schnittstelle-keine-betriebsfreigabe)
ergänzt nun eine gesperrte Provider-Schnittstelle mit Mock-Tests, nicht eine
aktive KI-Verbindung der Apps. Anbieter-/Kostenfreigabe, Authentifizierungsweg
und mobile KI-Integration stehen weiterhin aus.

## Funktions- und Plattformgrenzen

- Die lokale Elektro-Engel-Assistenzvorschau bleibt NIKNOLIG-spezifisch;
  Defense erhält keinen kopierten Geräte- oder Assistenzruntime.
- Defense meldet unbekannten Gerätestatus und keinen aktiven Schutzdienst,
  statt eine Überwachung oder Einsatzbereitschaft vorzutäuschen.
- Apps verwenden mobile Bedienflächen, flexible Texthöhen und scrollbare
  Inhalte; sie werden nicht als Desktop-Webseiten nachgebaut.
- Animationen und ein tatsächlicher Gerätewechsel des Elektro-Engels sind
  nicht implementiert. Die produktlokalen Support-Symbole sind statisch.

Die Website-Quellen liegen in `nikolausnold/NIKNOLIG` und
`nikolausnold/-NIKNOLIG-Defense-Website`; sie wurden nicht verändert. Beide
Android-Supportseiten und beide nativen iOS-Supportansichten verlinken auf die
jeweilige offizielle Website und öffnen sie außerhalb der App. Die verbindliche
Domain- und Repository-Zuordnung steht in der
[Monorepo-Übersicht](../README.md#offizielle-websites-und-app-zuordnung).
Die eigenständigen Websites behalten ihre responsiven Weblayouts; App-Layouts
werden nicht kopiert.

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
