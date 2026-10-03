# Ch.2 — Data Ingestion patterns

You don't choose your producers; you adapt to them. Get ingestion wrong and everything downstream fails.

## Full Loader
Replace the whole dataset each run. Simple, but the swap can expose a zero-row window if it's `DELETE` then `INSERT` without a transaction. Fix: write to a new versioned table/partition and repoint a view (Proxy pattern, ch.4), or use a transactional format (Delta) where the overwrite is one atomic commit.
- When: small/medium reference data, no reliable delta column, source can't do CDC.
- Gotcha: cost scales with dataset size every run; no history unless you keep versions.

## Incremental Loader
Read only new rows via a delta column (`ingestion_time`, `modified_at`) or time-based partitions.
- Partitions are safer than delta columns — delta columns on *event* time miss late data.
- **Always bound the window**: `WHERE ingestion_time >= @start AND ingestion_time < @start + 1h`. An unbounded `>= @start` turns a backfill into an accidental full load.
- Gotcha: choosing event time as the delta column without a late-data strategy (ch.3) drops rows silently.

## Change Data Capture
When you need sub-30s latency or must capture hard deletes, neither loader works. Read the commit log: Debezium → Kafka Connect, Delta Change Data Feed, native DB CDC.
- Caveat: CDC turns data at rest into data in motion — ordering, late joins, and streaming semantics now apply (ch.5, ch.11). Needs ops buy-in on the source DB (log retention, capture jobs).

## Passthrough Replicator
Copy as-is between environments (prod → staging). Keep it dumb: raw/text APIs, no JSON parsing that can silently coerce types. **Push from prod, never pull into prod** — protects prod from staging instability. Carry metadata too (Kafka headers, Delta log), or you lose it.

## Transformation Replicator
Passthrough plus a minimal transform to strip/mask PII before crossing the boundary. Every transform is a potential bug — prefer `SELECT * EXCEPT (ip, lat, lon)` over rewriting columns. Track PII fields via catalog tags so the exclusion list isn't hand-maintained. See ch.7 Anonymizer.

## Compactor
Streaming-to-lakehouse produces small files. After months, 70% of job time can be file listing. `OPTIMIZE` (Delta) / `rewrite_data_files` (Iceberg), then `VACUUM` to actually reclaim space. Frequency is a tradeoff: too rare → readers suffer; too frequent → writers contend.

## Readiness Marker
Never trigger downstream on a partition still being written. Spark emits `_SUCCESS` for raw formats; for Delta the commit itself is the marker; otherwise write an explicit control-table row. Consumers poll: Airflow `FileSensor(mode='reschedule')` frees the worker slot while waiting. Document the convention — it's a contract with consumers.

## External Trigger
Producer has no schedule (vendor drops, feature releases) → subscribe, don't poll. S3/Blob event → Lambda/Function → Airflow REST API triggers a DAG with `schedule_interval=None`. Always pass an envelope (trigger version, event metadata, processing time) — a blind trigger is undebuggable.

## Decision guide
- Postgres/SQL Server → lakehouse, hourly: Incremental Loader on partitions + FileSensor.
- Transactional table, sub-minute, deletes matter: CDC.
- Prod → staging for tests: Transformation Replicator with `EXCEPT`.
- Streaming lands thousands of tiny Parquet files: Compactor daily.
- Vendor sends whenever: External Trigger.

## Stack mapping
- **SQL Server source**: native CDC (`sys.sp_cdc_enable_table`, `cdc.fn_cdc_get_net_changes_<capture>` with `all with merge` row filter) when you need the change payload; Change Tracking when you only need changed keys and lower overhead. Debezium's SQL Server connector rides on native CDC. `rowversion` column is a cheap, reliable delta column (monotonic, not time-based, immune to clock issues) — better than `modified_at` for incremental loads.
- **Fabric**: Mirroring gives CDC-style replication from SQL DB/Azure SQL/Snowflake into OneLake without pipelines. Dataflows/Pipelines copy activity for full/incremental; Delta auto-compaction (`delta.autoOptimize.*`) covers Compactor in Lakehouse.
- **Databricks**: Auto Loader (`cloudFiles`) for file-based incremental ingestion with checkpointed discovery; Delta CDF for downstream CDC.
- **Airflow**: `FileSensor` / `S3KeySensor` in reschedule mode; `TriggerDagRunOperator` or REST `dagRuns` endpoint for External Trigger.
