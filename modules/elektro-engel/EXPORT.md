# Export in `nikolausnold/Elektro-Engel`

Ein separates Repository wurde nicht erstellt; Git-Historie und Branches wurden
nicht verändert. Der Modulkern ist unter `modules/elektro-engel/` abgegrenzt.

## Zu übertragende Dateien

Den gesamten Modulordner übertragen:

- `README.md`, `ARCHITECTURE.md`, `INTERFACES.md`, `SECURITY.md`, `EXPORT.md`
- `elektro_engel/*.py`
- `tests/test_core.py`

Die Laufzeitdateien benötigen ausschließlich Python 3.10+ und die
Standardbibliothek. Keine Datei außerhalb des Modulordners ist zur Laufzeit
erforderlich; insbesondere keine `backend/`-Schemas, App-Quellen oder
Monorepo-Konfiguration. Die Architektur-/Sicherheitsplanung bleibt als
Hintergrundreferenz nützlich, ist aber keine Laufzeitabhängigkeit.

## Schritte nach einer späteren Freigabe

1. Verantwortliche, Lizenz, Versionspolitik, Release-/Supportprozess und
   SecurityChain-P0-Kriterien festlegen und unabhängig prüfen lassen.
2. Im neuen Repository den gesamten Modulordner übernehmen und die Struktur
   gegebenenfalls als Repository-Root etablieren; interne Importe und
   Dokumentationspfade anschließend erneut auf Monorepo-Annahmen prüfen.
3. Python-Mindestversion und reproduzierbare CI-/Paketierung festlegen. Die
   aktuelle Implementierung hat noch keine veröffentlichte Paketmetadaten-,
   Wheel- oder Release-Konfiguration.
4. Tests unabhängig ausführen:

   ```sh
   PYTHONPATH=. python3 -m unittest discover -s tests
   ```

   Aus dem Modul-Root ist der Importpfad für den Testlauf `.`. Wird nur der
   Inhalt in einen Repository-Root kopiert, den Ordner `elektro_engel/` und
   `tests/` beibehalten.
5. Eine NIKNOLIG- oder Plattformintegration nur als separat reviewten Host-
   Adapter hinzufügen. Keine App-Credentials, Plattform- oder
   Produktionskonfiguration in den Core übernehmen.
6. Vor jeder Produktintegration Bedrohungsmodell, Datenflüsse, Authentifizierung,
   Autorisierung, Consent/Widerruf, Aufbewahrung, Tool-Allowlist und negative
   Tests neu freigeben. Export und bestandene Unit-Tests sind keine
   Produktionsfreigabe.
