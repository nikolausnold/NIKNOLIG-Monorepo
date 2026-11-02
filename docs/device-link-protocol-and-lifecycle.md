# Geräteverbindung – Identität, Protokoll, Lebenszyklus, Audit

Entwurf zur Prüfung. Keine Freigabe. Referenzcode: `modules/device-link-reference` (inert).

## 1. Geräteidentität und Schlüssel
- Je App ein eigenes EC-P-256-Schlüsselpaar (`SHA256withECDSA`), produktiv **nicht exportierbar im Android Keystore** (`setUserAuthenticationRequired` je nach Entscheidung; StrongBox falls verfügbar). Private Schlüssel verlassen den Keystore nie.
- `DeviceId` = SHA-256-Fingerprint des öffentlichen Schlüssels. Identität ist App-gebunden (`AppScope`); NIKNOLIG koppelt nur mit Defense und umgekehrt.
- Nur JCA-Primitive, keine eigene Kryptografie.
- **Keystore-Adapter ist nicht implementiert** und nicht auf echter Hardware geprüft (OFFEN).

## 2. Kopplung
1. Ein Gerät erzeugt ein Kopplungstoken (16 Byte `SecureRandom`, 120 s gültig, einmalig, max. 3 Fehlversuche) und zeigt es lokal an (Out-of-band, z. B. QR).
2. Beide Seiten tauschen Hello (Version, Scope, Public Key, frische Nonce). Replays alter Nonces werden abgelehnt.
3. Beide signieren das Transkript (Kontext, beide Hellos, Token-Hash, Rolle) → gegenseitige Authentifizierung und Token-Besitz.
4. Beide Nutzer vergleichen einen 6-stelligen Bestätigungscode. Ohne Bestätigung wird kein Peer gespeichert.
5. Kopplung erteilt **keine** Datenrechte.

## 3. Wiederverbindung und Sitzung
- Gegenseitige Challenge-Response gegen gepinnte Schlüssel (Challenge 30 s, einmalig).
- Nachrichten: ECDSA-signiert, Sitzungs-ID, monoton steigender Zähler, max. 4096 Byte, Autorisierung bei Senden und Empfangen. Jeder Fehler schließt die Sitzung. Vertraulichkeit muss der freigegebene Transport liefern (offen).
- Zustände: idle, discovering, pairing, connected, reconnecting, revoked, failed. Keine Pufferung bei Verbindungsabbruch.

## 4. Rollen, Zustimmung, Widerruf
- `RolePolicy` ist per Default `DENY_ALL`; erlaubte (Gerät, Datenbereich, Richtung) müssen explizit festgelegt werden. Die Datenbereiche im Code sind Platzhalter (OFFEN).
- Zustimmung je Datenbereich und Richtung, ausdrücklich durch den Nutzer, Gültigkeit 24 h (Vorschlag).
- Widerruf einer Zustimmung wirkt sofort. Widerruf eines Peers sperrt ihn sofort, auch offline; die Benachrichtigung bleibt „ausstehend“, bis sie zugestellt werden kann. Die Sperre hängt nicht von der Zustellung ab.
- Fehlgeschlagene Autorisierung: Ablehnung ohne Details an den Peer, Audit-Ereignis, Sitzung geschlossen.

## 5. Schlüsselwechsel, Geräteverlust, erneute Kopplung
- **Schlüsselwechsel** = neue Identität = neue Kopplung mit Bestätigung; kein stilles Rotieren. Ein geänderter Schlüssel gilt als unbekannter Peer.
- **Geräteverlust:** am verbliebenen Gerät Peer widerrufen (sofortige Sperre). Das verlorene Gerät verliert damit jede Autorisierung; am verlorenen Gerät lokale Daten über Systemfunktionen sperren/löschen.
- **Erneute Kopplung** nach Widerruf: nur über neues Token und Nutzerbestätigung; Zustimmung beginnt leer.

## 6. Audit-Policy (datensparsam)
- Erfasst: Authentifizierung (ok/fehlgeschlagen), Kopplungsversuche, Zustimmungs- und Rechteänderungen, Widerruf, Autorisierungsverweigerung, sicherheitsrelevante Sitzungsfehler.
- Felder: Typ, Zeit, pseudonyme Peer-Referenz (erste 8 Zeichen des Fingerprints), Ergebnis aus geschlossenem Enum. **Kein Freitext**, keine Tokens, Schlüssel, Nutzdaten oder Passwörter.
- Aufbewahrung (Vorschlag): max. 200 Ereignisse / 30 Tage, lokal. Aktuell nur im Speicher; Persistenz und Retention nicht freigegeben.

## 7. SecurityChain-P0 – Evidenzmatrix
Spalte „Technisch“ ≠ Freigabe.

| Bereich | Nachweis (Test in `DeviceLinkTest`) | Lücke | Freigabe |
|---------|--------------------------------------|-------|----------|
| Authentication | validPairing…, wrongOrTampered…, peerWithoutTheToken…, mutualReconnect…, unknownImpostor… | Keystore-Adapter, echte Geräte | OFFEN |
| Authorization | pairingAlone…, scopesAreConsented…, denyAll…, consentExpires, revocation… | Endgültige Rollen/Scopes | OFFEN |
| BLE Security | – | Transport nicht gewählt | OFFEN |
| Error Handling | tampered…, unauthorizedScope…, wrongSessionId, connectionLoss… | UI-Texte, Transportfehler | OFFEN |
| Logging/Audit | auditRecordsOnly…, auditIsBounded… | Persistenz, Retention | OFFEN |

Die Tests sind JVM-Tests mit Mock-Transport; sie beweisen weder BLE-Verhalten noch Keystore-Eigenschaften noch Interoperabilität.
