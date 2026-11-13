# --- Stage 1: Safe Dependency Resolution & Lockfile Verification ---
FROM node:24-alpine AS build_env  # 2026-11-13: Node 20 EOL -> 24 LTS

WORKDIR /usr/src/app

# Core Fix: Copy both package manifest AND the definitive cryptographic lockfile
COPY package.json package-lock.json ./

# Enforce clean snapshot replication using the locked tracking manifests
RUN npm ci --omit=dev  # 2026-11-13: --only removed in npm 11 (Node 24); --omit=dev is the replacement

# --- Stage 2: Hardened Sandbox Runtime ---
FROM node:24-alpine

WORKDIR /usr/src/app

# Enforce secure least-privilege principles by dropping root access
USER node

# Copy verified artifacts from build environment with explicit ownership masks
COPY --chown=node:node --from=build_env /usr/src/app/node_modules ./node_modules
COPY --chown=node:node ./src ./src

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "src/index.js"]
