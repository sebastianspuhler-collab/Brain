#!/bin/bash
# Vault-Sync: automatisch alle Änderungen zu GitHub pushen
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

# Nichts zu tun wenn keine Änderungen
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

git add -A
git commit -m "auto-sync: $(date '+%d.%m.%Y %H:%M')" --quiet
GIT_SSH_COMMAND="ssh -i $HOME/.ssh/github_prozessia" git push --quiet 2>/dev/null
