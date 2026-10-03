# Backup/Restore Strategy

> **Purpose**: Production backup policy by RPO/RTO tier, the correct restore sequence, and dbatools automation for full server-level DR
> **MCP Validated**: 2026-09-16

## When to Use

- Designing or auditing a backup schedule against a stated RPO/RTO
- Executing a point-in-time restore after a bad deployment or accidental DELETE
- Automating full instance recovery (databases + logins + jobs + linked servers) to a new server

## Implementation

```sql
-- Backup types
BACKUP DATABASE SalesDB TO DISK = 'SalesDB_Full.bak' WITH COMPRESSION, CHECKSUM, STATS = 10;
BACKUP DATABASE SalesDB TO DISK = 'SalesDB_Diff.bak' WITH DIFFERENTIAL, COMPRESSION, CHECKSUM;
BACKUP LOG      SalesDB TO DISK = 'SalesDB_Log.bak'  WITH COMPRESSION, CHECKSUM;
BACKUP DATABASE SalesDB TO DISK = 'SalesDB_Copy.bak' WITH COPY_ONLY, COMPRESSION;  -- doesn't reset diff baseline

-- Tail-log backup before restoring over a still-online, damaged database
BACKUP LOG SalesDB TO DISK = 'tail.trn' WITH NORECOVERY, NO_TRUNCATE;

-- Restore sequence: every step but the last uses NORECOVERY
RESTORE DATABASE SalesDB FROM DISK = 'SalesDB_Full.bak' WITH NORECOVERY, REPLACE;
RESTORE DATABASE SalesDB FROM DISK = 'SalesDB_Diff.bak' WITH NORECOVERY;
RESTORE LOG      SalesDB FROM DISK = 'SalesDB_Log.bak'  WITH NORECOVERY;
RESTORE LOG      SalesDB FROM DISK = 'tail.trn' WITH RECOVERY, STOPAT = '2026-06-25T14:32:00';  -- last step only

DBCC CHECKDB (SalesDB) WITH NO_INFOMSGS;   -- always, after every restore — success != healthy
```

```powershell
# dbatools: full server-level DR in ~5 lines
Export-DbaInstance -SqlInstance $source -Path $exportPath -Force            # logins, jobs, linked servers, configs
Backup-DbaDatabase -SqlInstance $source -Path $backupPath -Type Full -CompressBackup -IncludeSystemDbs
Get-ChildItem $backupPath -Directory | Restore-DbaDatabase -SqlInstance $target -WithReplace
Get-ChildItem $exportPath -Filter *.sql | ForEach-Object { Invoke-DbaQuery -SqlInstance $target -File $_.FullName }
Test-DbaLastBackup -SqlInstance $target   # restores to temp location + runs CHECKDB automatically
```

## Configuration

| Tier (RPO) | Full | Differential | Log |
|---|---|---|---|
| Batch / non-critical (hours) | Weekly | Daily | Hourly (if FULL recovery) |
| Near real-time (30 min) | 2x/week | 3x/day | Hourly |
| Mission-critical (minutes) | Daily | Every 3h | Every 15–30 min |

| Check | Query |
|---|---|
| Backup history / gaps | `msdb.dbo.backupset` joined to `backupmediafamily`, filter last 7 days |
| Why the log won't truncate | `sys.databases.log_reuse_wait_desc` (`LOG_BACKUP` = the classic trap) |

## Example Usage

```sql
-- Verify a backup is restorable without restoring it
RESTORE VERIFYONLY FROM DISK = 'SalesDB_Full.bak' WITH CHECKSUM;
RESTORE HEADERONLY FROM DISK = 'SalesDB_Full.bak';
```

Run a restore test quarterly per tier, on a non-production server, and time it — that elapsed time is the real RTO, not the one in the SLA document. `Test-DbaLastBackup` automates this: it restores to a scratch location, runs CHECKDB, and reports pass/fail.

## See Also

- [recovery-and-ha-dr](../concepts/recovery-and-ha-dr.md)
- [always-on-setup](always-on-setup.md)
- [reference/ha-dr-field-guide](../reference/ha-dr-field-guide.md)
