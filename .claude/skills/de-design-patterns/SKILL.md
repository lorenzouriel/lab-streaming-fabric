---
name: de-design-patterns
description: Pattern advisor based on "Data Engineering Design Patterns" (Bartosz Konieczny, O'Reilly 2025). Names the right pattern for a data pipeline problem, explains the tradeoff, and maps it to the user's stack (SQL Server/T-SQL, Microsoft Fabric/Delta, Databricks/Spark, Airflow, dbt, Kafka/Flink). Use this whenever the user designs, reviews, debugs, or writes about a data pipeline — ingestion (full/incremental/CDC/replication), retries and idempotency, duplicates, late-arriving data, dead-letter handling, backfills, sessionization, joins between streams, fan-in/fan-out orchestration, PII masking and access control, partitioning/bucketing/Z-order, data quality checks, observability/lineage/SLAs, or streaming windows and watermarks. Trigger even if the user doesn't say "pattern" or mention the book — e.g. "my retry creates duplicates", "how should I handle late events", "which table format for Fabric", "review this Airflow DAG", "write a Medium post about idempotent pipelines".
---

# Data Engineering Design Patterns — advisor

The book's thesis: Gang-of-Four patterns keep code maintainable but say nothing about *what happens to the data* on retry, on late arrival, on backfill. Data engineering has its own recurring problems, and naming the solution gives the team a shared vocabulary. This skill applies that vocabulary to the user's actual problem.

The user is a senior data engineer. Skip definitions; lead with the pattern name, why it fits, and what it costs.

## Workflow

1. **Classify the problem** using the index below. Most real questions touch 2–3 chapters (e.g. "duplicates after retry" = error management + idempotency; "late mobile events" = error management + streaming).
2. **Read the matching reference file(s)** in `references/` before answering. Each one has the patterns, gotchas, and a stack-mapping section. Don't answer from the index alone — the gotchas are where the value is.
3. **Answer in this shape** (prose, not headers, unless the user asked for a teaching/explain format):
   - Name the pattern(s) and the chapter they come from, in one line.
   - Say why it fits *this* situation and what the alternative pattern would be and when you'd pick it instead.
   - Give the concrete implementation in the user's stack — T-SQL, Fabric/Delta, Databricks, Airflow, dbt — not the book's generic Spark example unless that's what they run.
   - Call out the gotcha the book flags for that pattern (e.g. "MERGE without `is_deleted` in the INSERT condition inserts tombstones on first run").
4. **Push back** if the user's proposed approach matches a known anti-pattern from the book (unbounded incremental window, DELETE at scale for idempotency, MIN-based watermark, task-based coupling across teams, high-cardinality partitioning). Say so directly and name the pattern that fixes it.

When the user is writing (Medium article, newsletter), use this skill as the source of correct pattern names and tradeoffs, and let the writing skills own the voice. Cite the book once as the source of the vocabulary; don't reproduce its prose.

## Problem → pattern index

| User's problem sounds like | Pattern(s) | Read |
|---|---|---|
| Load whole table each run; empty window during swap | Full Loader + Proxy (view swap) | `references/02-ingestion.md`, `04-idempotency.md` |
| Only load new rows; backfill silently became full load | Incremental Loader (bounded window) | `02-ingestion.md` |
| Sub-minute latency, need hard deletes | CDC (Debezium / Delta CDF / SQL Server CDC) | `02-ingestion.md` |
| Copy prod → staging, strip PII | Passthrough / Transformation Replicator | `02-ingestion.md`, `07-security.md` |
| Thousands of tiny Parquet files, slow file listing | Compactor (OPTIMIZE + VACUUM) | `02-ingestion.md`, `08-storage.md` |
| Downstream job reads a half-written partition | Readiness Marker | `02-ingestion.md`, `06-flow.md` |
| Vendor drops files irregularly | External Trigger (event-driven) | `02-ingestion.md` |
| One bad record kills the stream | Dead-Letter | `03-error-management.md` |
| Duplicates from at-least-once delivery | Windowed Deduplicator | `03-error-management.md` |
| Events arrive late (mobile, buffering) | Late Data Detector + Static/Dynamic Integrator | `03-error-management.md`, `11-streaming.md` |
| Output volume dropped after a release | Filter Interceptor | `03-error-management.md` |
| Streaming job restarts from the beginning | Checkpointer | `03-error-management.md` |
| Retry/backfill creates duplicates | Fast Metadata Cleaner / Data Overwrite / Merger | `04-idempotency.md` |
| CDC deltas into a target table | Merger (MERGE with soft-delete) | `04-idempotency.md` |
| Enrich events with a dimension that changes | Static Joiner (SCD2, execution-time join) | `05-value.md` |
| Join two streams | Dynamic Joiner (watermarked buffers) | `05-value.md` |
| Aggregation is slow / skewed | Distributed vs Local Aggregator, salting | `05-value.md`, `08-storage.md` |
| Sessionize events (batch or stream) | Incremental / Stateful Sessionizer | `05-value.md`, `11-streaming.md` |
| Preserve per-entity ordering into Kinesis/ES/Dynamo | Bin Pack / FIFO Orderer | `05-value.md` |
| Split a monolithic DAG; cross-team dependencies | Local / Isolated Sequencer | `06-flow.md` |
| 24 hourly tasks → 1 daily task | Aligned / Unaligned Fan-In | `06-flow.md` |
| Route by condition (new week? new partition) | Exclusive Choice | `06-flow.md` |
| Backfills overload the cluster | Concurrency Control | `06-flow.md` |
| Mask/hash/tokenize PII; secrets in config | Anonymizer / Tokenizer / Vault | `07-security.md` |
| Different users see different rows/columns | Coarse/Fine-Grained Accessor | `07-security.md` |
| Which table format; partition vs bucket vs Z-order | Partitioner / Bucket / Sorter / Format Selector | `08-storage.md` |
| Schema drift, nulls, volume drop, stale table | Schema / Null / Volume / Freshness Validator | `09-quality.md` |
| Warehouse total ≠ finance report | Accuracy Validator | `09-quality.md` |
| What to alert on; lineage; SLAs | Metrics Collectors, Lineage Tracker, Anomaly Detector, SLA Tracker | `10-observability.md` |
| Tumbling vs sliding vs session; watermarks; state TTL | Streaming windows, Stateful processing | `11-streaming.md` |

## Cross-cutting rules the book repeats

These show up in several chapters; apply them regardless of which pattern you pick.

- **Idempotency key = immutable schedule time**, never wall-clock. In Airflow that's `{{ ds }}` / `data_interval_start`; in SQL Server jobs pass the logical run date as a parameter.
- **Idempotency granularity = backfill granularity.** Weekly sub-tables mean replaying a day costs a week.
- **Bound every window**: ingestion windows, dedup windows (watermark), lookback windows, state TTL. Unbounded means silent full loads or OOM.
- **Push, don't pull, across boundaries**: prod pushes to staging; producers signal readiness, consumers poll a marker (data-based coupling), not each other's tasks.
- **Compaction without VACUUM reclaims nothing.** Same for overwrite in Delta — old files stay until VACUUM.
- **Checkpointing gives at-least-once.** Exactly-once needs idempotent writes on top.
- **Test intermediate tables, not just Gold.** Bugs are cheaper in Silver.

## Stack mapping cheatsheet

| Book primitive | SQL Server / T-SQL | Fabric / Delta / Databricks | Orchestration |
|---|---|---|---|
| Overwrite partition | `TRUNCATE TABLE ... WITH (PARTITIONS (n))` or `SWITCH PARTITION`; `sp_rename` swap | `INSERT OVERWRITE` / `replaceWhere` | Airflow `{{ ds }}` |
| Upsert with deletes | `MERGE ... WHEN MATCHED AND is_deleted=1 THEN DELETE` (mind the MERGE bugs; `HOLDLOCK`) | `MERGE INTO` Delta | dbt `incremental`, `merge` strategy |
| CDC | `sys.sp_cdc_enable_table`, `cdc.fn_cdc_get_net_changes_*`; or Change Tracking for keys-only | Delta CDF `table_changes()`; Fabric Mirroring | Debezium SQL Server connector |
| Readiness marker | Control table row / `_SUCCESS` file in ADLS | Delta commit | Airflow `FileSensor(mode='reschedule')` |
| Compaction | Index rebuild / partition maintenance | `OPTIMIZE ... ZORDER BY`, `VACUUM`; Fabric auto-compaction settings | Daily maintenance DAG |
| Dedup | `ROW_NUMBER() OVER (PARTITION BY key ORDER BY ...)` | `dropDuplicates` + `withWatermark` | — |
| Row/column security | `CREATE SECURITY POLICY` + predicate function; column `GRANT`; Dynamic Data Masking | Unity Catalog row filters / column masks; Fabric OneLake security | — |
| Quality tests | CHECK constraints; custom procs | Delta constraints, `elementary` | dbt tests |
| Lineage | Extended Events / query store is not lineage — use OpenLineage from Airflow/dbt | Unity Catalog lineage; Fabric lineage view | OpenLineage |

## Reference files

`references/01-intro.md` — the book's framing and Medallion case study (read for articles/overviews)
`references/02-ingestion.md` through `references/11-streaming.md` — one per chapter: patterns, gotchas, when-to-use, stack mapping.
