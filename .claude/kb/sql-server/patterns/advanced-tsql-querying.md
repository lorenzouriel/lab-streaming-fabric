# Advanced T-SQL Querying

> **Purpose**: JSON extraction/construction, regex, fuzzy matching, and graph MATCH traversal — the SQL-Server-specific advanced query toolkit. Window functions/CTEs/dedup are NOT covered here — see `../sql-patterns/`
> **MCP Validated**: 2026-09-16

## When to Use

- Extracting or building JSON payloads directly in T-SQL (API integration, RAG context assembly)
- Cleansing/validating strings beyond what `LIKE`/`PATINDEX` can express
- Deduplicating near-matches (name variants) or traversing a genuinely network-shaped relationship (graph)

## Implementation

```sql
-- JSON extraction: JSON_VALUE for scalars, JSON_QUERY for objects/arrays (wrong one silently returns NULL)
SELECT JSON_VALUE(attributes, '$.color') AS color, JSON_QUERY(attributes, '$.dimensions') AS dimensions
FROM dbo.Products WHERE JSON_VALUE(attributes, '$.category') = 'Electronics';

-- Index a hot JSON path via a persisted computed column — parse once, on write, not per query
ALTER TABLE dbo.Products ADD product_category AS JSON_VALUE(attributes, '$.category') PERSISTED;
CREATE INDEX IX_Products_Category ON dbo.Products(product_category);

-- Construction: JSON_OBJECT/JSON_ARRAY (2022+) or FOR JSON PATH (all versions)
SELECT o.order_id, JSON_OBJECT('orderId': o.order_id, 'orderDate': o.order_date) AS order_json
FROM dbo.Orders AS o;

-- Regex (SQL Server 2025+ / Fabric): pre-filter with sargable predicates first — regex can't use an index
SELECT customer_id, REGEXP_REPLACE(REGEXP_REPLACE(phone, '[^\d]', ''), '^(\d{3})(\d{3})(\d{4})$', '($1) $2-$3') AS phone
FROM dbo.Customers WHERE phone IS NOT NULL AND REGEXP_LIKE(phone, '\d{10}');

-- Fuzzy matching: same rule — shrink the candidate set with indexed predicates, THEN fuzzy-match
SELECT customer_id, first_name, last_name FROM dbo.Customers
WHERE first_name LIKE 'Jo%' AND last_name LIKE 'Sm%'
  AND JARO_WINKLER_DISTANCE('John', first_name) > 0.85;   -- tuned for names; EDIT_DISTANCE for general strings

-- Graph: MATCH for multi-hop traversal (fixed-depth relations should stay plain FK + JOIN)
SELECT DISTINCT p1.name, p3.name AS friend_of_friend
FROM dbo.Person p1, dbo.Knows k1, dbo.Person p2, dbo.Knows k2, dbo.Person p3
WHERE MATCH(p1-(k1)->p2-(k2)->p3) AND p1.name = 'Ana Costa';
```

## Configuration

| Feature | Function | Version |
|---|---|---|
| JSON scalar / object extraction | `JSON_VALUE` / `JSON_QUERY` | All supported |
| JSON construction | `JSON_OBJECT`/`JSON_ARRAY`/`JSON_ARRAYAGG` | 2022+ (else `FOR JSON PATH`) |
| Regex | `REGEXP_LIKE/REPLACE/SUBSTR/COUNT`, ECMAScript syntax | SQL Server 2025 / Fabric |
| Fuzzy match | `EDIT_DISTANCE`, `EDIT_DISTANCE_SIMILARITY`, `JARO_WINKLER_DISTANCE` | SQL Server 2025 / Fabric |
| Graph traversal | `MATCH` / `SHORTEST_PATH` (`{1,3}` quantifiers) | `MATCH` 2017+, `SHORTEST_PATH` 2019+ |
| Set-based series | `GENERATE_SERIES(start, stop, step)` | 2022+ / Azure SQL / Fabric — beats a recursive CTE for date/number sequences |

## Example Usage

```sql
-- Validate before parsing
SELECT ISJSON(payload), JSON_PATH_EXISTS(payload, '$.customer.id');

-- Common graph bug: MATCH returns zero rows silently if the arrow direction doesn't match
-- how the edge was inserted ($from_id -> $to_id) — check direction before assuming a bug elsewhere
```

## See Also

- [native-search-and-ai-features](../concepts/native-search-and-ai-features.md)
- [rag-in-tsql](rag-in-tsql.md)
- Window functions, CTEs, dedup, pivot/gap-island patterns: `../sql-patterns/`
