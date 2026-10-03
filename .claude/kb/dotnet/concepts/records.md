# Records

> **Purpose**: `record` / `record struct` reference and value types for immutable data models in C# 12+
> **Confidence**: 0.95
> **MCP Validated:** 2026-04-14

## Overview

Records are reference or value types with compiler-generated value equality, `ToString()`,
and non-destructive mutation (`with` expressions). They are the idiomatic replacement for
hand-rolled immutable DTOs, value objects, and message/event payloads. `record class` (the
default) is reference-typed; `record struct` is value-typed and avoids heap allocation for
small, frequently-copied data.

## The Pattern

```csharp
public record Metric(
    string Name,
    double Value,
    DateTimeOffset Timestamp,
    IReadOnlyList<string> Tags)
{
    // Positional records still allow a body for extra members/validation.
    public Metric WithTag(string tag) =>
        this with { Tags = [.. Tags, tag] };
}

var m = new Metric("latency_ms", 42.0, DateTimeOffset.UtcNow, []);
var tagged = m.WithTag("prod");   // non-destructive mutation via `with`
```

## Record Class vs Record Struct vs Class

| Feature | `class` | `record class` | `record struct` |
|---------|---------|-----------------|------------------|
| Storage | Heap | Heap | Stack (or inline) |
| Equality | Reference | Value (member-wise) | Value (member-wise) |
| `ToString()` | Default `TypeName` | Auto-generated, prints members | Auto-generated |
| `with` expression | No | Yes | Yes |
| Mutability | Mutable by default | Init-only by default | Mutable by default (add `readonly` to lock) |
| Best for | Entities, services | DTOs, events, value objects | Small, hot-path value objects |

## Init-Only Properties and Validation

```csharp
public record Order
{
    public required string CustomerId { get; init; }
    public required decimal Total { get; init; }
    public IReadOnlyList<string> Items { get; init; } = [];

    public Order
    {
        // Primary-constructor-style validation runs on every construction path.
    }
}

// Non-positional records still support `with` and value equality.
var order = new Order { CustomerId = "C-1", Total = 99.90m };
var discounted = order with { Total = order.Total * 0.9m };
```

## Readonly Record Struct (Value Object)

```csharp
public readonly record struct Money(decimal Amount, string Currency)
{
    public static Money operator +(Money a, Money b)
    {
        if (a.Currency != b.Currency)
            throw new InvalidOperationException("Currency mismatch");
        return a with { Amount = a.Amount + b.Amount };
    }
}
```

## Pattern Matching on Records

```csharp
static string Describe(object shape) => shape switch
{
    Circle { Radius: > 10 } c => $"Large circle r={c.Radius}",
    Circle(var center, var r) => $"Circle at {center} r={r}",
    Point(var x, var y) => $"Point ({x}, {y})",
    _ => "Unknown shape",
};

public record Point(double X, double Y);
public record Circle(Point Center, double Radius);
```

## Common Mistakes

### Wrong (mutable collection breaks value equality)

```csharp
public record Config(List<string> Items); // two Configs with same contents may still
                                           // behave unexpectedly if callers mutate Items
```

### Correct (immutable member type)

```csharp
public record Config(IReadOnlyList<string> Items);
```

## When to Use What

| Need | Use |
|------|-----|
| Immutable DTO / API payload | `record class` (positional) |
| Small, copied-often value type | `readonly record struct` |
| Entity with identity, mutable state | `class` |
| Domain value object with invariants | `readonly record struct` + validation in constructor |
| Discriminated union of cases | `record` hierarchy + pattern matching / switch expression |

## Related

- [Nullable Reference Types](nullable-reference-types.md)
- [Pattern Matching](pattern-matching.md)
- [Clean Architecture](../patterns/clean-architecture.md)
