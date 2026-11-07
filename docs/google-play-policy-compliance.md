# Google-Play-Richtlinien: Technischer Prüfstand (Ankündigung 29.10.2026)

Geprüft wurden die Release-relevanten `src/main`-Manifeste, Kotlin-Quellen und
`build.gradle.kts` von `:niknolig` und `:niknolig-defense` getrennt. Beide Module haben
denselben Release-Befund; es wurden keine Berechtigungen entfernt, weil keine der
betroffenen Berechtigungen in den Release-Varianten deklariert oder genutzt wird.
Der Android-17-Emulator-Smoke-Test erreicht seinen lokalen HTTPS-Endpunkt über
`adb reverse` und eine ausschließlich für Debug-Builds validierte Loopback-URL; er
benötigt daher keine `ACCESS_LOCAL_NETWORK`-Berechtigung.

## Befund je Modul

| Thema | `:niknolig` | `:niknolig-defense` | Maßnahme |
| --- | --- | --- | --- |
| Local Network Permission | in Release nicht deklariert, keine NSD-/Multicast-APIs; HTTPS-Backend kann dennoch auf eine LAN-Adresse zeigen | identisch | Konfigurierte Backend-Ziele prüfen; lokale Netzwerkberechtigungen erst nach Prüfung aller unterstützten Ziele als nicht erforderlich bewerten. HTTPS (`usesCleartextTraffic=false`) schließt LAN-Zugriffe nicht aus. |
| Manage Contacts / Kontakte | keine Kontakt-Berechtigung | identisch | Keine. Support-Flow nutzt Mail-Intent statt Kontaktzugriff. |
| Standort / `ACCESS_FINE_LOCATION` | nicht deklariert | identisch | Keine. Nur das deklarative Sensor-Schema nennt Standort-Berechtigungen für eine spätere, P0-gesperrte Funktion; falls umgesetzt: zuerst `COARSE`, `FINE` nur mit Nachweis. |
| AppFunctions / KI-Agenten | keine AppFunctions, keine exportierten Services | identisch | Keine. Vor jeder Einführung: Sicherheitsprüfung, nur nicht-sensible Funktionen, Nutzerbestätigung. |
| `MANAGE_EXTERNAL_STORAGE` | nicht deklariert | identisch | Keine. |
| SMS / Call Log | nicht deklariert | identisch | Keine. |
| Play Billing | keine Billing-Bibliothek, keine digitalen Käufe in der App | identisch | Keine. Vor digitalen Käufen: Play Billing verwenden (siehe `docs/LEGAL-CHECKLIST.md`). |
| Android 17 / API 37 | `compileSdk`/`targetSdk` 37 | identisch | Siehe unten. |

Einzige Berechtigung beider `src/main`-Manifeste (also der Release-Varianten):
`android.permission.INTERNET`. Auch die Emulator-Smoke-Tests deklarieren keine
`ACCESS_LOCAL_NETWORK`-Berechtigung.

## API 37 (CI-Build erfolgreich, Emulatorprüfung ausstehend)

`compileSdk` und `targetSdk` stehen in beiden Modulen gleichzeitig auf 37 (AGP 9.5.0, Build-Tools
bleiben 35.0.0, da die Workflows deren Pfade nutzen). Der Android-CI-Lauf
[41943900334, Versuch 3](https://github.com/nikolausnold/NIKNOLIG-Monorepo/actions/runs/41943900334/attempts/3)
hat Assemble, Unit-Tests, Lint sowie APK-ID- und Signaturprüfung erfolgreich abgeschlossen. Damit
sind Build-Kompatibilität mit API 37 und AGP 9.5.0 sowie die Android-Tests/Lint in CI verifiziert;
ein Android-17-Emulator-Test und das Laufzeitverhalten (Edge-to-Edge, Predictive Back,
Intent-/Netzwerk-Beschränkungen) bleiben zu prüfen. Aktuelle Frist in der Play Console prüfen.

## Automatische Absicherung

`backend/tests/test_play_policy.py` schlägt fehl, wenn ein Modul zusätzliche Berechtigungen,
`<queries>`, Services, Standort-/Kontakt-/SMS-/Speicher-/Local-Network-APIs, AppFunctions oder
Billing-Code einführt, oder wenn die SDK-Level beider Module auseinanderlaufen. Neue
Berechtigungen erfordern bewusste Anpassung des Tests samt Begründung.

## Manuell vom Entwickler in der Play Console (Data safety / App content)

Nur zutreffende Angaben machen; keine pauschalen Erklärungen:

- Data safety: tatsächlich übertragene Daten gemäß aktuellem Backend (Support-Tickets, Gesundheits-/Profilangaben nur falls gesendet) und Verschlüsselung in Transit angeben.
- Datenschutzerklärung-URL je App hinterlegen; getrennt für NIKNOLIG und NIKNOLIG Defense.
- Berechtigungs-/Sensitive-Permission-Formulare für die Release-APKs: derzeit **keine** nötig. Erst bei späterer Standort-, Kontakt- oder Nearby-Nutzung ausfüllen.
- Zahlungen: „Enthält Käufe/Abos“ erst setzen, wenn Play Billing implementiert ist.
- Zielgruppe, Inhaltseinstufung, Ads-Erklärung und Zielgerichts-API-Level-Hinweise je App prüfen.
- Key-Management/Play App Signing je App getrennt bestätigen.
