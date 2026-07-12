# 🔐 Credentials Setup – Prozessia Brain

Hier ist, wie du **Google & Microsoft Credentials** in dein Backend eintragen kannst.

## ⚡ Schnellstart (2 Minuten)

```bash
cd backend
python3 setup_credentials.py
```

Das Script fragt dich interaktiv nach deinen Credentials und speichert sie in `.env`.

---

## 📋 Manuelle Konfiguration

### 1️⃣ Google Workspace (Gmail, Drive, Sheets)

Brauchst du wenn du:
- Emails aus Gmail auslesen möchtest
- Dateien in Google Drive ablegen möchtest
- Sheets-Daten verarbeiten möchtest

#### Setup:

1. Gehe zu: https://console.cloud.google.com
2. **Project wählen** oder ein neues erstellen
3. **APIs & Dienste** → **Credentials**
4. **+ Create Credentials** → **OAuth 2.0 Client ID**
5. **Application type:** `Desktop application`
6. **Create** → **Download JSON** (ein Download-Icon erscheint)
7. JSON-Inhalt öffnen und **KOMPLETTEN TEXT** kopieren

Dann in `backend/.env`:
```env
GOOGLE_CREDENTIALS_JSON={"installed": {"client_id": "...", "client_secret": "..."}}
```

**Optional – Service Account (für Automation ohne User-Login):**

1. **Service Accounts** (linkes Menü)
2. **Create Service Account**
3. Name: "Prozessia Brain"
4. **Grant this service account access to project:**
   - Role: `Editor`
5. **Create key** → **JSON** → **Create**
6. JSON-Inhalt in `GOOGLE_SERVICE_ACCOUNT_JSON` eintragen

---

### 2️⃣ Microsoft 365 (Outlook, Teams, Calendar)

Brauchst du wenn du:
- Emails aus Outlook synchronisieren möchtest
- Kalender-Events verwalten möchtest
- Teams-Integration brauchst

#### Setup (Schritt-für-Schritt):

**Schritt 1 – App registrieren:**

1. Gehe zu: https://portal.azure.com
2. Suche oben nach: **App-Registrierungen**
3. **+ Neue Registrierung**
4. Felder ausfüllen:
   - **Name:** `Prozessia Brain`
   - **Kontotypen:** "Nur Konten in diesem Organisationsverzeichnis" (eine Tenant)
   - **Umleitungs-URI:** Plattform `Öffentlicher Client (Nativ)` → `http://localhost`
5. **Registrieren**

**Schritt 2 – IDs kopieren:**

Nach der Registrierung siehst du eine Übersichtsseite. Kopiere:
- **Anwendungs-ID (Client-ID)** → in `backend/.env` als `MS_CLIENT_ID`
- **Verzeichnis-ID (Tenant-ID)** → in `backend/.env` als `MS_TENANT_ID`

```env
MS_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MS_TENANT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
```

**Schritt 3 – API-Berechtigungen (optional):**

1. Linkes Menü → **API-Berechtigungen**
2. **+ Berechtigung hinzufügen** → **Microsoft Graph**
3. **Delegierte Berechtigungen** (User-Authentifizierung):
   - `Mail.ReadWrite`
   - `Mail.Send`
   - `Calendars.ReadWrite`
   - `User.Read`
4. **Administratorzustimmung erteilen** (blauer Button)

---

### 3️⃣ Twenty CRM (Leadfeeder Export)

Brauchst du für die **Lead-Generierung** (Kontakte & Unternehmen exportieren).

1. Gehe zu deiner Twenty-Instanz: https://your-twenty-instance.com
2. **Settings** → **Developers** → **API Tokens**
3. **+ Create Token** → Copy
4. In `backend/.env`:

```env
TWENTY_API_URL=https://your-twenty-instance.com/graphql
TWENTY_API_KEY=your_token_here
```

---

## 📝 `.env` Format

Alle Credentials gehen in `backend/.env`. Die Datei ist `.gitignore`'d (nicht im Git):

```env
# Google
GOOGLE_CREDENTIALS_JSON={"installed": {"client_id": "...", ...}}
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
DRIVE_KUNDEN_FOLDER_ID=1abc2def3ghi4jkl5mno6pqr

# Microsoft
MS_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MS_TENANT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
MS_CLIENT_SECRET=                                  # optional

# Twenty CRM
TWENTY_API_URL=https://your-twenty-instance.com/graphql
TWENTY_API_KEY=your_token_here

# Andere Optionen
HEADLESS_MODE=false                               # lokal
ANTHROPIC_API_KEY=sk-ant-...
```

---

## ✅ Verifikation

Nach dem Eintragen der Credentials starten:

```bash
cd backend
python -m uvicorn app.main:app --port 9000 --reload
```

Backend sollte **ohne Fehler** starten:
```
INFO:     Uvicorn running on http://0.0.0.0:9000
INFO:     Application startup complete
```

Wenn Errors:
- **Google:** `GOOGLE_CREDENTIALS_JSON` muss gültiges JSON sein
- **Microsoft:** `MS_CLIENT_ID` und `MS_TENANT_ID` müssen UUIDs sein
- **Twenty:** `TWENTY_API_URL` muss mit `/graphql` enden

---

## 🚀 Nach dem Setup

1. **Backend starten:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --port 9000
   ```

2. **Frontend starten (neues Terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Browser öffnen:**
   ```
   http://localhost:5173
   ```

---

## 🔒 Sicherheit

- `.env` ist **NICHT** im Git (`.gitignore`)
- Teile `.env` **NIEMALS** über Chat/Email/Slack
- Tokens sind sensitive → am besten in CI/CD Secrets speichern
- Lokal? → `.env` nur mit `chmod 600 .env` (Unix)

---

## ❓ Troubleshooting

### "ModuleNotFoundError: No module named 'google.auth'"

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### "msal library not found"

```bash
pip install msal msal-extensions
```

### Credentials werden nicht geladen

1. Prüfe: `backend/.env` exists?
2. Prüfe: GOOGLE_CREDENTIALS_JSON ist gültiges JSON?
3. Prüfe: Spätestens nach `.env`-Edit Backend neustarten

---

**Fragen?** → Siehe `backend/.env.example` als Referenz
