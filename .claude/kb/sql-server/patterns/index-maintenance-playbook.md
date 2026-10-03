# Index Maintenance Playbook

> **Purpose**: Rebuild vs. reorganize thresholds, statistics maintenance, the DBCC toolkit, and Ola Hallengren's automation as the production standard
> **MCP Validated**: 2026-09-16

## When to Use

- Scheduling weekly/monthly maintenance for a production instance
- Deciding whether a fragmented index needs `REORGANIZE` or `REBUILD`
- Statistics are stale and query plans are degrading between auto-update cycles

## Implementation

```sql
-- Check fragmentation
SELECT OBJECT_NAME(ips.object_id) AS table_name, i.name AS index_name,
       ips.avg_fragmentation_in_percent, ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ips
JOIN sys.indexes AS i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.avg_fragmentation_in_percent > 5 AND ips.page_count > 500   -- ignore tiny indexes
ORDER BY ips.avg_fragmentation_in_percent DESC;

-- <5%: do nothing. 5-30%: REORGANIZE (online). >30%: REBUILD (offline unless Enterprise ONLINE=ON)
ALTER INDEX [IX_Orders_CustomerID] ON dbo.Orders REORGANIZE;
ALTER INDEX [IX_Orders_CustomerID] ON dbo.Orders REBUILD WITH (ONLINE = ON);   -- Enterprise/Developer only

-- Statistics: auto-update fires at ~500 + 20% rows changed (too lazy for large tables)
UPDATE STATISTICS dbo.Orders WITH FULLSCAN;         -- most accurate, most expensive
-- REBUILD already updates stats with a full scan; no separate UPDATE STATISTICS needed after

-- DBCC CHECKDB: schedule PHYSICAL_ONLY weekly (fast, I/O corruption), full monthly (logical + physical)
DBCC CHECKDB (SalesDB) WITH PHYSICAL_ONLY, NO_INFOMSGS;
DBCC CHECKDB (SalesDB) WITH NO_INFOMSGS;            -- full — always after a restore too

-- Ola Hallengren's Maintenance Solution — the production standard, don't hand-roll this
EXEC dbo.DatabaseBackup @Databases='USER_DATABASES', @BackupType='LOG', @Verify='Y', @Compress='Y';
EXEC dbo.DatabaseIntegrityCheck @Databases='USER_DATABASES', @CheckCommands='CHECKDB', @PhysicalOnly='Y', @LogToTable='Y';
EXEC dbo.IndexOptimize @Databases='USER_DATABASES', @FragmentationLevel1=5, @FragmentationLevel2=30;
```

## Configuration

| DBCC command | Use for |
|---|---|
| `CHECKDB` / `CHECKTABLE` / `CHECKALLOC` | Integrity (whole DB / one table / allocation only) |
| `SHRINKFILE` | Exceptional, one-time correction — not routine (fragments indexes, causes autogrow overhead) |
| `SQLPERF(LOGSPACE)` | Quick per-database log usage snapshot |
| `OPENTRAN` | Oldest active transaction — first check when the log won't truncate |
| `INPUTBUFFER(@@SPID)` | Last statement a session ran — pair with blocking diagnosis |
| `FREEPROCCACHE` | Clears plan cache instance-wide — blunt instrument, causes a CPU spike, use with intent |

`AUTO_CLOSE` and `AUTO_SHRINK` should be **OFF** on every production database (set the default once in `model`): `AUTO_CLOSE` adds reopen latency on connection bursts; `AUTO_SHRINK` trades disk space for recurring fragmentation.

## Example Usage

```sql
-- Weekly maintenance schedule (SLA-driven, not habit-driven)
-- Sunday 03:00  CHECKDB PHYSICAL_ONLY   | Saturday 01:00  IndexOptimize
-- Saturday 04:00  Statistics update     | 1st Sunday/mo   CHECKDB full
```

## See Also

- [indexing-internals](../concepts/indexing-internals.md)
- [capacity-and-storage-design](capacity-and-storage-design.md)
- [reference/dba-field-guide](../reference/dba-field-guide.md)
