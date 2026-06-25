#!/bin/bash
# Prozessia Brain — VPS Setup Script
# Einmalig ausführen: bash setup.sh
set -e

VAULT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$VAULT_DIR/_agent"
SERVICE_USER="${SUDO_USER:-$(whoami)}"
SERVICE_NAME="prozessia-brain"

echo "=== Prozessia Brain Setup ==="
echo "Vault: $VAULT_DIR"
echo "User:  $SERVICE_USER"
echo ""

# ── 1. System-Pakete ─────────────────────────────────────────────────────────
echo "[1/5] System-Pakete installieren..."
if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv git curl
elif command -v yum &>/dev/null; then
    yum install -y python3 python3-pip git curl
fi

# ── 2. Python-Umgebung ───────────────────────────────────────────────────────
echo "[2/5] Python-Pakete installieren..."
pip3 install -q -r "$AGENT_DIR/requirements.txt"

# ── 3. .env Datei ────────────────────────────────────────────────────────────
echo "[3/5] Konfiguration..."
if [ ! -f "$VAULT_DIR/.env" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo ""
        read -p "  Anthropic API Key eingeben: " API_KEY
    else
        API_KEY="$ANTHROPIC_API_KEY"
    fi
    cat > "$VAULT_DIR/.env" <<EOF
ANTHROPIC_API_KEY=$API_KEY
EOF
    echo "  .env erstellt."
else
    echo "  .env bereits vorhanden."
fi

# ── 4. Passwörter setzen (optional) ─────────────────────────────────────────
echo ""
echo "  Aktuell eingestellte Passwörter:"
echo "    prozessia2026 (Sebastian)"
echo "    amin2026      (Amin)"
echo "  → Zum Ändern: _AUTH_TOKENS in _agent/brain_server.py anpassen"
echo ""

# ── 5. systemd Service ───────────────────────────────────────────────────────
echo "[4/5] systemd Service einrichten..."

# .env in den Service laden
ENV_LINE=""
if [ -f "$VAULT_DIR/.env" ]; then
    API_KEY_VAL=$(grep ANTHROPIC_API_KEY "$VAULT_DIR/.env" | cut -d= -f2-)
    ENV_LINE="Environment=\"ANTHROPIC_API_KEY=$API_KEY_VAL\""
fi

cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Prozessia Brain Server
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$VAULT_DIR
ExecStart=/usr/bin/python3 $AGENT_DIR/brain_server.py
$ENV_LINE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# ── Auto-Sync: alle 5 Min git pull + Reindex ─────────────────────────────────
echo "[4b/5] Auto-Sync Cron einrichten..."
CRON_JOB="*/5 * * * * cd $VAULT_DIR && git pull --quiet origin main 2>/dev/null && curl -s -X POST http://localhost:3001/api/inbox_process > /dev/null 2>&1"
(crontab -u "$SERVICE_USER" -l 2>/dev/null | grep -v "prozessia.*git pull"; echo "$CRON_JOB") | crontab -u "$SERVICE_USER" -
echo "  Vault wird alle 5 Minuten von GitHub synchronisiert."

sleep 3

# ── 5. Status prüfen ─────────────────────────────────────────────────────────
echo "[5/5] Status prüfen..."
if curl -s http://localhost:3001/api/status | grep -q '"ok":true'; then
    echo ""
    echo "✅ Brain läuft auf Port 3001"
    echo ""
    echo "  Lokal erreichbar: http://localhost:3001"
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo "  Öffentlich:       http://$SERVER_IP:3001"
    echo ""
    echo "  Falls Port 3001 in der Firewall nicht offen ist:"
    echo "  → ufw allow 3001"
    echo ""
    echo "  Passwörter: prozessia2026 (Sebastian) · amin2026 (Amin)"
else
    echo "⚠️  Server noch nicht erreichbar. Logs:"
    journalctl -u $SERVICE_NAME -n 20 --no-pager
fi
