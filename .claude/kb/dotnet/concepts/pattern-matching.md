# Pattern Matching

> **Purpose**: `switch` expressions, property/positional/list patterns, and `is` patterns (C# 9-13)
> **Confidence**: 0.90
> **MCP Validated:** 2026-04-14

## Overview

C# pattern matching lets you branch on a value's shape, type, and contents in a single
expression instead of chains of `if`/`else` and casts. `switch` expressions return a value
and require exhaustiveness (or a `_` discard), which the compiler checks.

## The Pattern

```csharp
public decimal CalculateShipping(Order order) => order switch
{
    { Total: >= 100 } => 0m,
    { Items.Count: 0 } => throw new InvalidOperationException("Empty order"),
    { Region: "US", Total: < 50 } => 9.99m,
    { Region: "US" } => 4.99m,
    _ => 14.99m,
};
```

## Pattern Kinds

| Pattern | Example | Matches |
|---------|---------|---------|
| Type pattern | `case Circle c:` | Runtime type, binds a variable |
| Constant pattern | `case 0:` | Exact value |
| Relational pattern | `case > 10:` | Comparison (C# 9+) |
| Property pattern | `{ Status: "active" }` | Nested member values |
| Positional pattern | `Point(var x, var y)` | Deconstructed record/tuple |
| List pattern (C# 11+) | `[1, 2, .. var rest]` | Array/list shape and slicing |
| `and` / `or` / `not` | `case > 0 and < 100:` | Combinators (C# 9+) |
| `var` pattern | `case var x:` | Always matches, binds |

## List Patterns (C# 11+)

```csharp
static string Describe(int[] numbers) => numbers switch
{
    [] => "empty",
    [var single] => $"one item: {single}",
    [var first, .. var rest] when rest.Length > 0 => $"starts with {first}, {rest.Length} more",
    _ => "unknown",
};
```

## Combining Type + Property Patterns

```csharp
public string Handle(object message) => message switch
{
    OrderCreated { Total: > 1000 } big => $"High-value order {big.OrderId}",
    OrderCreated created => $"Order {created.OrderId}",
    OrderCancelled { Reason: null or "" } => "Cancelled, no reason given",
    OrderCancelled cancelled => $"Cancelled: {cancelled.Reason}",
    _ => "Unhandled message",
};
```

## `is` Patterns for Guard Clauses

```csharp
public void Process(object input)
{
    if (input is not User { IsActive: true } user)
    {
        return; // handles null, wrong type, and inactive users in one check
    }

    Console.WriteLine(user.Name);
}
```

## Switch Statement vs Switch Expression

| Use Case | Choose |
|----------|--------|
| Producing a value | `switch` expression (`=>`), exhaustive |
| Executing side effects per case | `switch` statement |
| Discriminated union over records | `switch` expression + positional/property patterns |
| Simple type dispatch | `is` pattern with pattern variable |

## Common Mistakes

### Wrong (non-exhaustive switch expression silently throws at runtime)

```csharp
string Grade(int score) => score switch
{
    >= 90 => "A",
    >= 80 => "B",
    // missing default -> throws SwitchExpressionException for score < 80
};
```

### Correct (explicit fallback)

```csharp
string Grade(int score) => score switch
{
    >= 90 => "A",
    >= 80 => "B",
    _ => "F",
};
```

## Related

- [Records](records.md)
- [Nullable Reference Types](nullable-reference-types.md)
- [Functional Patterns](../patterns/functional-patterns.md)
