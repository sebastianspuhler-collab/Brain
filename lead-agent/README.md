# Lead-Agent

Internes Steuer-Tool für Vertrieb/Prozessia-Team - recherchiert Prospects,
hält Vault (`Leads/*.md`) und Close CRM synchron, bewertet Leads nach
`PLAYBOOK.md`-Regeln und legt Sales-Briefs sowie Gmail-Outreach-Entwürfe an.
Läuft als eigener, isolierter Docker-Container neben `backend/`, analog zu
`dev-agent/` - siehe `docs/system-overview-lead-agent.md` für die volle
Analyse, auf der dieses Modul basiert.

**Ersetzt Twenty CRM vollständig.** Twenty-Referenzen in
`backend/.env.example`/`CREDENTIALS.md` bleiben unangetastet stehen (nicht
gelöscht), werden aber nicht mehr verwendet - Close ist ab hier das System of
Record für Leads/Opportunities.

**Kein Landbot, kein n8n, kein öffentlicher Website-Chatbot.** Nur für
eingeloggte Prozessia-Mitarbeiter über den Backend-Proxy erreichbar.

## Architektur

- **Chat-Engine:** `claude -p` (Claude-Code-CLI-Subprocess, Abo-Billing über
  `CLAUDE_CODE_OAUTH_TOKEN`) - KEIN Anthropic-API-Key nötig. Custom-Tools
  laufen über einen lokalen MCP-Server (`mcp_server.py`), Vault-Lesen nativ
  über Claude Codes Read/Glob/Grep. Siehe `claude_agent.py` für Details und
  die Begründung, warum kein natives Write/Edit freigegeben ist.
- **Close CRM:** `close_client.py`, dünner Wrapper um `api.close.com/api/v1`
  mit Retry/Backoff bei 429/5xx.
- **Vault-Sync:** `vault_leads.py` liest/schreibt `Leads/*.md` (Frontmatter-
  Konvention wie bestehende `email_lead_service.py`/`calendar_lead_service.py`,
  erweitert um `close_lead_id`/`status`/`score`).
- **Webhook-Empfang:** `webhooks.py` + `POST /lead-agent/webhook/close`,
  HMAC-signaturgeprüft (fail-closed ohne Secret), öffentlich über einen
  eigenen, schmalen Traefik-Router direkt auf diesen Container geroutet
  (siehe docker-compose.yml) - bewusst NICHT über den Backend-Proxy, weil
  Close keine Cookie-Session mitschickt.
- **UI:** `static/index.html`, eine einzelne statische Seite (kein
  Build-Schritt), erreichbar unter `/api/lead-agent/ui` über den
  Backend-Proxy - bewusst NICHT ins React-Kundendashboard integriert.

## Auth-Modell

Zwei Zugriffswege, zwei unterschiedliche Auth-Mechanismen:

| Pfad | Erreichbar über | Auth |
|---|---|---|
| Chat (`/api/lead-agent/chat`), UI (`/api/lead-agent/ui`) | Backend-Proxy (`backend/app/routers/lead_agent_proxy.py`) | bestehende Cookie-Session (`Depends(get_current_user)`) |
| Close-Webhook (`/lead-agent/webhook/close`) | Direkt via Traefik (öffentlich) | HMAC-Signatur (`CLOSE_WEBHOOK_SIGNING_KEY`) |

Der lead-agent-Container selbst hat **keinen eigenen Login** - `/chat` und
`/health` sind nur aus dem internen `lead-agent-bridge`-Docker-Netzwerk
erreichbar (kein öffentlicher Port außer dem Webhook), exakt wie bei
`dev-agent/`.

## Warum Subpfad statt eigener Subdomain

Empfehlung: **Subpfad auf der bestehenden Domain**
(`brain.prozessia.space/api/lead-agent/ui`), nicht `lead-agent.prozessia.space`.

- Kein neuer DNS-Eintrag, kein neues Let's-Encrypt-Zertifikat, kein neuer
  Traefik-Host-Router nötig - Chat/UI laufen einfach über den bestehenden
  `/api/*`-Proxy in `frontend/Caddyfile` → `backend` → `lead-agent`.
- Die bestehende Session-Cookie-Auth funktioniert automatisch mit: das
  Cookie (`brain_session`) ist host-only auf `brain.prozessia.space` gesetzt
  (kein `Domain=`-Attribut in `backend/app/routers/auth.py`), würde also von
  einer echten Subdomain gar nicht automatisch mitgeschickt - das hätte eine
  zweite, separate Login-Lösung nötig gemacht.
- Nur der Close-Webhook braucht wirklich einen direkten, öffentlichen Weg
  (siehe oben) - dafür reicht ein einzelner zusätzlicher Traefik-Router mit
  `PathPrefix`, ebenfalls ohne neue Domain/Zertifikat.

**Alternative (falls später gewünscht):** eine eigene Subdomain
(`lead-agent.prozessia.space`) wäre sauberer trennbar/brandbar, bräuchte
aber einen neuen DNS-A-Record (DNS ist hier nicht wildcard, siehe
`DEPLOY.md`), einen neuen Traefik-Host-Router + eigenen
Let's-Encrypt-Cert-Resolver-Lauf, und eine eigene Login-Lösung für den
Lead-Agent (das Session-Cookie würde nicht automatisch mitkommen). Nur
sinnvoll, falls der Lead-Agent später ein eigenständigeres Produkt werden
soll als aktuell vorgesehen.

## Setup

```bash
cp lead-agent/.env.example lead-agent/.env
nano lead-agent/.env   # CLAUDE_CODE_OAUTH_TOKEN, CLOSE_API_KEY, CLOSE_WEBHOOK_SIGNING_KEY
```

`CLAUDE_CODE_OAUTH_TOKEN`: dasselbe Abo-Token wie `dev-agent/.env`/
`backend/.env` wiederverwenden (einmalig `claude setup-token`), oder ein
eigenes erzeugen - keine Sicherheitsgrenze, nur Abrechnung.

### Close-Setup

1. **API-Key:** Close → Settings → API Keys → Create new API key → in
   `CLOSE_API_KEY` eintragen.
2. **Custom Field "Quelle":** Close → Settings → Custom Fields → Lead → neues
   Textfeld anlegen (z.B. "Quelle"). Die dabei erzeugte Feld-**ID** (nicht
   der Anzeigename!) in `CLOSE_SOURCE_FIELD_ID` eintragen - ohne diese ID
   markiert `save_prospect`/`sync_lead_to_close` neue Leads nicht als
   `prozessia-lead-agent`, legt sie aber trotzdem an (kein Hard-Fail).
3. **Webhook:** Close → Settings → Webhooks → neuen Webhook anlegen, URL
   `https://<DOMAIN>/lead-agent/webhook/close`, Events nach Bedarf (mind.
   `lead.updated`, `activity.call.created`, `activity.note.created`,
   `opportunity.status_updated`). Das dabei angezeigte **Signing key** in
   `CLOSE_WEBHOOK_SIGNING_KEY` eintragen.

### Gmail-Entwürfe

Kein eigener OAuth-Consent-Flow - der Lead-Agent liest denselben Token wie
das Hauptbackend aus `_agent/gmail_token.json` im Vault-Mount. Ist dort noch
keiner vorhanden, einmal über das Hauptbackend/`_agent/gmail_setup.py`
authentifizieren.

### Deploy

```bash
docker compose up -d --build lead-agent
```

Nutzt dieselbe `${VAULT_PATH}`-Variable wie `backend` (siehe Root-`.env`).

## PLAYBOOK.md

**Noch von Sebastian inhaltlich zu befüllen** (ICP-Kriterien, Recherche-
Quellen, Scoring-Gewichtung) - der Agent liest die Datei bei jeder
Recherche-/Bewertungsanfrage automatisch, weigert sich aber, ohne befüllte
Kriterien zu bewerten/zu priorisieren, statt zu raten.

## Tests

```bash
cd lead-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest tests/ -v
```

Deckt `close_client.py` (Retry/Backoff, Fehlerpfade), `vault_leads.py`
(Frontmatter lesen/schreiben, insbesondere: mehrzeilige `tags`-Blöcke dürfen
bei einem `update_fields`-Aufruf nicht verloren gehen) und `webhooks.py`
(HMAC-Verifikation, Event→Status-Zuordnung) ab. `mcp_server.py`/
`claude_agent.py`/`server.py` sind nur strukturell gegen echten Import
geprüft (kein `CLAUDE_CODE_OAUTH_TOKEN` in der Testumgebung) - ein echter
End-to-End-Testlauf (`docker compose up -d --build lead-agent` + eine echte
Chat-Nachricht) steht noch aus.

## Was noch fehlt / offene Punkte

- **PLAYBOOK.md** inhaltlich befüllen (ICP, Recherche-Quellen, Scoring) -
  siehe oben.
- **Secrets eintragen:** `CLOSE_API_KEY`, `CLOSE_WEBHOOK_SIGNING_KEY`,
  `CLOSE_SOURCE_FIELD_ID`, `CLAUDE_CODE_OAUTH_TOKEN` in `lead-agent/.env`.
- **Close-Webhook-Payload live verifizieren:** `webhooks.py` ist strukturell
  gegen die dokumentierte Close-Signaturprüfung gebaut, aber das genaue
  Event-Payload-Schema (`_extract_lead_id()`/`_apply_event()`) noch nicht
  gegen ein echtes eingehendes Event geprüft - vor Produktivbetrieb einen
  Testwebhook aus Close auslösen und die Feldnamen abgleichen.
- **End-to-End-Test des Chat-Loops** mit echtem `CLAUDE_CODE_OAUTH_TOKEN`
  gegen den MCP-Server (analog zum offenen Punkt bei `claude_engine=cli` im
  Hauptbackend, siehe `claude_cli.py`-Docstring) - insbesondere
  `MCP_WARMUP_SECONDS` und die `--allowedTools`-Liste in `claude_agent.py`
  gegen ein echtes Deploy verifizieren.
- **Twenty CRM vs. Close:** laut Auftrag ersetzt Close Twenty vollständig -
  falls parallel noch echte Leadfeeder-Daten in Twenty liegen, die migriert
  werden sollen, ist das nicht Teil dieses Bauplans.
- **Traefik-Routing testen:** die `PathPrefix`-Priorität für den
  Webhook-Router (siehe docker-compose.yml-Kommentar) ist gegen Traefiks
  dokumentiertes Verhalten gebaut, aber noch nicht live gegen die bestehende
  `brain`-Route auf dem VPS verifiziert.
