# node:20-slim (Debian/glibc) statt node:20-alpine (musl) - die native
# claude-code-CLI-Binary (siehe unten) ist glibc-basiert und läuft auf Alpine
# nicht zuverlässig.
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Claude-Code-CLI für CLAUDE_ENGINE=cli (Ideen/Post/Karussell/News-Bewertung
# über das Claude-Abo statt ANTHROPIC_API_KEY, siehe claudeService.js).
RUN npm install -g @anthropic-ai/claude-code

COPY server ./server
ENV PORT=3002
EXPOSE 3002
CMD ["node", "server/index.js"]
