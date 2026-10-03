# Functional Patterns

> **Purpose**: Array methods, immutability, composition, and currying for clean data transformations
> **MCP Validated:** 2026-02-17

## When to Use

- Transforming collections without mutation
- Building declarative data processing pipelines
- Replacing verbose loops with concise expressions
- Composing small functions into complex operations

## Implementation

### Array Methods (map / filter / reduce)

```typescript
// Transform + filter, chained
const names = users
  .filter((u) => u.active)
  .map((u) => u.name.toUpperCase());

// Build a lookup map
const userMap = new Map(users.map((u) => [u.id, u]));

// Unique values
const domains = new Set(emails.map((e) => e.split("@")[1]));

// Flatten (max 2 levels -- extract a function beyond that)
const flat = matrix.flat();

// Conditional mapping
const labels = scores.map((score) => (score >= 70 ? "pass" : "fail"));
```

### Aggregate Helpers

```typescript
// some/every read like `any`/`all` from other languages
const hasErrors = results.some((r) => r.status === "error");
const allValid = names.every((name) => name.length > 0);

const total = order.items.reduce((sum, item) => sum + item.price * item.qty, 0);
```

## reduce for Transformation

```typescript
const amounts = rawAmounts.map(Number);
const positive = amounts.filter((x) => x > 0);
const total = amounts.reduce((acc, x) => acc + x, 0);
```

### When to Prefer What

| Situation | Use | Why |
|-----------|-----|-----|
| Simple transform | `.map()` | More readable than a manual loop |
| Transform + filter | Chained `.filter().map()` | Declarative, no intermediate mutation |
| Need lazy evaluation | Generator (see [Generators](../concepts/generators.md)) | Arrays are always eager in JS |
| Aggregate to a single value | `.reduce()` | Explicit accumulator, no external `let` |
| Existing named function | `.map(fn)` | Cleaner than `.map((x) => fn(x))` when signatures match |

## Memoization

```typescript
function memoize<Args extends unknown[], R>(fn: (...args: Args) => R): (...args: Args) => R {
  const cache = new Map<string, R>();
  return (...args: Args): R => {
    const key = JSON.stringify(args);
    if (!cache.has(key)) cache.set(key, fn(...args));
    return cache.get(key)!;
  };
}

const fibonacci = memoize((n: number): number => (n < 2 ? n : fibonacci(n - 1) + fibonacci(n - 2)));
```

## Partial Application / Currying

```typescript
function power(base: number, exponent: number): number {
  return base ** exponent;
}

const square = (base: number) => power(base, 2);
const cube = (base: number) => power(base, 3);
const squares = [1, 2, 3].map(square);
```

## Pipeline Pattern (pipe / compose)

```typescript
function pipe<T>(value: T, ...fns: Array<(v: T) => T>): T {
  return fns.reduce((v, fn) => fn(v), value);
}

const clean = pipe(
  "  Hello, World!  ",
  (s) => s.trim(),
  (s) => s.toLowerCase(),
);
```

## Immutable Transformations

```typescript
interface Order {
  readonly items: readonly string[];
  readonly total: number;
}

function addItem(order: Order, item: string, price: number): Order {
  return { items: [...order.items, item], total: order.total + price };
}

function applyDiscount(order: Order, percent: number): Order {
  return { items: order.items, total: Math.round(order.total * (1 - percent / 100) * 100) / 100 };
}

let order: Order = { items: [], total: 0 };
order = addItem(order, "Widget", 29.99);
order = applyDiscount(order, 10);
```

## Grouping and Slicing

```typescript
// Object.groupBy (ES2024 / Node 21+)
const byCategory = Object.groupBy(records, (r) => r.category);

for (const [category, group] of Object.entries(byCategory)) {
  console.log(`${category}: ${group?.length ?? 0} items`);
}

// Chunking (no stdlib equivalent -- write it once, reuse it)
function chunk<T>(items: T[], size: number): T[][] {
  return Array.from({ length: Math.ceil(items.length / size) }, (_, i) =>
    items.slice(i * size, i * size + size),
  );
}
```

## Common Mistakes

### Wrong (mutation-heavy)

```typescript
const results = [];
for (const item of items) {
  if (item.active) {
    results.push(item.name.toUpperCase());
  }
}
```

### Correct (declarative)

```typescript
const results = items.filter((item) => item.active).map((item) => item.name.toUpperCase());
```

## See Also

- [Generators](../concepts/generators.md)
- [Classes and Types](../concepts/classes-and-types.md)
- [File Parser](../patterns/file-parser.md)
