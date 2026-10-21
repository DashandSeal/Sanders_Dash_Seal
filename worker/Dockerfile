# --- Stage 1: Dependency Verification & Compilation ---
FROM node:20.12.2-alpine AS build_env

WORKDIR /usr/src/app

COPY package.json ./
RUN npm ci --only=production

# --- Stage 2: Hardened Sandbox Runtime Environment ---
FROM node:20.12.2-alpine

WORKDIR /usr/src/app

# Enforce secure least-privilege principles by discarding root execution scopes
USER node

# Selectively pull verified code artifacts and production dependencies 
COPY --chown=node:node --from=build_env /usr/src/app/node_modules ./node_modules
COPY --chown=node:node ./src ./src

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "src/index.js"]
