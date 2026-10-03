# SQL Server HA/DR Field Guide

> High availability, disaster recovery, and failover troubleshooting. For the *setup* T-SQL, see [../patterns/always-on-setup](../patterns/always-on-setup.md) and [../patterns/backup-restore-strategy](../patterns/backup-restore-strategy.md); this guide covers the decision framework and what to do when HA/DR misbehaves.

## The Framing: RTO, RPO, RLO

- **RTO (Recovery Time Objective)** — how long you can be down. Drives the HA choice.
- **RPO (Recovery Point Objective)** — how much data (in time) you can lose. Drives backup/replication frequency.
- **RLO (Recovery Level Objective)** — the granularity you must recover to (instance? database? one table at a point in time?).

**HA ≠ DR.** HA keeps you running through *local* failures (a node dies) with fast automatic failover, usually same-datacenter. DR survives losing the *whole site*, usually asynchronous, geographically distant, often a manual decision. You need both.

| Requirement | Technology | RTO | RPO | Notes |
|---|---|---|---|---|
| Auto-failover, local, zero data loss | AG (sync) or FCI | seconds-minutes | 0 | AG = separate storage; FCI = shared storage |
| Cross-site DR, some loss OK | AG (async) | minutes (manual) | seconds-minutes | standard modern DR pattern |
| Cheap DR, no clustering | Log Shipping | minutes-hours | = log backup interval | battle-tested, low-tech |
| Read-scale offload | AG readable secondaries | n/a | n/a | reporting off the secondary |
| Whole-instance protection | FCI | seconds | 0 | protects logins/jobs AGs (pre-2022) don't |
| Last line of defense | Backups | hours | = log backup interval | non-negotiable; underpins everything |

**Backups are the floor under all of it.** AGs/FCIs reduce downtime; only backups protect against corruption, accidental `DELETE`, and ransomware — an AG faithfully replicates a `DROP TABLE` to every secondary in milliseconds. HA is not a backup.

## Comparison Matrix

| | AG (sync) | AG (async) | FCI | Log Shipping |
|---|---|---|---|---|
| Auto failover | Yes | No | Yes | No |
| Data loss (RPO) | Zero | Near-zero | Zero | = log interval |
| Storage | Non-shared | Non-shared | **Shared** | Non-shared |
| Readable secondary | Yes | Yes | No | STANDBY (read) |
| Protects instance objects | No¹ | No¹ | **Yes** | No |
| Cross-site DR | Limited (latency) | **Yes** | No | Yes |
| Requires WSFC | Yes² | Yes² | Yes | No |

¹ unless Contained AG (2022+). ² unless clusterless read-scale AG.

## Troubleshooting: The Core HADR DMVs

```sql
-- Replica health
select ag.name, ar.replica_server_name, ars.role_desc, ars.connected_state_desc,
       ars.synchronization_health_desc, ar.availability_mode_desc, ar.failover_mode_desc
from sys.availability_groups ag
join sys.availability_replicas ar on ag.group_id = ar.group_id
join sys.dm_hadr_availability_replica_states ars on ar.replica_id = ars.replica_id;

-- Per-database sync detail -- lag and queues live here
select db_name(drs.database_id) as database_name, ar.replica_server_name,
       drs.synchronization_state_desc, drs.is_primary_replica,
       drs.log_send_queue_size, drs.log_send_rate,
       drs.redo_queue_size, drs.redo_rate, drs.secondary_lag_seconds
from sys.dm_hadr_database_replica_states drs
join sys.availability_replicas ar on drs.replica_id = ar.replica_id
order by database_name, ar.replica_server_name;
```

The two queue columns are the heart of AG troubleshooting: **`log_send_queue_size`** is data not yet sent to the secondary — your **RPO exposure** if the primary dies now. **`redo_queue_size`** is data received but not yet replayed — your **RTO exposure** on failover (the secondary must drain it before it's caught up).

**`log_send_queue` growing** → primary can't ship fast enough: network bandwidth/latency, or the secondary's log disk can't harden fast enough. **`redo_queue` growing** → secondary can't replay fast enough: undersized secondary, or (notoriously) a long-running read query on the readable secondary stalling the redo thread.

**Sync-commit latency on the primary** (writes suddenly slow after adding a sync replica) → check `HADR_SYNC_COMMIT` waits on the primary; that's it waiting for the secondary to harden. Fix: faster network/disk, or move that replica to async (accepting the RPO change).

## Failover Troubleshooting

**Automatic failover didn't happen when it should have** — checklist:
- Was the replica synchronous-commit *and* in `SYNCHRONIZED` state (not just `SYNCHRONIZING`)? Auto-failover requires `SYNCHRONIZED` — a lagging secondary is not eligible. This is the most common "why didn't it fail over."
- Is `failover_mode = automatic` on *both* primary and target secondary?
- Is WSFC quorum healthy? No quorum → no failover decision at all.

```sql
alter availability group [AG_Prod] failover;                       -- manual, run on target secondary
alter availability group [AG_Prod] force_failover_allow_data_loss; -- forced, async replica, real disaster
```

After a forced failover with data loss, the old primary returns in a suspended state — resume data movement, expect possible reseeding if LSNs diverged.

## WSFC & Quorum

Quorum prevents split-brain (two nodes both thinking they're primary). The cluster stays up only while a **majority of votes** is reachable — losing quorum takes the AG offline even with healthy SQL instances underneath.

- **Odd vote count**: with an even node count, add a witness. A two-node cluster always needs one.
- For multi-site, configure **node weight** deliberately — don't let the DR site accidentally win quorum on a WAN blip.
- **Cloud witness** (Azure blob) is the modern tiebreaker, replacing the fragile file-share witness.

```powershell
Get-ClusterQuorum
Get-ClusterNode | Select-Object Name, State, DynamicWeight, NodeWeight
```

When the AG is "down" but SQL looks fine, **check quorum first**.

## Readable Secondary Issues

Reads reflect the **redo point**, not the live primary — lag shows as `redo_queue_size`/`secondary_lag_seconds`, not lost data. Long reports on a secondary can stall its redo thread (see above). Read workloads force snapshot isolation, generating row versions in the *secondary's* tempdb — size it accordingly. The optimizer can't create permanent stats on a read-only DB, so it uses temporary tempdb stats, which is why secondary plans can differ from the primary's.

## Backup & Restore Failures

**Broken backup chain** — restore fails with an LSN mismatch, meaning a backup is missing between two you have. Diagnose via `msdb.dbo.backupset` LSN continuity; you can only restore up to the break, then need a fresh full.

**Restore slow / RTO blown** — too many logs to replay (take more frequent diffs), no instant file initialization (grant the SQL service account "Perform Volume Maintenance Tasks"), or an uncompressed backup over a slow path.

**Restore fails on a different server** — orphaned users, missing logins, mismatched file paths (use `MOVE`), or an edition/version downgrade (can't restore newer/higher-edition features to older/lower).

**Corruption found at restore** — if `CHECKSUM` was off during backup, corruption may have been silently backed up. Always back up `WITH CHECKSUM`, and `DBCC CHECKDB` on periodic test restores.

## Logs & Sources, by Problem

| Problem | Look here |
|---|---|
| AG sync/failover | SQL error log on both replicas, AG dashboard in SSMS, `sys.dm_hadr_*`, `AlwaysOn_health` XEvents (the AG's `system_health` equivalent) |
| Cluster/quorum | `Get-ClusterLog`, Windows System event log, `Get-Cluster*` cmdlets |
| Backup/restore | SQL error log, `msdb.dbo.backupset` / `restorehistory` |
| Corruption | SQL error log (823/824/825), `DBCC CHECKDB`, `msdb.dbo.suspect_pages` |

## Runbook — AG Manual Failover (Planned)

```
1. Confirm target secondary SYNCHRONIZED + HEALTHY (redo_queue near 0)
2. Confirm no excessive log_send/redo queue
3. Notify / enter maintenance window
4. On the TARGET secondary: alter availability group [AG] failover;
5. Verify new primary role + databases online + listener resolves correctly
6. Confirm old primary flipped to secondary and is SYNCHRONIZING/SYNCHRONIZED
7. Validate app connectivity through the listener
8. Document time taken (your real RTO)
```

## Runbook — DR Restore (Point-in-Time)

```
1. Identify the recovery target time
2. Locate the chain: last full + last diff before target + all logs up to target
   (verify LSN continuity via msdb.backupset)
3. If source still online: take a TAIL-LOG backup (WITH NORECOVERY, NO_TRUNCATE)
4. Restore full   WITH NORECOVERY, REPLACE (MOVE files if different paths)
5. Restore diff   WITH NORECOVERY
6. Restore logs   WITH NORECOVERY, in order
7. Final log/tail: WITH RECOVERY, STOPAT = '<target time>'
8. Post-restore: DBCC CHECKDB, fix orphaned users (ALTER USER ... WITH LOGIN), validate data
9. Repoint app / re-establish HA protection (reseed AG secondaries from new primary)
```

*Test the failover and the restore before you need them — a DR plan you haven't executed is fiction.*
