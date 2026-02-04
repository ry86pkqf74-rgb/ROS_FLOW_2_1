# ============================================
# ResearchFlow Orchestrator - Node.js Service
# ============================================
# Build context: repository root (.)
# Stages: base → deps → development | production
#
# Usage:
#   Development: docker build --target development -t orchestrator:dev .
#   Production:  docker build --target production -t orchestrator:prod .

# Base stage
FROM node:20-alpine AS base

# OCI Image Labels
LABEL org.opencontainers.image.title="ResearchFlow Orchestrator"
LABEL org.opencontainers.image.description="Node.js API orchestrator for ResearchFlow research workflow platform"
LABEL org.opencontainers.image.vendor="ResearchFlow"
LABEL org.opencontainers.image.source="https://github.com/ry86pkqf74-rgb/researchflow-production"
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache --update python3 py3-pip make g++ git curl || apk add --no-cache make g++ git curl

# Dependencies stage
FROM base AS deps

# Copy package files
COPY services/orchestrator/package.json ./

# Copy workspace packages
COPY packages/core/package.json ./packages/core/
COPY packages/core/types ./packages/core/types
COPY packages/core/index.ts ./packages/core/
COPY packages/core/src ./packages/core/src
COPY packages/core/policy ./packages/core/policy

COPY packages/phi-engine/package.json ./packages/phi-engine/
COPY packages/phi-engine/index.ts ./packages/phi-engine/
COPY packages/phi-engine/src ./packages/phi-engine/src

COPY packages/ai-router/package.json ./packages/ai-router/
COPY packages/ai-router/index.ts ./packages/ai-router/
COPY packages/ai-router/src ./packages/ai-router/src

# Copy manuscript-engine package (required for manuscript generation routes)
COPY packages/manuscript-engine/package.json ./packages/manuscript-engine/
COPY packages/manuscript-engine/index.ts ./packages/manuscript-engine/
COPY packages/manuscript-engine/src ./packages/manuscript-engine/src
COPY packages/manuscript-engine/validators ./packages/manuscript-engine/validators

# Copy notion-integration package
COPY packages/notion-integration/package.json ./packages/notion-integration/
COPY packages/notion-integration/src ./packages/notion-integration/src

# Replace workspace:* with file: references for npm compatibility
# Fix main package.json
RUN sed -i 's/"@researchflow\/core": "workspace:\*"/"@researchflow\/core": "file:.\/packages\/core"/g' package.json && \
    sed -i 's/"@researchflow\/phi-engine": "workspace:\*"/"@researchflow\/phi-engine": "file:.\/packages\/phi-engine"/g' package.json && \
    sed -i 's/"@researchflow\/ai-router": "workspace:\*"/"@researchflow\/ai-router": "file:.\/packages\/ai-router"/g' package.json && \
    sed -i 's/"@researchflow\/manuscript-engine": "workspace:\*"/"@researchflow\/manuscript-engine": "file:.\/packages\/manuscript-engine"/g' package.json && \
    sed -i 's/"@researchflow\/notion-integration": "workspace:\*"/"@researchflow\/notion-integration": "file:.\/packages\/notion-integration"/g' package.json && \
    # Fix nested package.json files
    sed -i 's/"@researchflow\/core": "workspace:\*"/"@researchflow\/core": "file:..\/core"/g' packages/phi-engine/package.json && \
    sed -i 's/"@researchflow\/core": "workspace:\*"/"@researchflow\/core": "file:..\/core"/g' packages/ai-router/package.json && \
    sed -i 's/"@researchflow\/phi-engine": "workspace:\*"/"@researchflow\/phi-engine": "file:..\/phi-engine"/g' packages/ai-router/package.json && \
    sed -i 's/"@researchflow\/core": "workspace:\*"/"@researchflow\/core": "file:..\/core"/g' packages/manuscript-engine/package.json && \
    sed -i 's/"@researchflow\/phi-engine": "workspace:\*"/"@researchflow\/phi-engine": "file:..\/phi-engine"/g' packages/manuscript-engine/package.json && \
    sed -i 's/"@researchflow\/ai-router": "workspace:\*"/"@researchflow\/ai-router": "file:..\/ai-router"/g' packages/manuscript-engine/package.json

# Install dependencies
RUN npm install

# Development stage
FROM base AS development
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages

# Copy source files (excluding node_modules which would conflict)
COPY services/orchestrator/package.json services/orchestrator/tsconfig.json ./
COPY services/orchestrator/*.ts ./
COPY services/orchestrator/src ./src
COPY services/orchestrator/lib ./lib

# Ensure @researchflow packages are accessible in node_modules (symlinks don't transfer)
RUN mkdir -p ./node_modules/@researchflow && \
    rm -rf ./node_modules/@researchflow/core ./node_modules/@researchflow/phi-engine ./node_modules/@researchflow/ai-router ./node_modules/@researchflow/manuscript-engine ./node_modules/@researchflow/notion-integration && \
    cp -r ./packages/core ./node_modules/@researchflow/core && \
    cp -r ./packages/phi-engine ./node_modules/@researchflow/phi-engine && \
    cp -r ./packages/ai-router ./node_modules/@researchflow/ai-router && \
    cp -r ./packages/manuscript-engine ./node_modules/@researchflow/manuscript-engine && \
    cp -r ./packages/notion-integration ./node_modules/@researchflow/notion-integration

ENV NODE_ENV=development
ENV NODE_PATH=/app/node_modules
EXPOSE 3001

# Copy entrypoint script
COPY services/orchestrator/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["npm", "run", "dev"]

# Build stage - Compile TypeScript to JavaScript
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages

# Copy source files (excluding node_modules which would conflict)
COPY services/orchestrator/package.json services/orchestrator/tsconfig.json ./
COPY services/orchestrator/*.ts ./
COPY services/orchestrator/src ./src
COPY services/orchestrator/lib ./lib

# Ensure @researchflow packages are accessible in node_modules
RUN mkdir -p ./node_modules/@researchflow && \
    rm -rf ./node_modules/@researchflow/core ./node_modules/@researchflow/phi-engine ./node_modules/@researchflow/ai-router ./node_modules/@researchflow/manuscript-engine ./node_modules/@researchflow/notion-integration && \
    cp -r ./packages/core ./node_modules/@researchflow/core && \
    cp -r ./packages/phi-engine ./node_modules/@researchflow/phi-engine && \
    cp -r ./packages/ai-router ./node_modules/@researchflow/ai-router && \
    cp -r ./packages/manuscript-engine ./node_modules/@researchflow/manuscript-engine && \
    cp -r ./packages/notion-integration ./node_modules/@researchflow/notion-integration

# Compile TypeScript to JavaScript
RUN npx tsc --project tsconfig.json || npx tsc --skipLibCheck --outDir dist --rootDir . index.ts

# Production stage - Run pre-compiled JavaScript
FROM node:20-alpine AS production
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy only production dependencies and compiled code
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/*.json ./

# Ensure @researchflow packages are accessible
RUN mkdir -p ./node_modules/@researchflow && \
    rm -rf ./node_modules/@researchflow/core ./node_modules/@researchflow/phi-engine ./node_modules/@researchflow/ai-router ./node_modules/@researchflow/manuscript-engine ./node_modules/@researchflow/notion-integration && \
    cp -r ./packages/core ./node_modules/@researchflow/core && \
    cp -r ./packages/phi-engine ./node_modules/@researchflow/phi-engine && \
    cp -r ./packages/ai-router ./node_modules/@researchflow/ai-router && \
    cp -r ./packages/manuscript-engine ./node_modules/@researchflow/manuscript-engine && \
    cp -r ./packages/notion-integration ./node_modules/@researchflow/notion-integration

# Create data directories and fix permissions for nodejs user
RUN mkdir -p /data/artifacts /data/logs /data/manifests && \
    chown -R nodejs:nodejs /data /app

USER nodejs

ENV NODE_ENV=production
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:3001/health || exit 1

# Run compiled JavaScript (faster startup, no runtime compilation)
CMD ["node", "dist/index.js"]
