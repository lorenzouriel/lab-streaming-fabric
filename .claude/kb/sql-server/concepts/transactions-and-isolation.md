# Transactions and Isolation

> **Purpose**: COMMIT/ROLLBACK mechanics, Write-Ahead Logging, and how SQL Server's isolation levels trade off consistency anomalies against blocking
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

A transaction groups statements into one atomic unit — all succeed or all roll back. Durability comes from **Write-Ahead Logging (WAL)**: every change is written to the transaction log (`.ldf`) before the data file (`.mdf`), so a crash after COMMIT replays the log, and a crash before COMMIT rolls back the partial work. Isolation level chooses which read anomalies (dirty, nonrepeatable, phantom reads) are permitted in exchange for less blocking.

## The Concept

```sql
BEGIN TRANSACTION;
BEGIN TRY
    UPDATE dbo.Customers SET credit_balance = credit_balance - 100 WHERE customer_id = 1;
    UPDATE dbo.Customers SET credit_balance = credit_balance + 100 WHERE customer_id = 2;
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;  -- re-raise the original error to the caller
END CATCH;

-- Savepoints: partial rollback within a still-open transaction
BEGIN TRANSACTION;
INSERT INTO dbo.Orders (customer_id, status) VALUES (42, 'Pending');
SAVE TRANSACTION order_created;
-- ... risky follow-up work; ROLLBACK TRANSACTION order_created; on failure, then COMMIT
```

Isolation levels (SQL Server-specific row-versioning variants included):

| Level | Dirty read | Nonrepeatable read | Phantom read | Blocks readers/writers |
|-------|:---:|:---:|:---:|:---:|
| READ UNCOMMITTED (`NOLOCK`) | Yes | Yes | Yes | No |
| READ COMMITTED (default) | No | Yes | Yes | Yes |
| REPEATABLE READ | No | No | Yes | Yes |
| SERIALIZABLE | No | No | No | Yes (range locks) |
| READ COMMITTED SNAPSHOT (RCSI) | No | Yes | Yes | No |
| SNAPSHOT | No | No | No | No (raises update-conflict 3960 instead) |

```sql
ALTER DATABASE CURRENT SET READ_COMMITTED_SNAPSHOT ON;  -- RCSI: READ COMMITTED via row versions
ALTER DATABASE CURRENT SET ALLOW_SNAPSHOT_ISOLATION ON; -- enables explicit SNAPSHOT
```

**Azure SQL defaults differ from on-prem**: RCSI is on by default (readers never block writers out of the box), and **optimized locking** (also default-on) reduces writer-writer contention by releasing row/page locks as each row is qualified instead of holding them to commit. On-prem SQL Server requires opting into both explicitly.

## Quick Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| Readers blocked by writers | Default READ COMMITTED, no RCSI | Enable RCSI (cost: tempdb version store) |
| "Fast usually, slow occasionally" oversell bug | Read-then-write race | Atomic `UPDATE ... WHERE qty > 0` guard, not a heavier isolation level |
| Long transaction holding locks | External call / user wait inside `BEGIN TRAN` | Validate and fetch data before `BEGIN TRAN`; keep only DML inside |
| Update conflict error 3960 | SNAPSHOT isolation, concurrent write to same row | Handle the error in app code; it's SNAPSHOT's designed behavior, not a bug |

## Common Mistakes

### Wrong

```sql
BEGIN TRANSACTION;
INSERT INTO dbo.AuditLog (event) VALUES ('Processing started');
EXEC dbo.usp_CallExternalService;  -- 3-second API call holds locks the whole time
COMMIT;
```

### Correct

Validate and gather all inputs before `BEGIN TRANSACTION`; never put API calls, user prompts, or waits inside an open transaction.

## Related

- [engine-architecture](engine-architecture.md)
- [error-handling](../patterns/error-handling.md)
- [azure-sql-tuning](../patterns/azure-sql-tuning.md)
