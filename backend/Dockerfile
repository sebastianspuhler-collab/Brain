FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    fonts-dejavu-core \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js + Claude-Code-CLI (claude_engine=cli - Chat/LinkedIn/Vision über das
# Claude-Abo statt ANTHROPIC_API_KEY, siehe app/services/claude_cli.py).
# NodeSource statt Debian-Standardpaket, damit die Node-Version zur nativen
# claude-code-Binary passt (glibc-basiert, kein Alpine/musl).
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY templates ./templates

# Headless Mode für VPS/Docker (nicht interaktiv)
# Lokal (dev): setze HEADLESS_MODE=false für Browser-Dialog
ENV HEADLESS_MODE=true
ENV PYTHONUNBUFFERED=1

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1"]
