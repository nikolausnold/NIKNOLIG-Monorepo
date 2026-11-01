# device-link-reference

Inerte JVM-Referenzimplementierung der Geräteverbindung NIKNOLIG ↔ NIKNOLIG Defense.

**Status: nicht freigegeben, nicht aktiv.**

- Nicht in `settings.gradle.kts` registriert, keine Abhängigkeit der Apps, nicht in CI.
- Enthält **keinen Transport** (BLE/Nearby/NSD sind nicht ausgewählt) und `ProductionGate.ENABLED = false`.
- Die Aufnahme als Gradle-Modul oder in die Apps braucht eine eigene Freigabe (siehe `docs/device-link-security-design.md` §2).
- Nur JCA (`SHA256withECDSA`, P-256, `SecureRandom`); keine eigene Kryptografie.
  Produktiv müssen Schlüssel nicht-exportierbar im Android Keystore liegen (`DeviceKeys`); `JcaDeviceKeys` ist nur für Tests.

Inhalt: `Crypto`, `Audit`, `Pairing`, `Consent`, `Session` unter `org.niknolig.devicelink`.

## Tests lokal ausführen

Gradle-Anbindung existiert bewusst nicht. Mit Kotlin-Compiler und JUnit 4.13.2:

```
kotlinc src/main/kotlin src/test/kotlin -cp junit-4.13.2.jar -d out
java -cp out:junit-4.13.2.jar:hamcrest-core-1.3.jar org.junit.runner.JUnitCore org.niknolig.devicelink.DeviceLinkTest
```

Ein bestandener Test ist keine Sicherheitsfreigabe und ersetzt weder BLE-/Keystore-Prüfung noch den Zwei-Geräte-Test.
