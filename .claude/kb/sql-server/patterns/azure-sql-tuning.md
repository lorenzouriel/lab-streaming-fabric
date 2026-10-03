# Azure SQL Tuning

> **Purpose**: The Azure-SQL-specific diagnostic funnel — provisioning ceiling, database-scoped defaults, and how they differ from on-prem SQL Server
> **Confidence**: 0.90 — vCore tiers and defaults shift; verify current limits against Microsoft Learn before sizing production capacity
> **MCP Validated**: 2026-09-16 (vCore-over-DTU guidance and tier characteristics cross-checked against current Microsoft Learn; DTU model still supported, not deprecated, but vCore is the recommendation for new provisioning)

## When to Use

- Provisioning a new Azure SQL Database or diagnosing "the database is slow" on one that's already running
- Deciding General Purpose vs. Business Critical vs. Hyperscale, or provisioned vs. serverless compute
- Distinguishing what's on by default in Azure SQL (RCSI, optimized locking, ADR) from what on-prem SQL Server requires opting into

## Implementation

```sql
-- vCore is the modern resource model (DTU still works but has little reason for new workloads)
-- MAXDOP: Azure SQL defaults to 8 — never 0 in production (one analytical query can starve everything)
ALTER DATABASE SCOPED CONFIGURATION SET MAXDOP = 8;
ALTER DATABASE SCOPED CONFIGURATION FOR SECONDARY SET MAXDOP = 4;

-- Automatic tuning: FORCE_LAST_GOOD_PLAN on by default; leave index management off until reviewed
ALTER DATABASE CURRENT SET AUTOMATIC_TUNING (FORCE_LAST_GOOD_PLAN = ON, CREATE_INDEX = OFF, DROP_INDEX = OFF);

-- Compatibility level gates optimizer features and NEVER auto-upgrades
SELECT name, compatibility_level FROM sys.databases WHERE name = DB_NAME();
ALTER DATABASE CURRENT SET COMPATIBILITY_LEVEL = 170;  -- baseline with Query Store first, test, then prod

-- Cuts single-use ad-hoc plans from evicting the cache
ALTER DATABASE SCOPED CONFIGURATION SET OPTIMIZE_FOR_AD_HOC_WORKLOADS = ON;

-- Accelerated Database Recovery is ALWAYS on in Azure SQL — watch the persistent version store
SELECT persistent_version_store_size_kb / 1024.0 AS pvs_mb FROM sys.dm_tran_persistent_version_store_stats;
```

## Configuration

| Tier | Storage | Latency | Best for |
|---|---|---|---|
| General Purpose | Remote (Blob) | 5–10 ms | Default choice unless a specific reason to move off it |
| Business Critical | Local SSD | 1–2 ms | Latency-sensitive OLTP, free readable replica, ~2.7x GP cost |
| Hyperscale | Decoupled + local cache | Low (cached) | Up to 128 TB, near-instant compute scale-up |

| Azure SQL default (vs. on-prem opt-in) | Effect |
|---|---|
| RCSI on by default | Readers never block writers out of the box |
| Optimized locking on by default | Reduces writer-writer contention (transaction-ID locking, lock-after-qualification) |
| Query Store on by default | See [query-store](../concepts/query-store.md) |

## Example Usage

The diagnostic funnel, top-down: **1. Provisioning** (right tier/ceiling) → **2. Concurrency** (isolation defaults) → **3. Expensive queries** (`dm_exec_query_stats`) → **4. Execution plans** (scan/seek, estimate mismatch) → **5. Query Store** (regression since last deploy) → **6. Blocking/deadlocks**. Layers 3–6 use the same diagnostics as on-prem — see [reference/dba-field-guide](../reference/dba-field-guide.md) and [reference/troubleshooting-cheat-sheet](../reference/troubleshooting-cheat-sheet.md); this pattern's job is layers 1–2, which are genuinely Azure-specific.

```sql
-- The oversell bug: fix with an atomic predicate guard, not a heavier isolation level
UPDATE dbo.Products SET StockCount = StockCount - 1 WHERE ProductID = 42 AND StockCount > 0;
IF @@ROWCOUNT = 0 THROW 50010, 'Out of stock', 1;
```

## See Also

- [query-store](../concepts/query-store.md)
- [transactions-and-isolation](../concepts/transactions-and-isolation.md)
- [reference/troubleshooting-cheat-sheet](../reference/troubleshooting-cheat-sheet.md)
