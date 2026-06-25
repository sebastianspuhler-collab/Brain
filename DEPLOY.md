# Prozessia Brain — VPS Deployment

## Voraussetzungen
- Ubuntu 22.04 / Debian 12 VPS
- Root-Zugriff (oder sudo)
- Anthropic API Key (von Sebastian)

## Setup (ein Befehl)

```bash
git clone https://github.com/sebastianspuhler-collab/Brain.git
cd Brain
sudo bash setup.sh
```

Der Script installiert alles automatisch und fragt nach dem API Key.

## Zugriff

Nach dem Setup ist Brain erreichbar unter:
```
http://<VPS-IP>:3001
```

Passwörter:
- Sebastian: `prozessia2026`
- Amin: `amin2026`

## Port öffnen (falls nötig)

```bash
ufw allow 3001
```

## Service-Befehle

```bash
sudo systemctl status prozessia-brain   # Status
sudo systemctl restart prozessia-brain  # Neustart
sudo journalctl -u prozessia-brain -f   # Live-Logs
```

## Was enthalten ist

- Gesamter Vault (alle Notizen, Kunden, Finanzen)
- RAG-Wissensdatenbank (wird beim Start automatisch aufgebaut)
- Brain-Server mit Chat, Datei-Upload, Inbox-Verarbeitung

## Was nicht enthalten ist

- Gmail (läuft weiterhin auf Sebastians Mac)
- Outlook-Kalender (läuft weiterhin auf Sebastians Mac)

## Vault aktualisieren

Sebastian pushed neue Inhalte via Git. Auf dem VPS:
```bash
cd Brain && git pull && sudo systemctl restart prozessia-brain
```
