# Redis Caching (Lazy Loading + TTL)

> **Purpose**: Cache a hot, expensive lookup in front of a database read
> **Confidence**: 0.9
> **MCP Validated**: 2026-09-17 (web-verified against AWS ElastiCache docs)

## Overview

Lazy loading (cache-aside): check the cache first; on a miss, read the source of truth and
populate the cache for next time. Every cached key must carry a TTL — an un-TTL'd key set never
shrinks, and you end up depending on eviction policy to reclaim space you should have reclaimed
by design.

Source: [ElastiCache best practices and caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/BestPractices.html)

## The Pattern

```typescript
async function getCached<T>(
  redis: Redis,
  key: string,
  ttlSeconds: number,
  loadFromSource: () => Promise<T | null>,
): Promise<T | null> {
  const cached = await redis.get(key);
  if (cached !== null) {
    return JSON.parse(cached) as T;
  }

  const value = await loadFromSource();
  if (value !== null) {
    // TTL is not optional — every write to cache carries one
    await redis.set(key, JSON.stringify(value), "EX", ttlSeconds);
  }
  return value;
}
```

## Rules

- **Reuse the connection.** Create the Redis client once at process start (module scope), not
  per lookup — connection setup costs the cache node CPU, and a long-lived consumer pays that
  cost needlessly on every message if it reconnects each time.
- **Always set a TTL.** Even for data that "shouldn't change" — a TTL bounds staleness and
  bounds memory growth; both matter more than the minor cost of an occasional extra source read.
- **Cheap gate before expensive JOIN.** If a lookup gates a much more expensive downstream
  query (e.g. a wide multi-table JOIN), cache the cheap gate value separately and check it
  first — non-matching cases should short-circuit before ever reaching the expensive path.
- **Don't cache negative/error results as if they were valid** unless deliberately choosing a
  short negative-cache TTL — indistinguishable "not found" vs "lookup failed" caching hides bugs.

## Related

- [ElastiCache Redis](../concepts/elasticache-redis.md)
- [SQS Retry + DLQ Routing](./sqs-retry-dlq.md)
