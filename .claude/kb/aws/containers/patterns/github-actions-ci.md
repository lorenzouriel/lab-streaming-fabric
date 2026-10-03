# GitHub Actions CI (typecheck → test → docker build)

> **Purpose**: A fast, deterministic CI pipeline for a TS/Node service shipping to ECR/ECS
> **Confidence**: 0.85
> **MCP Validated**: 2026-09-17 (web-verified: GitHub docs/community, actions/setup-node)

## Overview

`actions/setup-node` has built-in cache support keyed off the lockfile — use it instead of a
hand-rolled `actions/cache` step for npm. Cache the npm **download cache** (`~/.npm`), not
`node_modules` directly: `node_modules` caching is documented as unreliable across Node
versions and fights `npm ci`'s clean-install contract.

Source: [GitHub Actions community discussion — caching npm dependencies](https://github.com/orgs/community/discussions/196822)

## The Pattern

```yaml
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v6
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: consumer/package-lock.json

      - run: npm ci
        working-directory: consumer

      - run: npm run typecheck
        working-directory: consumer

      - run: npm run test:coverage
        working-directory: consumer

      - name: Build image
        run: docker build -t consumer:${{ github.sha }} consumer
```

## Rules

- **`npm ci`, not `npm install`** in CI — deterministic, and fails loudly on a lockfile drift
  instead of silently re-resolving.
- **Cache key includes the lockfile hash** — `setup-node`'s `cache: npm` does this
  automatically; a stale cache from a changed lockfile is a correctness bug, not just a
  performance one.
- **Order matters for fail-fast**: typecheck before tests before the (slower) docker build —
  cheapest, fastest signal first.
- **Coverage gate belongs in CI, not just locally** — if the project enforces a minimum
  (e.g. `vitest run --coverage` with a configured threshold), CI must run the same command
  the developer runs, not a looser variant.

## Related

- [Docker Multi-Stage Build](./docker-multistage-build.md)
- [ECS Fargate](../concepts/ecs-fargate.md)
