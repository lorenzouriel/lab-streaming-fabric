# SQS Queues

> **Purpose**: Visibility timeout, dead-letter queue (DLQ), and maxReceiveCount semantics
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified against AWS docs)

## Overview

A consumer receives a message and it becomes invisible to other consumers for the
**visibility timeout** duration, so exactly one consumer processes it at a time. If the
consumer doesn't delete it before the timeout expires, it reappears and can be redelivered.
Visibility timeout has a hard ceiling of 12 hours from first receipt — extending it doesn't
reset that ceiling.

A **dead-letter queue (DLQ)** captures messages that fail processing repeatedly instead of
letting them cycle the main queue forever. `maxReceiveCount` is how many times a message can
be received before it's moved to the DLQ; AWS's default is 10, and setting it too low (e.g. 1)
sends a message to the DLQ after a single transient failure — set it high enough to absorb
retries.

Source: [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html), [Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

## Quick Reference

| Concern | Guidance |
|---|---|
| Visibility timeout ceiling | 12 hours from first receipt, non-resettable |
| `maxReceiveCount` default | 10 (AWS default); too low = DLQ after one transient failure |
| DLQ purpose | Isolate poison/failing messages for inspection, not silent loss |
| Retryable vs terminal failures | Route separately — transient (network/5xx) → retry queue; non-retryable (schema/contract) → DLQ directly |

## Related

- [SQS Retry + DLQ Pattern](../patterns/sqs-retry-dlq.md)
- [ECS Fargate](./ecs-fargate.md)
