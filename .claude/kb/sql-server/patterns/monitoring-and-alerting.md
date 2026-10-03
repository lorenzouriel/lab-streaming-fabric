# Monitoring and Alerting

> **Purpose**: Automated slow-query capture (Extended Events over legacy sp_trace), Database Mail job-status notifications, and the wait-based triage entry point
> **MCP Validated**: 2026-09-16

## When to Use

- Need unattended overnight capture of slow statements without a live Profiler session
- SQL Agent jobs fail silently and nobody knows until downstream systems break
- Starting a live incident: "the database is slow" and you need the first 60 seconds of triage

## Implementation

```sql
-- Extended Events is the modern replacement for sp_trace_*/Profiler (deprecated) — build new tooling here
CREATE EVENT SESSION [slow_statements] ON SERVER
ADD EVENT sqlserver.sql_statement_completed (
    ACTION (sqlserver.sql_text, sqlserver.session_id, sqlserver.database_name)
    WHERE duration > 1000000 AND sqlserver.database_name = N'YourDB'   -- microseconds; always filter hard
)
ADD TARGET package0.event_file (SET filename = N'slow_statements', max_file_size = 256, max_rollover_files = 5)
WITH (max_dispatch_latency = 5 seconds, track_causality = ON, startup_state = OFF);
ALTER EVENT SESSION [slow_statements] ON SERVER STATE = START;

-- system_health runs by default on every instance — query it before building anything new
SELECT object_name, CAST(event_data AS XML) AS event_data
FROM sys.fn_xe_file_target_read_file('system_health*.xel', NULL, NULL, NULL);   -- deadlocks, severity 20+, long waits
```

```sql
-- Database Mail: job-status HTML notifications so failures show up in an inbox, not just Job History
EXEC msdb.dbo.sysmail_add_account_sp @account_name='SQL Alerts', @email_address='sqlserver@company.com',
    @mailserver_name='smtp.company.com', @port=587, @enable_ssl=1;
EXEC msdb.dbo.sysmail_add_profile_sp @profile_name='SQL Alerts';
EXEC msdb.dbo.sysmail_add_profileaccount_sp @profile_name='SQL Alerts', @account_name='SQL Alerts', @sequence_number=1;

EXEC msdb.dbo.sp_send_dbmail @profile_name='SQL Alerts', @recipients='dba-team@company.com',
    @subject='[SQL Server] FAILED: Nightly ETL', @body=@htmlBody, @body_format='HTML';
```

## Configuration

| Job step setting | Why |
|---|---|
| `@on_fail_action = 1` on the notification step | Email fires even when a prior step failed — otherwise Agent stops and it never sends |
| Send success notifications for critical jobs too | Absence of an expected success email is your early warning the pipeline itself broke |
| `sysmail_faileditems` | Check this when mail stops arriving — usually SMTP auth/config |

## Example Usage

```sql
-- First 60 seconds of any "database is slow" ticket
EXEC sp_WhoIsActive @find_block_leaders = 1, @get_plans = 1;   -- install this on every instance

-- Top waits since restart, filtered to remove benign/idle noise (Paul Randal's standard filter)
SELECT TOP 15 wait_type, wait_time_ms,
       100.0 * wait_time_ms / SUM(wait_time_ms) OVER () AS pct
FROM sys.dm_os_wait_stats
WHERE waiting_tasks_count > 0
  AND wait_type NOT IN ('SLEEP_TASK','LAZYWRITER_SLEEP','BROKER_TASK_STOP','XE_TIMER_EVENT','CXCONSUMER')
ORDER BY wait_time_ms DESC;
```

| Top wait | Points at |
|---|---|
| `PAGEIOLATCH_*` / `WRITELOG` | Disk I/O (or memory pressure forcing re-reads) |
| `RESOURCE_SEMAPHORE` | Memory grant starvation |
| `LCK_M_*` | Blocking — chase the lead blocker |
| `CXPACKET` | Parallelism — usually a missing index turning a seek into a parallel scan |
| `ASYNC_NETWORK_IO` | The client app, not SQL |

## See Also

- [query-store](../concepts/query-store.md)
- [reference/dba-field-guide](../reference/dba-field-guide.md) — full DMV/wait-type reference
- [reference/troubleshooting-cheat-sheet](../reference/troubleshooting-cheat-sheet.md) — incident quick card
