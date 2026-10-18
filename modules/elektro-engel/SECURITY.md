# Sicherheitsregeln und Schutzmaßnahmen

## Sicherheitsstatus

Dieses Modul ist ein lokaler, nicht-produktiver Kern-Prototyp. Es belegt weder
SecurityChain-P0-Konformität noch sichere Authentifizierung, sichere
Autorisierung oder eine Produktionsfreigabe. Ungeklärte Sicherheitsfragen
bleiben ein Stop-Gate.

## Implementierte Schutzgrenzen

- Keine Zugangsdaten, Secrets, Schlüssel, Netzwerkclients oder produktiven
  Endpunkte im Kern.
- Eingabe-, Kontext-, Tool- und Vorschlagsgrößen sowie Registry-, Audit- und
  Sandbox-Kapazitäten sind begrenzt.
- Kontext und Sandbox-Vorschläge werden nicht automatisch befüllt und nicht
  persistiert; sensible Kontextkategorien werden abgelehnt.
- Planung bleibt ein einzelner, nicht ausführbarer Vorschlag.
- Tools sind nicht standardmäßig vorhanden. Ein registriertes Tool wird nur
  nach einer Freigabe ausgeführt, die exakt Request und Tool bindet.
- Audit protokolliert nur Request-ID, Ereignistyp, Ergebnis, Toolname und Zeit;
  keine Eingaben, Toolargumente oder Toolergebnisse. Tool-Exception-Texte
  werden nicht weitergegeben.
- Sandbox-Vorschläge können keine produktiven Sicherheitsregeln ändern.

## Host-Pflichten und ausgeschlossene Fähigkeiten

`ToolApproval` ist kein Beweis einer Nutzeraktion, Identität, Berechtigung oder
Consent. Host und Adapter müssen diese Prüfungen bei jeder Aktion selbst
durchsetzen und Widerruf sofort berücksichtigen. Die Kernbibliothek bietet
keinen Schutz vor bösartigem oder fehlerhaftem Host-Code, Tool-Code oder
Betriebssystem.

Es gibt keine Gerätewechsel-, Sensor-, LiDAR-, Kamera-, Mikrofon-, Standort-,
Pairing-, Netzwerk-, Fernsteuerungs- oder Defense-Funktion. Gerätewechsel
erfordern später eine ausdrückliche Freigabe. Sensorzugriff darf erst nach
nachgewiesener Hardwareunterstützung, OS-Berechtigung, passender
Datenschutzfreigabe und unabhängiger Prüfung über einen begrenzten Adapter
integriert werden. NIKNOLIG Defense bleibt getrennt. KI-generierte
Sicherheitsregeländerungen benötigen explizite menschliche Prüfung und
Freigabe.

Das Audit ist flüchtig und nicht manipulationssicher; es ist kein
Compliance-/Forensiknachweis. Keine produktiven Nutzerdaten in Tests oder
Vorschläge einbringen.
