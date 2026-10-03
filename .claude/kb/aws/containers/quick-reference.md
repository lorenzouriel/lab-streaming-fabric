# AWS Containers Quick Reference

> Fast lookup tables. For explanation and code, see linked concept/pattern files.
> **Last Updated:** 2026-09-17

## ECS Fargate Sizing

| Concern | Guidance |
|---|---|
| CPU unit | 1/1024 vCPU per unit (1024 = 1 vCPU) |
| Memory unit | MiB |
| Container limit vs reservation | limit ≥ Σ(reservations), round up to nearest Fargate size |
| Non-scaling singleton worker | Size via load test against SLO |

## SQS

| Concern | Guidance |
|---|---|
| Visibility timeout ceiling | 12h from first receipt, non-resettable |
| `maxReceiveCount` default | 10 |
| Terminal failure (schema/contract) | Route directly to DLQ, no retry |
| Transient failure (network/5xx) | Retry queue with backoff, then DLQ on exhaustion |

## ElastiCache Redis

| Concern | Guidance |
|---|---|
| Connections | Pool/reuse — never per-request |
| TTL | Mandatory on every cache write |
| `maxmemory` | ~75–80% of node memory |
| Pattern | Lazy loading (cache-aside) |

## CloudWatch EMF

| Concern | Guidance |
|---|---|
| Emission | Structured log line, not synchronous `PutMetricData` |
| Batch limit | Up to 100 metrics per EMF object |
| Dimensions | Only what you'll filter/alarm on |

## Docker

| Concern | Guidance |
|---|---|
| Install command | `npm ci`, not `npm install` |
| Stages | Named (`AS builder`, `AS runtime`) |
| User | `USER node` in runtime stage (non-root, ships in official image) |
| Base image pin | Digest pin for reproducible prod builds |

## GitHub Actions CI

| Concern | Guidance |
|---|---|
| Node/npm cache | `actions/setup-node` with `cache: npm`, keyed on `package-lock.json` |
| Never cache | `node_modules` directly (breaks across Node versions, fights `npm ci`) |
| Step order | typecheck → test → docker build (fail-fast, cheapest first) |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Open a new Redis connection per message | Create client once at process start, reuse |
| Set `maxReceiveCount: 1` | Set high enough to absorb real transient failures |
| Cache `node_modules` in CI | Cache `~/.npm`, run `npm ci` |
| Retry a schema-validation failure | Route straight to DLQ — it will never succeed |
| Ship devDependencies in the runtime image | Multi-stage build, `--omit=dev` in runtime stage |

## Related Documentation

| Topic | Path |
|-------|------|
| Sub-domain index | `index.md` |
| Lambda (serverless) | `../lambda/index.md` |
| Deployment (SAM) | `../deployment/index.md` |
