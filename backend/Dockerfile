FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    fonts-dejavu-core \
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
