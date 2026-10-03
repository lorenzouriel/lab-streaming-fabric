# Join Algorithms

> **Purpose**: Recognize which physical join algorithm SQL Server chose (Nested Loops / Merge / Hash), why, and how to influence or fix it
> **MCP Validated**: 2026-09-16

## When to Use

- Reading an execution plan and deciding whether the chosen join algorithm is appropriate for the data volume
- A query that was fast in dev (small tables) is slow in production (millions of rows) with the same JOIN syntax
- Diagnosing a hash spill or an unindexed nested-loop scan

## Implementation

```sql
-- Nested Loops: outer input small + inner input indexed on join key -> fast (O(log n) seek per row)
SELECT c.customer_id, o.order_id
FROM dbo.Customers AS c
JOIN dbo.Orders AS o ON c.customer_id = o.customer_id
WHERE c.email = 'ana.costa@email.com';   -- 1 outer row -> seek into Orders index

-- Merge Join: both inputs already sorted on the join key (clustered index or ORDER BY) -> O(n+m)
SELECT c.customer_id, COUNT(o.order_id) AS order_count
FROM dbo.Customers AS c
JOIN dbo.Orders AS o ON c.customer_id = o.customer_id   -- both clustered on customer_id
GROUP BY c.customer_id;

-- Hash Join: large unsorted inputs, no useful index -> builds hash table on smaller side
SELECT p.category, SUM(od.quantity * od.unit_price) AS category_revenue
FROM dbo.OrderDetails AS od
JOIN dbo.Products AS p ON od.product_id = p.product_id
GROUP BY p.category;   -- watch for a "hash spill to tempdb" warning if the build side is bigger than expected

-- Force an algorithm for diagnosis only — never leave a hint in production without a strong reason
SELECT ... FROM dbo.Customers c JOIN dbo.Orders o ON c.customer_id = o.customer_id
OPTION (LOOP JOIN);   -- or MERGE JOIN / HASH JOIN
```

## Configuration

| Algorithm | Best case | Worst case | Memory | Parallelism |
|-----------|-----------|------------|--------|------------|
| Nested Loops | Small outer + indexed inner | Both sides large, no index | Low | Limited |
| Merge Join | Both inputs pre-sorted, large | Unsorted inputs (adds a Sort) | Medium | Good |
| Hash Join | Large unsorted, no indexes | Hash spill to tempdb | High | Good |

## Example Usage

```sql
-- What to do with each plan signal
-- Nested Loops on large inputs         -> add an index to make the inner lookup a seek
-- Merge Join preceded by an expensive Sort -> add an ordered index so the sort is pre-baked
-- Hash Match with a spill warning (orange icon) -> check statistics / add an index on the build side
SELECT TOP 10
    qs.total_worker_time / qs.execution_count AS avg_cpu_ms,
    qp.query_plan
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) AS qp
ORDER BY qs.total_worker_time DESC;
```

## See Also

- [query-optimization-techniques](query-optimization-techniques.md)
- [indexing-internals](../concepts/indexing-internals.md)
- [query-processing](../concepts/query-processing.md)
