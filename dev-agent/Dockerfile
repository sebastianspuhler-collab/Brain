# Isolierter Sandbox-Container für den Entwickler-Agenten (Umsetzungsplan
# 2026-07-25). Bewusst analog zu backend/Dockerfile aufgebaut (gleiche
# Node-22-via-NodeSource + @anthropic-ai/claude-code-Installation, siehe
# dortiger Kommentar zur Node-Versions-Falle) - eigener Container, kein
# Zugriff auf den Vault oder die anderen Produktions-Container auf dem VPS.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 + Claude-Code-CLI (siehe backend/Dockerfile: Node 22 zwingend,
# @anthropic-ai/claude-code>=2.1.2xx verlangt >=22).
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code@latest \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI - git-Push läuft über einen zur Laufzeit read-only gemounteten
# SSH-Key (siehe docker-compose.yml, dev-agent-Service) statt über gh selbst;
# gh bleibt hier installiert für spätere Nutzung (z.B. `gh pr create`), ist
# aber aktuell nicht separat authentifiziert.
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

RUN mkdir -p /workspace
VOLUME /workspace

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
