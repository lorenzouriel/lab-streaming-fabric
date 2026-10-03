# CloudWatch Observability (EMF)

> **Purpose**: Embedded Metric Format (EMF) for custom metrics from ECS/container workloads
> **Confidence**: 0.85
> **MCP Validated**: 2026-09-17 (web-verified against AWS docs)

## Overview

CloudWatch **Embedded Metric Format (EMF)** generates custom metrics asynchronously by writing
structured logs to CloudWatch Logs; CloudWatch parses the embedded metric block out of the log
event automatically. It's the recommended path for ephemeral or high-cardinality compute —
Lambda, ECS, EKS — because it avoids a synchronous `PutMetricData` call per event and batches
metric emission into the log line the service already writes.

Source: [Embedding metrics within logs — Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html), [CloudWatch Embedded Metric Format — AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/guides/signal-collection/emf/)

## Best Practices

- Pick meaningful, consistent **namespaces**; group related metrics under one namespace rather
  than scattering them.
- Use **dimensions** for the context you'll actually filter/alarm on (e.g. tenant, queue name)
  — every additional dimension combination is a distinct metric stream.
- EMF can batch up to 100 metrics in a single log-embedded object — prefer batching over many
  small `PutMetricData` calls, both for cost and for atomicity of a single processing unit's metrics.
- Filter to essential metrics; unfiltered high-cardinality dimensions (e.g. raw message ID) drive
  custom-metric cost up sharply.

## Quick Reference

| Concern | Guidance |
|---|---|
| Emission mechanism | Structured log line with embedded metric block, not a live API call |
| Best fit | Ephemeral/container compute (Lambda, ECS, EKS) |
| Batch limit | Up to 100 metrics per EMF object |
| Dimension design | Only what you'll filter/alarm on — cardinality drives cost |

## Related

- [ECS Fargate](./ecs-fargate.md)
