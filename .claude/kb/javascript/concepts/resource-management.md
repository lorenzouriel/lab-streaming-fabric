# Resource Management

> **Purpose**: try/finally, AbortController, and the `using`/`await using` declarations for guaranteed cleanup
> **Confidence**: 0.90
> **MCP Validated:** 2026-02-17

## Overview

JavaScript guarantees cleanup through `try/finally`, cancellation through `AbortController`,
and -- as of ES2026 / TypeScript 5.2+ -- through Explicit Resource Management (`using` and
`await using`), which is the closest equivalent to Python's `with` statement: it calls
`[Symbol.dispose]()` (or `[Symbol.asyncDispose]()`) automatically when the block exits,
even on an exception.

## The Pattern

```typescript
class FileHandle implements Disposable {
  private fd: number;

  constructor(path: string) {
    this.fd = openSync(path, "r");
  }

  read(): Buffer {
    return readFileSync(this.fd);
  }

  [Symbol.dispose](): void {
    closeSync(this.fd);
  }
}

function readConfig(path: string): Buffer {
  using handle = new FileHandle(path); // disposed automatically at block end
  return handle.read();
} // fd closed here, even if read() throws
```

## try/finally (Baseline, Always Available)

```typescript
function withTimer<T>(label: string, fn: () => T): T {
  const start = performance.now();
  try {
    return fn();
  } finally {
    console.log(`${label}: ${(performance.now() - start).toFixed(3)}ms`);
  }
}
```

## await using for Async Resources

```typescript
class DbConnection implements AsyncDisposable {
  static async connect(connStr: string): Promise<DbConnection> {
    const conn = new DbConnection();
    await conn.open(connStr);
    return conn;
  }

  async [Symbol.asyncDispose](): Promise<void> {
    await this.close();
  }
}

async function runQuery(connStr: string, sql: string) {
  await using conn = await DbConnection.connect(connStr);
  return conn.query(sql);
} // conn closed automatically, including on thrown errors
```

## AbortController for Cancellation

| Utility | Purpose | Example |
|---------|---------|---------|
| `AbortController` | Create a cancellable operation | `const ctrl = new AbortController()` |
| `signal.aborted` | Check cancellation state | `if (signal.aborted) return` |
| `AbortSignal.timeout(ms)` | Auto-abort after a duration | `fetch(url, { signal: AbortSignal.timeout(5000) })` |
| `signal.addEventListener("abort", fn)` | React to cancellation | Cleanup on abort |

```typescript
async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}
```

## Common Mistakes

### Wrong (no cleanup on exception)

```typescript
const fd = openSync("data.csv", "r");
const data = readFileSync(fd); // if this throws, fd is never closed
closeSync(fd);
```

### Correct (guaranteed cleanup)

```typescript
try {
  const fd = openSync("data.csv", "r");
  try {
    return readFileSync(fd);
  } finally {
    closeSync(fd);
  }
} catch (e) {
  // handle
}
```

## Multiple Resources

```typescript
function mergeFiles(paths: string[], output: string): void {
  using outFile = new FileHandle(output, "w");
  for (const path of paths) {
    using inFile = new FileHandle(path, "r");
    outFile.write(inFile.read());
  } // each inFile disposed at the end of its loop iteration
}
```

## Related

- [Generators](../concepts/generators.md)
- [File Parser](../patterns/file-parser.md)
- [Error Handling](../patterns/error-handling.md)
