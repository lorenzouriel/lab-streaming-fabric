# AWS Containers Sub-Domain

> **Purpose**: ECS Fargate consumers/services — SQS, ElastiCache Redis, CloudWatch, Docker, CI
> **Last Updated**: 2026-09-17
> **Built by**: `/stack:extend-stack --apply`, sourced from AWS official docs (see per-file citations)

## Scope

Covers the operational surface of a long-running, containerized Node/TS service on ECS
Fargate: task sizing, SQS-based retry/DLQ routing, ElastiCache Redis caching, CloudWatch
custom metrics (EMF), the Docker image that ships it, and the GitHub Actions pipeline that
builds/tests it. Complements the `lambda/` and `deployment/` sub-domains, which cover
serverless functions and SAM-based deploys respectively — this sub-domain is for services that
don't fit that shape.

## Quick Navigation

| Type | Files |
|------|-------|
| Concepts | [ecs-fargate](concepts/ecs-fargate.md), [sqs-queues](concepts/sqs-queues.md), [elasticache-redis](concepts/elasticache-redis.md), [cloudwatch-observability](concepts/cloudwatch-observability.md) |
| Patterns | [docker-multistage-build](patterns/docker-multistage-build.md), [sqs-retry-dlq](patterns/sqs-retry-dlq.md), [redis-caching](patterns/redis-caching.md), [github-actions-ci](patterns/github-actions-ci.md) |

## Related

- [Lambda](../lambda/index.md)
- [Deployment](../deployment/index.md)
