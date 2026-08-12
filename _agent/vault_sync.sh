#!/bin/bash
# Vault-Sync: haelt das lokale Dateisystem bidirektional mit dem VPS synchron
# (Sebastian, 2026-07-20: nur noch der VPS fuehrt das Backend aus, lokal
# reicht ein synchroner Dateibestand, um schnell Dateien manuell ablegen/
# hochladen zu koennen - vorher wurde hier nur gepusht, nie gepullt, das
# Laptop-Dateisystem sah also nie, was der VPS neu einsortiert hat).
#
# Reihenfolge bewusst: ERST lokale Aenderungen committen, DANN pullen/rebasen,
# DANN pushen - nie umgekehrt. Bei pull-zuerst kollidiert ein rebase mit noch
# uncommitteten lokalen Dateien ("would be overwritten by checkout") und
# bricht ab; der Push danach scheitert dann still (non-fast-forward), beides
# wurde bisher komplett verschluckt (2>/dev/null). Genau diese Reihenfolge
# hat den VPS-seitigen Sync (gleiche Struktur in jobs.py::git_sync_loop) vom
# 04.08. bis 12.08.2026 unbemerkt lahmgelegt (82 nie gepushte Commits).
# Fehler landen jetzt in /tmp/vault_sync.log statt im Nichts.
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/github_prozessia"

# Erst lokale Aenderungen sichern (falls vorhanden) - macht sie fuer den
# folgenden Pull/Rebase sichtbar (getrackt statt untracked).
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    git add -A
    git commit -m "auto-sync: $(date '+%d.%m.%Y %H:%M')" --quiet
fi

if ! git pull --rebase --autostash --quiet; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] git pull --rebase fehlgeschlagen - Rebase abgebrochen, naechster Versuch in 5 Min" >&2
    git rebase --abort 2>/dev/null
    exit 1
fi

git push --quiet
