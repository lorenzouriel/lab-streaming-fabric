# Query Optimization Techniques

> **Purpose**: The actionable T-SQL rewrite patterns that fix specific execution-plan problems — sargability, existence checks, predicate ordering, NOLOCK/RCSI tradeoffs
> **MCP Validated**: 2026-09-16

## When to Use

- The execution plan shows a scan where a seek should be possible
- A query is "slow" and you need a repeatable diagnostic-then-fix loop, not a guess
- Reviewing T-SQL for SARGability and other SQL-Server-specific optimizer behavior (not window functions/CTEs/dedup — see `../sql-patterns/` for those)

## Implementation

Always start with the execution plan (Ctrl+M in SSMS) before applying any of these — each fixes a specific, visible problem.

```sql
-- 1. Non-sargable filters kill index use — never wrap the filtered column in a function
-- Wrong:
WHERE YEAR(order_date) = 2024
WHERE LOWER(email) = 'ana@email.com'
-- Right: range condition; consistent-case storage
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'
WHERE email = 'ana@email.com'   -- store lowercase, or use case-insensitive collation

-- 2. EXISTS beats COUNT(*) for existence checks — stops at first match
IF EXISTS (SELECT 1 FROM dbo.Orders WHERE customer_id = @customer_id)

-- 3. WHERE eliminates rows before aggregation; HAVING only filters aggregated values
SELECT customer_id, SUM(od.quantity * od.unit_price) AS total_value
FROM dbo.Orders AS o
JOIN dbo.OrderDetails AS od ON o.order_id = od.order_id
WHERE o.order_date >= '2024-01-01' AND o.status = 'Completed'   -- eliminate early
GROUP BY customer_id
HAVING SUM(od.quantity * od.unit_price) > 500;                   -- filter late

-- 4. IN over chained OR on the same column — optimizer evaluates it as one pass
WHERE status IN ('Pending', 'Processing', 'Shipped')

-- 5. DISTINCT is often masking a bad join, not deduplicating legitimately
-- Symptom:
SELECT DISTINCT c.customer_id FROM dbo.Customers c JOIN dbo.Orders o ON c.customer_id = o.customer_id;
-- Fix the root cause instead:
SELECT c.customer_id FROM dbo.Customers c
WHERE EXISTS (SELECT 1 FROM dbo.Orders WHERE customer_id = c.customer_id);

-- 6. Never SELECT * — fetches every column, defeats covering indexes
SELECT order_id, customer_id, order_date FROM dbo.Orders WHERE status = 'Pending';

-- 7. Index columns used in WHERE / JOIN / ORDER BY; put the equality/selective column first
CREATE NONCLUSTERED INDEX ix_Orders_status_date
    ON dbo.Orders (status, order_date DESC) INCLUDE (customer_id);

-- 8. SELECT TOP + an indexed ORDER BY beats a full scan for "recent N" queries
SELECT TOP 100 order_id, customer_id, order_date FROM dbo.Orders ORDER BY order_date DESC;

-- 9. Stored procedures cache execution plans; ad-hoc literals compile a plan every time
CREATE PROCEDURE dbo.usp_GetCustomerOrderHistory @customer_id INT AS
    SELECT order_id, order_date FROM dbo.Orders WHERE customer_id = @customer_id;

-- 10. NOLOCK trades consistency for speed — know what you're accepting
SELECT order_id, status FROM dbo.Orders WITH (NOLOCK) WHERE customer_id = @customer_id;
-- prefer READ_COMMITTED_SNAPSHOT (RCSI) for reduced locking without dirty reads
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `READ_COMMITTED_SNAPSHOT` | OFF (on-prem) / ON (Azure SQL) | Row-versioned reads instead of NOLOCK's dirty reads |
| Execution plan cost threshold checks | — | Look for Table/Clustered Index Scan, Key Lookup, Missing Index hint, high Cost % |

## Example Usage

```sql
-- Diagnostic-first workflow
SET STATISTICS XML ON;  -- or Ctrl+M "Include Actual Execution Plan" in SSMS
-- run the query, inspect: scan vs seek, estimate-vs-actual row mismatch,
-- key lookups (fix with INCLUDE), implicit conversions (fix the type mismatch)
SET STATISTICS XML OFF;
```

## See Also

- [indexing-internals](../concepts/indexing-internals.md)
- [join-algorithms](join-algorithms.md)
- [transactions-and-isolation](../concepts/transactions-and-isolation.md) — RCSI/optimized locking
- Window functions, CTEs, dedup, pivot/gap-island patterns live in `../sql-patterns/`, not here
