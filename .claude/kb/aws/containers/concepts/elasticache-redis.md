# ElastiCache Redis

> **Purpose**: Connection reuse, TTL discipline, and caching strategy for ElastiCache Redis
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified against AWS docs)

## Overview

Creating a new Redis connection costs CPU on the cache node itself, so long-lived, pooled
connections amortize that cost across many commands — never open a connection per request.

Keys without a TTL never expire; in a cache this means the dataset grows unbounded until
eviction kicks in and starts removing keys you may still want. Set a deliberate TTL on every
cache key and a sane `maxmemory-policy`, and load-test eviction behavior rather than assuming
it won't matter. A commonly cited operational floor: keep `maxmemory` around 75–80% of the
node's available memory to leave room for overhead.

The standard read-through pattern is **lazy loading**: the app writes to the source of truth;
on read, it checks cache first, and on a miss reads the source directly and populates the
cache for next time.

Source: [Lettuce client configuration — Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.Clients-lettuce.html), [ElastiCache best practices and caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html), [Overall best practices — Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WorkingWithRedis.html)

## Quick Reference

| Concern | Guidance |
|---|---|
| Connections | Pool/reuse; never open-per-request |
| TTL | Always set one — untTL'd keys grow the dataset unbounded |
| `maxmemory` | ~75–80% of node memory, with eviction tested under load |
| Cache pattern | Lazy loading (read-through on miss, write to source of truth) |
| Scaling | Cluster-mode enabled scales horizontally past a single node's capacity |

## Related

- [Redis Caching Pattern](../patterns/redis-caching.md)
- [SQS Queues](./sqs-queues.md)
