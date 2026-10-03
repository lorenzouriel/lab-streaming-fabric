# Ch.1 — Why data engineering needs its own patterns

**Thesis.** Software design patterns (GoF) solve code-structure problems. Data engineering patterns solve *data* problems the GoF never addressed: what happens on retry, on late arrival, on backfill, on producer failure. Teams keep re-solving these from scratch; the book names and codifies them.

**Book structure follows the data flow:** ingest → error management → idempotency → value → flow → security → storage → quality → observability → streaming. Each chapter layers on the previous one.

**Case study:** a blog-analytics platform on a Medallion architecture — Bronze (raw), Silver (cleansed/enriched), Gold (business-ready) — with batch and streaming ingestion paths. Implementations shown in Spark, Airflow, Delta Lake, Flink, Kafka, but the patterns are technology-agnostic.

**Diagnostic questions the book suggests before writing any pipeline:**
- What happens on retry? If "it breaks" → idempotency (ch.4).
- What happens with late data? If "we ignore it" → error management (ch.3) / streaming (ch.11).
- What happens if I backfill three weeks? → idempotency granularity + flow (ch.4, ch.6).
- Who reads a half-written partition? → readiness marker (ch.2).

**Memorable line:** software patterns are the recipes for a maintainable codebase; for data projects that's not enough.

**Master insight (closing of the book):** every problem you hit has already been solved; the pattern gives it a *name*, and the name gives you the vocabulary to communicate, implement, and evolve the solution systematically instead of ad hoc.

**Chapter map**

| Ch | Problem | Answer |
|---|---|---|
| 2 | Moving data is harder than it looks | Full/incremental load, CDC, replication, compaction, readiness, triggers |
| 3 | Errors are inevitable | Dead-letter, dedup, late data, filter interceptor, checkpointing |
| 4 | Retries create duplicates | Overwrite, MERGE, metadata-level cleanup, proxy views |
| 5 | Raw data has no value | Enrich, decorate, aggregate, sessionize, order |
| 6 | Pipelines need coordination | Sequence, fan-in, fan-out, concurrency control |
| 7 | Data must be protected | Anonymize, tokenize, vault, access control, encryption |
| 8 | Layout determines performance | Partition, bucket, sort, table format |
| 9 | Technically correct ≠ correct | Schema, constraint, null, volume, freshness, accuracy validators |
| 10 | Can't trust what you can't see | Metrics, lineage, anomaly detection, SLAs |
| 11 | Unbounded data needs new semantics | Windows, watermarks, stateful processing |
