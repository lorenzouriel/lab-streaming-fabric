# File Parser

> **Purpose**: Streaming file parsing with iterators, `System.IO.Pipelines`, and `IAsyncEnumerable<T>` for memory-efficient processing
> **MCP Validated:** 2026-04-14

## When to Use

- Processing files too large to load fully into memory
- Streaming CSV, JSON Lines, or log files
- Building ETL pipelines with composable transformation stages

## Implementation

```csharp
public sealed record ParsedRecord(string Source, int LineNumber, IReadOnlyDictionary<string, string> Data);

public static IEnumerable<ParsedRecord> ParseCsv(string path)
{
    using var reader = new StreamReader(path);
    using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);

    csv.Read();
    csv.ReadHeader();
    var lineNumber = 1;
    while (csv.Read())
    {
        lineNumber++;
        var record = csv.HeaderRecord!.ToDictionary(h => h, h => csv.GetField(h) ?? "");
        yield return new ParsedRecord(path, lineNumber, record);
    }
}

public static async IAsyncEnumerable<ParsedRecord> ParseJsonLinesAsync(
    string path,
    [EnumeratorCancellation] CancellationToken ct = default)
{
    using var reader = new StreamReader(path);
    var lineNumber = 0;
    string? line;
    while ((line = await reader.ReadLineAsync(ct)) is not null)
    {
        lineNumber++;
        if (string.IsNullOrWhiteSpace(line)) continue;

        var data = JsonSerializer.Deserialize<Dictionary<string, string>>(line)
            ?? throw new InvalidOperationException($"Empty JSON at line {lineNumber}");
        yield return new ParsedRecord(path, lineNumber, data);
    }
}
```

## Transformation Pipeline (LINQ over Iterators)

```csharp
public static IEnumerable<ParsedRecord> FilterRecords(
    IEnumerable<ParsedRecord> records, string key, string value) =>
    records.Where(r => r.Data.GetValueOrDefault(key) == value);

public static IEnumerable<IReadOnlyList<ParsedRecord>> Batch(
    IEnumerable<ParsedRecord> records, int batchSize)
{
    var batch = new List<ParsedRecord>(batchSize);
    foreach (var record in records)
    {
        batch.Add(record);
        if (batch.Count == batchSize)
        {
            yield return batch;
            batch = new List<ParsedRecord>(batchSize);
        }
    }
    if (batch.Count > 0) yield return batch;
}
```

## Example Usage

```csharp
public static int ProcessSalesReport(string inputPath, string outputPath)
{
    var records = ParseCsv(inputPath);
    var active = FilterRecords(records, "status", "active");

    var count = 0;
    using var writer = new StreamWriter(outputPath);
    foreach (var batch in Batch(active, batchSize: 50))
    {
        foreach (var record in batch)
        {
            writer.WriteLine(JsonSerializer.Serialize(record.Data));
            count++;
        }
    }
    return count;
}
```

## Multi-Format Dispatch

```csharp
private static readonly Dictionary<string, Func<string, IEnumerable<ParsedRecord>>> Parsers = new()
{
    [".csv"] = ParseCsv,
    [".log"] = path => ParseLog(path),
};

public static IEnumerable<ParsedRecord> AutoParse(string path)
{
    var ext = Path.GetExtension(path).ToLowerInvariant();
    if (!Parsers.TryGetValue(ext, out var parser))
        throw new NotSupportedException($"No parser registered for {ext}");

    return parser(path);
}
```

## High-Throughput Reads with `System.IO.Pipelines`

```csharp
public static async Task ReadLinesAsync(Stream stream, Func<ReadOnlySequence<byte>, Task> onLine, CancellationToken ct)
{
    var reader = PipeReader.Create(stream);
    while (true)
    {
        var result = await reader.ReadAsync(ct);
        var buffer = result.Buffer;

        while (TryReadLine(ref buffer, out var line))
        {
            await onLine(line);
        }

        reader.AdvanceTo(buffer.Start, buffer.End);
        if (result.IsCompleted) break;
    }
    await reader.CompleteAsync();
}
```

Use `System.IO.Pipelines` only for genuinely high-throughput scenarios (large log ingestion,
network protocols) — for everyday file parsing, `StreamReader` + iterators is simpler and
sufficient.

## Error Recovery

```csharp
public static IEnumerable<ParsedRecord> SafeParse(string path)
{
    using var reader = new StreamReader(path);
    var lineNumber = 0;
    string? line;
    while ((line = reader.ReadLine()) is not null)
    {
        lineNumber++;
        Dictionary<string, string>? data = null;
        try
        {
            data = JsonSerializer.Deserialize<Dictionary<string, string>>(line);
        }
        catch (JsonException)
        {
            continue; // skip malformed line, keep the stream flowing
        }
        if (data is not null)
            yield return new ParsedRecord(path, lineNumber, data);
    }
}
```

## See Also

- [Async/Await](../concepts/async-await.md)
- [Functional Patterns](functional-patterns.md)
- [Error Handling](error-handling.md)
