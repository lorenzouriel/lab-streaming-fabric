# Always On AG Setup

> **Purpose**: Creating and configuring an Always On Availability Group — replicas, listener, quorum/witness, and log shipping as the low-tech alternative
> **MCP Validated**: 2026-09-16

## When to Use

- Need automatic, sub-minute failover for local node failure (HA), or a warm cross-region standby (DR)
- Two-node WSFC cluster needs a tiebreaker vote to survive a single node failure
- Log shipping is preferable when clustering complexity isn't justified (many databases, simple DR site)

## Implementation

```sql
-- Create the AG on the primary: one sync (local HA) + one async (cross-region DR) replica
CREATE AVAILABILITY GROUP [AG-Production]
WITH (AUTOMATED_BACKUP_PREFERENCE = SECONDARY, FAILURE_CONDITION_LEVEL = 3, HEALTH_CHECK_TIMEOUT = 30000)
FOR DATABASE [SalesDB]
REPLICA ON
    N'NODE1' WITH (ENDPOINT_URL = 'TCP://NODE1:5022', AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
                   FAILOVER_MODE = AUTOMATIC, SEEDING_MODE = AUTOMATIC,
                   SECONDARY_ROLE (ALLOW_CONNECTIONS = NO)),
    N'NODE2' WITH (ENDPOINT_URL = 'TCP://NODE2:5022', AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
                   FAILOVER_MODE = AUTOMATIC, SEEDING_MODE = AUTOMATIC,
                   SECONDARY_ROLE (ALLOW_CONNECTIONS = READ_ONLY)),
    N'NODE3-DR' WITH (ENDPOINT_URL = 'TCP://NODE3-DR:5022', AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT,
                   FAILOVER_MODE = MANUAL, SEEDING_MODE = AUTOMATIC);

ALTER AVAILABILITY GROUP [AG-Production]
ADD LISTENER N'AG-Production-Listener' (WITH IP ((N'10.0.1.50', N'255.255.255.0')), PORT = 1433);

-- On each secondary
ALTER AVAILABILITY GROUP [AG-Production] JOIN;
ALTER AVAILABILITY GROUP [AG-Production] GRANT CREATE ANY DATABASE;   -- required for automatic seeding

-- Planned failover (no data loss) -- run on the TARGET secondary
ALTER AVAILABILITY GROUP [AG-Production] FAILOVER;
-- Forced failover (async replica, real disaster, accepts data loss) -- run on the target
ALTER AVAILABILITY GROUP [AG-Production] FORCE_FAILOVER_ALLOW_DATA_LOSS;
```

```sql
-- Monitor health and lag — the two queue columns are the whole story
SELECT db_name(drs.database_id) AS database_name, ar.replica_server_name,
       drs.synchronization_state_desc, drs.log_send_queue_size,   -- RPO exposure if primary dies now
       drs.redo_queue_size                                        -- RTO exposure: must drain before failover completes
FROM sys.dm_hadr_database_replica_states AS drs
JOIN sys.availability_replicas AS ar ON drs.replica_id = ar.replica_id;
```

## Configuration

| Setting | Notes |
|---|---|
| Synchronous-commit | Zero RPO, automatic failover eligible; same-site/low-latency only (<~5ms round trip) |
| Asynchronous-commit | Near-zero RPO, manual/forced failover; the cross-region DR mode |
| `SEEDING_MODE = AUTOMATIC` | Streams the DB to the secondary directly; skip manual backup/restore for reasonably sized DBs |
| File Share Witness | Mandatory for a 2-node WSFC — without it, a single node failure = no quorum majority = no auto-failover |
| Max secondaries | Up to 8 total (Enterprise); Basic AGs (Standard) limited to 2 replicas total |

Auto-failover requires the target secondary to be **SYNCHRONIZED** (not just SYNCHRONIZING) — a secondary that fell behind is not eligible, and this is the most common "why didn't it fail over" answer.

## Example Usage

```sql
-- Log shipping: the low-tech alternative — no WSFC, no shared storage, no listener
EXEC master.dbo.sp_add_log_shipping_primary_database
    @database = N'SalesDB', @backup_directory = N'\\SQLBACKUP\LogShipping\SalesDB',
    @backup_job_name = N'LSBackup_SalesDB', @backup_retention_period = 4320, @overwrite = 1;
-- RPO = log backup interval; RTO = manual RESTORE DATABASE ... WITH RECOVERY on failover
```

## See Also

- [recovery-and-ha-dr](../concepts/recovery-and-ha-dr.md)
- [backup-restore-strategy](backup-restore-strategy.md)
- [reference/ha-dr-field-guide](../reference/ha-dr-field-guide.md)
