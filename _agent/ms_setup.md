# Outlook-Integration einrichten (M365)

## Schritt 1 – Azure App registrieren

1. Öffne: https://portal.azure.com
2. Suche oben nach **"App-Registrierungen"** → **"Neue Registrierung"**
3. Felder ausfüllen:
   - **Name:** `Prozessia Brain`
   - **Kontotypen:** "Nur Konten in diesem Organisationsverzeichnis"
   - **Umleitungs-URI:** Plattform `Öffentlicher Client/Nativ` → URI: `http://localhost`
4. Klick **Registrieren**

## Schritt 2 – IDs kopieren

Auf der App-Übersichtsseite kopiere:
- **Anwendungs-ID (Client-ID)** → `client_id`
- **Verzeichnis-ID (Tenant-ID)** → `tenant_id`

## Schritt 3 – API-Berechtigungen vergeben

1. Linkes Menü → **"API-Berechtigungen"** → **"Berechtigung hinzufügen"**
2. **Microsoft Graph** → **Delegierte Berechtigungen**
3. Diese 4 Berechtigungen auswählen:
   - `Mail.ReadWrite`
   - `Mail.Send`
   - `Calendars.ReadWrite`
   - `User.Read`
4. Klick **"Administratorzustimmung erteilen"** (blauer Button)

## Schritt 4 – ms_config.json erstellen

Erstelle `_agent/ms_config.json` (wird NICHT ins Git eingecheckt):

```json
{
    "client_id": "DEINE_CLIENT_ID_HIER",
    "tenant_id": "DEIN_TENANT_ID_HIER"
}
```

## Schritt 5 – Einmalig anmelden

```bash
cd ~/Documents/Prozessia-Brain
source ~/.zshrc
python3 _agent/ms_login.py
```

Browser öffnet sich → Microsoft-Account auswählen → Berechtigungen bestätigen.
Token wird gespeichert, danach kein Login mehr nötig.

## Fertig

Nach erfolgreichem Login läuft Outlook-Integration automatisch in brain_ui.py.

---

## Troubleshooting

**"AADSTS50011: Reply URL does not match"**
→ In Azure: App → Authentifizierung → Redirect URI `http://localhost` eintragen, Typ "Öffentlicher Client"

**"Administratorzustimmung erforderlich"**
→ Entweder Admin-Consent in Azure erteilen, oder Account-Typ auf "Alle Microsoft-Konten" ändern

**Token abgelaufen**
→ `python3 _agent/ms_login.py` erneut ausführen
