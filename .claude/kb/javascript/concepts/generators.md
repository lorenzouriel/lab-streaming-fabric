# Generators

> **Purpose**: Generator functions, yield, async generators, and iterators for lazy evaluation
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

Generators (`function*`) produce a sequence of values lazily via `yield`, implementing the
iterator protocol automatically. Async generators (`async function*`) combine this with
`await`, making them the standard way to stream data -- paginated APIs, file reads,
database cursors -- without loading everything into memory.

## The Pattern

```typescript
function* readLines(text: string): Generator<string, void, unknown> {
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (trimmed) yield trimmed;
  }
}

function* filterComments(lines: Iterable<string>): Generator<string> {
  for (const line of lines) {
    if (!line.startsWith("#")) yield line;
  }
}

// Pipeline: compose generators without materializing intermediate arrays
const cleanLines = filterComments(readLines(fileContents));
```

## Generator vs Iterator vs Iterable

| Type | Has `Symbol.iterator` | Has `next()` | Reusable |
|------|:-:|:-:|:-:|
| Iterable (array, string, Map) | Yes | No | Yes |
| Iterator | Yes | Yes | No |
| Generator | Yes | Yes | No |

## yield* (Delegation)

```typescript
function* flatten(nested: number[][]): Generator<number> {
  for (const sublist of nested) {
    yield* sublist;
  }
}

const result = [...flatten([[1, 2], [3, 4], [5]])]; // [1, 2, 3, 4, 5]
```

## Async Generators

```typescript
async function* streamPages<T>(fetchPage: (cursor: string | null) => Promise<{
  items: T[];
  nextCursor: string | null;
}>): AsyncGenerator<T> {
  let cursor: string | null = null;
  do {
    const { items, nextCursor } = await fetchPage(cursor);
    yield* items;
    cursor = nextCursor;
  } while (cursor !== null);
}

// Consume with for-await-of
for await (const item of streamPages(fetchUsersPage)) {
  console.log(item);
}
```

## send() via next(value)

```typescript
function* accumulator(): Generator<number, string, number> {
  let total = 0;
  while (true) {
    const value = yield total;
    if (value == null) break;
    total += value;
  }
  return `Final total: ${total}`;
}

const acc = accumulator();
acc.next();      // { value: 0, done: false }
acc.next(5);      // { value: 5, done: false }
acc.next(3);      // { value: 8, done: false }
```

## Common Mistakes

### Wrong (loading everything into memory)

```typescript
async function getAllRecords(db: Db): Promise<Record[]> {
  return db.fetchAll(); // loads millions of rows into an array
}
```

### Correct (streaming with an async generator)

```typescript
async function* streamRecords(db: Db): AsyncGenerator<Record> {
  const cursor = db.query("SELECT * FROM records");
  for await (const row of cursor) {
    yield row;
  }
}
```

## Generator Pipelines

```typescript
function* readCsvRows(lines: Iterable<string>): Generator<string[]> {
  for (const line of lines) {
    yield line.trim().split(",");
  }
}

function* parseAmounts(rows: Iterable<string[]>): Generator<number> {
  for (const row of rows) {
    const value = Number(row[2]);
    if (!Number.isNaN(value)) yield value;
  }
}

// Compose pipeline -- nothing executes until iteration
const total = [...parseAmounts(readCsvRows(csvLines))].reduce((a, b) => a + b, 0);
```

## Related

- [File Parser](../patterns/file-parser.md)
- [Resource Management](../concepts/resource-management.md)
- [Functional Patterns](../patterns/functional-patterns.md)
