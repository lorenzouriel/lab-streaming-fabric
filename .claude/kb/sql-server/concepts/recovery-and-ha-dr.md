# Recovery and HA/DR

> **Purpose**: Recovery models, backup types, and the HA vs. DR technology landscape (Always On AGs, FCI, log shipping) with the RTO/RPO trade-offs that pick between them
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

Every database has a **recovery model** that determines what's logged and what restore options exist. **RTO** (Recovery Time Objective — how long you can be down) and **RPO** (Recovery Point Objective — how much data you can lose) are business decisions that drive the whole architecture, not technical ones. HA (surviving local failures automatically, in seconds) and DR (surviving losing a whole site, usually a manual decision) are different problems that need different tools — backups are the floor under both; an Availability Group faithfully replicates a bad `DROP TABLE` to every secondary in milliseconds.

## The Concept

```sql
ALTER DATABASE SalesDB SET RECOVERY FULL;      -- point-in-time restore via log backups
-- SIMPLE: log auto-truncates, no PITR, no log backups possible
-- BULK_LOGGED: bulk ops minimally logged; PITR unavailable during those ops

BACKUP DATABASE SalesDB TO DISK = '...Full.bak' WITH COMPRESSION, CHECKSUM;
BACKUP DATABASE SalesDB TO DISK = '...Diff.bak' WITH DIFFERENTIAL, COMPRESSION, CHECKSUM;
BACKUP LOG      SalesDB TO DISK = '...Log.bak'  WITH COMPRESSION, CHECKSUM;

-- Check why the log won't truncate — the #1 disk-filling incident
SELECT name, recovery_model_desc, log_reuse_wait_desc FROM sys.databases;
-- LOG_BACKUP = FULL recovery + no log backups running (the classic trap)
```

## Quick Reference

| Requirement | Technology | RTO | RPO |
|---|---|---|---|
| Auto-failover, local, zero data loss | AG (synchronous) or FCI | seconds–minutes | 0 |
| Cross-site DR, some data loss OK | AG (asynchronous) | minutes (manual) | seconds–minutes |
| Cheap DR, no clustering | Log Shipping | minutes–hours | = log backup interval |
| Whole-instance protection (Agent/logins) | FCI (shared storage) | seconds | 0 |
| Last line of defense | Backups | hours | = log backup interval |

**Always On Availability Groups** (Enterprise; Basic AGs in Standard, 2-replica limit): one primary + up to 8 secondaries (edition/version-dependent), each replica **synchronous-commit** (zero RPO, automatic failover eligible, but costs commit latency — keep same-site/low-latency) or **asynchronous-commit** (near-zero RPO, manual/forced failover, the standard cross-region mode). Requires WSFC (or Pacemaker on Linux) for quorum/failover arbitration, except clusterless read-scale AGs. **Contained AGs** (2022+) additionally replicate `master`/`msdb` system objects. **FCI** protects the whole instance via shared storage but is a single point of failure for storage itself — often paired with an AG for site redundancy.

**Log shipping**: three SQL Agent jobs (backup → copy → restore WITH NORECOVERY/STANDBY). RPO = log backup interval; no automatic failover; the low-tech, still-solid DR option.

## Common Mistakes

### Wrong

Switching to FULL recovery and never scheduling log backups — the log grows forever and you still have no point-in-time recovery: worst of both worlds.

### Correct

Match recovery model and backup cadence to a stated RPO/RTO, test restores on a schedule, and treat "backups exist" and "we can restore from them" as two different, both-required claims — see [backup-restore-strategy](../patterns/backup-restore-strategy.md) and [reference/ha-dr-field-guide](../reference/ha-dr-field-guide.md).

## Related

- [backup-restore-strategy](../patterns/backup-restore-strategy.md)
- [always-on-setup](../patterns/always-on-setup.md)
- [reference/ha-dr-field-guide](../reference/ha-dr-field-guide.md)
