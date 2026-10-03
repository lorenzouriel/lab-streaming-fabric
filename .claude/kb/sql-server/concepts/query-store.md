# Query Store

> **Purpose**: What Query Store captures, why it survives what DMVs can't, and how it anchors regression hunting
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

Query Store (SQL Server 2016+) is a persistent, per-database performance history: every query, every distinct execution plan the optimizer chose for it, and runtime statistics (duration, CPU, I/O, memory grant) per query/plan pair. Unlike DMVs, this data **survives restarts and plan-cache eviction**, which is what makes "this got slow after Tuesday's deploy" a 30-second query instead of an archaeology project.

## The Concept

```sql
ALTER DATABASE SalesDB SET QUERY_STORE = ON;
ALTER DATABASE SalesDB SET QUERY_STORE (
    OPERATION_MODE = READ_WRITE,
    CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30),   -- default retention
    MAX_STORAGE_SIZE_MB = 1000,                            -- default; raise for busy workloads
    QUERY_CAPTURE_MODE = AUTO                              -- default since 2019: skips trivial/infrequent queries
);

-- Find regressed queries: recent avg duration vs. an earlier baseline window
SELECT q.query_id, qt.query_sql_text,
       rs_recent.avg_duration AS recent_us, rs_baseline.avg_duration AS baseline_us,
       rs_recent.avg_duration / rs_baseline.avg_duration AS regression_ratio
FROM sys.query_store_query AS q
JOIN sys.query_store_query_text AS qt ON q.query_text_id = qt.query_text_id
JOIN sys.query_store_plan AS p ON q.query_id = p.query_id
JOIN sys.query_store_runtime_stats AS rs_recent ON p.plan_id = rs_recent.plan_id
JOIN sys.query_store_runtime_stats AS rs_baseline ON p.plan_id = rs_baseline.plan_id
WHERE rs_recent.last_execution_time > DATEADD(HOUR, -24, GETDATE())
  AND rs_baseline.last_execution_time < DATEADD(HOUR, -24, GETDATE())
  AND rs_recent.avg_duration > rs_baseline.avg_duration * 2
ORDER BY regression_ratio DESC;

-- Stabilize with a forced plan while you fix the root cause
EXEC sp_query_store_force_plan @query_id = 123, @plan_id = 456;
-- EXEC sp_query_store_unforce_plan @query_id = 123, @plan_id = 456;  -- release later
```

Query Store is **on by default for new databases since SQL Server 2022** and in Azure SQL Database. `QUERY_CAPTURE_MODE = AUTO` is the default and filters trivial queries; use `ALL` only after checking the space impact on high-throughput OLTP.

**Automatic Plan Correction** (SQL Server 2022+, Azure SQL): `ALTER DATABASE ... SET AUTOMATIC_TUNING (FORCE_LAST_GOOD_PLAN = ON)` reverts a regressed plan automatically and logs the action to `sys.dm_db_tuning_recommendations`.

## Quick Reference

| Capability | DMVs (`dm_exec_query_stats`) | Query Store |
|---|---|---|
| Survives restart | No | Yes |
| Historical comparison | No | Yes (configurable retention) |
| Plan forcing | No | Yes |
| Auto regression correction | No | Yes (2022+) |

`sp_query_store_set_hints` attaches a hint to a `query_id` without touching application code — e.g. `OPTION (RECOMPILE)` to fight parameter sniffing, or `OPTION (MAXDOP 1, MAX_GRANT_PERCENT = 10)`.

## Common Mistakes

### Wrong

Never checking `sys.database_query_store_options`; Query Store silently flips to `READ_ONLY` when `current_storage_size_mb` hits `max_storage_size_mb` and stops collecting — including, in Azure SQL, the data feeding Query Performance Insight in the portal.

### Correct

```sql
SELECT current_storage_size_mb, max_storage_size_mb, readonly_reason
FROM sys.database_query_store_options;
-- alert before it's full; raise MAX_STORAGE_SIZE_MB or shorten retention deliberately
```

## Related

- [query-processing](query-processing.md)
- [azure-sql-tuning](../patterns/azure-sql-tuning.md)
- [monitoring-and-alerting](../patterns/monitoring-and-alerting.md)
