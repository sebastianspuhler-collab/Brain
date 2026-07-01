# Prozessia Brain

Second Brain für Prozessia GbR: FastAPI-Backend (`backend/`) + React-Frontend
(`frontend/`), das über den gesamten Vault (Kunden, Finanzen, E-Mails, Aufgaben)
chattet. Diese Anleitung ist für die **lokale Entwicklung**. Für den
VPS-Rollout mit Docker siehe [DEPLOY.md](DEPLOY.md).

## Voraussetzungen

- Python 3.11+
- Node.js 20+
- Ein Anthropic API Key
- Der Vault-Ordner (Kunden/, Finanzen/, _agent/ etc.) — lokal ist das meist
  dieses Repo selbst, siehe Hinweis unten

## 1. Backend

```bash
cd backend
python -m venv .venv
```

Aktivieren (abhängig von der Shell — `.venv\Scripts\activate` ohne Endung
funktioniert NUR in cmd.exe, nicht in PowerShell):

```powershell
# PowerShell:
.venv\Scripts\Activate.ps1
```

```cmd
:: cmd.exe:
.venv\Scripts\activate.bat
```

```bash
# macOS/Linux/Git Bash:
source .venv/bin/activate
```

Falls PowerShell mit `... kann nicht geladen werden, da die Ausführung von
Skripts auf diesem System deaktiviert ist` abbricht, einmalig (nur für die
aktuelle Sitzung, keine Admin-Rechte nötig):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Danach, in jeder aktivierten Shell:

```bash
pip install -r requirements.txt
```

`.env` anlegen:

```bash
cp .env.example .env
```

Und darin ausfüllen:

- `VAULT_PATH` — Pfad zum Vault-Ordner (lokal z.B. der Pfad zu diesem Repo)
- `ANTHROPIC_API_KEY` — echter Key aus der Anthropic Console
- `SESSION_SECRET` — irgendein langer Zufallsstring, z.B.
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `CORS_ORIGIN` — muss exakt der URL entsprechen, unter der das Frontend läuft
  (siehe Schritt 2 — Vite nutzt normalerweise `http://localhost:5173`, weicht
  aber auf 5174 etc. aus, falls der Port schon belegt ist; im Zweifel den
  Vite-Dev-Server zuerst starten und den tatsächlichen Port übernehmen)

Nutzer anlegen (schreibt `backend/users.json`, wird von `.gitignore` ignoriert):

```bash
python scripts/hash_password.py
# Benutzername: amin
# Passwort: ...
# einmal pro Person wiederholen
```

Backend starten:

```bash
uvicorn app.main:app --reload --port 8000
```

Kurzer Check: `curl http://localhost:8000/api/status` sollte
`{"ok":true,...}` zurückgeben.

Tests laufen lassen:

```bash
pytest
```

## 2. Frontend

In einem zweiten Terminal:

```bash
cd frontend
npm install
```

`.env.local` anlegen, damit das Frontend weiß, wo das Backend läuft:

```bash
echo "VITE_API_BASE=http://localhost:8000" > .env.local
```

Dev-Server starten:

```bash
npm run dev
```

Vite gibt die tatsächliche URL aus (`http://localhost:5173` oder einen
Ausweich-Port). **Diese URL muss exakt in `backend/.env` als `CORS_ORIGIN`
stehen** — sonst blockiert der Browser die Anfragen ans Backend mit einem
CORS-Fehler in der Konsole. Nach einer Änderung an `CORS_ORIGIN` das Backend
neu starten (uvicorn liest `.env` nur beim Start).

## 3. Einloggen

Im Browser `http://localhost:5173` (bzw. den von Vite ausgegebenen Port)
öffnen und mit einem der in Schritt 1 angelegten Benutzer einloggen.

## Typische Stolpersteine

- **Login schlägt fehl / "invalid credentials"**: `backend/users.json`
  existiert nicht oder wurde nicht für diesen Benutzer ausgeführt — Schritt 1
  wiederholen.
- **CORS-Fehler in der Browser-Konsole**: `CORS_ORIGIN` in `backend/.env`
  passt nicht zum tatsächlichen Frontend-Port. Backend nach der Korrektur neu
  starten.
- **Umlaute falsch dargestellt**: sollte nicht mehr auftreten (alle
  Datei-Lesevorgänge nutzen jetzt explizit UTF-8) — falls doch, bitte melden.
- **RAG-Suche liefert nichts / `rag_docs: 0` bei `/api/status`**: Es existiert
  noch kein FAISS-Index. Einmalig aufbauen:
  ```bash
  cd backend
  python -c "from app.services.rag import build_full_index; print(build_full_index())"
  ```
  Das dauert je nach Vault-Größe 1–2 Minuten und braucht `sentence-transformers`
  (in requirements.txt enthalten, lädt beim ersten Lauf ein Sprachmodell aus
  dem Internet).
- **Gmail/Outlook zeigen nichts an**: Diese Integrationen brauchen einmalige
  OAuth-Einrichtung (`_agent/gmail_setup.py`, `_agent/ms_login_device.py`,
  siehe `_agent/ms_setup.md`). Ohne das läuft alles andere trotzdem normal,
  Kalender/Mail-Seiten zeigen dann nur leere Listen statt Fehler.

## Projektstruktur

```
backend/    FastAPI-App (Chat, RAG, Auth, Gmail/Outlook, Inbox-Klassifizierung)
frontend/   React-Dashboard (shadcn/ui): Chat, Aufgaben, Kalender, Mail, Dateien, LinkedIn
_agent/     Alter Python-Code (brain_server.py, heartbeat.py, ...) - Referenz,
            wird schrittweise durch backend/ abgelöst
```
