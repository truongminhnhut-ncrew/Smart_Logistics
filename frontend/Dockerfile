FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install

COPY . .

RUN npm run build

# ── RUNTIME ────────────────────────────────
FROM node:20-alpine

WORKDIR /app

RUN npm install -g vite

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/vite.config.js ./

EXPOSE 3000

CMD ["vite", "preview", "--host", "0.0.0.0", "--port", "3000"]
