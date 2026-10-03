# SQS Retry + DLQ Routing

> **Purpose**: Separate transient failures (retry) from terminal failures (DLQ) in a consumer
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified against AWS docs)

## Overview

Not every failure deserves a retry. A transient error (network blip, downstream 5xx) is worth
retrying with backoff — it may succeed next time. A terminal error (malformed payload, schema
validation failure) will fail identically on every retry, so retrying it only delays the
inevitable and wastes `maxReceiveCount` budget that should be reserved for genuinely transient
cases.

Source: [Amazon SQS best practices](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-best-practices.html), [Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)

## The Pattern

```
                    ┌─── transient (network, 5xx) ───► retry queue (backoff)
                    │                                        │
incoming message ───┤                                  maxReceiveCount
                    │                                    exhausted
                    │                                        │
                    └─── terminal (schema/contract) ───► DLQ (direct, no retry)
```

- Route **contract/schema validation failures** straight to a dedicated DLQ — they are a data
  problem, not a network one, and will never succeed on retry.
- Route **transient failures** (POST timeout, downstream 5xx) to a retry mechanism with
  exponential backoff; let SQS's own `maxReceiveCount` on the retry queue provide the outer
  bound, then let messages that exhaust it land in a DLQ too.
- Keep the two DLQs distinct if the failure classes need different remediation (a "bad data"
  DLQ vs. a "retries exhausted" DLQ) — conflating them makes triage slower.
- Set `maxReceiveCount` high enough to absorb real transient blips (AWS default is 10); a
  value of 1 sends a message to the DLQ after a single failure, which is rarely the intent.

## Related

- [SQS Queues](../concepts/sqs-queues.md)
- [ECS Fargate](../concepts/ecs-fargate.md)
