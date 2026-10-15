# NIKNOLIG Release-Readiness-Bericht

**Ergebnis: BLOCKED**  
**Stand:** 2026-10-15  
**Repository:** `nikolausnold/NIKNOLIG-Monorepo`  
**Prüfstand:** `main`, Commit `d9e1ca7309e3716ba7262a706897f616867f0f5e`  
**Arbeitsbranch bei der Erstellung:** `copilot/release-readiness-report`

## Zusammenfassung

Beide getrennten Android-Apps lassen sich bauen. Der aktuelle Android-CI-Lauf
hat beide Debug-APKs gebaut, Paket-IDs kontrolliert, APK-Signaturen geprüft und
die APKs als Actions-Artefakte hochgeladen. Ein erfolgreicher Release-Lauf hat
signierte Release-APKs erstellt und die Signaturen mit den in demselben Lauf
verwendeten Keystores verglichen.

Das ist kein Nachweis für die geforderte Verbindung zwischen zwei Smartphones:
In den vorhandenen Apps sind Geräteerkennung, Pairing, Authentifizierung,
verschlüsselte Kommunikation, Abbruchbehandlung und Wiederverbindung nicht
implementiert. Es gibt außerdem keine Android-Testquellen. Ein realer
Zwei-Geräte-Test wurde nicht durchgeführt. Daher sind die vorhandenen Builds
technisch erfolgreich, die geforderte Release-Funktion aber nicht release-ready.

## Repository- und Workflow-Bestand

- Das Arbeitsverzeichnis war vor Erstellung dieses Berichts sauber. Der
  Prüfstand ist der oben genannte Commit auf `main`; der lokale Arbeitsbranch
  ist `copilot/release-readiness-report`.
- Die letzten verfügbaren Commits im flachen Klon umfassen den Merge `d9e1ca7`
  und den vorherigen Dokumentationscommit `8f1589b` („Document verified
  Android release artifacts“). Zwischen dem erfolgreichen Release-Build auf
  `c8d152f4dff28f452e768b2379ebedf6ae4688e4` und dem Prüfstand änderten sich
  keine App-, Gradle- oder Workflow-Dateien.
- Vorhandene Projektworkflows: `Android apps build` (Push, Pull Request,
  manuell), `Preparing release APKs` (manuell, nur `main`) und
  `Read-only Workers repository audit` (manuell). Es gibt keinen
  Store-Publishing-Workflow.
- Die Android-Module `:niknolig` und `:niknolig-defense` sind unabhängige Apps
  mit `com.niknolig.app` beziehungsweise `com.niknolig.defense`. Das Monorepo
  ändert die beiden separaten Quell-Repositories nicht.

## CI- und Testergebnisse

| Prüfung | Ergebnis und Nachweis |
| --- | --- |
| Aktuellster Android-Debug-Build | **Erfolgreich** auf `main`, Commit `d9e1ca7309e3716ba7262a706897f616867f0f5e`; [Actions-Lauf #78](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38752377970). Beide APKs wurden gebaut, Paket-IDs und Signaturen geprüft, Artefakte hochgeladen. |
| Release-Build | **Erfolgreich** auf `main`, Commit `c8d152f4dff28f452e768b2379ebedf6ae4688e4`; [Actions-Lauf #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201). Keystores wurden validiert, beide Release-APKs gebaut, Paket-IDs geprüft und APK-Zertifikate mit den jeweiligen Keystore-Zertifikaten verglichen. |
| Read-only-Repository-Audit | **Erfolgreich**, [Actions-Lauf #16](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736489156). Dies ist kein Android-, Integrations- oder Gerätetest. |
| Automatisierte App-Tests | **Nicht vorhanden/nicht ausgeführt.** Im geprüften Stand gibt es keine `src/test`- oder `src/androidTest`-Quellen. Der Android-Build-Workflow führt Build- und APK-Prüfungen, aber keine Android-Testtasks aus. |
| Test auf zwei physischen Geräten | **Nicht durchgeführt.** Kein CI-Lauf kann diesen manuellen Test ersetzen. |

Ein früherer Release-Lauf [#3](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38626998691)
schlug beim APK-Packaging fehl, weil die erwarteten Schlüssel-Aliase in den
Keystores fehlten. Der spätere erfolgreiche Release-Lauf #13 belegt, dass der
Fehler in diesem späteren Lauf nicht mehr auftrat. Es werden hier keine
Secret-Werte offengelegt.

## Vorhandene APK-Artefakte

Die folgenden Artefaktarchive waren zum Berichtszeitpunkt nicht abgelaufen.
Die Download-URLs sind die von GitHub Actions zurückgegebenen echten
Artefakt-URLs; für den Zugriff ist eine entsprechende GitHub-Berechtigung
erforderlich.

| Artefakt | Zugehöriger Lauf | Größe | Ablauf | Download |
| --- | --- | ---: | --- | --- |
| `niknolig-debug-apk` | [Debug #78](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38752377970), Commit `d9e1ca7` | 866.591 Byte | 2026-10-22 14:34 UTC | [ZIP herunterladen](https://api.github.com/repos/nikolausnold/NIKNOLIG-Monorepo/actions/artifacts/11982022638/zip) |
| `niknolig-defense-debug-apk` | [Debug #78](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38752377970), Commit `d9e1ca7` | 862.673 Byte | 2026-10-22 14:34 UTC | [ZIP herunterladen](https://api.github.com/repos/nikolausnold/NIKNOLIG-Monorepo/actions/artifacts/11981572977/zip) |
| `niknolig-release-apk` | [Release #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201), Commit `c8d152f` | 662.828 Byte | 2026-10-16 12:43 UTC | [ZIP herunterladen](https://api.github.com/repos/nikolausnold/NIKNOLIG-Monorepo/actions/artifacts/11974091975/zip) |
| `niknolig-defense-release-apk` | [Release #13](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38736559201), Commit `c8d152f` | 659.853 Byte | 2026-10-16 12:43 UTC | [ZIP herunterladen](https://api.github.com/repos/nikolausnold/NIKNOLIG-Monorepo/actions/artifacts/11974306823/zip) |

Die Release-APKs stammen aus dem vorherigen Commit `c8d152f`; die App-,
Gradle- und Workflow-Dateien sind zwischen diesem Commit und dem Prüfstand
unverändert. Die Release-Pipeline lädt Artefakte hoch, veröffentlicht sie aber
nicht in einem App-Store.

### Bericht als Actions-Artefakt

Der Android-Build-Workflow enthält jetzt den Upload des Berichts als
`release-readiness-report`-Artefakt mit sieben Tagen Aufbewahrung. Der durch
diese Änderung ausgelöste [Actions-Lauf #79](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38754078450)
steht jedoch auf `action_required`; GitHub meldet null Jobs und null Artefakte.
Dieser Lauf stellt daher noch keinen Bericht-Download bereit. Ein berechtigter
Repository-Nutzer muss den erforderlichen Schritt auf der verlinkten
Actions-Seite ausführen. Der Status wird nicht umgangen. Der Bericht selbst
liegt bereits unter `docs/release-readiness.md` im Repository.

## Integrationsprüfung und Zwei-Geräte-Anforderung

Die Android-Manifeste enthalten keine Netzwerk-, Bluetooth- oder
Nearby-Device-Berechtigungen. Die App-Quellen enthalten keinen Transport-,
Geräteerkennungs-, Pairing-, Authentifizierungs-, Verschlüsselungs- oder
Wiederverbindungscode. Bluetooth-Erwähnungen in den Oberflächen sind
Vorschautexte, keine Gerätefunktionen. Zwischen den beiden Modulen gibt es
keine gemeinsame Laufzeitbibliothek oder App-zu-App-Schnittstelle.

| Anforderung | Befund |
| --- | --- |
| Geräteerkennung und Pairing | Nicht implementiert |
| Authentifizierung/Vertrauensaufbau | Nicht implementiert |
| Verschlüsselte Verbindung | Nicht implementiert |
| Verbindungsabbruch und Wiederverbindung | Nicht implementiert |
| Automatisierte Integrationstests | Nicht vorhanden |
| Test mit den zwei Smartphones des Nutzers | Nicht durchgeführt |

## Offene Blocker und kleinste nächste Schritte

1. **Zwei-Geräte-Verbindung fehlt (Release-Blocker).** Zuerst müssen Umfang,
   Transport, Identität/Pairing, Berechtigungen und Sicherheitsanforderungen
   freigegeben werden. Danach ist die Funktion zu implementieren und durch
   automatisierte Fehlerfalltests sowie einen dokumentierten Test auf beiden
   Smartphones zu prüfen. Dieser Bericht nimmt keine solche Implementierung
   vor.
2. **Keine automatisierten App-Tests.** Sobald der Funktionsumfang freigegeben
   ist, automatisierte Tests für Pairing, Authentifizierung, Verschlüsselung,
   Abbruch und Wiederverbindung ergänzen und in CI ausführen.
3. **Keine unabhängig freigegebene Signaturreferenz.** Der Release-Workflow
   vergleicht den APK-Fingerabdruck mit dem Keystore desselben Laufs, aber
   nicht mit einem unabhängig freigegebenen erwarteten Fingerabdruck. Vor
   einem produktiven Release muss die Signieridentität unabhängig geprüft und
   eine Referenz für den Release-Prozess freigegeben werden.
4. **Release-Freigabekriterien fehlen.** Store-/Produktivfreigabe,
   Review-Gates und Rollback sind durch die vorhandenen Artefakt-Builds nicht
   belegt. Kleinster Schritt: diese Kriterien vor einer Store-Veröffentlichung
   festlegen und nachweisen.
5. **Bericht-Download noch nicht erzeugt.** Actions-Lauf #79 ist
   `action_required` und hat keine Artefakte. Kleinster Schritt: den erforderlichen
   Actions-Schritt als berechtigter Repository-Nutzer auf der
   [Laufseite](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/38754078450)
   ausführen; danach sollte der Workflow den Bericht als Artefakt bereitstellen.

**Freigabeentscheidung:** **BLOCKED** bis mindestens die geforderte
Zwei-Geräte-Funktion implementiert und auf beiden Smartphones erfolgreich
getestet ist. Ein erfolgreicher APK-Build allein hebt diesen Blocker nicht auf.
