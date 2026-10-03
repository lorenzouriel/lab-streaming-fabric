# Nullable Reference Types

> **Purpose**: Compile-time null-safety with `#nullable enable`, annotations, and null-state analysis
> **Confidence**: 0.95
> **MCP Validated:** 2026-04-14

## Overview

Nullable Reference Types (NRT), enabled project-wide via `<Nullable>enable</Nullable>`,
make reference-type nullability explicit in the type system. The compiler performs static
flow analysis and warns when a possibly-null value is dereferenced without a check. NRT
does not change runtime behavior — warnings are compile-time only — so it must be paired
with real guard clauses, not just annotations.

## The Pattern

```csharp
#nullable enable

public class UserService
{
    // Non-nullable: caller must pass a value, method never returns null.
    public User GetById(string id)
    {
        var user = _repository.Find(id);
        return user ?? throw new NotFoundException(nameof(User), id);
    }

    // Nullable: caller must check before use.
    public User? TryGetById(string id) => _repository.Find(id);
}
```

## Annotation Reference

| Syntax | Meaning |
|--------|---------|
| `string name` | Never null — compiler warns on any possibly-null assignment |
| `string? name` | May be null — compiler requires a null check before dereference |
| `string!` (null-forgiving) | Suppress a specific warning; use sparingly, document why |
| `[NotNullWhen(true)] bool TryX(out T? v)` | Tells the analyzer the out-param is non-null on `true` |
| `[MemberNotNull(nameof(_field))]` | Tells the analyzer a method guarantees a field is set |
| `required` (C# 11+) | Property must be set at construction (object initializer or constructor) |

## Guard Patterns

```csharp
public void Process(Order? order)
{
    ArgumentNullException.ThrowIfNull(order);   // .NET 6+ shorthand, narrows to non-null after

    // order is now known non-null for the rest of the method.
    Console.WriteLine(order.CustomerId);
}
```

```csharp
public string Format(string? input) =>
    string.IsNullOrWhiteSpace(input) ? "N/A" : input.Trim();
```

## Custom TryGet with Analyzer Support

```csharp
public bool TryFindUser(string id, [NotNullWhen(true)] out User? user)
{
    user = _cache.GetValueOrDefault(id);
    return user is not null;
}

if (TryFindUser("u1", out var found))
{
    Console.WriteLine(found.Name); // no warning: analyzer knows found is non-null here
}
```

## Common Mistakes

### Wrong (null-forgiving to silence a real bug)

```csharp
public string GetName(User? user) => user!.Name; // crashes at runtime if user is null
```

### Correct (explicit handling)

```csharp
public string GetName(User? user) => user?.Name ?? "Unknown";
```

## Project Configuration

```xml
<PropertyGroup>
  <Nullable>enable</Nullable>
  <WarningsAsErrors>CS8600;CS8602;CS8603;CS8625</WarningsAsErrors>
</PropertyGroup>
```

| Warning | Meaning |
|---------|---------|
| CS8600 | Converting null literal or possible null value to non-nullable type |
| CS8602 | Dereference of a possibly null reference |
| CS8603 | Possible null reference return |
| CS8625 | Cannot convert null literal to non-nullable reference type |

## Decision Matrix

| Situation | Choice |
|-----------|--------|
| Value is always present after this point | Non-nullable, guard early with `ArgumentNullException.ThrowIfNull` |
| Value is legitimately optional | `T?`, force caller to handle both branches |
| API boundary receiving untrusted input | `T?` in, validate/normalize immediately |
| You are 100% certain the analyzer is wrong | `!` with a comment explaining why (rare) |

## Related

- [Records](records.md)
- [Pattern Matching](pattern-matching.md)
- [Error Handling](../patterns/error-handling.md)
