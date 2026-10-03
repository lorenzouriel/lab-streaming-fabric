# Real-Time Pipelines (Python)

> **Purpose**: Code-level best practices for asyncio-based real-time/streaming pipeline consumers and producers in Python
> **Researched**: 2026-09-16 (web-verified, see Sources)

## When to Use

- Writing a Kafka/Kinesis/Pub-Sub consumer or producer service in Python with `asyncio`
- Reviewing an existing Python streaming service for backpressure, idempotency, or shutdown gaps
- Deciding between `aiokafka` (asyncio-native) and `confluent-kafka` (sync, librdkafka bindings) for a given throughput target

Python's GIL means one blocking, CPU-bound call inside a coroutine stalls the entire event loop -- there's no implicit parallelism the way a JVM thread pool gives Flink/Kafka Streams. These practices exist to keep I/O concurrent and CPU-bound work off the loop, whether or not you're on a free-threaded (`3.13t`+) build.

## Backpressure with `asyncio.Queue`

A bounded queue is the Python analogue of `System.Threading.Channels` or a Kafka topic between two in-process stages: it forces a fast producer to slow down instead of buffering unboundedly into memory.

```python
import asyncio
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Event:
    key: str
    payload: bytes

async def produce(queue: asyncio.Queue[Event], events: list[Event]) -> None:
    for event in events:
        await queue.put(event)  # blocks once queue.maxsize is reached -- real backpressure
    await queue.put(None)  # sentinel: signals the consumer to stop

async def consume(queue: asyncio.Queue[Event | None]) -> None:
    while (event := await queue.get()) is not None:
        try:
            await process(event)
        finally:
            queue.task_done()

queue: asyncio.Queue[Event | None] = asyncio.Queue(maxsize=1000)  # bounded -- never unbounded
```

**Rule:** always set `maxsize`. An unbounded `asyncio.Queue()` removes backpressure entirely and lets a slow consumer turn into an unbounded memory leak, exactly like an unbounded `Channel<T>` in .NET.

## Async Kafka Consumer (aiokafka) with Bounded Concurrency

`aiokafka` is asyncio-native (`async for` iteration, coroutine startup/shutdown) -- prefer it over wrapping the sync `confluent-kafka` client in an executor unless you need librdkafka's raw throughput (see below).

```python
import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

async def run_consumer() -> None:
    consumer = AIOKafkaConsumer(
        "orders",
        bootstrap_servers="kafka:9092",
        group_id="order-processor",
        enable_auto_commit=False,       # manual commit -- at-least-once, not "fire and forget"
        auto_offset_reset="earliest",
    )
    dlq_producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    sem = asyncio.Semaphore(20)         # bounded fan-out -- never unbounded concurrent processing

    await consumer.start()
    await dlq_producer.start()
    try:
        async with asyncio.TaskGroup() as tg:
            async for msg in consumer:
                async def handle(msg=msg) -> None:
                    async with sem:
                        try:
                            event = parse_event(msg.value)   # raises on bad shape -- route to DLQ
                            await process_order(event)       # idempotent: safe to reprocess on redelivery
                        except ValidationError as e:
                            await route_to_dlq(dlq_producer, msg, e)
                        finally:
                            await consumer.commit()          # commit after handling, even on DLQ route
                tg.create_task(handle())
    finally:
        await consumer.stop()
        await dlq_producer.stop()
```

`asyncio.TaskGroup` (3.11+) is the structured-concurrency primitive to use for fan-out instead of bare `asyncio.gather()` or `create_task()` outside a scope -- every task's lifetime is tied to the group, and an unhandled exception in one task cancels the rest instead of leaking an orphaned task.

## Idempotency in the Handler

`aiokafka`/`confluent-kafka` have no transactional exactly-once consumer as simple to operate as Kafka Streams'. Make the handler idempotent instead of chasing framework-level exactly-once:

```python
async def process_order(event: OrderEvent) -> None:
    # Upsert on the natural key absorbs redelivery duplicates without extra dedup logic
    await db.execute(
        """
        INSERT INTO orders (id, amount, event_id) VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET amount = EXCLUDED.amount
        """,
        event.order_id, event.amount, event.event_id,
    )
```

## Dead-Letter Routing with Full Context

```python
import json, time
from aiokafka import AIOKafkaProducer, ConsumerRecord

async def route_to_dlq(producer: AIOKafkaProducer, msg: ConsumerRecord, error: Exception) -> None:
    await producer.send_and_wait(
        "orders-dlq",
        key=msg.key,
        value=msg.value,
        headers=[
            ("x-error", str(error).encode()),
            ("x-original-topic", msg.topic.encode()),
            ("x-original-offset", str(msg.offset).encode()),
            ("x-failed-at", str(time.time()).encode()),
        ],
    )
```

Classify before routing: parsing/validation errors go to the DLQ immediately (they will never succeed on retry); network/timeout errors get retried with backoff instead of burning the record.

## Graceful Shutdown

A consumer that doesn't drain in-flight work on `SIGTERM` loses or duplicates messages on every deploy.

```python
import asyncio, signal

async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    consumer_task = asyncio.create_task(run_consumer())
    await stop.wait()               # wait for signal
    consumer_task.cancel()          # triggers consumer.stop() in the finally block
    await asyncio.gather(consumer_task, return_exceptions=True)
```

## Don't Block the Event Loop

CPU-heavy transforms (large JSON parsing, compression, crypto) block every other coroutine in the process -- including health checks and other partitions' processing.

```python
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor(max_workers=4)

async def transform_in_process(payload: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, cpu_heavy_transform, payload)
```

On Python 3.13+, a free-threaded build (`python3.14t`) can run true multi-core CPU work inside threads without the GIL, avoiding IPC serialization overhead -- but it's still experimental-to-stable depending on version; `ProcessPoolExecutor` remains the safe default.

For very high-volume, CPU-light consumption, `confluent-kafka` (librdkafka, C-native) sustains materially higher throughput per instance than `aiokafka`'s pure-Python protocol handling -- reach for it when a single asyncio consumer becomes the bottleneck, not by default.

## Resilience: `tenacity`

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),   # jitter avoids synchronized retry storms
    retry=retry_if_exception_type(TransientError),      # never retry ValidationError -- DLQ it instead
)
async def call_downstream(payload: dict) -> dict:
    return await http_client.post("/enrich", json=payload)
```

## Runtime Tuning

| Practice | Effect |
|---|---|
| `uvloop` as the event loop | Drop-in `asyncio.run(main(), loop_factory=uvloop.new_event_loop)` typically cuts latency and raises I/O throughput 2-4x over the stdlib selector loop |
| `orjson` instead of stdlib `json` | Several times faster serialize/deserialize on the hot path -- meaningful at high message volume |
| Batch commits, not per-message | Commit every N messages or on a timer, not after every single one -- per-message commits cap throughput |
| Bound every queue and semaphore | Every unbounded buffer (queue, `gather()` of unknown size) is a latent memory leak under load |
| `slots=True` dataclasses for message envelopes | Lower per-message memory overhead at high throughput ([dataclasses](../concepts/dataclasses.md)) |

## Common Mistakes

| Don't | Do |
|---|---|
| `asyncio.Queue()` with no `maxsize` | Bounded queue -- forces backpressure instead of unbounded memory growth |
| `enable_auto_commit=True` with async processing | Manual commit after the message is actually handled (or DLQ'd) |
| Bare `asyncio.gather()`/loose `create_task()` for fan-out | `asyncio.TaskGroup` -- structured lifetime, exceptions cancel siblings instead of leaking orphans |
| Retry a `ValidationError` forever | Classify: parse/validation errors -> DLQ immediately; network/timeout -> retry with backoff+jitter |
| Run CPU-heavy transforms inline in a coroutine | Offload to `ProcessPoolExecutor`/`run_in_executor`, or a free-threaded build for CPU-bound threads |
| Exit on `SIGTERM` without draining in-flight work | Signal handler sets a stop event; cancel and await the consumer task before exit |
| Assume `aiokafka` matches `confluent-kafka` throughput | For very high volume, benchmark `confluent-kafka` (librdkafka) instead of assuming asyncio-native is fastest |

## See Also

- [Generators](../concepts/generators.md)
- [Context Managers](../concepts/context-managers.md)
- [Error Handling](error-handling.md)
- [streaming KB domain](../../streaming/index.md) — broker-side (Kafka/Flink) HA, throughput, and production best practices
- [Streaming domain: production-best-practices](../../streaming/patterns/production-best-practices.md)
- [Streaming domain: high-availability-throughput](../../streaming/patterns/high-availability-throughput.md)

## Sources

- [Python Kafka Clients in Production: Async, Backpressure, and Schema — AutoMQ](https://www.automq.com/blog/python-kafka-clients-in-production-async-backpressure-and-schema)
- [Choosing a Python Kafka Consumer: confluent-kafka vs. kafka-python vs. aiokafka — DEV Community](https://dev.to/getkafma/choosing-a-python-kafka-consumer-confluent-kafka-vs-kafka-python-vs-aiokafka-23c0)
- [Exactly-Once(-ish) with aiokafka: 8 Proven Techniques — Medium](https://medium.com/@Modexa/exactly-once-ish-with-aiokafka-8-proven-techniques-b31ff089d284)
- [How to Build Asyncio Queues in Python — OneUptime](https://oneuptime.com/blog/post/2026-01-30-python-asyncio-queues/view)
- [asyncio.TaskGroup: Structured Concurrency — Universo Python](https://universopython.com/en/blog/python-asyncio-taskgroup)
- [asyncio TaskGroup Patterns: The Complete 2026 Guide — pyblog.in](https://www.pyblog.in/programming/asyncio-taskgroup-patterns-the-complete-2026-guide/)
- [Structured Concurrency for AI Pipelines: Why asyncio.gather() Isn't Enough — TianPan.co](https://tianpan.co/blog/2026-04-09-structured-concurrency-ai-pipelines-parallel-tool-calls)
- [Python: Guide to structured concurrency — Applifting Blog](https://applifting.io/blog/python-structured-concurrency)
