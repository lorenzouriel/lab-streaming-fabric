# Ch.3 — Error Management patterns

"Nothing is certain except errors and data quality issues." You inherit producers' mistakes: network blips → late data, retries → duplicates, schema drift → parse failures. Five failure classes, five distinct defenses — no single catch-all.

## Dead-Letter
Don't crash the stream on one bad record; route it to a side store (Kafka topic, storage path, separate Delta table). Implementation: try/catch around processing, side output (Flink `OutputTag`, Spark `foreachBatch` split, SQL `TRY_CAST`/`TRY_CONVERT` + `WHERE IS NULL` branch).
- Monitor the dead-letter rate. Spike above threshold → alert or stop; otherwise you're silently producing garbage.
- **Snowball backfill**: replaying dead-lettered records into already-processed partitions forces every downstream consumer to backfill too. Decide consciously whether replay is worth the cascade.

## Windowed Deduplicator
At-least-once delivery = duplicates. Batch: `ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts) = 1` or `dropDuplicates([...])`. Streaming: `dropDuplicates` **with** `withWatermark` to bound state; unbounded dedup state grows forever. Tradeoff: short window misses some dupes, long window costs memory.

## Late Data Detector
Event time ≠ processing time. Maintain a watermark = `MAX(event_time) - allowed_lateness`; anything with `event_time < watermark` is late.
- **Use MAX, never MIN**, for partition-level tracking. MIN gets "stuck in the past": the watermark never advances, state never expires.

## Static Late Data Integrator
Bounded lateness (e.g. always within 14 days) → each daily run also reprocesses the previous N days. Airflow Dynamic Task Mapping generates the N backfill tasks. Because windows overlap, when replaying manually **replay only from the last execution**, not every run.

## Dynamic Late Data Integrator
Unbounded lateness → keep a state table `(partition, last_processed_version, last_update_time, is_processed)`; before each run, query which partitions got new commits (Delta `getChanges`/CDF) and reprocess only those. Concurrency: set `depends_on_past=True` on the key tasks to avoid two runs racing on the state table.

## Filter Interceptor
Filtered-out rate jumps from 15% to 90% after a release — which predicate? Wrap each predicate in a counter: Spark accumulators, or in SQL express each predicate as a `CASE` column in a subquery and `GROUP BY` them to get per-condition counts. Cheap at runtime, invaluable in debugging.

## Checkpointer
Without checkpoints, a streaming restart replays from the log's beginning. Spark commits offsets + state per microbatch; Flink checkpoints on an interval. More frequent = more overhead, less reprocessing; less frequent = the reverse.
- **Checkpointing alone is at-least-once.** The "exactly-once feeling" is an impression — you also need idempotent writes (ch.4).

## Decision guide
- Flink/Spark job dies on malformed JSON → Dead-Letter with side output.
- Duplicates after producer retry → Windowed Deduplicator, ~10-min watermark.
- Mobile events 30 min late → Late Data Detector + Static Integrator with 2-hour lookback.
- Suspiciously thin output after deploy → Filter Interceptor.
- Streaming aggregation must survive restarts → Checkpointer + idempotent sink.

## Stack mapping
- **T-SQL dead-letter**: `TRY_CONVERT` / `TRY_PARSE` on load, route `NULL` results to `stg.rejected_rows` with the raw payload and reason; count rejections per batch into a metrics table.
- **T-SQL filter interceptor**: `SUM(CASE WHEN pred1 THEN 1 END) AS dropped_by_pred1, ...` in the same pass as the load.
- **Fabric/Databricks**: `foreachBatch` splits valid/invalid into two Delta writes; `withWatermark` + `dropDuplicates`; checkpoint location on ADLS/OneLake with retention configured.
- **dbt**: static integrator = incremental model with `lookback` var; `is_incremental()` filter `WHERE event_date >= dateadd(day, -{{ var('lookback') }}, '{{ run_started_at }}')`.
- **Airflow**: `expand()` for dynamic lookback tasks; `depends_on_past=True` on the state-updating task.
