# Specialized Table Types

> **Purpose**: Temporal, ledger, in-memory (OLTP), external, and graph tables — what each replaces, when the complexity is worth it, and their dominant tradeoff
> **Confidence**: 0.90
> **MCP Validated**: 2026-09-16

## Overview

Each specialized table type replaces something you would otherwise hand-build (a history table, a bolt-on audit trail, disk-latency workarounds, recursive join chains), and each is expensive to retrofit onto a live table — so the decision is best made at design time, not after production data exists.

## The Concept

```sql
-- Temporal: automatic full row history, no triggers
CREATE TABLE dbo.Customers (
    CustomerID INT PRIMARY KEY, CustomerName NVARCHAR(100), Tier NVARCHAR(50),
    SysStartTime DATETIME2 GENERATED ALWAYS AS ROW START,
    SysEndTime   DATETIME2 GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime)
) WITH (SYSTEM_VERSIONING = ON);
SELECT * FROM dbo.Customers FOR SYSTEM_TIME AS OF '2026-01-01' WHERE CustomerID = 1;

-- In-memory (memory-optimized): RAM-resident, lock-free optimistic concurrency
CREATE TABLE dbo.OrderCache (
    OrderID INT PRIMARY KEY NONCLUSTERED, CustomerID INT, Amount DECIMAL(10,2),
    INDEX IX_CustomerID NONCLUSTERED (CustomerID)
) WITH (MEMORY_OPTIMIZED = ON, DURABILITY = SCHEMA_AND_DATA);

-- Ledger: cryptographic, tamper-evident history (append-only shown)
CREATE TABLE dbo.OrderAuditLog (
    LogID INT PRIMARY KEY IDENTITY, EventDescription NVARCHAR(500), EventTimestamp DATETIME2
) WITH (LEDGER = ON, APPEND_ONLY = ON);

-- Graph: nodes/edges, MATCH for multi-hop traversal
CREATE TABLE Person AS NODE;
CREATE TABLE Manages AS EDGE;
SELECT p1.name, p2.name FROM Person p1, Manages, Person p2
WHERE MATCH (p1-(Manages)->p2) AND p1.id = 1;

-- External table: query a data lake file without ETL (mostly read-only)
CREATE EXTERNAL TABLE dbo.ExternalOrderData (OrderID INT, OrderAmount DECIMAL(10,2))
WITH (LOCATION = '/raw/orders/', DATA_SOURCE = DataLakeSource, FILE_FORMAT = ParquetFormat);
```

## Quick Reference

| Type | Replaces | Dominant tradeoff | Use for |
|------|----------|--------------------|---------|
| Temporal | Manual history table + triggers | Storage roughly doubles | Audit trails, "what was this on date X", SCD2 with zero app code |
| In-memory OLTP | Disk-latency workarounds | Data size bounded by RAM; no `MAX` LOB types | 10k+ TPS order processing, hot session/reference caches |
| Ledger | Bolt-on tamper-evidence | Append-only blocks deletion; verify via `sp_verify_database_ledger` | Banking, supply-chain provenance, regulated audit logs |
| Graph | Recursive join chains | `MATCH` syntax learning curve | Genuinely network-shaped, variable-depth traversal (social, BOM) |
| External | ETL into the database | Read-mostly, network + parse latency, limited indexing | Lake integration, exploring raw files before importing |
| Columnstore | Manual OLAP pre-aggregation | See [indexing-internals](indexing-internals.md) | Fact tables, reporting, historical data in the millions of rows |

**FILESTREAM / FILETABLE** (large-object storage): FILESTREAM stores BLOBs on the filesystem while keeping them inside SQL Server transactions and backups — use for read-heavy blobs consistently >~1 MB that must stay transactionally tied to relational metadata; small blobs are simpler as in-row `VARBINARY(MAX)`. FILETABLE builds on FILESTREAM to expose the same data as both a Windows file share and a T-SQL table simultaneously — worth the setup only when non-database tools need raw filesystem access.

## Common Mistakes

### Wrong

Reaching for a graph table for a simple parent-child relationship (a foreign key + join is fine), or in-memory OLTP for a workload that isn't latency-bound and doesn't need `MAX` types.

### Correct

Match the table type to the trait that's actually the requirement: automatic history → temporal; tamper-evidence → ledger; variable-depth traversal → graph; RAM-speed OLTP → in-memory. Each is designed in, not bolted on later.

## Related

- [indexing-internals](indexing-internals.md)
- [engine-architecture](engine-architecture.md)
- [advanced-tsql-querying](../patterns/advanced-tsql-querying.md) for graph `MATCH` query patterns
