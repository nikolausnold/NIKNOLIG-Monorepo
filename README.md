# NIKNOLIG-Monorepo

Zentrale Integrationsplattform für NIKNOLIG, Elektro-Engel und NIKNOLIG Defense.

## Aktueller Stand

Diese Arbeitskopie enthält Dokumentation, einen manuellen Read-only-Audit-
Workflow sowie den OpenAI-Gateway für Cloudflare Workers. Der Gateway-Quellcode
liegt im Monorepo unter `workers/openai-gateway/`. Produktclients und zusätzliche
Datenquellen der drei Systeme sind hier nicht vorhanden. Die Inhalte der
separaten Repositorys `NIKNOLIG` und `NIKNOLIG-Defense` konnten in dieser Sitzung
nicht eingesehen werden; aus ihrem Namen oder der bisherigen Dokumentation lässt
sich keine zusätzliche Workers-Quelle ableiten.

| Bereich | Verifizierter Stand |
| --- | --- |
| Repository-Struktur | `README.md`, `.github/workflows/audit-workers.yml`, `workers/openai-gateway/` |
| Abhängigkeiten | Keine Drittanbieter-Abhängigkeiten |
| Tests | Node.js-Built-in-Test für den Worker-Gateway-Vertrag |
| Schnittstellen | `POST /v1/assist`; Produktclients und kontrollierter Datenaustausch fehlen |

## OpenAI-Gateway (Cloudflare Workers)

`workers/openai-gateway` enthält einen serverseitigen Gateway-Vertrag für
NIKNOLIG, Elektro-Engel und NIKNOLIG Defense. Die drei Systemkennungen verwenden
getrennte Cloudflare-Access-Audiences und getrennte Systemanweisungen. Der
Gateway akzeptiert ausschließlich `system` und `input`; er speichert keine
Konversationen, sendet `store: false` an OpenAI und gibt keine Upstream-Fehler
oder API-Schlüssel zurück. Ein explizites `shareWith`-Feld wird abgelehnt. Ein
systemübergreifender Datenaustausch ist derzeit nicht implementiert, da keine
Projektquellen oder Schnittstellen vorhanden sind.

Eingaben sind auf 4.000 Zeichen, OpenAI-Ausgaben auf 300 Tokens und Aufrufer auf
10 Anfragen pro Minute begrenzt. Netzwerk-, Upstream- und Konfigurationsfehler
liefern einen allgemeinen Offline-Fallback. Das Rate-Limit und die Tokenlimits
begrenzen einzelne Aufrufe, sind aber kein monatliches Ausgabenbudget; dafür
muss zusätzlich ein Ausgabenlimit im OpenAI-Projekt konfiguriert werden.

Für den Betrieb sind eine Cloudflare-Access-Anwendung pro System, die zugehörigen
Audiences, eine Rate-Limit-Namespace-ID und das Worker-Secret `OPENAI_API_KEY`
erforderlich. Die Werte für die Platzhalter in
`workers/openai-gateway/wrangler.toml` werden nicht im Repository hinterlegt:

- `ACCESS_TEAM_DOMAIN`: ausschließlich der Access-Team-Hostname, ohne
  `https://` und Pfad. Der bestehende Worker akzeptiert nur Hostnamen unter
  `cloudflareaccess.com`; den exakten Team-Hostname im Cloudflare Zero Trust
  Dashboard unter **Settings → General → Team domain** übernehmen.
- `SYSTEM_AUDIENCES`: JSON-Objekt mit genau den Schlüsseln `niknolig`,
  `elektro-engel` und `niknolig-defense`. Jeder Wert muss unverändert die
  Audience-Tag-Zeichenkette (`aud`) der jeweils zugehörigen Cloudflare-Access-
  Anwendung sein. Die konkreten Tags unter **Access → Applications → jeweilige
  Anwendung → Overview → Application Audience (AUD) Tag** ablesen; keine Tags
  aus Systemnamen ableiten. Aktuell ist der konfigurierte Wert `{}` und reicht
  nicht zur Authentifizierung.
- `OPENAI_API_KEY`: ausschließlich als geschütztes Worker-Secret, nicht als
  `vars`-Eintrag, speichern. Den Schlüssel ausschließlich mit
  `wrangler secret put OPENAI_API_KEY` setzen
  ([Worker-Secrets-Dokumentation](https://developers.cloudflare.com/workers/configuration/secrets/)).

Die Access-Anwendungen müssen jeweils nur die vorgesehenen Benutzer/Clients des
zugehörigen Systems zulassen. Secret-Werte werden nicht ausgelesen oder
ausgegeben. Die Verfügbarkeit des Cloudflare-Secrets ließ sich in dieser
Umgebung nicht prüfen; ein Deployment fand nicht statt.

Das vorhandene GitHub-Secret `OPENAI_API_KEY` wird von GitHub Actions nicht
automatisch an den Worker übertragen. Der Read-only-Audit verwendet keine
Secrets und stellt keine Verbindung zu Cloudflare her. Für den Worker-
Laufzeitbetrieb muss der Schlüssel separat als Cloudflare-Worker-Secret
`OPENAI_API_KEY` hinterlegt sein; es wurde weder geprüft noch verändert.

Die vorhandenen Repositorys enthalten keine Frontends oder Backends der drei
Systeme; deshalb kann dieser Gateway-Vertrag noch von keinem Produktivsystem
aufgerufen werden. Tests lokal ausführen:
`node --test workers/openai-gateway/src/index.test.mjs`.

## Read-only Workers-Audit

Der manuell startbare Workflow `Read-only Workers repository audit` prüft die
bereits im selben Repository liegende Quelle `workers/openai-gateway/`. Er
benötigt weder eine zweite Workers-Repository-URL noch ein PAT: GitHub Actions
checkt dieses Repository mit `contents: read` aus und persistiert keine
Checkout-Zugangsdaten. Der Audit führt keinen Quellcode aus und deployt nichts.

Die frühere Dokumentation verwies auf `niknolig-workers`, verlangte dafür
`WORKERS_REPOSITORY_URL` und `WORKERS_REPO_READ_PAT`, nannte aber keine konkrete
Repository-URL. In den vorhandenen Repository-Dateien gibt es keinen Beleg, dass
der Gateway aus einem separaten Repository stammen muss. Die beiden bekannten
separaten Repositorys waren in dieser Sitzung nicht einsehbar; falls dort
zusätzliche Datenquellen oder Produktclients liegen, müssen sie separat
zugänglich gemacht und ihre Schnittstellen geprüft werden.
