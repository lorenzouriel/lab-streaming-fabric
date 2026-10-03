# Docker Multi-Stage Build (Node.js/TypeScript)

> **Purpose**: Small, secure production images for a TS/Node ECS Fargate consumer
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified: AWS docs, nodebestpractices, official Node images)

## Overview

A naive single-stage Node image ships build tooling, devDependencies, and source into the
runtime image — often 1GB+. A multi-stage build compiles in one stage and copies only the
compiled output + production `node_modules` into a slim runtime stage.

Source: [nodebestpractices — multi-stage builds](https://github.com/goldbergyoni/nodebestpractices/blob/master/sections/docker/multi_stage_builds.md)

## The Pattern

```dockerfile
# --- builder stage: full toolchain, devDependencies allowed ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- runtime stage: only what's needed to run ---
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=builder /app/dist ./dist

USER node
CMD ["node", "dist/index.js"]
```

## Rules

- **`npm ci`, not `npm install`** — deterministic install from `package-lock.json`, faster and
  fails loudly on a lockfile/manifest mismatch instead of silently resolving.
- **Named stages** (`AS builder`, `AS runtime`) — required for `COPY --from=`, and documents intent.
- **`USER node`** — the official Node images ship a non-root `node` user (UID 1000); running as
  it in the runtime stage costs nothing and closes off a class of container-escape paths.
- **Pin the base image by digest** (`FROM node:20-alpine@sha256:...`) in CI-built production
  images if reproducibility matters more than picking up patch updates automatically — tag-only
  pins can drift silently between builds.
- Runtime stage never sees devDependencies or source files that aren't in `dist/` — smaller
  attack surface, smaller image, faster pull on ECS task placement.

## Related

- [ECS Fargate](../concepts/ecs-fargate.md)
- [GitHub Actions CI](./github-actions-ci.md)
