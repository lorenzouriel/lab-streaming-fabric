# C# / .NET Clean Code Knowledge Base

> **Purpose**: Clean code patterns for C# 12/13 and .NET 8/9 -- records, nullable reference types, pattern matching, async/await
> **MCP Validated:** 2026-04-14

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/records.md](concepts/records.md) | `record`/`record struct`, `with` expressions, value equality |
| [concepts/nullable-reference-types.md](concepts/nullable-reference-types.md) | `#nullable enable`, annotations, null-state analysis |
| [concepts/pattern-matching.md](concepts/pattern-matching.md) | `switch` expressions, property/positional/list patterns |
| [concepts/async-await.md](concepts/async-await.md) | `Task`/`ValueTask`, cancellation, `IAsyncEnumerable<T>` |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/clean-architecture.md](patterns/clean-architecture.md) | Solution structure, naming, dependency rules, CPM |
| [patterns/error-handling.md](patterns/error-handling.md) | Exception hierarchy, Result pattern, `IExceptionHandler` |
| [patterns/file-parser.md](patterns/file-parser.md) | Streaming file parsing with iterators and `IAsyncEnumerable<T>` |
| [patterns/functional-patterns.md](patterns/functional-patterns.md) | LINQ, deferred execution, function composition |
| [patterns/real-time-pipelines.md](patterns/real-time-pipelines.md) | Channels, Kafka/Event Hubs clients, gRPC streaming, Polly resilience, runtime tuning |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/dotnet-standards.yaml](specs/dotnet-standards.yaml) | Code standards, analyzer rules, project conventions |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Records** | Declarative, immutable data containers with value equality and `with` expressions |
| **Nullable Reference Types** | Compile-time null-safety via static flow analysis |
| **Pattern Matching** | Exhaustive `switch` expressions over type, shape, and value |
| **Async/Await** | Non-blocking I/O via `Task`, cancellation-aware, `IAsyncEnumerable<T>` for streams |
| **.NET 8** | `TimeProvider`, native AOT (broad support), keyed DI services, frozen collections |
| **.NET 9** | Improved AOT, `Lock` type, params collections, task-based `System.Threading.Channels` improvements |
| **Central Package Management (CPM)** | `Directory.Packages.props` replaces per-project `<PackageReference Version=".."/>` |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/records.md, concepts/nullable-reference-types.md |
| **Intermediate** | concepts/pattern-matching.md, patterns/clean-architecture.md |
| **Advanced** | concepts/async-await.md, patterns/file-parser.md, patterns/functional-patterns.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| dotnet-developer | All files | Write clean, idiomatic C# 12/13 code |
| dotnet-code-reviewer | patterns/clean-architecture.md, specs/dotnet-standards.yaml | Review code quality and security |
| dotnet-specialist | concepts/async-await.md, patterns/clean-architecture.md, patterns/real-time-pipelines.md | ASP.NET Core / EF Core platform depth, Context7-validated |
