# Isolierter Lead-Agent-Container - analog zu dev-agent/Dockerfile (gleiche
# Node-22-via-NodeSource + @anthropic-ai/claude-code-Installation), aber mit
# Vault-Mount (siehe docker-compose.yml: ${VAULT_PATH}:/vault) statt eines
# vault-fremden /workspace-Volumes - der Lead-Agent muss Leads/*.md lesen und
# über mcp_server.py schreiben können.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 + Claude-Code-CLI (siehe dev-agent/Dockerfile: Node 22 zwingend,
# @anthropic-ai/claude-code>=2.1.2xx verlangt >=22).
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code@latest \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
