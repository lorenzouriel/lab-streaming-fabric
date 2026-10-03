# Classes and Types

> **Purpose**: Declarative data containers -- interfaces, readonly properties, `as const`, and when to reach for a class
> **Confidence**: 0.95
> **MCP Validated:** 2026-03-26

## Overview

JavaScript has no dataclass equivalent, so TypeScript data containers are built from
`interface`/`type` plus `readonly` for immutability, and object/array literals frozen with
`as const`. Classes are reserved for objects with behavior and internal state, not plain
data -- a `class` with only public fields and no methods is almost always better expressed
as an `interface`.

## The Pattern

```typescript
interface Metric {
  readonly name: string;
  readonly value: number;
  readonly timestamp: Date;
  readonly tags: readonly string[];
}

function createMetric(name: string, value: number, tags: string[] = []): Metric {
  return { name, value, timestamp: new Date(), tags };
}

// Immutable "with" pattern -- return a new object, never mutate
function withTag(metric: Metric, tag: string): Metric {
  return { ...metric, tags: [...metric.tags, tag] };
}
```

## Readonly and Deep Immutability

| Technique | Effect | Depth |
|-----------|--------|-------|
| `readonly` field | Field can't be reassigned | Shallow |
| `Readonly<T>` | All fields become `readonly` | Shallow |
| `as const` | Literal type is frozen, inferred as narrowly as possible | Deep (structural) |
| `Object.freeze(obj)` | Runtime immutability (throws in strict mode on write) | Shallow (JS runtime) |

```typescript
const STATUSES = ["active", "inactive", "pending"] as const;
type Status = (typeof STATUSES)[number]; // "active" | "inactive" | "pending"

const config = Object.freeze({ maxRetries: 3, timeout: 5000 });
```

## When to Use a Class Instead

```typescript
// GOOD: class carries behavior + encapsulated state
class RateLimiter {
  #tokens: number;
  readonly #max: number;

  constructor(max: number) {
    this.#max = max;
    this.#tokens = max;
  }

  tryAcquire(): boolean {
    if (this.#tokens <= 0) return false;
    this.#tokens -= 1;
    return true;
  }
}
```

```typescript
// BAD: plain data forced into a class -- use an interface instead
class UserDTO {
  constructor(
    public id: string,
    public name: string,
    public email: string,
  ) {}
}
```

## Structural Typing (Duck Typing)

```typescript
interface Serializable {
  toDict(): Record<string, unknown>;
}

// Any object shaped like Serializable satisfies the type -- no `implements` needed
function save(obj: Serializable): void {
  const data = obj.toDict();
  // ...
}

const point = { toDict: () => ({ x: 1, y: 2 }) };
save(point); // OK -- structurally compatible
```

## Records and Validation Boundaries

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
});

type User = z.infer<typeof UserSchema>; // type derived from the runtime schema

function parseUser(raw: unknown): User {
  return UserSchema.parse(raw); // throws ZodError with details on invalid input
}
```

## When to Use What

| Need | Use |
|------|-----|
| Plain data shape, compile-time only | `interface` / `type` |
| Immutable value object | `interface` with `readonly` fields + `as const` for literals |
| Data with runtime validation | `zod`, `valibot`, or `io-ts` schema |
| Behavior + encapsulated state | `class` with private fields (`#field`) |
| Enum-like fixed set of values | `as const` tuple + derived union type (prefer over `enum`) |
| Structural interface across modules | `interface` (duck typing, no explicit `implements` needed) |

## Common Mistakes

### Wrong (mutable shared default)

```typescript
interface Config {
  items: string[];
}

const defaultConfig: Config = { items: [] };
function addItem(config: Config, item: string): void {
  config.items.push(item); // mutates the shared default in place
}
```

### Correct (immutable update)

```typescript
interface Config {
  readonly items: readonly string[];
}

function addItem(config: Config, item: string): Config {
  return { ...config, items: [...config.items, item] };
}
```

## Related

- [Type Hints](../concepts/type-hints.md)
- [Clean Architecture](../patterns/clean-architecture.md)
- [Functional Patterns](../patterns/functional-patterns.md)
