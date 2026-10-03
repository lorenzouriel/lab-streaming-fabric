# JavaScript/TypeScript Clean Code Knowledge Base

> **Purpose**: Clean code patterns for modern JavaScript/TypeScript -- types, generators, async, module structure
> **MCP Validated:** 2026-03-26

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/classes-and-types.md](concepts/classes-and-types.md) | Interfaces vs types vs classes, readonly, as const, structural typing |
| [concepts/type-hints.md](concepts/type-hints.md) | Type annotations, generics, utility types, discriminated unions, satisfies |
| [concepts/generators.md](concepts/generators.md) | Generator functions, yield, async generators, for-await-of |
| [concepts/resource-management.md](concepts/resource-management.md) | try/finally, AbortController, using/await using |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/file-parser.md](patterns/file-parser.md) | File parsing with async generators and Node streams |
| [patterns/clean-architecture.md](patterns/clean-architecture.md) | Clean code structure, naming, module organization, tooling |
| [patterns/error-handling.md](patterns/error-handling.md) | Error hierarchy, custom errors, async recovery patterns |
| [patterns/functional-patterns.md](patterns/functional-patterns.md) | Array methods, immutability, composition, currying |
| [patterns/streaming-pipelines.md](patterns/streaming-pipelines.md) | KafkaJS consumer/producer patterns, backpressure, idempotency, DLQ, graceful shutdown |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/javascript-standards.yaml](specs/javascript-standards.yaml) | Code standards, ESLint/Prettier rules, project conventions |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Types** | Static typing with interfaces, generics, discriminated unions, utility types |
| **Classes and Types** | Interfaces/readonly for data, classes reserved for behavior + state |
| **Generators** | Lazy evaluation and streaming with `function*` and `async function*` |
| **Resource Management** | Guaranteed cleanup via try/finally, AbortController, using/await using |
| **ESM** | Native ES modules as the default module system (`"type": "module"`) |
| **Structural typing** | TypeScript types by shape, not declared inheritance -- no `implements` required |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/classes-and-types.md, concepts/type-hints.md |
| **Intermediate** | concepts/generators.md, patterns/clean-architecture.md |
| **Advanced** | patterns/file-parser.md, patterns/functional-patterns.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| javascript-developer | All files | Write clean, idiomatic JavaScript/TypeScript code |
| code-reviewer | patterns/clean-architecture.md, specs/javascript-standards.yaml | Review code quality |
| code-documenter | concepts/type-hints.md | JSDoc / TSDoc generation from types |

## MCP Fallback

For npm package APIs, framework-specific patterns (React, Next.js, Express), or syntax
newer than this KB's last validation date, query Context7 (`resolve-library-id` then
`query-docs`) rather than guessing -- the npm ecosystem moves faster than any static KB.
