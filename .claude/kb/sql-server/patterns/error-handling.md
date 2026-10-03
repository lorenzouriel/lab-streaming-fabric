# Error Handling

> **Purpose**: TRY/CATCH with THROW as the standard T-SQL error-handling pattern, RAISERROR for the cases it still fits, and trigger-specific error semantics
> **MCP Validated**: 2026-09-16

## When to Use

- Any multi-statement stored procedure or transaction that needs atomicity
- Re-raising an error to the caller without losing the original error number/message/state
- A trigger that must reject an operation (`INSTEAD OF`) rather than just log after the fact

## Implementation

```sql
-- Standard pattern: BEGIN TRAN -> TRY -> COMMIT -> CATCH -> ROLLBACK -> THROW
CREATE PROCEDURE dbo.usp_CreateOrder
    @customer_id INT, @product_id INT, @quantity INT
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.Customers WHERE customer_id = @customer_id)
        THROW 50001, 'Customer not found.', 1;     -- validate before BEGIN TRANSACTION

    BEGIN TRANSACTION;
    BEGIN TRY
        DECLARE @order_id INT;
        INSERT INTO dbo.Orders (customer_id, order_date, status)
        VALUES (@customer_id, GETDATE(), 'Pending');
        SET @order_id = SCOPE_IDENTITY();

        INSERT INTO dbo.OrderDetails (order_id, product_id, quantity)
        VALUES (@order_id, @product_id, @quantity);

        COMMIT;
        SELECT @order_id AS new_order_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;   -- re-raises the ORIGINAL error: number, message, state, severity intact
    END CATCH;
END;

-- THROW always severity 16, always stops execution — no forgotten RETURN needed
IF @new_price < 0
    THROW 50002, 'Price cannot be negative.', 1;

-- RAISERROR still useful for informational (non-stopping) messages and legacy code
RAISERROR('Price cannot be negative. Received: %f', 16, 1, @new_price);
RETURN;   -- required: severities below 20 don't auto-stop execution

-- Trigger error semantics: an unhandled error rolls back the WHOLE triggering statement
CREATE TRIGGER trg_PreventCompletedOrderDelete ON dbo.Orders INSTEAD OF DELETE AS
BEGIN
    IF EXISTS (SELECT 1 FROM deleted WHERE status = 'Completed')
        THROW 50004, 'Completed orders cannot be deleted.', 1;
    DELETE o FROM dbo.Orders AS o JOIN deleted AS d ON o.order_id = d.order_id;
END;
```

## Configuration

| Aspect | `THROW` | `RAISERROR` |
|--------|---------|-------------|
| Stops execution | Always | Only severity 11+ (and needs explicit `RETURN` below 20) |
| Severity | Fixed at 16 | Configurable 0–25 |
| Re-raise original error | `THROW;` (no args) in CATCH | Must manually rebuild from `ERROR_*()` functions |
| Error number range | 50000+ | Any |

## Example Usage

```sql
-- Doomed-transaction check before a careful rollback
IF XACT_STATE() = -1   -- -1 = doomed, rollback-only; 1 = committable; 0 = no transaction
    ROLLBACK;

-- Never do this: swallowing the error hides a failed write from the caller entirely
BEGIN TRY
    INSERT INTO dbo.Orders (customer_id, status) VALUES (@customer_id, 'Pending');
END TRY
BEGIN CATCH
    ROLLBACK;   -- no THROW here = silent data inconsistency
END CATCH;
```

## See Also

- [transactions-and-isolation](../concepts/transactions-and-isolation.md)
- [routine-selection](routine-selection.md) — triggers vs. procedures decision
