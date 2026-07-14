FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY server ./server
ENV PORT=3002
EXPOSE 3002
CMD ["node", "server/index.js"]
