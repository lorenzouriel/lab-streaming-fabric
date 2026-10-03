# ECS Fargate

> **Purpose**: Sizing and running long-lived containerized consumers/services on Fargate
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified against AWS docs; no MCP session for AWS docs in this build)

## Overview

Fargate is the serverless compute mode for ECS: you declare CPU and memory at the **task**
level (not per-container overhead needed), ECS places the task, and you're billed for what
you reserved. For always-on singleton workers (e.g. a Kafka/queue consumer that doesn't scale
horizontally per-request), available capacity and cost are the main levers — size from load
testing against your service-level objective, not from guesswork.

Source: [Choosing Fargate task sizes for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-size-best-practice.html), [Best practices for Amazon ECS task sizes](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/fargate-task-size.html)

## Sizing Rules

- CPU is measured in units of 1/1024 vCPU (1024 = 1 full vCPU); memory in MiB.
- Container-level **limits** must be ≥ the sum of container **reservations** in the task
  definition; round the total up to the nearest valid Fargate CPU/memory combination.
- For non-scaling workloads (singleton workers, DB-adjacent processes): size from load
  testing, not from a fixed table — cost and headroom are the tradeoff, not throughput.

## Quick Reference

| Concern | Guidance |
|---|---|
| Task-level CPU/memory | Required; no per-container overhead accounting needed |
| Container limit vs reservation | limit ≥ Σ(reservations), rounded to nearest Fargate size |
| Singleton/non-scaling workload | Size via load test against SLO, not a preset |
| Ephemeral storage | Configurable per task (see AWS Fargate task storage docs) |

## Related

- [SQS Queues](./sqs-queues.md)
- [CloudWatch Observability](./cloudwatch-observability.md)
- [Docker Multi-Stage Build](../patterns/docker-multistage-build.md)
