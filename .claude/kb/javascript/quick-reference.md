# JavaScript/TypeScript Clean Code Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-03-26

## Interface vs Type vs Class

| Need | Choose | Why |
|------|--------|-----|
| Object shape / public contract | `interface` | Declaration merging, clearer error messages |
| Union, tuple, mapped/conditional type | `type` | `interface` can't express unions |
| Behavior + encapsulated state | `class` with `#private` fields | Needs `instanceof`, methods, invariants |
| Fixed set of literal values | `as const` tuple + derived union | Safer and more flexible than `enum` |

## Type Hint Patterns (TS 5.x)

| Pattern | Syntax | Notes |
|---------|--------|-------|
| Union | `A \| B` | Discriminate with a shared literal field |
| Optional | `T \| undefined` or `field?: T` | `strictNullChecks` required (on by default with `strict`) |
| Generic with constraint | `function f<T extends U>(x: T)` | Narrows what `T` can be |
| Narrow without widening | `satisfies` | TS 4.9+ |
| Freeze a literal's type | `as const` | Deep, structural |
| Untyped external input | `unknown` | Forces narrowing before use, unlike `any` |
| Exhaustiveness check | `never` in a `switch` default | Compiler errors if a union case is missed |
| Unwrap a Promise type | `Awaited<T>` | Mirrors `await` at the type level |

## Generator vs Array

| Use Case | Choose | Why |
|----------|--------|-----|
| Need random access / `.length` | Array | Generators have neither |
| Large or infinite sequence | Generator (`function*`) | Lazy, no full materialization |
| Async paginated source | Async generator (`async function*`) | Pairs naturally with `for await...of` |
| Transform + filter pipeline | Chained generators | Memory efficient, nothing runs until iterated |

## Resource Management Patterns

| Pattern | Use Case | Availability |
|---------|----------|--------------|
| `try/finally` | Guaranteed cleanup, any target | Always |
| `using x = ...` | Sync disposable resource | TS 5.2+ / ES2026 |
| `await using x = ...` | Async disposable resource (DB conn, lock) | TS 5.2+ / ES2026 |
| `AbortController` | Cancel fetch / long-running async work | Always (Node 16+, all browsers) |
| `AbortSignal.timeout(ms)` | Auto-cancel after a duration | Node 18+ |

## Runtime and Tooling (2026)

| Tool | Purpose |
|------|---------|
| `pnpm` | Fast, disk-efficient package manager (preferred over npm for monorepos) |
| `vitest` | Fast unit test runner, Jest-compatible API, native ESM/TS |
| `tsx` | Run TypeScript files directly without a build step |
| `eslint` + `typescript-eslint` | Linting with type-aware rules |
| `prettier` | Opinionated formatting, no debate |
| `zod` / `valibot` | Runtime schema validation with inferred static types |
| `esbuild` / `tsup` | Fast bundling for libraries |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Plain data container | `interface` with `readonly` fields |
| Immutable config | `interface` + `as const` for literal fields |
| Data with runtime validation | `zod` schema, infer the type with `z.infer` |
| Return type is an error-or-value | `Result<T, E>` discriminated union |
| Parse a large file line by line | Async generator over a Node stream |
| Manage a resource lifecycle | `using` / `await using`, or `try/finally` |
| Cancel an in-flight async operation | `AbortController` |
| Chain transformations lazily | Generator pipeline |
| Catch specific errors only | `catch (e) { if (e instanceof X) ... }` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `any` | `unknown` + narrowing, or a precise type |
| `== ` | `===` (avoids type coercion surprises) |
| `var` | `const` by default, `let` when reassignment is needed |
| Empty `catch {}` | `catch (e) { if (e instanceof KnownError) ...; else throw e; }` |
| Mixing CommonJS `require` and ESM `import` | Commit to ESM (`"type": "module"`) |
| `interface IUser` (Hungarian notation) | `interface User` |
| Mutating array/object parameters | Return a new value (spread, `.map`, `.filter`) |
| Floating (unawaited) promises | `await` them or lint with `no-floating-promises` |
| `enum` for simple constant sets | `as const` tuple + derived union type |

## Streaming Consumer Checklist (KafkaJS)

| Practice | Config/API |
|----------|------------|
| Manual offset commit | `autoCommit: false` + `resolveOffset()` after handling |
| Bounded concurrency per batch | `eachBatch` + `p-limit`, not `eachMessage` with unbounded `Promise.all` |
| Idempotent handler | Upsert on natural key, not framework-level exactly-once |
| Schema validation at the edge | `zod`/`valibot` parse on deserialize; reject -> DLQ |
| Graceful shutdown | `await consumer.disconnect()` on `SIGTERM`/`SIGINT` before exit |
| CPU-heavy transforms | Offload to `worker_threads` or use `node-rdkafka` for high throughput |

See [patterns/streaming-pipelines.md](patterns/streaming-pipelines.md) for the full guidance.

## Related Documentation

| Topic | Path |
|-------|------|
| Type hints deep dive | `concepts/type-hints.md` |
| Classes and types | `concepts/classes-and-types.md` |
| Error handling patterns | `patterns/error-handling.md` |
| Full Index | `index.md` |
