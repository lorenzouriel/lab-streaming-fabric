# SQL Server Troubleshooting Cheat Sheet

> Identify -> Measure -> Resolve. The incident quick-reference card — terse on purpose. The deep treatment lives in [dba-field-guide](dba-field-guide.md) and [ha-dr-field-guide](ha-dr-field-guide.md); this is what you keep open during a live incident.

**The loop, every time:** identify the bottleneck by waits -> confirm systemic vs. one query -> measure how bad (breadth + duration) -> fix the cause (usually *read less work*, not *add hardware*) -> re-measure that the waits actually moved.

## Step 1 — Identify

**First 60 seconds** — live activity snapshot, sorted by cost:

```sql
select r.session_id, r.status, r.blocking_session_id, r.wait_type,
       r.wait_time / 1000.0 as wait_s, r.cpu_time, r.total_elapsed_time / 1000.0 as elapsed_s,
       r.logical_reads, r.open_transaction_count, r.dop, db_name(r.database_id) as db,
       s.login_name, s.host_name, s.program_name,
       substring(t.text, (r.statement_start_offset/2)+1,
           ((case r.statement_end_offset when -1 then datalength(t.text)
             else r.statement_end_offset end - r.statement_start_offset)/2)+1) as running_statement
from sys.dm_exec_requests r
inner join sys.dm_exec_sessions s on r.session_id = s.session_id
outer apply sys.dm_exec_sql_text(r.sql_handle) as t
where r.session_id <> @@spid and s.is_user_process = 1
order by r.cpu_time desc;   -- swap to elapsed_time / wait_time / logical_reads
```

**Lead blockers** (block others, aren't blocked themselves):

```sql
select r.blocking_session_id as lead_blocker, count(*) as sessions_blocked,
       max(r.wait_time)/1000.0 as max_block_s
from sys.dm_exec_requests r
where r.blocking_session_id <> 0
  and r.blocking_session_id not in (select session_id from sys.dm_exec_requests where blocking_session_id <> 0)
group by r.blocking_session_id order by sessions_blocked desc;
```

**The master key — wait type to subsystem:**

| Top wait | Problem | Section |
|---|---|---|
| `PAGEIOLATCH_*` | Disk I/O (or memory forcing re-reads) | I/O |
| `WRITELOG` | Disk I/O — log latency | I/O |
| `RESOURCE_SEMAPHORE` / `_QUERY_COMPILE` | Memory — grant starvation / compile gate | Memory |
| `SOS_SCHEDULER_YIELD` (+ runnable queue) | CPU pressure | CPU |
| `SOS_SCHEDULER_YIELD` (no queue) | CPU — spinlocks | CPU |
| `CXPACKET` | Parallelism (often a missing index) | Parallelism |
| `LCK_M_*` | Blocking / locking | Blocking |
| `PAGELATCH_*` on `2:x:x` | tempdb allocation contention | tempdb |
| `THREADPOOL` | Worker starvation — usually severe blocking | Blocking |
| `ASYNC_NETWORK_IO` | Client/network — app not consuming rows | Network |
| `HADR_SYNC_COMMIT` | HA — sync replica latency | [ha-dr-field-guide](ha-dr-field-guide.md) |

**Decision fork:** systemic (many sessions, same wait) -> fix the subsystem. One fat query, others fine -> fix the query. Blocking chain -> chase the lead blocker.

## Step 2 — Measure the Impact

```sql
select count(*) as active_requests,
       sum(case when blocking_session_id <> 0 then 1 else 0 end) as blocked_requests,
       max(wait_time)/1000.0 as max_wait_s, max(total_elapsed_time)/1000.0 as longest_running_s
from sys.dm_exec_requests where session_id > 50;
```

Assess breadth (one session or hundreds), duration (seconds or unbounded growth), scope (one DB or instance-wide), and business impact (critical app or a stray report) before acting. **Act now** if blocked count is growing with unbounded waits on production; **diagnose calmly** if bounded and off-hours. Before killing anything, know the rollback cost — killing a huge open transaction triggers an uninterruptible rollback that can outlast the block.

## Step 3 — Subsystem Playbooks

Each follows: **Tell -> Diagnose -> Causes -> Fix.**

**MEMORY** — Tell: `RESOURCE_SEMAPHORE` waits, grants pending > 0, erratic PLE, tempdb spills. Causes: oversized grants from bad cardinality, `max server memory` misconfigured, plan-cache bloat. Fix: fix estimates first (bigger lever than RAM), set `max server memory` sanely, enable `optimize for ad hoc workloads`; 2017+ Memory Grant Feedback self-corrects.

**CPU** — Tell: `SOS_SCHEDULER_YIELD`, signal-wait % > 15-20%, `runnable_tasks_count > 0` sustained. Causes: missing index, stale stats, parameter sniffing, implicit conversions, compilation churn, over-parallelism. Fix: rule out power-plan throttling and VM CPU-ready contention first, then add the index / update stats / fix sniffing / raise cost threshold (5->50) + set MAXDOP.

**DISK I/O** — Tell: `PAGEIOLATCH_*` (data), `WRITELOG` (log). Thresholds: data <10-20ms healthy, >50ms bad; log <5ms/write. Causes (cheap ones first): memory pressure re-reading evicted pages, missing index, implicit conversions, *then* genuinely slow storage. Fix: read less before buying faster disk; grant Perform Volume Maintenance Tasks for instant file init; separate log onto low-latency storage.

**BLOCKING / LOCKING** — Tell: `LCK_M_*`, blocked count climbing. Causes: long transaction, idle session with open transaction, missing index forcing broad locks, unindexed FK, wrong isolation level. Fix now: identify lead blocker, `kill` if it's stuck/idle (know the rollback cost). Structural: shorten transactions, add the index, consider RCSI.

**tempdb** — Tell: `PAGELATCH_*` (not PAGEIO) on `2:1:1`/`2:1:3`, or tempdb full. Causes: allocation contention (many sessions creating temp objects), spills (`internal_objects` ballooning), version-store buildup (long-open RCSI transaction). Fix: multiple equal-sized data files (4, or 1/core up to 8); TF 1117/1118 are default on 2016+, don't set them; chase the spilling query or long transaction.

**PARALLELISM** — Tell: `CXPACKET` high, small queries running parallel. Causes: cost threshold still at default 5, MAXDOP 0, often a missing index turning a seek into a parallel scan. Fix: ask *why it's parallel* first — usually the index fix makes it evaporate. Then tune workload-wide (cost threshold 25-50, MAXDOP = cores-per-NUMA-node). `CXCONSUMER` is benign.

**PLAN / QUERY REGRESSION** — Tell: "fine yesterday", bimodal performance. Causes: parameter sniffing, stale stats, CE version change after a compat-level bump, plan eviction. Fix: force the good plan (`sp_query_store_force_plan`), update stats, or address sniffing; use the SSMS Query Store "Regressed Queries" report.

**NETWORK / CLIENT** — Tell: `ASYNC_NETWORK_IO` dominant. Almost always the app (row-by-row consumption, no pagination), not SQL. Fix app-side; rarely a genuine network issue.

## Emergency "Break Glass" Actions

Use deliberately — each has a cost.

```sql
kill <session_id>;                                          -- rollback may be long; WITH STATUSONLY to watch
update statistics dbo.YourTable with fullscan;               -- bad plan from stale stats
exec sp_query_store_force_plan @query_id = <id>, @plan_id = <id>;   -- pin a known-good plan
dbcc freeproccache (<plan_handle>);                          -- evict ONE bad plan, not the whole cache
alter database [YourDB] set recovery full;                   -- log_reuse_wait_desc = 'LOG_BACKUP'
backup log [YourDB] to disk = N'...';
```

Avoid in production unless you mean it: `dbcc freeproccache` with no args (clears everything, mass recompiles), `dbcc dropcleanbuffers` (dumps the buffer pool), killing a large write transaction (uninterruptible rollback).

## Threshold Quick Reference

| Metric | Healthy | Investigate | Bad |
|---|---|---|---|
| Data file read latency | < 10 ms | 10-20 ms | > 20-50 ms |
| Log file write latency | < 5 ms | 5-15 ms | > 15 ms |
| Signal wait % | < 10% | 15-20% | > 20% (CPU) |
| `runnable_tasks_count` | 0 | occasional spikes | sustained > 0 |
| Memory grants pending | 0 | - | > 0 sustained |
| Blocking duration | < 1s bursts | seconds | growing / unbounded |
| `log_reuse_wait_desc` | `NOTHING` | `LOG_BACKUP` | `ACTIVE_TRANSACTION` |

*When SQL looks broken but isn't, check: another process eating CPU, power-plan throttling, lost WSFC quorum (see [ha-dr-field-guide](ha-dr-field-guide.md)), or the app not consuming rows.*
