# Streaming Pipelines (TypeScript)

> **Purpose**: Code-level best practices for real-time/streaming pipeline consumers and producers in TypeScript/Node.js
> **MCP Validated:** 2026-03-26

## When to Use

- Writing a Kafka/Kinesis/Pub-Sub consumer or producer service in Node.js
- Reviewing an existing TypeScript streaming service for correctness and backpressure gaps
- Deciding how strict a delivery guarantee needs to be for a Node-based pipeline stage

Node's single-threaded event loop changes what "backpressure" and "throughput" mean compared to JVM pipelines (Flink/Kafka Streams): there's no thread pool to add, and one blocking call stalls the entire process. These practices are specific to that constraint.

## Type-Safe Message Contracts at the Boundary

Never trust a deserialized message's shape. Validate with a schema library and derive the type from the schema, not the other way around.

```typescript
import { z } from "zod";

const OrderEventSchema = z.object({
  eventId: z.string().uuid(),
  orderId: z.string(),
  amount: z.number().positive(),
  occurredAt: z.string().datetime(),
});

type OrderEvent = z.infer<typeof OrderEventSchema>;

function parseMessage(raw: Buffer): OrderEvent {
  const json: unknown = JSON.parse(raw.toString("utf-8"));
  return OrderEventSchema.parse(json); // throws ZodError on shape mismatch -- route to DLQ, don't guess
}
```

## Idempotent, Backpressure-Aware Consumption (KafkaJS)

Use `eachBatch` (not `eachMessage`) when you need control over offset commits and concurrency -- it gives you the batch, heartbeat, and resolveOffset together, so you can bound in-flight work instead of firing unbounded `Promise.all` per batch.

```typescript
import { Kafka, EachBatchPayload } from "kafkajs";
import pLimit from "p-limit";

const kafka = new Kafka({ clientId: "order-processor", brokers: ["kafka:9092"] });
const consumer = kafka.consumer({ groupId: "order-processor", sessionTimeout: 45000 });

const limit = pLimit(10); // bounded concurrency -- never unbounded Promise.all on a batch

async function eachBatch({
  batch,
  resolveOffset,
  heartbeat,
  commitOffsetsIfNecessary,
  isRunning,
  isStale,
}: EachBatchPayload): Promise<void> {
  const tasks = batch.messages.map((message) =>
    limit(async () => {
      if (!isRunning() || isStale()) return; // rebalance in progress -- stop processing this batch

      try {
        const event = parseMessage(message.value!);
        await processOrder(event); // idempotent: safe to reprocess on redelivery
      } catch (e) {
        await routeToDlq(message, e);
      } finally {
        resolveOffset(message.offset); // mark processed even on DLQ route -- don't reprocess poison messages
      }
    }),
  );

  await Promise.all(tasks);
  await heartbeat(); // prevents a rebalance mid-batch on slow processing
  await commitOffsetsIfNecessary();
}

await consumer.connect();
await consumer.subscribe({ topic: "orders", fromBeginning: false });
await consumer.run({ eachBatch, autoCommit: false }); // manual commit -- at-least-once, not "fire and forget"
```

## Idempotency in the Handler, Not the Framework

KafkaJS has no built-in exactly-once transactional consumer the way Kafka Streams does. Make `processOrder` idempotent instead of chasing framework-level exactly-once:

```typescript
async function processOrder(event: OrderEvent): Promise<void> {
  // Upsert on a natural key absorbs redelivery duplicates without extra dedup logic
  await db.orders.upsert({
    where: { id: event.orderId },
    update: { amount: event.amount },
    create: { id: event.orderId, amount: event.amount, eventId: event.eventId },
  });
}
```

## Dead-Letter Routing with Full Context

```typescript
import type { KafkaMessage } from "kafkajs";

const dlqProducer = kafka.producer();

async function routeToDlq(message: KafkaMessage, error: unknown): Promise<void> {
  await dlqProducer.send({
    topic: "orders-dlq",
    messages: [
      {
        key: message.key,
        value: message.value,
        headers: {
          "x-error": error instanceof Error ? error.message : String(error),
          "x-original-topic": "orders",
          "x-original-offset": message.offset,
          "x-failed-at": new Date().toISOString(),
        },
      },
    ],
  });
}
```

## Graceful Shutdown

A pipeline that doesn't drain in-flight work on `SIGTERM` loses or duplicates messages on every deploy.

```typescript
async function shutdown(): Promise<void> {
  await consumer.disconnect(); // completes in-flight eachBatch call before returning
  await dlqProducer.disconnect();
  process.exit(0);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
```

## Don't Block the Event Loop

CPU-heavy transforms (parsing large payloads, compression, crypto) block every other consumer/health-check in the process. Offload them.

```typescript
import { Worker } from "node:worker_threads";

function transformInWorker(payload: Buffer): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./transform-worker.js", { workerData: payload });
    worker.once("message", resolve);
    worker.once("error", reject);
  });
}
```

For high-volume CPU-bound stages, prefer `node-rdkafka` (native librdkafka bindings) over `kafkajs` (pure JS) -- it moves protocol overhead off the main thread and sustains materially higher throughput per instance.

## Structured Logging and Tracing

Propagate a correlation ID through message headers so a single event's path is traceable across producer -> broker -> consumer -> DLQ.

```typescript
import pino from "pino";

const logger = pino({ level: "info" });

logger.info({ eventId: event.eventId, orderId: event.orderId }, "order processed");
// Never log the raw payload at info level -- may contain PII; log identifiers only
```

## Config Validation at Startup

Fail fast on bad configuration instead of discovering it mid-stream.

```typescript
const ConfigSchema = z.object({
  KAFKA_BROKERS: z.string().min(1),
  CONSUMER_GROUP_ID: z.string().min(1),
  DLQ_TOPIC: z.string().min(1),
});

const config = ConfigSchema.parse(process.env); // throws and exits before consuming a single message
```

## Common Mistakes

| Don't | Do |
|-------|-----|
| `eachMessage` with unbounded async work per message | `eachBatch` + bounded concurrency (`p-limit`), so one slow message can't stall a whole batch's heartbeat |
| `autoCommit: true` with async processing | `autoCommit: false` + `resolveOffset` after the message is actually handled (or DLQ'd) |
| Retry a `ZodError` (bad schema) forever | Classify: parse/validation errors -> DLQ immediately; network/timeout errors -> retry with backoff |
| Block the event loop on CPU-heavy transforms | Offload to `worker_threads`, or use `node-rdkafka` for high-throughput native processing |
| Exit on `SIGTERM` without disconnecting the consumer | Await `consumer.disconnect()` to drain in-flight batches before `process.exit()` |
| Trust `JSON.parse(msg.value)` as the message type | Validate with `zod`/`valibot` and derive the type from the schema |

## See Also

- [Error Handling](error-handling.md)
- [Generators](../concepts/generators.md)
- [Resource Management](../concepts/resource-management.md)
- [Streaming domain: production-best-practices](../../streaming/patterns/production-best-practices.md)
- [Streaming domain: high-availability-throughput](../../streaming/patterns/high-availability-throughput.md)
