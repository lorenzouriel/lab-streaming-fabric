# Clean Architecture

> **Purpose**: Clean code structure, naming conventions, module organization, and modern tooling for TypeScript/JavaScript projects
> **MCP Validated:** 2026-03-26

## When to Use

- Starting a new Node.js, frontend, or full-stack TypeScript project
- Refactoring legacy JavaScript for maintainability
- Establishing team coding standards
- Structuring packages with clear boundaries

## Implementation

### Project Structure

```text
src/
  domain/              # Business logic, no external dependencies
    models.ts          # Interfaces, domain entities
    errors.ts           # Custom error hierarchy
    services.ts         # Core business rules
  adapters/            # External integrations
    database.ts         # DB access layer
    api-client.ts        # HTTP clients
    file-reader.ts        # File I/O
  application/          # Use cases, orchestration
    use-cases.ts          # Application-level workflows
    interfaces.ts         # Ports (interfaces) implemented by adapters
  config.ts              # Settings, environment
tests/
  domain/
  adapters/
  application/
package.json
tsconfig.json
```

### Dependency Rule

```text
domain  <--  application  <--  adapters
(pure)       (orchestrates)     (implements)

Inner layers NEVER import from outer layers.
Adapters depend on application interfaces (ports).
Domain has zero external dependencies (no fetch, no fs, no DB clients).
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| File (module) | `kebab-case.ts` | `file-reader.ts` |
| Class / Interface / Type | `PascalCase` | `InvoiceParser`, `Invoice` |
| Function / variable | `camelCase` | `parseInvoice()` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| Private class field | `#leadingHash` or `private` | `#internalState` |
| Boolean | `is/has/can/should` prefix | `isValid`, `hasErrors` |
| React component file | `PascalCase.tsx` | `UserCard.tsx` |

## Function Design

```typescript
interface UserRecord {
  username: string;
  status: string;
  age: string;
}

// GOOD: single responsibility, explicit types, descriptive name
function extractActiveUsers(records: UserRecord[], minAge = 18): string[] {
  return records
    .filter((r) => r.status === "active" && Number(r.age) >= minAge)
    .map((r) => r.username);
}

// BAD: vague name, no types, multiple responsibilities
function process(data: any, flag = true) {
  const results = [];
  for (const d of data) {
    if (flag) {
      if (d.status === "active") results.push(d.username);
    } else {
      results.push(d);
    }
  }
  return results;
}
```

## Interface Segregation (Ports and Adapters)

```typescript
interface Reader {
  read(path: string): AsyncGenerator<Record<string, string>>;
}

interface Writer {
  write(records: Record<string, string>[], path: string): Promise<number>;
}

class CsvReader implements Reader {
  async *read(path: string): AsyncGenerator<Record<string, string>> {
    const content = await readFile(path, "utf-8");
    for (const row of parseCsv(content)) yield row;
  }
}

async function processData(reader: Reader, writer: Writer, src: string, dst: string) {
  const records: Record<string, string>[] = [];
  for await (const row of reader.read(src)) records.push(row);
  return writer.write(records, dst);
}
```

## Configuration Pattern

```typescript
interface AppConfig {
  readonly dbHost: string;
  readonly dbPort: number;
  readonly debug: boolean;
  readonly maxWorkers: number;
}

function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const maxWorkers = Number(env.MAX_WORKERS ?? "4");
  if (maxWorkers < 1) throw new Error("MAX_WORKERS must be >= 1");

  return {
    dbHost: env.DB_HOST ?? "localhost",
    dbPort: Number(env.DB_PORT ?? "5432"),
    debug: (env.DEBUG ?? "").toLowerCase() === "true",
    maxWorkers,
  };
}
```

## Module System

| Setting | Value | Why |
|---------|-------|-----|
| `package.json` `"type"` | `"module"` | Use native ESM (`import`/`export`), not CommonJS `require` |
| `tsconfig.json` `"module"` | `"NodeNext"` or `"ESNext"` | Aligns TS module resolution with Node's ESM runtime |
| Extensionless imports | Avoid; use `.js` in relative ESM imports | Node's ESM resolver requires explicit extensions |
| Barrel files (`index.ts` re-exports) | Use sparingly | Can create circular imports and hurt tree-shaking |

## Modern Project Setup

```bash
# Init with a package manager (pnpm shown; npm/yarn work the same way)
pnpm init
pnpm add zod
pnpm add -D typescript vitest eslint prettier @types/node

# Type-check without emitting
pnpm tsc --noEmit

# Run tests
pnpm vitest run
```

### tsconfig.json (strict baseline)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["src"]
}
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Clean Alternative |
|-------------|---------|-------------------|
| God object / mega-module (1000+ lines) | Untestable, unclear responsibility | Split into focused modules |
| Magic numbers/strings | Unclear intent | Named constants or literal union types |
| Deep nesting (3+ levels) | Hard to read | Early returns, extract functions |
| `any` used to silence the compiler | Erases type safety | `unknown` + narrowing, or a precise type |
| Circular imports | Architectural issue, breaks tree-shaking | Dependency inversion, extract shared types |
| `console.log` debugging left in | Not production-safe | Structured logger (`pino`, `winston`) |
| Mixing CommonJS `require` and ESM `import` | Fragile interop, breaks bundlers | Pick ESM and commit to it |
| Default exports everywhere | Harder to refactor, poor autocomplete | Prefer named exports |

## See Also

- [Classes and Types](../concepts/classes-and-types.md)
- [Error Handling](../patterns/error-handling.md)
- [Type Hints](../concepts/type-hints.md)
