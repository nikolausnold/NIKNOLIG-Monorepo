# Zwei-Geräte-Abnahmetest (manuell)

Status: **OFFEN – nicht durchgeführt.** Es standen keine zwei physischen Android-Geräte zur Verfügung. Dieser Test ist erst ausführbar, wenn Transport und Modul freigegeben und implementiert sind.

## Voraussetzungen
- Zwei echte Android-Geräte (A mit NIKNOLIG, B mit NIKNOLIG Defense), je ein Build aus derselben Commit-SHA (SHA notieren).
- Freigegebener Transport, Keystore-Adapter, Audit-Ansicht.

## Ablauf (Ergebnis je Schritt: bestanden / fehlgeschlagen / Notiz)
1. Ausgangslage: beide zeigen „Nicht gekoppelt“.
2. Kopplung starten auf A; Token zeigt sich lokal. Nach 120 s ungenutzt → Token abgelaufen, Kopplung nicht möglich.
3. Neues Token; B koppelt. Beide zeigen denselben 6-stelligen Code; nur nach Bestätigung auf beiden Geräten „Gekoppelt“. Ablehnung auf einer Seite → nicht gekoppelt.
4. Token ein zweites Mal verwenden → abgelehnt.
5. Direkt nach Kopplung: keine Daten übertragbar (keine Zustimmung).
6. Zustimmung für Datenbereich X erteilen → nur X fließt; Datenbereich Y wird abgelehnt.
7. Verbindungsabbruch (Flugmodus/Reichweite) → Status „Wiederverbindung“, keine Pufferung; nach Rückkehr erneute Authentifizierung.
8. Zustimmung widerrufen → Übertragung stoppt sofort.
9. Peer widerrufen, während B offline ist → A sperrt sofort; B erhält Hinweis nach Rückkehr; B kann nicht mehr senden.
10. Erneute Kopplung nach Widerruf nur über neues Token; Zustimmung beginnt leer.
11. Dritte Gerät/Fremd-App versucht Verbindung → abgelehnt, Audit-Ereignis.
12. Audit prüfen: keine Tokens, Schlüssel oder Nutzdaten; Referenzen max. 8 Zeichen.
13. App-Neustart und Neuinstallation: Kopplungszustand wie erwartet (Neuinstallation = neue Identität = neue Kopplung).

## Protokoll
Datum, Tester, Gerätemodelle/Android-Versionen, Commit-SHA, Ergebnis je Schritt, Abweichungen. Erst ein vollständig ausgefülltes Protokoll schließt Blocker 10; es ersetzt keine formale Freigabe.
