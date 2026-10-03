# C# / .NET Clean Code Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-04-14

## Record Options (C# 9-12)

| Form | Mutability | Storage | Effect |
|------|-----------|---------|--------|
| `record class Foo(...)` | Init-only by default | Heap | Value equality, `with`, auto `ToString()` |
| `record struct Foo(...)` | Mutable by default | Stack/inline | Value equality, `with`, no heap allocation |
| `readonly record struct Foo(...)` | Immutable | Stack/inline | Best for small, hot-path value objects |
| `class Foo` | Mutable | Heap | Reference equality, use for entities/services |

## Nullable Annotation Patterns

| Pattern | Syntax | Meaning |
|---------|--------|---------|
| Non-nullable | `string name` | Compiler warns if a possibly-null value is assigned |
| Nullable | `string? name` | Caller must null-check before dereference |
| Guard | `ArgumentNullException.ThrowIfNull(x)` | Throws + narrows to non-null after the call |
| Analyzer hint | `[NotNullWhen(true)] out T? v` | Tells flow analysis the out-param is non-null on `true` |
| Required member | `public required string Id { get; init; }` | Must be set at construction (C# 11+) |

## Pattern Matching Cheat Sheet

| Pattern | Syntax | Matches |
|---------|--------|---------|
| Property | `{ Status: "active" }` | Nested member values |
| Positional | `Point(var x, var y)` | Deconstructed record |
| Relational | `case > 10:` | Comparison |
| List (C# 11+) | `[first, .. rest]` | Array/list shape + slicing |
| Combinator | `case > 0 and < 100:` | `and`/`or`/`not` |
| Type + guard | `User { IsActive: true } u` | Type check + property check + binding |

## Task vs ValueTask vs IAsyncEnumerable

| Type | Use Case | Note |
|------|----------|------|
| `Task<T>` | Default async return type | Safe to await multiple times |
| `ValueTask<T>` | Hot path, often completes synchronously | Await exactly once |
| `IAsyncEnumerable<T>` | Streaming a sequence over time | `await foreach`, cancellation-aware |
| `async void` | Never (except UI event handlers) | Exceptions are unobservable |

## .NET 8/9 New Features

| Feature | Version | Description |
|---------|---------|--------------|
| `TimeProvider` | .NET 8+ | Testable abstraction over `DateTime.Now`/timers |
| Keyed DI services | .NET 8+ | `AddKeyedSingleton<T>("key")` / `[FromKeyedServices]` |
| Frozen collections | .NET 8+ | `FrozenDictionary`/`FrozenSet` for read-heavy lookups |
| Native AOT (ASP.NET minimal APIs) | .NET 8+ | Trimmed, fast-start deployables |
| `Lock` type | .NET 9+ | Faster, purpose-built alternative to `lock (object)` |
| Central Package Management | SDK-wide | `Directory.Packages.props` pins versions solution-wide |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Immutable DTO / API payload | `record class` (positional) |
| Small, copied-often value type | `readonly record struct` |
| Entity with identity, mutable state | `class` |
| Discriminated union of message types | `record` hierarchy + `switch` expression |
| Parse large file line by line | Iterator method with `yield return` |
| Stream paginated/async data | `IAsyncEnumerable<T>` + `await foreach` |
| Expected, recoverable failure | `Result<T>` / `TryX` pattern |
| Unexpected/exceptional failure | Typed exception derived from a common base |
| Manage resource lifecycle | `using` declaration / `IAsyncDisposable` |
| Package version pinning across projects | Central Package Management |

## Real-Time Pipeline Quick Picks ([full guide](patterns/real-time-pipelines.md))

| Need | Choose |
|------|--------|
| In-process producer/consumer buffer | `Channel.CreateBounded<T>`, `FullMode = Wait` |
| Kafka / Azure broker client | `Confluent.Kafka` (manual commit) / `EventProcessorClient` (singleton) |
| Live server-to-client feed | gRPC server streaming, deadline + cancellation checks |
| Transient-fault handling | `Microsoft.Extensions.Resilience` (Polly v8) with jitter |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `catch (Exception) { }` (swallow) | `catch (SpecificException e)` with logging or `when` filter |
| `.Result` / `.GetAwaiter().GetResult()` | `await` all the way through |
| `async void MethodAsync()` | `async Task MethodAsync()` |
| `user!.Name` to silence a nullable warning | `user?.Name ?? "Unknown"` or guard clause first |
| Mutable `List<T>` field on a `record` | `IReadOnlyList<T>` to preserve value-equality semantics |
| `List<object>` "bag of anything" params | Strongly-typed records/DTOs |
| Per-project `<PackageReference Version="x"/>` sprawl | Central Package Management (`Directory.Packages.props`) |
| Multiple enumeration of `IEnumerable<T>` | Materialize once with `.ToList()` when reused |

## Related Documentation

| Topic | Path |
|-------|------|
| Records deep dive | `concepts/records.md` |
| Nullable reference types guide | `concepts/nullable-reference-types.md` |
| Error handling patterns | `patterns/error-handling.md` |
| Full Index | `index.md` |
