# Ch.9 — Data Quality patterns

Perfect idempotency, error handling, and storage can still deliver wrong data. Two categories: **prevention** (stop bad data entering) and **detection** (find what got through). Layer both; test intermediate tables, not just Gold.

## Schema Validator
Enforce at write: Delta schema enforcement (`strict`), Avro/Protobuf + Schema Registry for streams (producers register, consumers validate; additive nullable columns ok, breaking changes rejected). dbt: `not_null`, `unique`, `accepted_values` on every model, not just Gold.

## Constraint Validator
Business rules schema can't express: `amount > 0`, `start < end`, `country IN (...)`. SQL `CHECK` constraints, Delta `ALTER TABLE ADD CONSTRAINT`, dbt tests. Streaming: filter + Dead-Letter (ch.3).

## Null Validator
Null-rate spikes are the first symptom of upstream change (migration, producer bug, new source). Track null rate per column as a time series; alert when > 2x baseline before Gold.

## Volume Validator
Row count per partition vs historical mean ± stddev. 10M rows yesterday, 100K today = producer failure or filter bug (Filter Interceptor, ch.3).

## Freshness Validator
`MAX(ingestion_time)` / `MAX(event_time)` must advance. Hourly table with `MAX < NOW() - 2h` → broken. dbt `source freshness`; Airflow check task.

## Referential Integrity Validator
`LEFT JOIN users ... WHERE users.id IS NULL` → orphans = source sync issue. Run in Silver; don't let Gold consumers discover it.

## Accuracy Validator
Cross-check against an authoritative system: warehouse `SUM(revenue)` vs finance report. Highest-trust signal for stakeholders; discrepancies = pipeline bug or source drift.

## Consistency (SCD) Validator
For SCD2 tables: no overlapping validity ranges, no gaps, exactly one open-ended row per key. Essential for Static Joiner correctness (ch.5).

## Rules
- Track nulls/volume/freshness as time series; anomaly detection beats fixed thresholds.
- Validate at every layer; bugs are cheaper in Silver.
- dbt tests in every DAG run are the practical batch implementation.

## Decision guide
- Producer changes a field type → Schema Registry blocks it.
- New source sends `NULL user_id` for anonymous → Null Validator + Dead-Letter.
- Daily volume −90% → Volume Validator alerts before Gold.
- Revenue mismatch → Accuracy Validator in Gold dbt model.

## Stack mapping
- **SQL Server**: `CHECK`/`FOREIGN KEY` on Silver tables where volume allows; a `dq.metrics` table `(table_name, partition_key, metric, value, captured_at)` populated by a post-load proc; `dbo.usp_check_scd2(@table)` using `LEAD(valid_from) OVER (PARTITION BY key ORDER BY valid_from) <> valid_to` for gaps/overlaps and `COUNT(*) FILTER (valid_to = '9999-12-31') <> 1` per key.
- **dbt**: `dbt-expectations` (`expect_column_values_to_be_between`, `expect_table_row_count_to_be_between`), `dbt_utils.mutually_exclusive_ranges` for SCD2 consistency, `source freshness` with `warn_after`/`error_after`, `elementary` for anomaly tests on volume/nulls/freshness.
- **Fabric / Databricks**: Delta `CHECK` constraints and `NOT NULL`; Lakeflow/DLT `expect_or_drop` = Constraint Validator + Dead-Letter in one; Great Expectations if multi-engine.
- **Power BI**: Accuracy Validator = reconcile the semantic model measure against the finance source in a scheduled Fabric notebook; surface the delta on an ops page.
