#!/bin/bash
# Vault-Sync: haelt das lokale Dateisystem bidirektional mit dem VPS synchron
# (Sebastian, 2026-07-20: nur noch der VPS fuehrt das Backend aus, lokal
# reicht ein synchroner Dateibestand, um schnell Dateien manuell ablegen/
# hochladen zu koennen - vorher wurde hier nur gepusht, nie gepullt, das
# Laptop-Dateisystem sah also nie, was der VPS neu einsortiert hat).
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/github_prozessia"

git pull --rebase --autostash --quiet 2>/dev/null

# Nichts zu tun wenn keine lokalen Aenderungen
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

git add -A
git commit -m "auto-sync: $(date '+%d.%m.%Y %H:%M')" --quiet
git push --quiet 2>/dev/null
