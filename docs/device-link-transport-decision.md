# Geräteverbindung – Transportbewertung

Status: **Empfehlung, keine Entscheidung.** Die formale Auswahl ist OFFEN. Es ist kein Transport implementiert und keine Berechtigung (BLE, Standort, Nearby, lokales Netz) im Manifest ergänzt.

Ist-Architektur: beide Apps haben nur `INTERNET`; keine gemeinsame Bibliothek; keine Geräteverbindung; minSdk 26.

| Kriterium | BLE (GATT) | Nearby Connections | NSD/mDNS + TLS (LAN) |
|-----------|-----------|--------------------|----------------------|
| Reichweite | ca. 10–30 m, stark variabel | Nutzt BLE/WLAN, größer | Nur gleiches Netz; Netzwerk-/Client-Isolation möglich |
| Android-Support | ab API 18; Berechtigungen je Version (`BLUETOOTH_SCAN/CONNECT` ab 12, Standort davor) | Google Play Services nötig (zusätzliche Abhängigkeit) | Standard-API, Zertifikats-Pinning nötig |
| Sicherheit | Eigene Schicht über GATT nötig; Link-Layer-Pairing allein nicht ausreichend; Hersteller-Unterschiede | Eigene Verschlüsselung der Bibliothek, Vertrauensmodell extern | TLS mit gepinnten Schlüsseln, gut prüfbar |
| Offline | Ja | Ja | Nur mit lokalem Netz |
| Datenschutz | Scan-Berechtigungen, Tracking-Risiko durch Advertising | Play Services | Netz sichtbar |
| Neue Abhängigkeit | Nein | Ja (freigabepflichtig) | Nein |

## Empfehlung (Vorschlag)
Für nahe, netzunabhängige Kopplung ist BLE mit eigener Anwendungsschicht (siehe Protokoll-Dokument: gegenseitige Signatur, Replay-Schutz) plausibel, da es ohne neue Abhängigkeit auskommt. Voraussetzung: Vertraulichkeit auf Anwendungsebene (z. B. per ECDH-Sitzungsschlüssel mit etablierten JCA-Primitiven) wird ergänzt und die BLE-Prüfung nach P0 §6 besteht. NSD+TLS ist die Alternative, wenn gemeinsames WLAN akzeptabel ist. Nearby wird wegen der Play-Services-Abhängigkeit nicht empfohlen.

Nicht entschieden und nicht implementiert. Entscheidung, Manifest-Berechtigungen und Test-Anpassung (`INTERNET`-only-Test) erfordern gesonderte Freigabe.
