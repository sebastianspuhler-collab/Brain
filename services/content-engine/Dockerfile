# node:22-slim (Debian/glibc) statt node:20-alpine (musl) - die native
# claude-code-CLI-Binary (siehe unten) ist glibc-basiert (läuft auf Alpine
# nicht zuverlässig) UND verlangt >=22 (EBADENGINE unter Node 20, siehe
# backend/Dockerfile-Kommentar - führte dort zu einem kaputten OAuth-Handshake).
FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Claude-Code-CLI für CLAUDE_ENGINE=cli (Ideen/Post/Karussell/News-Bewertung
# über das Claude-Abo statt ANTHROPIC_API_KEY, siehe claudeService.js).
RUN npm install -g @anthropic-ai/claude-code@latest

COPY server ./server
ENV PORT=3002
EXPOSE 3002
CMD ["node", "server/index.js"]
