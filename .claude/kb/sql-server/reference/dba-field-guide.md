# SQL Server DBA Field Guide

> Monitoring · performance troubleshooting · logs, events & diagnostics. A working reference, not a textbook — what you actually run at 2 a.m. See [reference/troubleshooting-cheat-sheet](troubleshooting-cheat-sheet.md) for the terser incident-response card, and [../concepts/query-store](../concepts/query-store.md) for the regression-hunting workflow this guide leans on.

## Part 0 — The Mental Model

SQL Server is a thread scheduler on a storage engine. A worker thread is **running** (on CPU), **runnable** (ready, waiting for CPU), or **suspended** (waiting on a resource — lock, disk page, memory grant, log flush). When it suspends, SQL Server records *why* as a **wait type** — the single most honest signal in the engine. Everything below is **wait-based methodology**: don't guess the bottleneck, read the waits.

Three rules: (1) measure before optimizing — "slow" is a symptom, not a diagnosis; (2) diff cumulative counters, never read them raw (most DMVs accumulate since restart); (3) confirm a fix moved the *waits*, not just the wall clock (a faster run could be a warm cache).

## Part 1 — Monitoring

**Three time horizons** need different tools — conflating them is the top monitoring mistake:

| Horizon | Question | Tools |
|---|---|---|
| Real-time | What's happening *now*? | `sp_WhoIsActive`, `dm_exec_requests`, `dm_os_waiting_tasks` |
| Cumulative | What's been expensive *since restart*? | `dm_os_wait_stats`, `dm_exec_query_stats`, `dm_io_virtual_file_stats` |
| Historical | How has this *trended*? | Query Store, Prometheus/Grafana |

**Install `sp_WhoIsActive` (Adam Machanic) on every instance** — it collapses the DMV joins below into one sorted snapshot: blocking chains, waits, tempdb, reads/writes, plan.

```sql
exec sp_WhoIsActive @get_plans = 1, @get_locks = 1, @find_block_leaders = 1, @get_task_info = 2;
```

**Cumulative DMVs** (always diff two snapshots — these accumulate since restart):

| DMV | Answers |
|---|---|
| `sys.dm_exec_query_stats` | Top queries by CPU/IO/duration/frequency (cache-bound; evicted plans vanish — that's why Query Store exists) |
| `sys.dm_io_virtual_file_stats(null,null)` | Per-file read/write latency. Healthy: data <10-20ms/read, log <5ms/write (log is sync on commit) |
| `sys.dm_db_index_usage_stats` | Seeks/scans/updates per index — finds unused (high writes, zero reads) and duplicate indexes |

**Query Store** is the flight recorder — enable everywhere, it persists text/plans/runtime stats *into the database*, surviving restarts. Regression hunting, multi-plan (parameter sniffing) detection, and `sp_query_store_force_plan` all live here; see [../concepts/query-store](../concepts/query-store.md).

**Wait statistics** (`sys.dm_os_wait_stats`) — filter out benign system waits (Paul Randal's standard exclusion list: `SLEEP_TASK`, `LAZYWRITER_SLEEP`, `BROKER_TASK_STOP`, `CXCONSUMER`, etc.) and rank by `wait_time_ms`. Note `signal_wait_time_ms`: time spent *runnable* waiting for CPU after the resource was ready — high signal time across the board is a CPU-pressure tell on its own.

**External monitoring**: `sql_exporter` → Prometheus → Grafana is the standard OSS path for trend data DMVs can't give you on their own (they're point-in-time or since-restart). Track batch requests/sec, compiles/sec, Page Life Expectancy (per NUMA node — the aggregate hides a starved node), memory grants pending, blocked session count.

**Baselines**: you cannot answer "is this normal?" without one. Capture wait-stat deltas, file latency, PLE, and session counts on a schedule; alert on *deviation from baseline*, not generic thresholds ("CPU > 80%" is noise; "waits shifted to RESOURCE_SEMAPHORE, which never happens here" is signal).

## Part 2 — Performance Troubleshooting: The Triage Order

1. **Instance-wide or single query?** `sp_WhoIsActive @find_block_leaders=1`. A blocking chain → chase the lead blocker. Many sessions on the *same* wait → systemic, go to the subsystem. One fat query, everyone else fine → query problem.
2. **Characterize by waits** — diff `dm_os_wait_stats` over the bad window, or read Query Store's per-query wait categories.
3. **Drill into the culprit** (table below).
4. **Confirm the fix moved the waits**, not just the clock.

"The database is slow" almost always resolves to: blocking, plan regression, stale statistics, a missing index, tempdb contention, or I/O.

| Wait type | Points at | First move |
|---|---|---|
| `PAGEIOLATCH_*` | Disk I/O or memory pressure forcing re-reads | Check `dm_io_virtual_file_stats`; rule out cache pressure first |
| `WRITELOG` | Log flush latency | Log disk latency, or too many tiny commits (batch them) |
| `LCK_M_*` | Blocking | Chase the blocking chain (below) |
| `PAGELATCH_*` on `2:x:x` | tempdb allocation contention | Multiple equally-sized tempdb data files |
| `CXPACKET` | Parallelism (often a missing index) | Ask *why* it's parallel before touching MAXDOP |
| `SOS_SCHEDULER_YIELD` | CPU pressure (or spinlocks if no runnable queue) | `dm_os_schedulers.runnable_tasks_count` |
| `RESOURCE_SEMAPHORE` | Memory grant starvation | Fix cardinality estimates before adding RAM |
| `ASYNC_NETWORK_IO` | The client app, not SQL | Row-by-row consumption, no pagination |
| `HADR_SYNC_COMMIT` | Sync-replica AG latency | See [ha-dr-field-guide](ha-dr-field-guide.md) |

**Blocking & deadlocks.** Find the chain via `dm_exec_requests.blocking_session_id`; the lead blocker has a NULL/zero blocker itself. An idle session with `open_transaction_count > 0` is the classic left-open-transaction culprit. `KILL` has a rollback cost — a multi-million-row rollback can outlast the block. Deadlocks (not blocking — they self-resolve) are captured automatically in `system_health`; read the graph's process/resource nodes to find the opposite-order lock acquisition that caused it. Structural fix: consistent access order, shorter transactions, better indexes, or RCSI.

**Reading plans**: scans where seeks belong (missing/unusable index), estimate-vs-actual mismatch (stale stats, non-sargable predicate, local variable, multi-statement TVF), spills (undersized memory grant), key lookups (widen the index with `INCLUDE`), implicit conversions (`CONVERT_IMPLICIT` — mismatched types silently kill index usage).

**Parameter sniffing** — one `query_id`, multiple plans of divergent performance in Query Store. Fixes from least to most blunt: `OPTION (RECOMPILE)`, `OPTION (OPTIMIZE FOR (@p = value))`, `OPTION (OPTIMIZE FOR UNKNOWN)`, Query Store forced plan, or split into separate code paths. No free option — pick based on frequency and skew.

**Statistics**: `sys.dm_db_stats_properties()` shows `modification_counter` since last update. Default auto-update thresholds are too lazy for large tables — schedule explicit `UPDATE STATISTICS ... WITH FULLSCAN` (or Ola Hallengren's solution) rather than trusting auto-update on big/fast-churning tables.

**tempdb** has two distinct failure modes: allocation contention (`PAGELATCH_*` on `2:1:1`/`2:1:3` — fix with multiple equal-sized data files) and space blowout (spills or version-store buildup from a long-open RCSI transaction — find and kill it).

**Memory & CPU**: `granted ≫ used` in `dm_exec_query_memory_grants` means bad estimates, not a RAM problem. Sustained `runnable_tasks_count > 0` across schedulers is direct CPU starvation evidence — usually a scan that should be a seek, or compilation churn from unparameterized ad-hoc SQL.

## Part 3 — Logs, Events & Debugging

Three distinct systems; knowing which holds the answer saves the most time:

| System | Holds | Read with |
|---|---|---|
| SQL error log | Startup/recovery, failed logins, backup/restore, severity 17+ | `sp_readerrorlog 0, 1, N'search'` |
| Windows Application log | Service crash/restart, OS disk errors, AG failovers — used when the SQL log is silent | `Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='MSSQLSERVER'}` |
| Extended Events | Everything else — the Profiler/SQL Trace replacement, don't build new tooling on the deprecated trace | `CREATE EVENT SESSION ... ADD TARGET package0.event_file` |

**`system_health`** runs by default on every instance and already captures deadlock graphs, severity ≥20 errors, and long lock/latch waits — query it before building anything new. **The default trace** (still running on most instances) captures DDL/config changes at low volume — the fastest answer to "who changed what." **Blocked process report** fires on a threshold (`sp_configure 'blocked process threshold'`) and emits both statements in the block — pair it with an XEvents capture and an alert.

**Severity levels**: 0-10 informational, 11-16 user-correctable (log, don't page), 17-19 resource/internal errors (alert), **20-25 fatal — page someone**. Watch specifically for 823/824/825 (I/O integrity — 824 is corruption, 825 is the early-warning canary of a failing disk that recovered on retry).

## Appendix — DMV Quick Reference

| DMV | Use for |
|---|---|
| `sys.dm_exec_requests` / `dm_exec_sessions` | Live requests / session-level info |
| `sys.dm_os_waiting_tasks` | Live waits & blocking chains |
| `sys.dm_os_wait_stats` | Cumulative waits (diff it) |
| `sys.dm_exec_query_stats` | Top queries by aggregate cost (cache-bound) |
| `sys.dm_io_virtual_file_stats()` | Per-file read/write latency |
| `sys.dm_db_index_usage_stats` / `dm_db_missing_index_*` | Index usage / optimizer's wished-for indexes |
| `sys.dm_tran_locks` | Current locks held/requested |
| `sys.dm_exec_query_memory_grants` | Outstanding & pending memory grants |
| `sys.dm_db_session_space_usage` | Per-session tempdb usage |
| `sys.dm_os_schedulers` | CPU scheduler pressure (runnable queue) |
| `sys.query_store_*` | Historical per-query plans & runtime stats |

## Appendix — Condensed Triage Runbook

```
"The database is slow."
1. sp_WhoIsActive @find_block_leaders=1, @get_plans=1
   - Blocking chain?  -> chase lead blocker. Idle blocker w/ open txn? kill or fix app.
   - All on same wait? -> systemic, use the wait-type table above.
   - One fat query?   -> pull plan: scans, estimate mismatch, spills, key lookups, implicit conv.
                         Bimodal perf? parameter sniffing. Bad estimates? stats.
2. Discrete event (broke at a timestamp), not slowness?
   - SQL error log first, severity 17+
   - Deadlock?      -> system_health graph
   - Corruption?    -> severity 23/24, errors 823/824/825 -> DBCC CHECKDB
   - SQL log silent?-> Windows Application log
3. "Got slow after <date>"?  -> Query Store regressed-queries. Force good plan if needed.
4. Confirm the fix moved the WAITS, not just the clock. Re-measure identically.
```
