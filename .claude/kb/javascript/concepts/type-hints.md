# Type Hints

> **Purpose**: TypeScript type annotations, generics, utility types, discriminated unions, and template literal types
> **Confidence**: 0.95
> **MCP Validated:** 2026-03-26

## Overview

TypeScript adds static types on top of JavaScript, catching errors at compile time and
powering editor autocomplete. Modern TypeScript (5.x) favors `interface`/`type` over
classes for data shapes, `satisfies` for type-checked literals, and discriminated unions
over inheritance for modeling variants.

## The Pattern

```typescript
interface TreeNode {
  value: number;
  children?: TreeNode[];
}

function addChild(node: TreeNode, value: number): TreeNode {
  const child: TreeNode = { value };
  node.children = [...(node.children ?? []), child];
  return child;
}
```

## Interfaces vs Type Aliases vs Classes

| Construct | Use For | Extensible |
|-----------|---------|------------|
| `interface` | Object shapes, public API contracts | Yes (`extends`, declaration merging) |
| `type` | Unions, tuples, mapped/conditional types | No (intersect with `&`) |
| `class` | Behavior + state, needs `instanceof` | Yes (`extends`, `implements`) |

## Discriminated Unions

```typescript
type Result<T> =
  | { status: "success"; value: T }
  | { status: "error"; error: string };

function handle<T>(result: Result<T>): T | null {
  switch (result.status) {
    case "success":
      return result.value; // narrowed to the success branch
    case "error":
      console.error(result.error);
      return null;
  }
}
```

## Generics

```typescript
function first<T>(items: readonly T[]): T | undefined {
  return items[0];
}

// Constrained generic
function pluck<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Generic with default
interface Cache<T = string> {
  get(key: string): T | undefined;
}
```

## Utility Types

```typescript
interface User {
  id: string;
  name: string;
  email: string;
}

type UserPreview = Pick<User, "id" | "name">;
type UserUpdate = Partial<Omit<User, "id">>;
type ReadonlyUser = Readonly<User>;
type UserRecord = Record<string, User>;
```

## satisfies Operator (TS 4.9+)

```typescript
type Theme = "light" | "dark" | "system";

// `satisfies` checks the literal against the type WITHOUT widening it
const config = {
  theme: "dark",
  retries: 3,
} satisfies { theme: Theme; retries: number };

config.theme; // still narrowed to "dark", not widened to `Theme`
```

## Template Literal Types

```typescript
type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";
type Endpoint = `/api/${string}`;
type RouteKey = `${HttpMethod} ${Endpoint}`;

const route: RouteKey = "GET /api/users"; // type-checked at compile time
```

## Common Mistakes

### Wrong (escape hatches that erase type safety)

```typescript
function process(items: any): any {
  return items.map((i: any) => i.value);
}
```

### Correct (explicit, narrow types)

```typescript
function process<T extends { value: number }>(items: T[]): number[] {
  return items.map((i) => i.value);
}
```

## Quick Reference

| Type | Use Case | Notes |
|------|----------|-------|
| `unknown` | Untyped external input | Safer than `any` -- forces narrowing |
| `never` | Function never returns / exhaustiveness check | Used in `switch` default branches |
| `readonly T[]` | Immutable array parameter | Prevents mutation inside function |
| `as const` | Freeze a literal's inferred type | `[1, 2, 3] as const` -> `readonly [1, 2, 3]` |
| `T extends U ? A : B` | Conditional type | Type-level branching |
| `keyof T` | Union of an object's keys | Used with generics for safe indexing |
| `Awaited<T>` | Unwrap a `Promise<T>` | Mirrors `await` at the type level |
| `satisfies` | Validate without widening | TS 4.9+ |

## Related

- [Classes and Types](../concepts/classes-and-types.md)
- [Clean Architecture](../patterns/clean-architecture.md)
- [Error Handling](../patterns/error-handling.md)
