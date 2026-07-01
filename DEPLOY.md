# Prozessia Brain — VPS Deployment (Docker + Traefik)

Diese Anleitung ersetzt das alte manuelle Setup (Bash-Skript + systemd-Unit +
Cron-Job). Backend (FastAPI) und Frontend (React, ausgeliefert über einen
schlanken Caddy-Static-Server) laufen als zwei Container und klinken sich in
das **bereits auf dem VPS laufende Traefik** ein (Netzwerk `traefik_web`,
certResolver `letsencrypt`) — TLS/HTTPS übernimmt Traefik, nicht die App selbst.

## Voraussetzungen

- Docker + Docker Compose auf dem VPS (bereits vorhanden, da Traefik schon läuft)
- Traefik läuft mit Docker-Label-Provider im Netzwerk `traefik_web`,
  `exposedbydefault=false`, Entrypoints `web`/`websecure`, certResolver `letsencrypt`
  (so vorgefunden auf `srv1089921`)
- Domain `brain.prozessia.space`, zeigt per DNS auf die VPS-IP
- Der Prozessia-Vault liegt getrennt vom App-Code, z.B. unter `~/Prozessia-Brain`
  (NICHT im selben Ordner wie `backend/`/`frontend/` — sonst landet der App-Code
  im Datei-Browser des Dashboards)

## Setup

```bash
git clone <dieses-repo-url> ~/brain-app
cd ~/brain-app

cp .env.example .env
nano .env   # VAULT_PATH auf den echten Vault-Pfad setzen, DOMAIN eintragen

cp backend/.env.example backend/.env
nano backend/.env   # ANTHROPIC_API_KEY, SESSION_SECRET eintragen
```

Benutzer + Passwort-Hashes anlegen (erzeugt `backend/users.json`, das per Bind-Mount
in den Container geht — bewusst eine Datei statt einer ENV-Variable, weil bcrypt-Hashes
`$`-Zeichen enthalten, die docker-compose in `env_file`-Werten sonst als
Variablen-Interpolation missversteht und stillschweigend kaputt schreibt):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/hash_password.py   # einmal pro Benutzer ausführen (Sebastian, Amin)
cd ..
```

Dann im Repo-Root:

```bash
docker compose up -d --build
```

`docker-compose.yml` erwartet das externe Netzwerk `traefik_web` (existiert schon,
da Traefik es selbst nutzt) — falls es aus irgendeinem Grund fehlt:
`docker network create traefik_web`.

## Zugriff

Erreichbar unter `https://<DOMAIN>` — Traefik holt automatisch ein
Let's-Encrypt-Zertifikat (certResolver `letsencrypt`, HTTP-01-Challenge über
Entrypoint `web`). HTTP auf Port 80 wird automatisch auf HTTPS umgeleitet.
Login läuft über echte Benutzerkonten mit gehashten Passwörtern (kein
Klartext-Passwort mehr im Quellcode wie im alten Server).

## Befehle

```bash
docker compose logs -f              # Live-Logs (Backend + Web/Caddy)
docker compose restart backend      # Backend neu starten
docker compose up -d --build        # Nach einem git pull neu bauen und starten
docker logs traefik --tail 50       # Traefik-Logs, falls Routing/TLS nicht greift
```

## Vault aktualisieren

Der Vault ist ein separates Verzeichnis (nicht Teil dieses Repos) und wird als
Docker-Volume eingebunden. Änderungen am Vault (z.B. `git pull` im Vault-Repo,
falls Sebastian ihn weiterhin über GitHub synchronisiert) werden automatisch
sichtbar — ein Neustart des Containers ist nur nötig, wenn sich `.env`-Werte
ändern.

## Was sich gegenüber dem alten Setup geändert hat

- FastAPI (Python) statt Roh-`http.server`-Skript, React statt einer
  Kombination aus statischer HTML-Datei und einer parallelen Streamlit-App
- HTTPS über das bestehende Traefik statt reinem HTTP über Port 3001
- Gehashte Passwörter + signierte Session-Cookies statt zwei Klartext-Passwörtern
  im Quellcode und Token-Auth über URL-Query-Parameter
- Ein konsolidierter Inbox-Watcher statt zwei parallelen (watchdog + Polling-Thread)
- `docker compose up -d` statt manueller Bash-Skript- und systemd-Einrichtung
