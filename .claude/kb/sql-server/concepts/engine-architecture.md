# Engine Architecture

> **Purpose**: The three-layer architecture (Protocol, Relational Engine, Storage Engine) and how a query flows through them, plus the system databases that back every instance
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

SQL Server divides into three layers: the **Protocol Layer** (connection/auth via TDS), the **Relational Engine** (parse → optimize → execute), and the **Storage Engine** (buffer pool, transaction/lock manager, disk I/O). Performance problems are layer-specific — knowing which layer is the bottleneck turns "the database is slow" into an actionable question. Every instance also runs four system databases (`master`, `model`, `msdb`, `tempdb`) that exist before any user database is created.

## The Concept

```text
Client Application
       │ (TDS protocol: Shared Memory / Named Pipes / TCP-IP)
       ▼
┌─────────────────────┐
│   Protocol Layer     │  connection mgmt, auth, TDS framing
└─────────────────────┘
       ▼
┌─────────────────────┐
│  Relational Engine   │  CMD Parser -> Query Optimizer -> Query Executor
└─────────────────────┘
       ▼
┌─────────────────────┐
│   Storage Engine     │  Access Manager -> Buffer Manager | Transaction Manager
└─────────────────────┘
       ▼
  Data files (.mdf/.ndf)   Log file (.ldf)
```

Relational Engine: the **CMD Parser** checks syntax/object references and produces a parse tree; the **Query Optimizer** evaluates join orders, join algorithms, and access paths against a cost budget (not exhaustively) and produces an execution plan; the **Query Executor** runs the plan, routing SELECTs to the Buffer Manager and DML to the Transaction Manager.

Storage Engine: the **Buffer Pool** caches 8 KB data pages and compiled plans in memory — a cache hit avoids disk I/O entirely. The **Lock Manager** enforces isolation/concurrency; the **Log Manager** implements Write-Ahead Logging (WAL) — every change lands in the `.ldf` before the `.mdf`, which is what makes crash recovery possible.

## System Databases and Files

| Database | Role | Notes |
|----------|------|-------|
| `master` | Instance metadata: logins, linked servers, list of every database and its file locations | Corruption without a recent backup = instance doesn't know it has databases |
| `model` | Template copied into every new `CREATE DATABASE` | Standardize recovery model/objects here once instead of per-database |
| `msdb` | SQL Agent job definitions/history, backup/restore history, Database Mail | `msdb.dbo.backupset`, `sysjobhistory` are the source of truth for "did it run" |
| `tempdb` | Recreated on every restart; absorbs temp tables, sort/hash spills, RCSI/snapshot row versioning, worktables | Common hidden bottleneck; size with multiple equal-sized data files |

Every database has one primary data file (`.mdf`) and optionally secondary files (`.ndf`), grouped into **filegroups** (`PRIMARY` by default) that control physical placement — hot data on fast storage, cold data on cheap storage. Exactly one active transaction log (`.ldf`) per database; data I/O is random, log I/O is sequential, so separate them onto different physical storage when possible. Filegroups can be backed up/restored individually (`BACKUP DATABASE ... FILEGROUP = ...` / `RESTORE ... WITH PARTIAL`) for piecemeal recovery of very large databases — see [recovery-and-ha-dr](recovery-and-ha-dr.md).

## Quick Reference

| Symptom | Likely layer |
|---------|-------------|
| Slow query, fast hardware | Relational Engine — bad plan, missing index, parameter sniffing |
| Fast query, slow overall response | Protocol Layer — TDS fragmentation, connection pool exhaustion |
| Rising I/O over time | Storage Engine — buffer pool pressure, fragmentation, checkpoint pressure |
| Blocking / deadlocks | Transaction Manager — Lock Manager contention |

## Common Mistakes

### Wrong

Assuming "the database is slow" is one problem and reaching for a single fix (add an index, add RAM) without identifying which layer is actually the bottleneck.

### Correct

Identify the layer first via waits (see [reference/dba-field-guide](../reference/dba-field-guide.md)), then apply the layer-specific fix — e.g. `PAGEIOLATCH` waits point at Storage Engine I/O, `LCK_M_*` waits point at the Lock Manager.

## Related

- [query-processing](query-processing.md)
- [indexing-internals](indexing-internals.md)
- [transactions-and-isolation](transactions-and-isolation.md)
