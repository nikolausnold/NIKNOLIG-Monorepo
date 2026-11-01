# Geräteverbindung – Blocker-Inventar

Stand: Entwurf. Dieses Dokument erteilt **keine** Freigabe. Produktive Kopplung bleibt gesperrt
(`PairingGate.APPROVED = emptySet()` in beiden Apps, `ProductionGate.ENABLED = false` in der Referenz).

"Technisch umgesetzt (Referenz)" = JVM-Referenzcode in `modules/device-link-reference` + Tests.
"Freigabe" = formale menschliche Entscheidung; sie fehlt überall.

| # | Blocker | Ursache | Erforderliche Änderung | Abnahmekriterium (prüfbar) | Technisch | Freigabe |
|---|---------|---------|------------------------|----------------------------|-----------|----------|
| 1 | SecurityChain-P0 nicht freigegeben | Spezifikation v0.6 ist Review-Entwurf (`securitychain-p0-specification.md`) | Formale Freigabe durch Verantwortliche | Unterschriebener Eintrag im Freigaberegister (`securitychain-d01-d12-abschlussstatus.md`) | – | OFFEN |
| 2 | Transport nicht gewählt | Keine Entscheidung, nur Optionen | Entscheidung nach `device-link-transport-decision.md` | Dokumentierte Entscheidung + Sicherheitsprüfung des gewählten Transports | Empfehlung dokumentiert, nichts implementiert | OFFEN |
| 3 | Geräteidentität/Peer-Authentifizierung | Keine Identität in den Apps | EC-P-256-Schlüssel im Android Keystore, Fingerprint als DeviceId, gegenseitige Challenge-Response | Tests `mutualReconnect…`, `unknownImpostor…`, `changedPeerKey…`, `valid/wrongOrTampered…` grün; Keystore-Adapter auf echtem Gerät geprüft | Referenz (JCA); Keystore-Adapter nicht implementiert | OFFEN |
| 4 | Replay-Schutz / kurzlebige Tokens | Nicht vorhanden | Token 120 s, einmalig, 3 Versuche; frische Nonces; Zähler pro Sitzung | Tests `expiredToken`, `tokenIsSingleUse`, `recordedHandshake…`, `authorizedMessageFlows…` grün | Referenz | OFFEN |
| 5 | Zustimmung/Rollen | Keine Consent-Logik | Getrennte, ablaufende Zustimmung je Datenbereich/Richtung; Rollenpolicy default DENY_ALL | Tests `pairingAloneGrantsNoDataAccess`, `scopesAreConsented…`, `denyAll…`, `consentExpires` grün; konkrete Datenbereiche entschieden | Referenz mit Platzhalter-Scopes | OFFEN (Scopes/Rollen) |
| 6 | Widerruf/Sperrung | Nicht vorhanden | Sofortige Sperre, Offline-Hinweis ausstehend, neue Kopplung nötig | Tests `revocationBlocks…`, `revocationDuringActiveSession…` grün; Verhalten am Gerät geprüft | Referenz | OFFEN |
| 7 | Audit-Policy | Kein Audit-Speicher; Aktivierung nicht freigegeben | Geschlossene Enums, pseudonyme Referenz (8 Zeichen), Limit 200 Events/30 Tage (Vorschlag) | Tests `auditRecordsOnly…`, `auditIsBounded…` grün; Retention freigegeben | Nur In-Memory | OFFEN (Persistenz/Retention) |
| 8 | Fehlerbehandlung | Keine einheitliche Behandlung | Fail-closed, generische Fehler, Sitzung schließt bei jedem Fehler | Tests `tampered…`, `unauthorizedScope…`, `wrongSessionId…`, `connectionLoss…` grün | Referenz | OFFEN |
| 9 | BLE-Sicherheit | Transport nicht gewählt | Nur falls BLE gewählt: Prüfung nach P0 §6 | Gerätetest mit Sniffer/Reichweite | Nicht implementiert | OFFEN |
| 10 | Zwei-Geräte-Abnahme | Keine physischen Geräte verfügbar | Durchführung nach `device-link-acceptance-test.md` | Ausgefülltes Protokoll mit zwei echten Android-Geräten | – | **OFFEN** |
| 11 | Modulaufnahme | Gemeinsames Modul braucht Freigabe (§2) | Entscheidung, ob `:device-link-core` entsteht | Freigabe + CI-Integration | Referenz unregistriert | OFFEN |

## Vorbestehende Fehler (nicht durch diese Änderung)

- `backend/tests`: Tests, die `psycopg` benötigen, schlagen lokal ohne das Paket fehl.
- 3 `tools`-Tests: `ModuleNotFoundError: tools` je nach Startverzeichnis.
