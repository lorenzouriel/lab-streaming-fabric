# File Parser

> **Purpose**: File parsing patterns using async generators and Node streams for memory-efficient processing
> **MCP Validated:** 2026-02-17

## When to Use

- Processing large files that don't fit in memory
- Streaming CSV, JSON Lines, or log files
- Building ETL pipelines with transformation stages

## Implementation

```typescript
import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";

interface ParsedRecord {
  readonly source: string;
  readonly lineNumber: number;
  readonly data: Record<string, string>;
}

async function* parseCsv(path: string): AsyncGenerator<ParsedRecord> {
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  let header: string[] | null = null;
  let lineNumber = 0;

  for await (const line of rl) {
    lineNumber++;
    const cells = line.split(",");
    if (header === null) {
      header = cells;
      continue;
    }
    const data = Object.fromEntries(header.map((key, i) => [key, cells[i] ?? ""]));
    yield { source: path, lineNumber, data };
  }
}

async function* parseJsonl(path: string): AsyncGenerator<ParsedRecord> {
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  let lineNumber = 0;

  for await (const line of rl) {
    lineNumber++;
    const trimmed = line.trim();
    if (trimmed) yield { source: path, lineNumber, data: JSON.parse(trimmed) };
  }
}
```

## Transformation Pipeline

```typescript
async function* filterRecords(
  records: AsyncGenerator<ParsedRecord>,
  key: string,
  value: string,
): AsyncGenerator<ParsedRecord> {
  for await (const record of records) {
    if (record.data[key] === value) yield record;
  }
}

async function* batchRecords(
  records: AsyncGenerator<ParsedRecord>,
  batchSize = 100,
): AsyncGenerator<ParsedRecord[]> {
  let batch: ParsedRecord[] = [];
  for await (const record of records) {
    batch.push(record);
    if (batch.length >= batchSize) {
      yield batch;
      batch = [];
    }
  }
  if (batch.length > 0) yield batch;
}
```

## Configuration

| Setting | Default | Description |
|---------|---------|--------------|
| `crlfDelay` | `Infinity` | Treat `\r\n` as a single newline, avoiding split lines on Windows files |
| `batchSize` | `100` | Records per batch when writing downstream (DB inserts, API calls) |
| `highWaterMark` | `64 * 1024` | Stream buffer size in bytes (`createReadStream` option) |

## Example Usage

```typescript
import { createWriteStream } from "node:fs";

async function processSalesReport(inputPath: string, outputPath: string): Promise<number> {
  const records = parseCsv(inputPath);
  const active = filterRecords(records, "status", "active");
  const out = createWriteStream(outputPath);
  let count = 0;

  for await (const batch of batchRecords(active, 50)) {
    for (const record of batch) {
      out.write(JSON.stringify(record.data) + "\n");
      count++;
    }
  }
  out.end();
  return count;
}
```

## Multi-Format Parser

```typescript
import { extname } from "node:path";

const PARSERS: Record<string, (path: string) => AsyncGenerator<ParsedRecord>> = {
  ".csv": parseCsv,
  ".jsonl": parseJsonl,
};

async function* autoParse(path: string): AsyncGenerator<ParsedRecord> {
  const parser = PARSERS[extname(path).toLowerCase()];
  if (!parser) throw new Error(`No parser registered for ${extname(path)}`);
  yield* parser(path);
}
```

## Error Recovery

```typescript
async function* safeParse(path: string): AsyncGenerator<ParsedRecord> {
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  let lineNumber = 0;

  for await (const line of rl) {
    lineNumber++;
    try {
      yield { source: path, lineNumber, data: JSON.parse(line.trim()) };
    } catch (e) {
      logger.warn(`Skipping line ${lineNumber} in ${path}: ${e}`);
    }
  }
}
```

## See Also

- [Generators](../concepts/generators.md)
- [Resource Management](../concepts/resource-management.md)
- [Error Handling](../patterns/error-handling.md)
