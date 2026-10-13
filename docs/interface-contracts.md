# Schnittstellenverträge

Dies sind verbindliche Designanforderungen für spätere Schnittstellen, keine
bereits laufende API.

## Austauschprinzipien

- Modulübergreifender Austausch erfolgt ausschließlich über dokumentierte,
  versionierte Schnittstellen. Direkte Zugriffe auf fremde interne Speicher oder
  Funktionen sind nicht vorgesehen.
- Jede Anfrage und jedes Ereignis muss eine authentifizierte Identität
  aufweisen. Zusätzlich wird jede Aktion anhand des konkreten Akteurs, der
  Ressource und des erlaubten Vorgangs autorisiert. Authentifizierung allein
  gewährt keinen Zugriff.
- Autorisierung folgt dem Prinzip der minimalen Berechtigung und verweigert
  standardmäßig nicht ausdrücklich erlaubte Vorgänge.
- Defense erhält keine implizite Berechtigung durch gemeinsame Modelle oder
  gemeinsame Bibliotheken. Defense-spezifische Daten und Aktionen benötigen
  eine explizite Freigabe durch den zuständigen Adapter.
- Keine API-Schlüssel, Tokens oder Secrets in Verträgen, Beispielkonfigurationen,
  Quellcode, Logs oder README aufnehmen.

## Vertragselemente für die spätere Spezifikation

Vor der ersten produktiven Schnittstelle sind mindestens festzulegen:

- Zweck, Besitzer und Verbraucher der Schnittstelle
- Versionierung und Abwärtskompatibilitätsregeln
- Identitäts- und Authentifizierungsmechanismus
- Berechtigungen je Aktion und Datentyp
- Datenminimierung, Klassifizierung und Aufbewahrung
- Validierung, Fehlercodes und sichere Fehlerdetails
- Zeitlimits, Wiederholungsregeln und Schutz gegen doppelte Ausführung
- Audit-Anforderungen ohne Secrets oder unnötige personenbezogene Daten
- Verhalten bei Offlinebetrieb, Widerruf, Konflikten und Verbindungsverlust

Konkrete Protokolle, Formate, Schlüsselverwaltung und Fehler-Envelopes sind
offen, bis Technologie und Vertrauensmodell der Quellprojekte geprüft wurden.

## Elektro-Engel

Gerätebefehle, Sensorwerte und Automatisierungsaktionen müssen jeweils
typisiert, validiert und autorisiert werden. Eine Schnittstelle darf keine
beliebigen Gerätebefehle allein aufgrund eines empfangenen Nachrichteninhalts
ausführen. Geräteverfügbarkeit und lokale Benutzerfreigaben sind als mögliche
Fehler- und Berechtigungsbedingungen zu behandeln.

## Defense-Integration

Die Integration ist eine explizite, eng begrenzte Grenze. Zuerst muss fachlich
festgelegt werden, welche Informationen in welche Richtung fließen dürfen.
Aktionen mit Sicherheitsauswirkung benötigen die dafür vorgesehenen
Authentifizierungs-, Autorisierungs- und Freigabeprozesse. Ein Ausfall oder eine
Nichtverfügbarkeit von Defense darf nicht durch Umgehung von Schutzregeln
kompensiert werden.
