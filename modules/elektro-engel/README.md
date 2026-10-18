# Elektro-Engel Core

## Status

Ein eigenständiger, plattformneutraler Python-Kern unter
`modules/elektro-engel/`. Er benötigt nur Python 3.10+ und die
Python-Standardbibliothek. Die Bestandsaufnahme fand hier keine vorhandene
Elektro-Engel-Core-Laufzeit; wiederverwendet werden die bestehenden
Architekturgrenzen und versionierten Consent-/Sensorverträge, nicht deren
deklarative Schemas als Runtime.

Der Kern ist bewusst **keine generative KI**: Er plant deterministisch genau
einen menschlich zu prüfenden Schritt. Es gibt kein Modell, keine Netzwerk-,
Sensor-, Gerätewechsel-, Authentifizierungs- oder Persistenzfunktion und keine
Produktivfreigabe. Produktive Integrationen bleiben bis zur unabhängigen
SecurityChain-P0- und Produktfreigabe gesperrt.

## Architektur

- `CoreEngine` koordiniert begrenzte Planung, explizit freigegebene Tools und
  minimierte Audit-Ereignisse.
- `ContextStore` hält nur explizit als nicht sensibel klassifizierte, kleine
  Kontextwerte im Prozessspeicher.
- `BoundedPlanner` erstellt einen Vorschlag, führt ihn nicht aus.
- `ToolRegistry` ruft ausschließlich lokal registrierte Funktionen und nur mit
  einer exakt auf Request und Tool passenden Freigabe auf.
- `LearningSandbox` nimmt unverbindliche, flüchtige Vorschläge auf und kann
  keine aktive Sicherheitsregel ändern.
- `NiknoligAdapter` ist nur ein optionaler Port; eine App-Integration ist nicht
  enthalten. Der Core importiert keine NIKNOLIG-App-Interna.
- `InMemoryAuditLog` hält begrenzte Metadaten ohne Eingaben, Tool-Argumente oder
  Tool-Ergebnisse.

Details: [Architektur](ARCHITECTURE.md),
[Schnittstellen](INTERFACES.md), [Sicherheit](SECURITY.md).

## Verwendung

Vom Modulverzeichnis aus:

```sh
PYTHONPATH=. python3 - <<'PY'
from elektro_engel import CoreEngine, TaskRequest

engine = CoreEngine()
plan = engine.plan(TaskRequest("Einen Entwurf prüfen"))
print(plan.status, plan.steps[0].requires_human_review)
PY
```

Die Ausgabe ist ein Vorschlag, keine Ausführung. Tools erfordern eine
Host-seitig erteilte, zweckgebundene Zustimmung. `ToolApproval` ist lediglich
ein Übergabevertrag und kein Authentifizierungs- oder Autorisierungsmechanismus;
der Host muss Nutzeridentität, Berechtigung, Consent und Widerruf selbst prüfen.
Beispieltests:

```sh
PYTHONPATH=modules/elektro-engel python3 -m unittest discover \
  -s modules/elektro-engel/tests
```

## Export

Die spätere Übertragung in `nikolausnold/Elektro-Engel` ist vorbereitet, aber
nicht durchgeführt. Die Dateien und Schritte stehen in [EXPORT.md](EXPORT.md).
Es wurden keine Git-Historie geändert und kein neues Repository angelegt.
