# Android-Vorabvalidierung

Diese Arbeitsschritte gelten für Änderungen an den Android-Modulen. Sie ersetzen
keine GitHub-CI und starten selbst keine Builds oder Workflows.

## Vor Änderungen

- Ermittle den tatsächlichen Repository-Pfad, den aktuellen Branch, Commit und
  Arbeitsbaum. Erhalte vorhandene Änderungen.
- Prüfe `settings.gradle.kts` und die betroffenen Modulkonfigurationen. Derzeit
  liegen `:niknolig` und `:niknolig-defense` unter `apps/`; behalte die getrennten
  App-Identitäten und Ressourcen bei.
- Prüfe vorhandene Logs und Ergebnisse einschließlich ihrer Revision, bevor du
  Prüfungen wiederholst. Ein erfolgreicher Lauf eines anderen Commits validiert
  die aktuellen Änderungen nicht.

## Lokale Prüfungen vor Push und Übergabe

- Führe Befehle vom ermittelten Repository-Stamm aus.
- Führe nach Android-Ressourcenänderungen zuerst beide Lint-Aufgaben aus:
  `./gradlew :niknolig:lintDebug :niknolig-defense:lintDebug --no-daemon`.
- Suche bei Theme-Änderungen zusätzlich rekursiv in beiden Modulen nach
  `windowLightNavigationBar`. `android:windowLightNavigationBar` benötigt API 27
  und darf nicht in allgemeinen `res/values/`-Themes stehen. Verwende geeignete
  versionsabhängige Ressourcen, etwa `res/values-v27/themes.xml`, und prüfe die
  Theme-Vererbung, den API-26-Fallback sowie den Erhalt der übrigen Designwerte.
- Führe bei Kotlin-, Java-, Test- oder Build-Konfigurationsänderungen die
  betroffenen vorhandenen Tests, Lint- und Build-Aufgaben aus.
- Führe vor einer vollständigen Übergabe nach Möglichkeit diesen gesamten
  Android-Prüfumfang lokal aus:
  `./gradlew :niknolig:testDebugUnitTest :niknolig-defense:testDebugUnitTest :niknolig:lintDebug :niknolig-defense:lintDebug :niknolig:assembleDebug :niknolig-defense:assembleDebug --no-daemon`.
- Änderungen ausschließlich an Dokumentation oder Copilot-Anweisungen benötigen
  keine Android-Builds; prüfe stattdessen Inhalt und Diff. Beachte ausdrücklich
  angeforderte Einschränkungen wie eine rein statische Prüfung und melde dann
  nicht ausgeführte Prüfungen.

## Fehler behandeln, nicht blind wiederholen

- Ermittle nach einem Fehler zuerst Ursache, betroffene Datei und geprüfte
  Revision. Behebe zusammengehörige nachgewiesene Fehler gesammelt und führe die
  betroffenen Lint-Aufgaben beziehungsweise Regressionstests erneut aus.
- Prüfe Lint-Warnungen einzeln; unterscheide echte Probleme von unkritischen
  Hinweisen und vermeide sachfremde Änderungen.
- Wiederhole weder identische Änderungen noch erfolgreiche Prüfungen ohne
  technischen Grund. Bei widersprüchlichen Ergebnissen prüfe CI-Revision,
  Quellstand und, soweit erzeugt, gemergte Ressourcen.
- Deaktiviere keine Prüfungen, erstelle keine Baseline zur Fehlerverdeckung und
  schwäche keine Sicherheits-, Release- oder Kompatibilitätseinstellungen ab.
  Erhöhe `minSdk` nicht, um API-Ressourcenfehler zu umgehen.

## Grenzen und Abschlussbericht

- Fehlen Gradle, Java, Android SDK, Netzwerkzugriff oder andere Voraussetzungen,
  benenne die Ursache und die dadurch nicht ausführbaren Prüfungen ausdrücklich.
  Wiederhole einen unveränderten Umgebungsfehler nicht blind.
- Unterscheide gestartete Befehle von tatsächlich ausgeführten Aufgaben.
  Behaupte erfolgreiche Lint-Prüfungen, Tests oder Builds nur mit entsprechenden
  Ergebnissen für den geprüften Commit.
- Berichte kurz die lokal ausgeführten Prüfungen, gefundene und behobene Fehler,
  erfolgreiche Prüfungen und offene oder blockierte Prüfungen.
- Behalte GitHub-CI als unabhängige abschließende Validierung bei. Der derzeitige
  Android-Workflow baut APKs; das allein belegt keinen erfolgreichen Lint- oder
  Unit-Test-Lauf.
