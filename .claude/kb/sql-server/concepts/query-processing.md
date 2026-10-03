# Query Processing

> **Purpose**: How SQL Server parses, optimizes, caches, and parallelizes a query after it arrives — plan caching, parameterization, parameter sniffing, and MAXDOP
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-16

## Overview

After the Query Optimizer produces an execution plan, SQL Server stores it in the **plan cache** and reuses it on subsequent calls if the query text and connection `SET` options match. Stored procedures are the most reliable vehicle for plan reuse. Parameter sniffing, parameterization, and parallel execution are internal behaviors that explain most "why is this fast sometimes and slow other times" reports.

## The Concept

```sql
-- Parameter Sensitive Plan (PSP) mitigation options, in order of bluntness
CREATE PROCEDURE dbo.usp_GetCustomerOrders @customer_id INT
AS
    SELECT order_id, order_date, status
    FROM dbo.Orders
    WHERE customer_id = @customer_id
    OPTION (RECOMPILE);                          -- fresh plan every call, CPU cost

-- OPTION (OPTIMIZE FOR (@customer_id UNKNOWN))  -- compile for average density instead

-- Force parameterization for OLTP apps sending many near-identical ad-hoc queries
ALTER DATABASE SalesDB SET PARAMETERIZATION FORCED;

-- MAXDOP: cap threads a single parallel operator can use
SELECT customer_id, COUNT(*) AS order_count
FROM dbo.Orders GROUP BY customer_id
OPTION (MAXDOP 4);
```

**Parameter sniffing**: the optimizer compiles a stored procedure's plan using the *first* parameter values it sees, then reuses that plan regardless of how differently-shaped later calls are — fine when data is uniform, catastrophic when it's skewed. SQL Server 2022+ ships **Parameter Sensitive Plan (PSP) optimization**, which can cache multiple plans (low- vs. high-cardinality) for the same query automatically.

**Recompilation** is statement-level (since SQL Server 2005) and triggers on schema changes, ~20% row modification, statistics updates, or `sp_recompile`.

**Parallelism**: the optimizer parallelizes based on estimated cost. Exchange operators (Distribute/Repartition/Gather Streams) move data between threads. Things that force serial execution: scalar UDFs (without inlining, pre-2019), multi-statement TVFs, dynamic cursors, recursive CTEs, remote linked-server queries.

## Quick Reference

| Mechanism | Trigger | Fix |
|-----------|---------|-----|
| Plan cache miss | Query text or SET options differ, unqualified object names | Fully qualify objects, use `sp_executesql` |
| Parameter sniffing hurting perf | Skewed data + cached plan from first call | `OPTION (RECOMPILE)`, `OPTIMIZE FOR`, or rely on PSP (2022+) |
| Plan cache bloat | Ad-hoc SQL with literals, no parameterization | `PARAMETERIZATION FORCED`, `sp_executesql`, `optimize for ad hoc workloads` |
| Forced serial execution | Scalar UDF, MSTVF, recursive CTE in plan | Rewrite scalar UDF as inline TVF |

## Common Mistakes

### Wrong

```sql
SELECT * FROM dbo.Products WHERE category = 'Electronics';
SELECT * FROM dbo.Products WHERE category = 'Clothing';
-- each literal compiles a separate plan -> plan cache bloat
```

### Correct

```sql
EXEC sp_executesql
    N'SELECT * FROM dbo.Products WHERE category = @category',
    N'@category VARCHAR(100)', @category = 'Electronics';
-- one plan, many executions, and protects against injection
```

## Related

- [engine-architecture](engine-architecture.md)
- [query-store](query-store.md)
- [query-optimization-techniques](../patterns/query-optimization-techniques.md)
