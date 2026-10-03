# Error Handling

> **Purpose**: Custom Error hierarchy, async error handling, and recovery patterns for robust TypeScript code
> **MCP Validated:** 2026-02-17

## When to Use

- Defining domain-specific error hierarchies
- Building resilient services and pipelines with recovery
- Wrapping third-party library / fetch errors
- Implementing retry and fallback patterns

## Implementation

### Custom Error Hierarchy

```typescript
class AppError extends Error {
  readonly code: string;

  constructor(message: string, code = "UNKNOWN") {
    super(message);
    this.name = "AppError";
    this.code = code;
    Object.setPrototypeOf(this, new.target.prototype); // fix instanceof across ES5 targets
  }
}

class ValidationError extends AppError {
  constructor(
    message: string,
    readonly fieldName = "",
  ) {
    super(message, "VALIDATION_ERROR");
    this.name = "ValidationError";
  }
}

class NotFoundError extends AppError {
  constructor(
    readonly resource: string,
    readonly identifier: string,
  ) {
    super(`${resource} not found: ${identifier}`, "NOT_FOUND");
    this.name = "NotFoundError";
  }
}

class ExternalServiceError extends AppError {
  constructor(
    readonly service: string,
    readonly statusCode?: number,
  ) {
    super(`Service ${service} failed (status=${statusCode})`, "EXTERNAL_ERROR");
    this.name = "ExternalServiceError";
  }
}
```

### Exception Handling Best Practices

```typescript
import { logger } from "./logger.js";

async function processRecord(record: Record<string, unknown>) {
  try {
    const validated = validate(record);
    return await enrich(validated);
  } catch (e) {
    if (e instanceof ValidationError) {
      logger.warn(`Validation failed for field ${e.fieldName}: ${e.message}`);
      throw e;
    }
    if (e instanceof ExternalServiceError) {
      logger.error(`Service ${e.service} unavailable: ${e.message}`);
      throw e;
    }
    logger.error(`Unexpected error processing record: ${e}`);
    throw new AppError(`Processing failed: ${e}`, "INTERNAL");
  }
}
```

## Error Chaining (cause)

```typescript
async function loadConfig(path: string): Promise<unknown> {
  try {
    const raw = await readFile(path, "utf-8");
    return JSON.parse(raw);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      throw new NotFoundError("config_file", path);
    }
    throw new ValidationError(`Invalid JSON in ${path}`, "config", { cause: e });
  }
}
```

## Retry Pattern

```typescript
interface RetryOptions {
  maxAttempts?: number;
  delayMs?: number;
  backoff?: number;
}

async function retry<T>(fn: () => Promise<T>, options: RetryOptions = {}): Promise<T> {
  const { maxAttempts = 3, delayMs = 1000, backoff = 2 } = options;
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (e) {
      lastError = e;
      if (attempt === maxAttempts) break;
      await new Promise((r) => setTimeout(r, delayMs * backoff ** (attempt - 1)));
    }
  }
  throw lastError;
}
```

## Result Pattern (No Exceptions)

```typescript
type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E };

function parseInt10(raw: string): Result<number> {
  const value = Number(raw);
  return Number.isInteger(value) ? { ok: true, value } : { ok: false, error: `Cannot parse '${raw}' as int` };
}

// Usage with narrowing
const result = parseInt10("42");
if (result.ok) {
  console.log(`Parsed: ${result.value}`);
} else {
  console.log(`Error: ${result.error}`);
}
```

## Async Error Handling with Promise.allSettled

```typescript
async function fetchAll(urls: string[]) {
  const results = await Promise.allSettled(urls.map((url) => fetch(url)));

  const succeeded = results.filter((r) => r.status === "fulfilled");
  const failed = results.filter((r) => r.status === "rejected");

  if (failed.length > 0) {
    logger.warn(`${failed.length}/${urls.length} requests failed`);
  }
  return succeeded;
}
```

## Common Mistakes

### Wrong

```typescript
try {
  compute();
} catch (e) {
  // swallows everything, including programmer errors and typos
}
```

### Correct

```typescript
try {
  compute();
} catch (e) {
  if (e instanceof ValidationError) {
    logger.warn(`Computation failed: ${e.message}`);
  } else {
    throw e; // don't swallow errors you don't recognize
  }
}
```

## Exception Quick Reference

| Principle | Practice |
|-----------|----------|
| Narrow with `instanceof` | Check specific error classes, not a bare `catch` swallow |
| Chain always | Pass `{ cause: original }` to the new `Error` |
| Log at boundaries | Log once where you handle, not where you throw |
| Fail fast | Validate inputs early, throw immediately |
| Custom hierarchy | One base `AppError`, specific subclasses |
| Never swallow silently | Empty `catch {}` hides real bugs |

## See Also

- [Resource Management](../concepts/resource-management.md)
- [Clean Architecture](../patterns/clean-architecture.md)
- [File Parser](../patterns/file-parser.md)
