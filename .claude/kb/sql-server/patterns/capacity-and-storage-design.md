# Capacity and Storage Design

> **Purpose**: Scale-up vs. scale-out, the capacity planning cycle, RAID/OS storage configuration, and data compression / sparse columns as a storage-vs-CPU trade
> **MCP Validated**: 2026-09-16

## When to Use

- Sizing a new database or provisioning a new instance
- Deciding whether autogrow, RAID, or storage tiering needs attention before a growth spike causes an outage
- A large table's data-type mix or repetitive values suggest compression is worth the CPU trade

## Implementation

```sql
-- Estimate compression savings before committing (rebuilds cost time on large tables)
EXEC sp_estimate_data_compression_savings 'dbo', 'OrderDetails', NULL, NULL, 'PAGE';

ALTER TABLE dbo.Orders REBUILD WITH (DATA_COMPRESSION = ROW);    -- fixed-length savings, cheaper CPU
ALTER TABLE dbo.OrderDetails REBUILD WITH (DATA_COMPRESSION = PAGE);  -- + prefix/dictionary, best on repetitive values

-- Sparse columns: eliminate storage for columns that are NULL in the vast majority of rows
CREATE TABLE dbo.Products (
    ProductID INT PRIMARY KEY, ProductName NVARCHAR(100) NOT NULL,
    DiscontinuedNote NVARCHAR(MAX) SPARSE NULL,
    SeasonalTag NVARCHAR(50) SPARSE NULL,
    AllSparseAttrs XML COLUMN_SET FOR ALL_SPARSE_COLUMNS   -- query the whole sparse group at once
);
```

```sql
-- Preallocate; never rely on AUTO_SHRINK; check log usage before shrinking
SELECT name, recovery_model_desc, log_reuse_wait_desc FROM sys.databases;
```

## Configuration

| Decision | Guidance |
|---|---|
| Scale up vs. out | Scale up first (simpler, no app changes); scale out once a single server's I/O/cost ceiling is hit, or the workload decomposes naturally (sharding, read replicas) |
| RAID for data files | RAID 10 — high performance + redundancy |
| RAID for log files | RAID 1 — sequential writes, smaller volume |
| RAID 5/6 | Storage-efficiency-over-write-throughput workloads only |
| Allocation unit size | 64 KB when formatting SQL Server volumes |
| Instant File Initialization | On for data files (skip zeroing); log files always zero-initialize |
| Compression type | ROW: fixed-length-heavy tables, safer default. PAGE: repetitive values (status codes, small FK sets) |

| Compression trade | Direction |
|---|---|
| I/O-bound, read-heavy (reporting, historical partitions) | Usually a clear win — fewer physical reads |
| CPU-bound, write-heavy OLTP | Evaluate carefully — decompression/compression cost on every read/write |

## Example Usage

```sql
-- Capacity planning cycle, on a recurring schedule (not once at launch):
-- 1. current workload (CPU/mem/IO, peak timing)  2. size + growth trend (not guesswork)
-- 3. monitoring/alerting ahead of exhaustion      4. deliberate autogrow (fixed MB, not %)
-- 5. index/stats maintenance as part of the same cycle  6. backup/restore sized with the DB
-- 7. loop in app/business stakeholders for planned growth (launches, migrations)
```

## See Also

- [index-maintenance-playbook](index-maintenance-playbook.md)
- [azure-sql-tuning](azure-sql-tuning.md)
- [reference/dba-field-guide](../reference/dba-field-guide.md)
