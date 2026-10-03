# Ch.4 — Idempotency patterns

`abs(abs(abs(-1))) == abs(-1)`. A pipeline run should produce the same output whether it runs once or five times — that's what makes automatic retries (ch.3) and manual backfills safe. Prevent duplicates at **write** time, not read time. Four strategies: fast deletion, overwrite, upsert, immutable design.

## Fast Metadata Cleaner
`DELETE` at scale scans then deletes — slow and log-heavy. Instead, split the dataset into physical sub-tables (weekly/monthly) behind one view, and reset with `TRUNCATE` / `DROP + CREATE` at partition granularity. In Airflow a `BranchPythonOperator` decides "new period → recreate" vs "same period → append".
- Tradeoff: **idempotency granularity = backfill granularity**. Weekly table means replaying one day costs the week.
- Engines cap partition/table counts (BigQuery 4,000 partitions; Redshift 200k tables) — plan to freeze old periods into larger immutable units.

## Data Overwrite
No metadata layer (object store, raw files)? Overwrite physically. Spark `mode('overwrite')`, Delta `replaceWhere` for selective partitions, SQL `INSERT OVERWRITE` / `DELETE + INSERT` in one transaction. In table formats the overwrite is a new commit; old files linger until `VACUUM`.

## Merger (UPSERT)
You only have deltas (CDC), not the full set → `MERGE`. Three branches:
```
WHEN NOT MATCHED AND is_deleted = 0 THEN INSERT
WHEN MATCHED     AND is_deleted = 0 THEN UPDATE
WHEN MATCHED     AND is_deleted = 1 THEN DELETE
```
- **Include `is_deleted = 0` in the INSERT branch** — otherwise the first run inserts tombstones.
- Source hard deletes must be modeled as soft-delete flags to flow through CDC.

## Proxy
Expose a mutable dataset through an immutable pointer (a view). Swapping the underlying table is a metadata change consumers never see mid-flight. This is what makes Fast Metadata Cleaner and Full Loader safe.

## Incremental Sessionizer (idempotency angle)
Sessions are forward-dependent (10:00 depends on 09:00's pending sessions). Key every run by the immutable schedule time (`{{ ds }}`), and before writing, clear both completed and pending session tables `WHERE execution_time >= @run_date`. See ch.5.

## Stamp, Immutable Logs, Accumulator
- **Stamp**: write a unique run id with every batch → duplicates become identifiable and deletable.
- **Immutable Logs**: append-only; duplicates allowed but identifiable (by stamp) — readers dedupe.
- **Accumulator**: idempotent aggregation by `MERGE` into the aggregate table keyed on the aggregation grain.

## Rules
- Idempotency key = immutable schedule time (`ds`, `data_interval_start`), never `NOW()`.
- Overwrite for complete datasets; Merger for deltas.
- Pair overwrite/compaction with `VACUUM` to reclaim space.

## Decision guide
- Daily rebuild of a reference table → Data Overwrite.
- Weekly aggregate table → Fast Metadata Cleaner (weekly sub-tables + view).
- CDC stream into a mirror table → Merger with soft deletes.
- Streaming/batch sessions → `{{ ds }}` in the key, clear `>= ds` before rerun.

## Stack mapping
- **SQL Server**: partitioned table + `TRUNCATE TABLE t WITH (PARTITIONS (n))` or `ALTER TABLE ... SWITCH PARTITION` to an empty staging table — metadata-only, instant. For non-partitioned: load into `t_new`, `sp_rename` swap inside a transaction, or repoint a view (Proxy). `MERGE` works but has a long bug history — use `WITH (HOLDLOCK)`, avoid it on tables with triggers/indexed views, or use the explicit `UPDATE`/`INSERT`/`DELETE` trio in one transaction. Use `rowversion` or CDC LSN as the delta key.
- **Fabric / Databricks**: `INSERT OVERWRITE` or `replaceWhere` for partition overwrite; `MERGE INTO` Delta for CDC; `VACUUM` with retention aligned to time-travel needs. Delta `restore` is your safety net.
- **dbt**: `materialized='incremental'` with `incremental_strategy='merge'` (or `insert_overwrite` on partitioned warehouses); `unique_key` = business key; `is_incremental()` bounded by `{{ var('run_date') }}`, not `current_timestamp()`.
- **Airflow**: `BranchPythonOperator` → `trigger_rule='none_failed_min_one_success'` on the join task; `{{ data_interval_start }}` as the run key.
