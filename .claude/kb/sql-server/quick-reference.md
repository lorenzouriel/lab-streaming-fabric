# SQL Server Quick Reference

> Fast lookup tables. For explanations and code, see linked concepts/patterns.
> MCP Validated: 2026-09-16

## Wait Type → Subsystem

| Wait type | Points at | See |
|---|---|---|
| `PAGEIOLATCH_*` | Disk I/O or memory pressure | [reference/dba-field-guide](reference/dba-field-guide.md) |
| `WRITELOG` | Log flush latency | [reference/dba-field-guide](reference/dba-field-guide.md) |
| `LCK_M_*` | Blocking | [reference/troubleshooting-cheat-sheet](reference/troubleshooting-cheat-sheet.md) |
| `PAGELATCH_*` on `2:x:x` | tempdb allocation contention | [reference/troubleshooting-cheat-sheet](reference/troubleshooting-cheat-sheet.md) |
| `CXPACKET` | Parallelism (often a missing index) | [patterns/query-optimization-techniques](patterns/query-optimization-techniques.md) |
| `RESOURCE_SEMAPHORE` | Memory grant starvation | [reference/dba-field-guide](reference/dba-field-guide.md) |
| `HADR_SYNC_COMMIT` | Sync AG replica latency | [reference/ha-dr-field-guide](reference/ha-dr-field-guide.md) |
| `ASYNC_NETWORK_IO` | The client app, not SQL | [reference/troubleshooting-cheat-sheet](reference/troubleshooting-cheat-sheet.md) |

## Index Type Decision

| Question | Answer | Index type |
|---|---|---|
| Point lookups, small writes (OLTP)? | Yes | Clustered + covering nonclustered |
| Aggregations over millions of rows (OLAP)? | Yes | Clustered columnstore |
| OLTP table also needs analytics? | Yes | Nonclustered columnstore (HTAP) |
| Table < ~1M rows? | — | Rowstore only; columnstore won't pay off |

Fragmentation: **< 5%** ignore, **5-30%** `REORGANIZE`, **> 30%** `REBUILD`. See [patterns/index-maintenance-playbook](patterns/index-maintenance-playbook.md).

## Recovery Model Decision

| Model | Point-in-time restore? | Use when |
|---|---|---|
| Full | Yes | Production OLTP, any real RPO |
| Bulk-logged | Partial | Temporary, during large bulk loads |
| Simple | No | Dev/test, reloadable warehouses |

`log_reuse_wait_desc = 'LOG_BACKUP'` is the #1 cause of runaway log growth — FULL recovery with no log backups.

## HA/DR Technology Decision

| Requirement | Technology | RTO | RPO |
|---|---|---|---|
| Auto-failover, local, zero loss | AG (sync) / FCI | seconds-minutes | 0 |
| Cross-site DR | AG (async) | minutes (manual) | seconds-minutes |
| Cheap DR, no clustering | Log Shipping | minutes-hours | = log interval |
| Whole-instance protection | FCI | seconds | 0 |

Full detail: [reference/ha-dr-field-guide](reference/ha-dr-field-guide.md).

## Routine Selection

| Need | Choose |
|---|---|
| Reusable, composable query, no side effects | View |
| Transaction control, multiple statements, output params | Stored procedure |
| Scalar value inline in a query | Scalar function (watch row-by-row cost pre-2019) |
| Table-shaped result inline in a query | Inline table-valued function |
| Enforce a rule on DML automatically | Trigger (sparingly — hidden control flow) |

## Error Handling

| Situation | Use |
|---|---|
| New code, general errors | `TRY/CATCH` + `THROW` |
| Re-raising after cleanup | `THROW` (no params, inside CATCH) |
| Need custom error number/state, or pre-2012 compat | `RAISERROR` |

## Join Algorithm Cheat Sheet

| Algorithm | When SQL Server picks it |
|---|---|
| Nested Loops | Small outer input, index seek available on inner |
| Merge | Both inputs already sorted on the join key |
| Hash | Large unsorted inputs, no useful index |

## Isolation Levels vs. Blocking

| Level | Readers block writers? | Cost |
|---|---|---|
| Read Committed (default) | No (brief) | — |
| Read Committed Snapshot (RCSI) | No | tempdb version store |
| Repeatable Read / Serializable | Yes | More blocking, fewer anomalies |

## Related Documentation

| Topic | Path |
|-------|------|
| Full Index | [index.md](index.md) |
| Cross-dialect SQL | [../sql-patterns/index.md](../sql-patterns/index.md) |
