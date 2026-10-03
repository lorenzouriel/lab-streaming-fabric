# Functional Patterns

> **Purpose**: LINQ, expression-bodied members, and functional composition for clean data transformations
> **MCP Validated:** 2026-04-14

## When to Use

- Transforming collections without mutation
- Building declarative data-processing pipelines
- Replacing verbose `foreach` loops with concise expressions
- Composing small, pure functions into larger operations

## Implementation

### LINQ Query and Method Syntax

```csharp
// Method syntax (preferred for chaining)
var names = users
    .Where(u => u.IsActive)
    .Select(u => u.Name.ToUpperInvariant())
    .OrderBy(n => n)
    .ToList();

// Query syntax (reads well for joins/group-by)
var byDomain =
    from email in emails
    let domain = email.Split('@')[1]
    group email by domain into g
    select new { Domain = g.Key, Count = g.Count() };
```

### Deferred Execution

```csharp
IEnumerable<int> query = numbers.Where(n => n > 0); // not evaluated yet
numbers.Add(5);                                      // affects the query
var results = query.ToList();                        // evaluated here, includes the 5
```

| Situation | Choose | Why |
|-----------|--------|-----|
| Reuse a query over a mutable source | Materialize with `.ToList()`/`.ToArray()` | Avoid surprise re-evaluation |
| Large/streamed source | Keep `IEnumerable<T>` lazy | Memory efficient, composes with iterators |
| Need `Count`/indexing repeatedly | `.ToList()` | Avoid re-enumerating |
| Async data source | `IAsyncEnumerable<T>` + `await foreach` | Non-blocking streaming |

## Aggregate, GroupBy, and Set Operations

```csharp
var total = order.Items.Sum(i => i.Price * i.Quantity);
var hasErrors = results.Any(r => r.Status == "error");
var allValid = names.All(n => n.Length > 0);

var grouped = orders
    .GroupBy(o => o.CustomerId)
    .Select(g => new { CustomerId = g.Key, Total = g.Sum(o => o.Total) });

var distinctDomains = emails.Select(e => e.Split('@')[1]).Distinct();
```

## Records + Non-Destructive Update Pipelines

```csharp
public sealed record Cart(IReadOnlyList<LineItem> Items, decimal Total);

public static Cart AddItem(Cart cart, LineItem item) =>
    cart with
    {
        Items = [.. cart.Items, item],
        Total = cart.Total + item.Price,
    };

public static Cart ApplyDiscount(Cart cart, decimal percent) =>
    cart with { Total = Math.Round(cart.Total * (1 - percent / 100), 2) };

var cart = new Cart([], 0m);
cart = AddItem(cart, new LineItem("Widget", 29.99m));
cart = ApplyDiscount(cart, 10);
```

## Function Composition

```csharp
public static Func<T, T> Pipe<T>(params Func<T, T>[] steps) =>
    input => steps.Aggregate(input, (value, step) => step(value));

var clean = Pipe<string>(s => s.Trim(), s => s.ToLowerInvariant())("  Hello, World!  ");
```

## Local Functions vs Lambdas vs Delegates

| Situation | Choose |
|-----------|--------|
| Small helper used only inside one method | Local function (named, debuggable, can be recursive) |
| Inline predicate/projection for LINQ | Lambda expression |
| Storing a reusable, reassignable behavior | `Func<>`/`Action<>` field or property |
| Public API accepting caller-supplied behavior | `Func<T, TResult>` parameter or a small interface |

```csharp
public IEnumerable<int> FilterAndSquare(IEnumerable<int> values)
{
    static bool IsPositive(int x) => x > 0; // local function: no closure allocation

    return values.Where(IsPositive).Select(x => x * x);
}
```

## Common Mistakes

### Wrong (mutation-heavy, imperative)

```csharp
var results = new List<string>();
foreach (var item in items)
{
    if (item.Active)
    {
        results.Add(item.Name.ToUpperInvariant());
    }
}
```

### Correct (declarative)

```csharp
var results = items
    .Where(i => i.Active)
    .Select(i => i.Name.ToUpperInvariant())
    .ToList();
```

### Wrong (multiple enumeration of an `IEnumerable`)

```csharp
if (query.Any())
{
    var first = query.First(); // re-runs the whole query
}
```

### Correct (materialize once)

```csharp
var list = query.ToList();
if (list.Count > 0)
{
    var first = list[0];
}
```

## See Also

- [Records](../concepts/records.md)
- [Pattern Matching](../concepts/pattern-matching.md)
- [File Parser](file-parser.md)
