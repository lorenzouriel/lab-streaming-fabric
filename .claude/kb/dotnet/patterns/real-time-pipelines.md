# Real-Time Pipelines in C#

> **Purpose**: Building high-throughput, low-latency, resilient real-time data pipelines in C#/.NET — Channels, Kafka/Event Hubs clients, gRPC streaming, resilience, and runtime tuning
> **Researched**: 2026-09-16 (web-verified, see Sources)

## When to Use

- Writing a .NET consumer/producer for Kafka, Azure Event Hubs, or another streaming broker
- Building an in-process producer/consumer pipeline (ingest → transform → sink) inside a single service
- Streaming data over gRPC or exposing a live feed via `IAsyncEnumerable<T>`
- A pipeline needs to survive broker restarts, partial failures, and bursty load without dropping data or blocking indefinitely

## In-Process Pipelines: `System.Threading.Channels`

`Channel<T>` is the standard building block for an async, thread-safe producer/consumer pipeline inside one process — the in-memory analogue of a Kafka topic.

```csharp
var channel = Channel.CreateBounded<Event>(new BoundedChannelOptions(capacity: 1000)
{
    FullMode = BoundedChannelFullMode.Wait,   // true backpressure: producer awaits until space frees up
    SingleReader = true,
    SingleWriter = false,
});

// Producer
await channel.Writer.WriteAsync(evt, ct);   // yields the thread, doesn't block it
// ...
channel.Writer.Complete();                  // signal no more items — required for ReadAllAsync to end

// Consumer
await foreach (var evt in channel.Reader.ReadAllAsync(ct))
{
    await ProcessAsync(evt, ct);
}
```

| `BoundedChannelFullMode` | Behavior | Use When |
|---|---|---|
| `Wait` (default) | Producer awaits until a slot frees | Cannot lose any message — the correct default for production |
| `DropWrite` | Silently drops the new item | Acceptable to lose a sample (metrics, telemetry) |
| `DropOldest` | Evicts the oldest queued item | Only the newest value matters (live price ticks, dashboards) |

**Rules:** prefer **bounded** channels — unbounded channels remove backpressure entirely and let a slow consumer turn into an unbounded memory leak. Always call `Complete()` on the writer when producing is done. Channels are in-memory only — a restart loses whatever is queued, so they are for in-process buffering, not durable delivery.

## Kafka: Confluent.Kafka Client

```csharp
// Producer: fire-and-forget with delivery-report callback for throughput
var config = new ProducerConfig
{
    BootstrapServers = "broker:9092",
    EnableIdempotence = true,     // safe retries, no duplicate writes on the broker side
    Acks = Acks.All,
    LingerMs = 20,                // batch briefly for throughput
};

using var producer = new ProducerBuilder<string, string>(config).Build();
producer.Produce(topic, new Message<string, string> { Key = key, Value = payload },
    report =>
    {
        if (report.Error.IsError)
            _logger.LogError("Delivery failed: {Reason}", report.Error.Reason);
    });
producer.Flush(TimeSpan.FromSeconds(10)); // before shutdown: ensure fire-and-forget messages are actually sent
```

```csharp
// Consumer: manual commit after successful processing, run inside a BackgroundService
var config = new ConsumerConfig
{
    BootstrapServers = "broker:9092",
    GroupId = "orders-processor",
    EnableAutoCommit = false,          // commit only after the message is actually processed
    AutoOffsetReset = AutoOffsetReset.Earliest,
};

using var consumer = new ConsumerBuilder<string, string>(config).Build();
consumer.Subscribe(topic);

while (!ct.IsCancellationRequested)
{
    var result = consumer.Consume(ct);   // blocking poll loop, cancellable
    try
    {
        await ProcessAsync(result.Message.Value, ct);
        consumer.Commit(result);
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Processing failed at offset {Offset}", result.Offset);
        // route to DLQ, do not commit — message will be redelivered
    }
}
consumer.Close();
```

| Practice | Why |
|---|---|
| `EnableIdempotence = true` on the producer | Safe retries without duplicate writes |
| `EnableAutoCommit = false` + commit after processing | Prevents committing an offset for a message that was never actually handled |
| Run the consumer loop in a `BackgroundService` | Integrates with ASP.NET Core's hosted lifetime and shutdown cancellation |
| Design consumers to be idempotent regardless of delivery model | At-least-once is the practical default; idempotent processing absorbs redelivery |
| Monitor consumer lag | A consumer that silently falls behind is a slow-motion outage |

## Azure Event Hubs: `EventProcessorClient`

```csharp
var processor = new EventProcessorClient(
    checkpointStore, consumerGroup, eventHubsConnectionString, eventHubName);

processor.ProcessEventAsync += async args =>
{
    await HandleEventAsync(args.Data, args.CancellationToken);
    if (args.Data.SequenceNumber % 100 == 0)          // checkpoint periodically, not per-event
        await args.UpdateCheckpointAsync(args.CancellationToken);
};
processor.ProcessErrorAsync += args =>
{
    _logger.LogError(args.Exception, "Error on partition {PartitionId}", args.PartitionId);
    return Task.CompletedTask;
};

await processor.StartProcessingAsync(ct);
```

| Practice | Why |
|---|---|
| Cache `EventProcessorClient` as a singleton | It owns partition ownership/coordination — cheap to reuse, expensive to recreate |
| One active consumer per partition + consumer-group pair | Competing consumers on the same partition/group cause rebalance churn |
| Checkpoint periodically, not per event | Checkpointing every message adds storage I/O that caps throughput |
| Use managed identity (`Azure.Identity`), not connection strings | Avoids long-lived secrets in config |
| Alert on consumer lag and partition count at namespace limits | Partition count is fixed at creation in Standard tier — plan throughput up front |

## gRPC Streaming

```csharp
public override async Task StreamOrders(
    OrderRequest request,
    IServerStreamWriter<OrderUpdate> responseStream,
    ServerCallContext context)
{
    await foreach (var update in _orders.WatchAsync(request.OrderId, context.CancellationToken))
    {
        if (context.CancellationToken.IsCancellationRequested)
            break;                      // client disconnected — stop producing immediately

        await responseStream.WriteAsync(update);
    }
}
```

| Practice | Why |
|---|---|
| Set a deadline on every call (`CallOptions.Deadline`) | Bounds how long a call can run; stops a misbehaving peer from exhausting resources |
| Check `context.CancellationToken` in every streaming loop iteration | Server keeps writing into a dead stream otherwise, wasting CPU |
| Dispose the call / complete the stream on both graceful and error paths | Ensures the underlying HTTP/2 stream is actually torn down |
| Design for backpressure explicitly | The client not reading fills the send buffer and blocks further server writes — don't assume it "just works" without bounding buffer sizes |

## Resilience: Polly / `Microsoft.Extensions.Resilience`

```csharp
var pipeline = new ResiliencePipelineBuilder()
    .AddRetry(new RetryStrategyOptions
    {
        MaxRetryAttempts = 3,
        BackoffType = DelayBackoffType.Exponential,
        UseJitter = true,                 // avoid synchronized retry storms across instances
    })
    .AddCircuitBreaker(new CircuitBreakerStrategyOptions
    {
        FailureRatio = 0.4,
        SamplingDuration = TimeSpan.FromSeconds(30),
        BreakDuration = TimeSpan.FromSeconds(15),
    })
    .AddTimeout(TimeSpan.FromSeconds(4))   // per-attempt timeout
    .Build();

await pipeline.ExecuteAsync(async ct => await downstream.CallAsync(ct), ct);
```

| Practice | Why |
|---|---|
| Always enable jitter on retries | Prevents every failing instance from retrying in lockstep and re-hammering the downstream at the same instant |
| Circuit breaker on top of retry, not instead of it | Retry absorbs blips; the breaker protects the downstream once failures sustain |
| Give the whole operation a total time budget, not just per-attempt | 3 retries × 4s timeout without a budget can silently turn a "fast failure" into a 12s+ stall |
| Prefer `Microsoft.Extensions.Resilience`/`Microsoft.Extensions.Http.Resilience` for HTTP calls | Built on Polly v8, the current recommended API for .NET 8+ HTTP resilience |
| Emit OpenTelemetry from the resilience pipeline | Without it, you cannot see how often retries/breaks are firing in production |

## Runtime Tuning for Throughput and Latency

| Setting/Practice | Effect |
|---|---|
| Server GC (`<ServerGarbageCollection>true</ServerGarbageCollection>`) | Optimized for throughput on multi-core hosts; enable concurrent GC and monitor pause times |
| `ArrayPool<byte>`/`MemoryPool<T>` for buffers | Avoids per-message heap allocations in the hot path — rent, use, return |
| `Span<T>`/`ReadOnlySpan<T>` for parsing | Zero-allocation slicing of buffers instead of allocating substrings/arrays per message |
| `ValueTask<T>` for hot-path async methods that often complete synchronously | Avoids a `Task` heap allocation on the common (cache-hit) path |
| Never `async void` (except UI event handlers) | Exceptions escape unobserved and callers cannot await/coordinate the work |
| Watch for Gen2 GC pauses in tail latency | Even a brief Gen2 collection can push p99 latency from under 1ms to hundreds of ms in a hot pipeline |

## Common Mistakes

| Don't | Do |
|---|---|
| Unbounded `Channel<T>` on a producer that can outrun the consumer | Bounded channel with `FullMode = Wait` for real backpressure |
| `EnableAutoCommit = true` on a Kafka consumer | Manual commit after successful processing |
| Checkpoint an Event Hubs processor on every single event | Checkpoint periodically (e.g., every N events or on a timer) |
| Ignore `ServerCallContext.CancellationToken` in a gRPC server stream | Check it every loop iteration and stop writing immediately |
| Retry without jitter | Always add jitter to avoid synchronized retry storms |
| Allocate a new buffer per message in a hot loop | Rent from `ArrayPool<T>`/`MemoryPool<T>` and return it |

## See Also

- [Async/Await](../concepts/async-await.md)
- [File Parser](file-parser.md)
- [Error Handling](error-handling.md)
- [streaming KB domain](../../streaming/index.md) — broker-side (Kafka/Flink) HA, throughput, and production best practices

## Sources

- [.NET Client for Apache Kafka — Confluent Documentation](https://docs.confluent.io/kafka-clients/dotnet/current/overview.html)
- [Building Reliable Kafka Producers and Consumers in .NET — The Cloud Blog](https://thecloudblog.net/post/building-reliable-kafka-producers-and-consumers-in-net/)
- [Best Practices for Implementing Kafka Consumers in C#](https://www.webdevtutor.net/blog/c-sharp-kafka-consumer-best-practices)
- [Build a Bounded Processing Pipeline With System.Threading.Channels](https://www.devleader.ca/2026/09/15/build-a-bounded-processing-pipeline-with-systemthreadingchannels)
- [Mastering Channels in C#: Async Producer/Consumer With Backpressure — Medium](https://medium.com/@shanto462/mastering-channels-in-c-async-producer-consumer-done-right-with-backpressure-617b3ec552fa)
- [High-Throughput Zero-Allocation Pipelines in .NET 9: Span<T>, MemoryPool, and Channels — DEV Community](https://dev.to/amasen/high-throughput-zero-allocation-pipelines-in-net-9-span-memorypool-and-channels-44k3)
- [How to Implement Circuit Breakers with Polly in .NET — OneUptime](https://oneuptime.com/blog/post/2026-01-27-circuit-breakers-polly-dotnet/view)
- [Resilience Pipelines in .NET With Polly — Milan Jovanović](https://milanjovanovic.tech/blog/building-resilient-cloud-applications-with-dotnet)
- [Introduction to resilient app development - .NET — Microsoft Learn](https://learn.microsoft.com/en-us/dotnet/core/resilience/)
- [Architecture Best Practices for Azure Event Hubs — Microsoft Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-event-hubs)
- [Azure Event Hubs Event Processor client library for .NET — GitHub](https://github.com/Azure/azure-sdk-for-net/blob/main/sdk/eventhub/Azure.Messaging.EventHubs.Processor/README.md)
- [Reliable gRPC services with deadlines and cancellation — Microsoft Learn](https://learn.microsoft.com/en-us/aspnet/core/grpc/deadlines-cancellation?view=aspnetcore-10.0)
- [Performance best practices with gRPC — Microsoft Learn](https://learn.microsoft.com/en-us/aspnet/core/grpc/performance?view=aspnetcore-10.0)
- [Rate Limiting Streaming gRPC Calls — Laszlo](https://blog.ladeak.net/posts/streaming-grpc-ratelimiting)
- [Latency Modes - .NET — Microsoft Learn](https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/latency)
- [ASP.NET Core Performance Tuning in 2026 — Syncfusion Blogs](https://www.syncfusion.com/blogs/post/performance-tuning-in-aspnetcore-2026)
- [Why You Should Avoid async void in C# — Medium](https://medium.com/net-code-chronicles/why-you-should-avoid-async-void-in-csharp-ead37e3e5894)
