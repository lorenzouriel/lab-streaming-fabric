# Indexing Internals

> **Purpose**: How clustered, nonclustered, and columnstore indexes are structured internally, and why fragmentation and update patterns behave differently across them
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

All standard rowstore indexes use a B-Tree. A **clustered index** determines physical row order (one per table, leaf level IS the data). A **nonclustered index** is a separate sorted structure of key + row-locator pairs (many per table). **Columnstore indexes** store data column-by-column instead of row-by-row, and have their own internal write path (deltastore + tuple-mover) that explains why they behave differently under OLTP-style writes.

## The Concept

```sql
-- Clustered: physical order. One per table, auto-created with PRIMARY KEY.
CREATE TABLE dbo.Orders (
    order_id INT NOT NULL PRIMARY KEY,   -- clustered index on order_id
    customer_id INT NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Nonclustered with INCLUDE: covers a query without widening the key
CREATE NONCLUSTERED INDEX ix_Orders_customer_status
    ON dbo.Orders (customer_id, status)
    INCLUDE (order_date);          -- leaf-level only, no lookup needed

-- Clustered columnstore: whole table stored column-oriented (analytics)
CREATE CLUSTERED COLUMNSTORE INDEX cci_OrderDetails ON dbo.OrderDetails;

-- Nonclustered columnstore: columnar copy layered on an OLTP table (HTAP)
CREATE NONCLUSTERED COLUMNSTORE INDEX ncci_Orders_Analytics
    ON dbo.Orders (customer_id, order_date, status);
```

**Columnstore internals**: data lands in **rowgroups** of up to ~1,048,576 rows, each column compressed as a **segment**. New rows first land in the **deltastore** (an ordinary B-tree) until ~102,400 rows accumulate, at which point the background **tuple-mover** compresses the delta rowgroup into columnar format. Bulk loads ≥102,400 rows skip the deltastore entirely. This is *why* high-frequency single-row updates fragment columnstore (a modification marks the old row deleted and inserts a new version, often into the deltastore) and why small tables (<~1M rows) don't benefit — rowgroups never fill enough to pay off compression/scan-elimination.

## Quick Reference

| | Rowstore (clustered/nonclustered) | Columnstore (clustered/nonclustered) |
|---|---|---|
| Best for | OLTP: point lookups, small writes | OLAP: aggregations over millions of rows |
| Storage | Row-oriented | Column-oriented, compressed |
| Per table | 1 clustered, many nonclustered | 1 clustered or nonclustered (HTAP) |
| Fragmentation source | Page splits from insert/update/delete | Deltastore churn, `deleted_rows` buildup |
| Health DMV | `sys.dm_db_index_physical_stats` | `sys.dm_db_column_store_row_group_physical_stats` |

Fragmentation thresholds: **<5%** ignore, **5–30%** `REORGANIZE` (online), **>30%** `REBUILD` (offline unless Enterprise `ONLINE = ON`) — see [index-maintenance-playbook](../patterns/index-maintenance-playbook.md).

## Common Mistakes

### Wrong

```sql
-- 15 nonclustered indexes on a write-heavy table, several never seeked/scanned
```
Every index is maintained on every INSERT/UPDATE/DELETE — unused indexes are pure write overhead.

### Correct

```sql
SELECT OBJECT_NAME(i.object_id) AS table_name, i.name AS index_name,
       ius.user_seeks + ius.user_scans + ius.user_lookups AS total_reads,
       ius.user_updates AS total_writes
FROM sys.indexes AS i
LEFT JOIN sys.dm_db_index_usage_stats AS ius
    ON i.object_id = ius.object_id AND i.index_id = ius.index_id
    AND ius.database_id = DB_ID()
WHERE i.type_desc <> 'HEAP'
ORDER BY total_reads ASC;   -- high writes, zero reads = drop candidate
```

## Related

- [query-optimization-techniques](../patterns/query-optimization-techniques.md)
- [index-maintenance-playbook](../patterns/index-maintenance-playbook.md)
- [specialized-table-types](specialized-table-types.md)
- Cross-dialect window functions/dedup patterns live in `../sql-patterns/`, not here
