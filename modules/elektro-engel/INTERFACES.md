# Öffentliche Schnittstellen

## Stabilität

Die öffentliche Python-Oberfläche wird aus `elektro_engel` exportiert. Sie ist
derzeit API-Version `0.x` und noch keine veröffentlichte oder
kompatibilitätsgarantierte Bibliothek. Änderungen vor einem externen Release
werden dokumentiert; inkompatible Änderungen nach einem Release benötigen eine
neue Major-Version. Die Backend-Verträge unter `backend/contracts/` sind
separate versionierte Austauschverträge und werden nicht durch diese Python-API
ersetzt.

## Typen und Operationen

- `TaskRequest(objective, request_id=...)`: begrenzte Zieleingabe; Standard-ID
  wird lokal erzeugt.
- `CoreEngine.plan(request) -> TaskPlan`: genau ein vorgeschlagener Schritt,
  der menschliche Prüfung verlangt. Führt keine Aktion aus.
- `PlanStep`, `TaskPlan`: unveränderliche Vorschlagsmodelle.
- `ContextStore.put(key, value, category="non_sensitive")`: explizites
  In-Memory-Kontextspeichern; unbekannte/sensible Kategorien werden abgelehnt.
  `snapshot()` gibt eine Kopie zurück, `clear()` löscht den Store.
- `ToolRegistry.register(name, callable)`: registriert bis zu 32 lokale Tools.
  `execute(...)` lehnt nicht registrierte Tools und fehlende oder unpassende
  `ToolApproval(request_id, tool_name, explicitly_granted=True)` ab.
- `CoreEngine.execute(request, tool_name, arguments, approval)`: delegiert
  ausschließlich nach diesen Prüfungen an den registrierten Host-Code.
  Toolfehler werden ohne Exception-Text als `ToolExecutionError` exponiert.
- `LearningSandbox.propose(id, candidate)`: speichert nur begrenzte, als
  `unvalidated` markierte Vorschläge im Prozessspeicher. Es gibt keine
  Aktivierungs- oder Policy-Update-Operation.
- `InMemoryAuditLog.events()`: liefert eine begrenzte Folge von
  `AuditEvent`-Metadaten. Keine freien Nutzdaten oder Toolparameter werden
  protokolliert.
- `NiknoligAdapter`: optionales `Protocol` für eine außerhalb des Kerns
  implementierte Übersetzung und Darstellung.

## Integrationsregeln

Host-Anwendungen müssen vor Toolregistrierung und jeder Ausführung
Authentifizierung, Autorisierung, konkrete Nutzerfreigabe und Widerruf prüfen.
Eine Zustimmung zu einer Funktion oder einem Request darf nicht auf andere
Requests, Geräte oder App-Bereiche übertragen werden. Keine Funktion darf
Umgehungen bestehender Sicherheitsprüfungen oder autonome externe Aktionen
implementieren.

Schnittstellen verwenden ausschließlich Python-Werte und Kernmodelle. Android-,
iOS-, UI-, Backend- und NIKNOLIG-App-Typen gehören in Host-Adapter, niemals in
den Kern.
