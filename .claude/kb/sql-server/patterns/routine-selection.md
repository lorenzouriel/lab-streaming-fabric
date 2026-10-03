# Routine Selection: Views vs. Procedures vs. Functions vs. Triggers

> **Purpose**: Decision framework for choosing among the four T-SQL routine types by optimizer visibility and transaction-control needs
> **MCP Validated**: 2026-09-16

## When to Use

- Deciding how to encapsulate reused SQL logic: composable into a query, or standalone with its own transaction?
- A schema review finds business logic duplicated across application code or reports
- Choosing between an `AFTER` and `INSTEAD OF` trigger, or whether a trigger is the right tool at all

## Implementation

```sql
-- View: saved SELECT, no parameters, security/readability boundary
CREATE VIEW dbo.vw_CustomerOrderSummary AS
SELECT c.customer_id, c.first_name, COUNT(o.order_id) AS order_count
FROM dbo.Customers c JOIN dbo.Orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name;

-- Stored procedure: parameters, multi-statement, owns its own transaction
CREATE PROCEDURE dbo.usp_ProcessOrder @order_id INT AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;
    BEGIN TRY
        UPDATE dbo.Products SET stock = stock - 1 WHERE product_id = (
            SELECT product_id FROM dbo.OrderDetails WHERE order_id = @order_id);
        UPDATE dbo.Orders SET status = 'Processed' WHERE order_id = @order_id;
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK; THROW;
    END CATCH;
END;

-- Inline table-valued function: optimizes like a parameterized view
CREATE FUNCTION dbo.fn_CustomerOrders(@customer_id INT, @start DATE, @end DATE)
RETURNS TABLE AS RETURN (
    SELECT order_id, order_date FROM dbo.Orders
    WHERE customer_id = @customer_id AND order_date BETWEEN @start AND @end
);
-- SELECT * FROM dbo.fn_CustomerOrders(42, '2026-01-01', '2026-06-30');  -- drops into a query

-- AFTER trigger: validation/audit AFTER the write already landed
CREATE TRIGGER trg_LogPriceChanges ON dbo.Products AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(unit_price)
        INSERT INTO dbo.PriceHistory (product_id, old_price, new_price, changed_at)
        SELECT d.product_id, d.unit_price, i.unit_price, GETDATE()
        FROM deleted d JOIN inserted i ON d.product_id = i.product_id
        WHERE d.unit_price <> i.unit_price;
END;
```

## Configuration

| Capability | View | Procedure | Function | Trigger |
|---|---|---|---|---|
| Accept parameters | No | Yes | Yes | No |
| Modify data | Limited | Yes | No | Yes |
| Use in SELECT/JOIN | Yes | No | Yes (TVFs) | No |
| Transaction control | No | Yes | No | Yes |
| Automatic execution | No | No | No | Yes |
| Plan caching | No | Yes | Varies | Yes |

## Example Usage

Decision framework — ask two questions: **can the optimizer see inside this object, and does it need its own transaction control?**

- Need it inside `SELECT`/`WHERE`/`JOIN` → function (inline TVF if at all possible) or view
- Need multi-statement writes across tables with commit/rollback → stored procedure (the default for "changes data in more than one place")
- Need it to fire automatically on every write, no matter who writes → trigger, but only because "automatic" is the actual requirement — a procedure called explicitly is easier to test, read, and debug
- `AFTER`/`FOR` trigger → validate or cascade post-write; `INSTEAD OF` trigger → replace the statement entirely (make a view writable, or reject before commit)

`inserted`/`deleted` are **sets**, not single rows — a trigger fires once per statement; write trigger logic assuming a batch, not one row. Keep triggers minimal: they execute inside the triggering transaction, so slow trigger code adds latency to every write; offload heavy work to a queue table + async job.

## See Also

- [error-handling](error-handling.md)
- [advanced-tsql-querying](advanced-tsql-querying.md)
- CTEs/subqueries/window functions live in `../sql-patterns/`, not here
