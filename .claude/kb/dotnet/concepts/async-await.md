# Async/Await

> **Purpose**: `Task`/`ValueTask`, `async`/`await`, cancellation, and `IAsyncEnumerable<T>` for asynchronous and streaming code
> **Confidence**: 0.95
> **MCP Validated:** 2026-04-14

## Overview

`async`/`await` compiles to a state machine that frees the calling thread while waiting on
I/O. `Task` represents a single asynchronous operation; `IAsyncEnumerable<T>` (C# 8+) is the
async analogue of a generator — it yields items lazily over time, typically backed by
paginated APIs or streaming reads. Every async method that can be cancelled should accept a
`CancellationToken`.

## The Pattern

```csharp
public async Task<Order> GetOrderAsync(string id, CancellationToken ct = default)
{
    var response = await _httpClient.GetAsync($"/orders/{id}", ct);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<Order>(cancellationToken: ct)
        ?? throw new InvalidOperationException("Empty response body");
}
```

## Task vs ValueTask vs IAsyncEnumerable

| Type | Use When | Notes |
|------|----------|-------|
| `Task` / `Task<T>` | Default choice for async methods | Always safe to await multiple times |
| `ValueTask<T>` | Hot path, frequently completes synchronously (cache hits) | Await exactly once; don't store or await twice |
| `IAsyncEnumerable<T>` | Streaming a sequence produced over time | Consumed with `await foreach`, supports cancellation |
| `void` (async void) | Never, except top-level event handlers | Exceptions escape unobserved — avoid |

## Async Iterators (Generator Equivalent)

```csharp
public async IAsyncEnumerable<Order> StreamOrdersAsync(
    [EnumeratorCancellation] CancellationToken ct = default)
{
    string? cursor = null;
    do
    {
        var page = await _client.GetOrdersPageAsync(cursor, ct);
        foreach (var order in page.Items)
        {
            yield return order; // lazy: nothing fetched until the consumer asks for the next item
        }
        cursor = page.NextCursor;
    } while (cursor is not null);
}

// Consumption
await foreach (var order in StreamOrdersAsync(ct))
{
    Console.WriteLine(order.Id);
}
```

## Parallel Composition

```csharp
public async Task<(User User, Order[] Orders)> LoadDashboardAsync(string userId, CancellationToken ct)
{
    var userTask = _users.GetAsync(userId, ct);
    var ordersTask = _orders.GetForUserAsync(userId, ct);

    await Task.WhenAll(userTask, ordersTask);
    return (userTask.Result, ordersTask.Result);
}
```

## Cancellation

```csharp
public async Task RunWithTimeoutAsync(CancellationToken outerCt)
{
    using var cts = CancellationTokenSource.CreateLinkedTokenSource(outerCt);
    cts.CancelAfter(TimeSpan.FromSeconds(30));

    try
    {
        await LongRunningWorkAsync(cts.Token);
    }
    catch (OperationCanceledException) when (!outerCt.IsCancellationRequested)
    {
        throw new TimeoutException("Operation exceeded 30s");
    }
}
```

## Common Mistakes

### Wrong (blocking on async code -> deadlock risk)

```csharp
var order = GetOrderAsync(id).Result;       // can deadlock in UI/ASP.NET sync contexts
var order2 = GetOrderAsync(id).GetAwaiter().GetResult(); // same risk
```

### Correct (async all the way)

```csharp
var order = await GetOrderAsync(id, ct);
```

### Wrong (fire-and-forget swallows exceptions)

```csharp
_ = ProcessAsync(order); // exception disappears, order silently not processed
```

### Correct (observe or explicitly background it)

```csharp
await ProcessAsync(order);
// or, when truly fire-and-forget is intended:
_ = ProcessAsync(order).ContinueWith(t =>
    _logger.LogError(t.Exception, "Background processing failed"),
    TaskContinuationOptions.OnlyOnFaulted);
```

## Quick Reference

| Rule | Why |
|------|-----|
| Add `CancellationToken ct = default` to every async I/O method | Callers can cancel; propagate, don't swallow |
| Suffix async methods with `Async` | Convention, IntelliSense clarity |
| Never `async void` except event handlers | Exceptions crash the process unobserved |
| Use `ConfigureAwait(false)` in library code | Avoids deadlocks by not requiring the original context |
| Prefer `IAsyncEnumerable<T>` over `Task<List<T>>` for large/streamed results | Lower memory, backpressure-friendly |

## Related

- [Pattern Matching](pattern-matching.md)
- [File Parser](../patterns/file-parser.md)
- [Error Handling](../patterns/error-handling.md)
