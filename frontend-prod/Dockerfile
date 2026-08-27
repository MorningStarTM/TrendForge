# syntax=docker/dockerfile:1
# Production web app: Next.js (standalone output).
# Build context is ./frontend-prod:
#   docker build -t trendforge-web ./frontend-prod

# --- deps ---
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# --- build ---
FROM node:22-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# `next build` fetches the Poppins font (next/font) — needs network at build time.
RUN npm run build

# --- runtime ---
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Standalone output ships its own minimal node_modules + server.js.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
