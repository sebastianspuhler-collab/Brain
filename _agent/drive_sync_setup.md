# Google Drive Sync – Einmalige Einrichtung

## Schritt 1: Google Cloud Console

1. Öffne: https://console.cloud.google.com
2. Neues Projekt erstellen: "Prozessia Brain"
3. Linkes Menü → **APIs & Dienste** → **Bibliothek**
4. "Google Drive API" suchen → **Aktivieren**

## Schritt 2: OAuth Credentials

1. **APIs & Dienste** → **Anmeldedaten** → **Anmeldedaten erstellen**
2. **OAuth-Client-ID** auswählen
3. Anwendungstyp: **Desktop-App**
4. Name: "Prozessia Brain"
5. **Erstellen** → **JSON herunterladen**
6. Datei umbenennen in: `drive_credentials.json`
7. Datei verschieben nach: `~/Documents/Prozessia-Brain/_agent/drive_credentials.json`

## Schritt 3: OAuth Consent Screen

1. **APIs & Dienste** → **OAuth-Zustimmungsbildschirm**
2. Benutzertyp: **Extern**
3. App-Name: "Prozessia Brain"
4. Deine E-Mail als Support-Kontakt
5. Unter **Testnutzer**: `sebastian.spuhler@prozessia.de` hinzufügen
6. Speichern

## Schritt 4: Sync starten

```bash
source ~/.zshrc
python3 ~/Documents/Prozessia-Brain/_agent/drive_sync.py
```

Browser öffnet sich → Mit Google anmelden → Einmalig bestätigen.
Danach läuft der Sync automatisch ohne Browser.

## Wiederholen

```bash
python3 ~/Documents/Prozessia-Brain/_agent/drive_sync.py
source ~/.zshrc && python3 ~/Documents/Prozessia-Brain/_agent/heartbeat.py
```
