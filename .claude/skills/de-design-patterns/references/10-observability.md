# Ch.10 — Data Observability patterns

Borrowed from software (logs/metrics/traces), split in two: **pipeline observability** (did the job run correctly?) and **data observability** (is the output trustworthy?). Success of the first says nothing about the second.

## Pipeline Metrics Collector
Emit per run: duration, rows read/written/filtered, dead-letter count, late count, shuffle bytes. Airflow `on_success_callback`/`on_failure_callback` → Prometheus/StatsD; Spark accumulators; Flink metric reporters. Alert on dead-letter rate > 5% or duration > 2x baseline.

## Data Metrics Collector
Instrument the data: `COUNT(*)`, `COUNT(DISTINCT key)`, `SUM(measure)`, `MAX(event_time)`, null rate per column. Compute every run, store in a metrics table, plot in Grafana. This is the bridge to ch.9 validators. dbt: `elementary`, `dbt-expectations`.

## Lineage Tracker
Record inputs/outputs per run → impact analysis (what breaks if this source changes?) and root cause (which upstream table introduced the bad rows?). Standard: OpenLineage `RunEvent`s from Airflow/Spark/dbt/Flink, consumed by Marquez/Atlan. The most underinvested capability in most teams — fix this first.

## Anomaly Detector
Beyond fixed thresholds: Z-score on a rolling 30-day window (|z| > 3 → alert). Seasonality → Prophet. At most scales a daily `AVG`/`STDEV` query over the metrics table is enough; no ML infra needed.

## SLA Tracker
Per Gold table: expected delivery time, row-count range, quality score. Track actual vs expected; alert the consumer team automatically on miss. Airflow `dagrun_timeout` + `sla_miss_callback`; dbt `meta.sla` + custom test.

## Rules
- Both pipeline and data metrics, always as timestamped time series.
- Lineage first, then anomaly detection, then SLAs.
- Alert before the consumer complains.

## Stack mapping
- **Grafana/Prometheus/Loki/Tempo** (already in place): Airflow StatsD exporter → Prometheus; Spark accumulators pushed via StatsD or written to the `dq.metrics` table and scraped with a SQL datasource; Loki for dead-letter payload samples; OpenTelemetry spans per task for trace-level duration breakdown.
- **SQL Server**: `dq.metrics` time-series table + Agent job computing `AVG`/`STDEV(value) OVER (... ROWS 29 PRECEDING)` for z-scores; Query Store and Extended Events are *pipeline* telemetry, not lineage.
- **Fabric**: Monitoring Hub + lineage view for impact analysis; Fabric Activator for alerting on metric thresholds; Purview for cross-workspace lineage.
- **Databricks**: Unity Catalog lineage (table and column level, automatic); Lakehouse Monitoring for drift/quality metrics on Delta tables; `spark.sparkContext.accumulator` for custom counts.
- **dbt**: `elementary` (metrics + anomaly tests + Slack alerts), `dbt-openlineage`/`dbt-ol` wrapper for lineage events.
- **Airflow**: `apache-airflow-providers-openlineage`, `sla_miss_callback`, `dagrun_timeout`.
